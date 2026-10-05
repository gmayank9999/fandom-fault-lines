import os
import re
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, anonymize

logger = setup_logger("preprocess")


def clean_text(text):
    text = str(text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)         # reddit gif/image/emote embeds: ![gif](giphy|abc)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)      # markdown links: keep the link text only
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"&amp;#x200B;|&amp;|&gt;|&lt;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


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
    lookup = lookup[~lookup["author"].isin(config.BOT_ACCOUNTS)].copy()
    lookup["author"] = lookup["author"].apply(anonymize)
    lookup[["kind", "id", "author"]].to_csv(config.CLEAN_PARENTS_PATH, index=False)
    logger.info(f"Author lookup for network: {len(lookup)} ids ({len(parents)} fetched parents)")

    # ---- 1. Drop bot/deleted authors ----
    posts = posts[~posts["author"].isin(config.BOT_ACCOUNTS)]
    comments = comments[~comments["author"].isin(config.BOT_ACCOUNTS)]

    # ---- 2. Drop empty/placeholder comment bodies ----
    comments = comments[comments["body"].notna()]
    comments = comments[~comments["body"].astype(str).isin(["[removed]", "[deleted]", ""])]

    # ---- 3. Drop exact duplicates (can happen at pagination page boundaries) ----
    posts = posts.drop_duplicates(subset="id")
    comments = comments.drop_duplicates(subset="id")

    # ---- 4. Clean comment text ----
    comments["body_clean"] = comments["body"].apply(clean_text)
    comments = comments[comments["body_clean"].str.len() >= config.MIN_COMMENT_LENGTH]
    comments = comments[comments["body_clean"].str.contains(r"[A-Za-z]", regex=True)]   # drop emoji/symbol-only

    # ---- 5. Anonymize usernames (deterministic, one-way) ----
    posts["author"] = posts["author"].apply(anonymize)
    comments["author"] = comments["author"].apply(anonymize)

    posts.to_csv(config.CLEAN_POSTS_PATH, index=False)
    comments.to_csv(config.CLEAN_COMMENTS_PATH, index=False)

    logger.info(f"Clean: {len(posts)} posts, {len(comments)} comments")
    logger.info(f"Unique anonymized comment authors: {comments['author'].nunique()}")
    for sub in config.SUBREDDITS:
        logger.info(f"  r/{sub}: {len(posts[posts['subreddit']==sub])} posts, "
                      f"{len(comments[comments['subreddit']==sub])} comments")


if __name__ == "__main__":
    main()
