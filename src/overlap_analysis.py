import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("overlap_analysis")

DELETED = {"[deleted]"}


def overlap_row(label, users_a, users_b, sub_a, sub_b):
    overlap = users_a & users_b
    union = users_a | users_b
    return {
        "definition": label,
        f"users_{sub_a}": len(users_a), f"users_{sub_b}": len(users_b),
        "users_in_both": len(overlap),
        f"pct_of_{sub_a}": round(100 * len(overlap) / max(len(users_a), 1), 2),
        f"pct_of_{sub_b}": round(100 * len(overlap) / max(len(users_b), 1), 2),
        "jaccard_pct": round(100 * len(overlap) / max(len(union), 1), 2),
    }


MIN_COMMENT_LEVELS = (1, 2, 5)


def baseline_overlap_table(user_counts, rival_pair):
    """Overlap for EVERY pair of subreddits, so the rival pair can be compared with non-rival pairs.
    user_counts: {subreddit: Series(user -> number of comments)}.
    For each pair and activity level (users with >= k comments in BOTH communities' own count):
      pct_of_smaller  share of the smaller community that also appears in the other
      jaccard_pct     overlap / union
      lift            observed overlap / overlap expected if users picked communities independently
                      (|A|*|B| / N, N = all distinct users across all subreddits). Lift removes the
                      effect of subreddit size, which raw percentages do not."""
    import itertools
    subs = list(user_counts)
    rows = []
    for k in MIN_COMMENT_LEVELS:
        sets = {s: set(c[c >= k].index) for s, c in user_counts.items()}
        population = set().union(*sets.values())
        for a, b in itertools.combinations(subs, 2):
            both = sets[a] & sets[b]
            union = sets[a] | sets[b]
            expected = len(sets[a]) * len(sets[b]) / max(len(population), 1)
            rows.append({
                "pair": f"{a} + {b}", "is_rival_pair": {a, b} == set(rival_pair), "min_comments": k,
                f"users_a": len(sets[a]), "users_b": len(sets[b]), "users_in_both": len(both),
                "pct_of_smaller": round(100 * len(both) / max(min(len(sets[a]), len(sets[b])), 1), 2),
                "jaccard_pct": round(100 * len(both) / max(len(union), 1), 2),
                "lift": round(len(both) / expected, 2) if expected else None,
            })
    return pd.DataFrame(rows)


def main():
    if len(config.SUBREDDITS) != 2:
        logger.error(f"Expected exactly 2 subreddits, found {len(config.SUBREDDITS)}. Aborting overlap analysis.")
        return
    sub_a, sub_b = config.SUBREDDITS

    # The sentiment file is clean_comments plus sentiment/talk_target columns, so one read serves both.
    comments = pd.read_csv(config.SENTIMENT_PATH)
    posts = pd.read_csv(config.CLEAN_POSTS_PATH)
    comments = comments[~comments["author"].isin(DELETED)]
    posts = posts[~posts["author"].isin(DELETED)]

    ca = comments[comments["subreddit"] == sub_a]
    cb = comments[comments["subreddit"] == sub_b]
    pa = posts[posts["subreddit"] == sub_a]
    pb = posts[posts["subreddit"] == sub_b]

    commenters_a, commenters_b = set(ca["author"]), set(cb["author"])
    active_a, active_b = commenters_a | set(pa["author"]), commenters_b | set(pb["author"])
    counts_a, counts_b = ca["author"].value_counts(), cb["author"].value_counts()
    repeat_a = set(counts_a[counts_a >= 2].index)
    repeat_b = set(counts_b[counts_b >= 2].index)

    # Three definitions, all reported (never just the most dramatic one).
    summary = pd.DataFrame([
        overlap_row("commenters (>=1 comment)", commenters_a, commenters_b, sub_a, sub_b),
        overlap_row("active users (commented or posted)", active_a, active_b, sub_a, sub_b),
        overlap_row("repeat commenters (>=2 comments in that subreddit)", repeat_a, repeat_b, sub_a, sub_b),
    ])
    summary.to_csv(config.OVERLAP_SUMMARY_PATH, index=False)
    logger.info(f"Overlap summary (same 28-day window for both subreddits):\n{summary.to_string(index=False)}")
    logger.info("Note: counts cover every comment in the window; cross-participation outside the "
                "window is not observed.")

    # ---- Baseline: is the Marvel-DC overlap high or low compared with NON-rival pairs? ----
    if os.path.exists(config.CLEAN_BASELINE_PATH):
        base = pd.read_csv(config.CLEAN_BASELINE_PATH)
        user_counts = {sub_a: ca["author"].value_counts(), sub_b: cb["author"].value_counts()}
        for sub, g in base.groupby("subreddit"):
            user_counts[sub] = g["author"].value_counts()
        table = baseline_overlap_table(user_counts, (sub_a, sub_b))
        table.to_csv(config.OVERLAP_BASELINE_PATH, index=False)
        logger.info("Overlap baseline (same window, all comments, all pairs):\n" + table.to_string(index=False))
    else:
        logger.warning("No baseline authors found (data/processed/baseline_authors.csv); skipping baseline.")

    # ---- Who are the shared users? ----
    shared = commenters_a & commenters_b
    rows = []
    for u in shared:
        da, db = ca[ca["author"] == u], cb[cb["author"] == u]
        rows.append({
            "overlapping_user": u,
            f"comments_{sub_a}": len(da), f"comments_{sub_b}": len(db),
            f"mean_sentiment_{sub_a}": da["sentiment_compound"].mean(),
            f"mean_sentiment_{sub_b}": db["sentiment_compound"].mean(),
            f"rival_talk_comments_{sub_a}": int((da["talk_target"] == "rival_talk").sum()),
            f"rival_talk_comments_{sub_b}": int((db["talk_target"] == "rival_talk").sum()),
        })
    shared_df = pd.DataFrame(rows)
    shared_df.to_csv(config.OVERLAP_PATH, index=False)

    for sub, df in [(sub_a, ca), (sub_b, cb)]:
        is_shared = df["author"].isin(shared)
        logger.info(f"r/{sub}: shared users wrote {is_shared.mean():.1%} of its comments "
                    f"(mean sentiment {df[is_shared]['sentiment_compound'].mean():.3f} vs "
                    f"{df[~is_shared]['sentiment_compound'].mean():.3f} for everyone else; "
                    f"rival-talk share {(df[is_shared]['talk_target'] == 'rival_talk').mean():.1%} vs "
                    f"{(df[~is_shared]['talk_target'] == 'rival_talk').mean():.1%}).")
    if len(shared_df):
        logger.info(f"Shared users: median comments {shared_df[f'comments_{sub_a}'].median():.0f} in r/{sub_a}, "
                    f"{shared_df[f'comments_{sub_b}'].median():.0f} in r/{sub_b}.")


if __name__ == "__main__":
    main()
