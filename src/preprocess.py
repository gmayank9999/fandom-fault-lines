import os
import re
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, anonymize, anonymize_id, anonymize_fullname

logger = setup_logger("preprocess")


def clean_text(text):
    text = str(text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)         # reddit gif/image/emote embeds: ![gif](giphy|abc)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # markdown links: keep the link text only
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"&amp;#x200B;|&amp;|&gt;|&lt;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def basic_clean(comments):
    """Bot/deleted removal, empty-body removal, de-duplication, text cleaning, length and letter filters.
    One function so that the main window and any replication window are cleaned identically."""
    comments = comments[comments["author"].notna() &
                        ~comments["author"].astype(str).str.lower().isin({s.lower() for s in config.BOT_ACCOUNTS} | {"[removed]", ""})]
    comments = comments[comments["body"].notna()]
    comments = comments[~comments["body"].astype(str).isin(["[removed]", "[deleted]", ""])]
    comments = comments.drop_duplicates(subset="id").copy()
    comments["body_clean"] = comments["body"].apply(clean_text)
    comments = comments[comments["body_clean"].str.len() >= config.MIN_COMMENT_LENGTH]
    return comments[comments["body_clean"].str.contains(r"[A-Za-z]", regex=True)]   # drop emoji/symbol-only


def preprocess_baseline():
    """Non-rival subreddits (authors only) used as the overlap baseline: drop bots, anonymize."""
    if not os.path.exists(config.RAW_BASELINE_PATH):
        return
    b = pd.read_csv(config.RAW_BASELINE_PATH)
    b = b[~b["author"].isin(config.BOT_ACCOUNTS) & b["author"].notna()].drop_duplicates(subset=["subreddit", "id"])
    b["author"] = b["author"].apply(anonymize)
    b = b[b["author"] != "[deleted]"]
    b[["subreddit", "author", "created_utc"]].to_csv(config.CLEAN_BASELINE_PATH, index=False)
    logger.info(f"Baseline authors: {len(b)} comments in {b['subreddit'].nunique()} subreddits")


def main():
    os.makedirs("data/processed", exist_ok=True)

    posts = pd.read_csv(config.RAW_POSTS_PATH)
    comments = pd.read_csv(config.RAW_COMMENTS_PATH)

    logger.info(f"Raw: {len(posts)} posts, {len(comments)} comments")

    # ---- 0. Author lookup for the reply network ----
    # Every id -> author we know about (sampled comments/posts, plus the parents fetched by
    # collect_parents), minus bots and deleted accounts, anonymized. A comment that replies to
    # something NOT in this table cannot become an edge. Only author ids are kept, no text.
    parents = pd.read_csv(config.RAW_PARENTS_PATH) if os.path.exists(config.RAW_PARENTS_PATH) \
        else pd.DataFrame(columns=["kind", "id", "subreddit", "author"])
    lookup = pd.concat([
        comments[["id", "author"]].assign(kind="t1"),
        posts[["id", "author"]].assign(kind="t3"),
        parents[["id", "author", "kind"]],
    ]).drop_duplicates(subset=["kind", "id"])
    lookup = lookup[lookup["author"].notna() & ~lookup["author"].astype(str).str.lower().isin({s.lower() for s in config.BOT_ACCOUNTS})].copy()
    lookup["author"] = lookup["author"].apply(anonymize)
    lookup["id"] = [anonymize_id(i, k) for i, k in zip(lookup["id"], lookup["kind"])]
    lookup[["kind", "id", "author"]].to_csv(config.CLEAN_PARENTS_PATH, index=False)
    logger.info(f"Author lookup for network: {len(lookup)} ids ({len(parents)} fetched parents)")

    # ---- 1-4. Drop bots, empty/placeholder bodies and duplicates; clean text; length/letter filters ----
    posts = posts[posts["author"].notna() & ~posts["author"].astype(str).str.lower().isin({s.lower() for s in config.BOT_ACCOUNTS})].drop_duplicates(subset="id").copy()
    comments = basic_clean(comments)

    # ---- 5. Anonymize usernames (deterministic, one-way) ----
    posts["author"] = posts["author"].apply(anonymize)
    comments["author"] = comments["author"].apply(anonymize)

    # ---- 6. Hash ids and drop permalinks ----
    # A raw Reddit id or permalink resolves to the real author (reddit.com/comments/<id>), so the
    # pseudonymized usernames would be pointless if the ids were published as they are.
    posts["id"] = [anonymize_id(i, "t3") for i in posts["id"]]
    comments["id"] = [anonymize_id(i, "t1") for i in comments["id"]]
    comments["parent_id"] = comments["parent_id"].map(anonymize_fullname)
    comments["link_id"] = comments["link_id"].map(anonymize_fullname)
    posts = posts.drop(columns=[c for c in ("url",) if c in posts.columns])
    comments = comments.drop(columns=["body"])       # body_clean is what every stage uses

    preprocess_baseline()

    posts.to_csv(config.CLEAN_POSTS_PATH, index=False)
    comments.to_csv(config.CLEAN_COMMENTS_PATH, index=False)

    logger.info(f"Clean: {len(posts)} posts, {len(comments)} comments")
    logger.info(f"Unique anonymized comment authors: {comments['author'].nunique()}")
    for sub in config.SUBREDDITS:
        logger.info(f"  r/{sub}: {len(posts[posts['subreddit']==sub])} posts, "
                      f"{len(comments[comments['subreddit']==sub])} comments")


if __name__ == "__main__":
    main()
