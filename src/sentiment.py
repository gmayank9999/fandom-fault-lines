import os
import sys
from functools import lru_cache

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, compile_alias_regex

logger = setup_logger("sentiment")


def categorize(score):
    if score >= 0.05:
        return "positive"
    elif score <= -0.05:
        return "negative"
    return "neutral"


@lru_cache(maxsize=None)
def _alias_regex(subreddit):
    return compile_alias_regex(config.FRANCHISE_ALIASES.get(subreddit, [subreddit.lower()]))


def tag_target(row, sub_a, sub_b):
    """self_talk / rival_talk / both / general, using whole-word alias matching."""
    text = str(row["body_clean"])
    own_sub = row["subreddit"]
    other_sub = sub_b if own_sub == sub_a else sub_a

    mentions_own = bool(_alias_regex(own_sub).search(text))
    mentions_other = bool(_alias_regex(other_sub).search(text))

    if mentions_own and mentions_other:
        return "both"
    elif mentions_other:
        return "rival_talk"
    elif mentions_own:
        return "self_talk"
    return "general"


def main():
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    analyzer = SentimentIntensityAnalyzer()

    comments["sentiment_compound"] = comments["body_clean"].apply(
        lambda t: analyzer.polarity_scores(str(t))["compound"]
    )
    comments["sentiment_label"] = comments["sentiment_compound"].apply(categorize)

    logger.info("Sentiment distribution by subreddit:")
    logger.info(comments.groupby("subreddit")["sentiment_label"].value_counts(normalize=True).to_string())
    logger.info(f"Share of comments with VADER score exactly 0 (no sentiment words found): "
                f"{(comments['sentiment_compound'] == 0).mean():.1%}")

    baseline_mean = comments["sentiment_compound"].mean()
    logger.info(f"Pooled baseline sentiment (both communities combined): {baseline_mean:.3f}")
    for sub in config.SUBREDDITS:
        sub_mean = comments[comments["subreddit"] == sub]["sentiment_compound"].mean()
        logger.info(f"  r/{sub}: {sub_mean:.3f} (vs. baseline {baseline_mean:.3f}, "
                    f"delta {sub_mean - baseline_mean:+.3f})")

    if len(config.SUBREDDITS) == 2:
        sub_a, sub_b = config.SUBREDDITS
        comments["talk_target"] = comments.apply(lambda row: tag_target(row, sub_a, sub_b), axis=1)
        summary = comments.groupby(["subreddit", "talk_target"])["sentiment_compound"].agg(["mean", "std", "count"])
        summary["share_of_subreddit"] = summary["count"] / summary.groupby(level=0)["count"].transform("sum")
        summary.to_csv(config.SENTIMENT_BY_TARGET_PATH)
        logger.info(f"Sentiment by talk target (self/rival/both/general):\n{summary.to_string()}")
    else:
        logger.warning(f"Expected exactly 2 subreddits for the self/rival split; found "
                       f"{len(config.SUBREDDITS)}. Skipping this comparison.")

    comments.to_csv(config.SENTIMENT_PATH, index=False)


if __name__ == "__main__":
    main()
