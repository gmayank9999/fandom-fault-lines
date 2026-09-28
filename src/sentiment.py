import os
import sys
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("sentiment")


def categorize(score):
    if score >= 0.05:
        return "positive"
    elif score <= -0.05:
        return "negative"
    return "neutral"


def tag_target(row, sub_a, sub_b):
    text = str(row["body_clean"]).lower()
    own_sub = row["subreddit"]
    other_sub = sub_b if own_sub == sub_a else sub_a

    own_aliases = config.FRANCHISE_ALIASES.get(own_sub, [own_sub.lower()])
    other_aliases = config.FRANCHISE_ALIASES.get(other_sub, [other_sub.lower()])

    mentions_own = any(alias in text for alias in own_aliases)
    mentions_other = any(alias in text for alias in other_aliases)

    if mentions_own and mentions_other:
        return "both"
    elif mentions_other:
        return "rival_talk"
    elif mentions_own:
        return "self_talk"
    else:
        return "general"


def main():
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    analyzer = SentimentIntensityAnalyzer()

    comments["sentiment_compound"] = comments["body_clean"].apply(
        lambda t: analyzer.polarity_scores(str(t))["compound"]
    )
    comments["sentiment_label"] = comments["sentiment_compound"].apply(categorize)
    comments.to_csv(config.SENTIMENT_PATH, index=False)

    logger.info("Sentiment distribution by subreddit:")
    logger.info(comments.groupby("subreddit")["sentiment_label"].value_counts(normalize=True).to_string())

    # ---- Pooled baseline: gives every per-community number a reference point ----
    baseline_mean = comments["sentiment_compound"].mean()
    logger.info(f"Pooled baseline sentiment (both communities combined): {baseline_mean:.3f}")
    for sub in config.SUBREDDITS:
        sub_mean = comments[comments["subreddit"] == sub]["sentiment_compound"].mean()
        logger.info(f"  r/{sub}: {sub_mean:.3f} (vs. baseline {baseline_mean:.3f}, "
                      f"delta {sub_mean - baseline_mean:+.3f})")

    # ---- Self/rival/both/general target classification (directly answers RQ1) ----
    subs = comments["subreddit"].unique()
    if len(subs) == 2:
        sub_a, sub_b = subs[0], subs[1]
        comments["talk_target"] = comments.apply(lambda row: tag_target(row, sub_a, sub_b), axis=1)
        summary = comments.groupby(["subreddit", "talk_target"])["sentiment_compound"].agg(["mean", "count"])
        summary.to_csv(config.SENTIMENT_BY_TARGET_PATH)
        logger.info(f"Sentiment by talk target (self/rival/both/general):\n{summary.to_string()}")
        comments.to_csv(config.SENTIMENT_PATH, index=False)  # re-save with talk_target column included
    else:
        logger.warning("Expected exactly 2 subreddits for self/rival sentiment split; found "
                          f"{len(subs)}. Skipping this comparison.")


if __name__ == "__main__":
    main()
