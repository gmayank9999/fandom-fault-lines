import os
import sys
import pandas as pd
from scipy.stats import mannwhitneyu

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("statistical_tests")


def run_mannwhitney(group_a, group_b, label):
    """Mann-Whitney U plus an effect size. effect_size_r is the rank-biserial correlation
    (-1..+1): +0.3 means a random comment from group A is more positive than one from group B
    about 65% of the time. |r| < 0.1 is negligible, ~0.1 small, ~0.3 medium, ~0.5 large."""
    if len(group_a) < 5 or len(group_b) < 5:
        return {"comparison": label, "n_a": len(group_a), "n_b": len(group_b),
                "median_a": None, "median_b": None, "statistic": None, "p_value": None,
                "effect_size_r": None, "note": "sample too small"}
    stat, p = mannwhitneyu(group_a, group_b, alternative="two-sided")
    effect = 2 * stat / (len(group_a) * len(group_b)) - 1
    return {"comparison": label, "n_a": len(group_a), "n_b": len(group_b),
            "median_a": float(group_a.median()), "median_b": float(group_b.median()),
            "statistic": stat, "p_value": p, "effect_size_r": effect, "note": ""}


def holm_correct(p_values):
    """Holm-Bonferroni adjusted p-values (controls the family-wise error rate across all the
    comparisons in this table). None entries are skipped and stay None."""
    idx = [i for i, p in enumerate(p_values) if p is not None and p == p]
    order = sorted(idx, key=lambda i: p_values[i])
    adjusted = [None] * len(p_values)
    m = len(order)
    running_max = 0.0
    for rank, i in enumerate(order):
        running_max = max(running_max, min(1.0, (m - rank) * p_values[i]))
        adjusted[i] = running_max
    return adjusted


def run_family(comments, label_suffix=""):
    sub_a, sub_b = config.SUBREDDITS
    rows = []
    sent = "sentiment_compound"
    a = comments[comments["subreddit"] == sub_a]
    b = comments[comments["subreddit"] == sub_b]

    rows.append(run_mannwhitney(a[sent], b[sent], f"overall sentiment: r/{sub_a} vs r/{sub_b}{label_suffix}"))
    for sub, df in [(sub_a, a), (sub_b, b)]:
        rows.append(run_mannwhitney(df[df["talk_target"] == "self_talk"][sent],
                                    df[df["talk_target"] == "rival_talk"][sent],
                                    f"self-talk vs rival-talk within r/{sub}{label_suffix}"))
    rows.append(run_mannwhitney(a[a["talk_target"] == "rival_talk"][sent],
                                b[b["talk_target"] == "rival_talk"][sent],
                                f"rival-talk: r/{sub_a} (about {sub_b}) vs r/{sub_b} (about {sub_a}){label_suffix}"))
    rows.append(run_mannwhitney(a[a["talk_target"] == "self_talk"][sent],
                                b[b["talk_target"] == "self_talk"][sent],
                                f"self-talk: r/{sub_a} vs r/{sub_b}{label_suffix}"))
    return rows


def main():
    comments = pd.read_csv(config.SENTIMENT_PATH)
    if len(config.SUBREDDITS) != 2:
        logger.warning("Expected exactly 2 subreddits; skipping statistical tests.")
        return

    results = run_family(comments)
    # Robustness check: VADER gives exactly 0 when it finds no sentiment words at all, which
    # is "no signal" rather than "neutral". Re-run the same tests without those comments.
    results += run_family(comments[comments["sentiment_compound"] != 0], " [excluding score==0]")

    df = pd.DataFrame(results)
    df["p_holm"] = holm_correct([None if pd.isna(p) else p for p in df["p_value"]])
    df["significant_at_0.05"] = df["p_value"].apply(lambda p: None if pd.isna(p) else bool(p < 0.05))
    df["significant_holm_0.05"] = df["p_holm"].apply(lambda p: None if pd.isna(p) else bool(p < 0.05))
    df.to_csv(config.STATISTICAL_TESTS_PATH, index=False)
    logger.info(f"\n{df.to_string(index=False)}")


if __name__ == "__main__":
    main()
