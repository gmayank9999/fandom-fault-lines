import os
import sys
import numpy as np
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


def cluster_bootstrap_diff(df_a, df_b, value_col, cluster_col, n_boot=2000, seed=42):
    """Difference in mean sentiment (A - B) with a CLUSTER bootstrap: whole clusters (users, or threads)
    are resampled with replacement, not single comments. One user can write dozens of comments in one
    thread; treating those as independent (as Mann-Whitney does) makes differences look more certain
    than they are. Clusters may appear in both groups (a user who wrote self-talk AND rival-talk).
    Returns dict(diff, ci_low, ci_high, p_boot, n_clusters) or None if a group is empty."""
    if len(df_a) == 0 or len(df_b) == 0:
        return None
    key = pd.concat([df_a[cluster_col], df_b[cluster_col]]).astype(str).unique()
    idx = {k: i for i, k in enumerate(key)}
    sa, na, sb, nb = (np.zeros(len(key)) for _ in range(4))
    for df, s_, n_ in ((df_a, sa, na), (df_b, sb, nb)):
        g = df.groupby(df[cluster_col].astype(str))[value_col].agg(["sum", "count"])
        pos = [idx[k] for k in g.index]
        s_[pos], n_[pos] = g["sum"].to_numpy(), g["count"].to_numpy()
    rng = np.random.default_rng(seed)
    # Bounded memory even for tens of thousands of users. A bootstrap draw with
    # no observations in either group is undefined, never a zero mean.
    batches = []
    for start in range(0, n_boot, 32):
        draws = rng.integers(0, len(key), size=(min(32, n_boot - start), len(key)))
        da, db = na[draws].sum(1), nb[draws].sum(1)
        valid = (da > 0) & (db > 0)
        batches.extend((sa[draws].sum(1)[valid] / da[valid] - sb[draws].sum(1)[valid] / db[valid]).tolist())
    diffs = np.asarray(batches)
    if len(diffs) < n_boot * 0.8:
        return None
    obs = sa.sum() / na.sum() - sb.sum() / nb.sum()
    p = 2 * min((1 + (diffs <= 0).sum()) / (len(diffs) + 1),
                (1 + (diffs >= 0).sum()) / (len(diffs) + 1))
    return {"diff": float(obs), "ci_low": float(np.percentile(diffs, 2.5)),
            "ci_high": float(np.percentile(diffs, 97.5)), "p_boot": float(min(p, 1.0)),
            "n_clusters": int(len(key))}


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


COMPARISONS = [
    # (label template, group A selector, group B selector)  selectors: (sub or None, target or None)
    ("overall sentiment: r/{a} vs r/{b}", ("a", None), ("b", None)),
    ("self-talk vs rival-talk within r/{a}", ("a", "self_talk"), ("a", "rival_talk")),
    ("self-talk vs rival-talk within r/{b}", ("b", "self_talk"), ("b", "rival_talk")),
    ("rival-talk: r/{a} (about {b}) vs r/{b} (about {a})", ("a", "rival_talk"), ("b", "rival_talk")),
    ("self-talk: r/{a} vs r/{b}", ("a", "self_talk"), ("b", "self_talk")),
]


def _select(comments, sub_a, sub_b, sel):
    which, target = sel
    df = comments[comments["subreddit"] == (sub_a if which == "a" else sub_b)]
    return df if target is None else df[df["talk_target"] == target]


def run_family(comments, score_col, label_suffix=""):
    sub_a, sub_b = config.SUBREDDITS
    rows = []
    comments = comments[comments[score_col].notna()]          # transformer scores only a subset
    for template, sel_a, sel_b in COMPARISONS:
        if score_col == "sentiment_transformer" and sel_a[1] is None:
            continue    # the scored subset over-represents franchise talk, so "overall" is not meaningful
        ga, gb = _select(comments, sub_a, sub_b, sel_a), _select(comments, sub_a, sub_b, sel_b)
        row = run_mannwhitney(ga[score_col], gb[score_col], template.format(a=sub_a, b=sub_b) + label_suffix)
        row["scorer"] = score_col
        row["mean_a"] = float(ga[score_col].mean()) if len(ga) else None
        row["mean_b"] = float(gb[score_col].mean()) if len(gb) else None
        for cluster, tag in (("author", "user"), ("link_id", "thread")):
            res = cluster_bootstrap_diff(ga, gb, score_col, cluster) if len(ga) >= 5 and len(gb) >= 5 else None
            row[f"diff_{tag}_boot"] = res["diff"] if res else None
            row[f"ci_low_{tag}_boot"] = res["ci_low"] if res else None
            row[f"ci_high_{tag}_boot"] = res["ci_high"] if res else None
            row[f"p_{tag}_boot"] = res["p_boot"] if res else None
        rows.append(row)
    return rows


def main():
    comments = pd.read_csv(config.SENTIMENT_PATH)
    if len(config.SUBREDDITS) != 2:
        logger.warning("Expected exactly 2 subreddits; skipping statistical tests.")
        return

    scorers = [c for c in ("sentiment_compound", "sentiment_adapted", "sentiment_transformer") if c in comments]
    frames = []
    for col in scorers:
        fam = run_family(comments, col)
        # Robustness check: VADER gives exactly 0 when it finds no sentiment words, i.e. "no signal"
        # rather than "neutral". Re-run the same tests without those comments (lexicon scorers only).
        if col != "sentiment_transformer":
            fam += run_family(comments[comments[col] != 0], col, " [excluding score==0]")
        df = pd.DataFrame(fam)
        # Holm correction is applied inside each (scorer, robustness) family of 5 tests.
        df["family"] = [c + (" excl0" if "excluding" in lab else "") for c, lab in zip(df["scorer"], df["comparison"])]
        df["p_holm"] = None
        for fam_name, g in df.groupby("family"):
            adj = holm_correct([None if pd.isna(p) else p for p in g["p_value"]])
            df.loc[g.index, "p_holm"] = adj
            for tag in ("user", "thread"):
                df.loc[g.index, f"p_{tag}_holm"] = holm_correct(g[f"p_{tag}_boot"].tolist())
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)
    df["p_holm"] = pd.to_numeric(df["p_holm"])
    df["significant_at_0.05"] = df["p_value"].apply(lambda p: None if pd.isna(p) else bool(p < 0.05))
    df["significant_holm_0.05"] = df["p_holm"].apply(lambda p: None if pd.isna(p) else bool(p < 0.05))
    # A result counts as supported only if it also survives clustering by user AND by thread.
    df["survives_clustering"] = [
        None if pd.isna(a) or pd.isna(b) else bool(a < 0.05 and b < 0.05)
        for a, b in zip(df["p_user_holm"], df["p_thread_holm"])
    ]
    df.to_csv(config.STATISTICAL_TESTS_PATH, index=False)
    logger.info(df.drop(columns=["statistic", "note"]).to_string(index=False))


if __name__ == "__main__":
    main()
