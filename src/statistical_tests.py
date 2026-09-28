import os
import sys
import pandas as pd
from scipy.stats import mannwhitneyu

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("statistical_tests")


def run_mannwhitney(group_a, group_b, label):
    if len(group_a) < 5 or len(group_b) < 5:
        return {"comparison": label, "n_a": len(group_a), "n_b": len(group_b),
                "statistic": None, "p_value": None, "significant_at_0.05": None,
                "note": "sample too small"}
    stat, p = mannwhitneyu(group_a, group_b, alternative="two-sided")
    return {"comparison": label, "n_a": len(group_a), "n_b": len(group_b),
            "statistic": stat, "p_value": p, "significant_at_0.05": bool(p < 0.05), "note": ""}


def main():
    comments = pd.read_csv(config.SENTIMENT_PATH)
    subs = comments["subreddit"].unique()
    results = []

    if len(subs) == 2:
        sub_a, sub_b = subs[0], subs[1]

        # Test 1: overall sentiment, community A vs community B
        results.append(run_mannwhitney(
            comments[comments["subreddit"] == sub_a]["sentiment_compound"],
            comments[comments["subreddit"] == sub_b]["sentiment_compound"],
            f"sentiment: r/{sub_a} vs r/{sub_b} (overall)"
        ))

        # Test 2 & 3: within each subreddit, self-talk vs rival-talk sentiment
        for sub in [sub_a, sub_b]:
            sub_data = comments[comments["subreddit"] == sub]
            self_scores = sub_data[sub_data["talk_target"] == "self_talk"]["sentiment_compound"]
            rival_scores = sub_data[sub_data["talk_target"] == "rival_talk"]["sentiment_compound"]
            results.append(run_mannwhitney(self_scores, rival_scores,
                                             f"sentiment: self-talk vs rival-talk within r/{sub}"))

    results_df = pd.DataFrame(results)
    results_df.to_csv(config.STATISTICAL_TESTS_PATH, index=False)
    logger.info(f"\n{results_df.to_string(index=False)}")


if __name__ == "__main__":
    main()
