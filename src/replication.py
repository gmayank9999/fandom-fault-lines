"""Replication: do the headline findings hold in a different month?

One 28-day window is dominated by whatever the news cycle was (Lanterns for DC, Doomsday for Marvel).
This stage repeats the key measurements on a second, non-overlapping window and puts the two side by
side. A finding that changes sign or disappears between windows is a feature of the window, not of the
communities.

Window 2 comes from `python -m src.collect_full --window-end YYYY-MM-DD` (files in data/raw/full_<date>/).
Everything is computed in memory; only aggregate tables are written (no text, no user ids).

Outputs (data/processed/):
  replication_<date>.csv           headline metrics, both windows side by side
"""
import glob
import os
import sys

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.overlap_analysis import baseline_overlap_table
from src.preprocess import basic_clean
from src.sentiment import adapted_analyzer, tag_target
from src.statistical_tests import run_family
from src.utils import anonymize, setup_logger

logger = setup_logger("replication")


def load_window(base_dir, subs):
    from src.study_data import days
    from datetime import datetime, timedelta
    name = os.path.basename(base_dir.rstrip("/\\"))
    end = datetime.strptime(name[5:], "%Y-%m-%d") if name.startswith("full_") else config.WINDOW_END_DATE
    window = {"start": (end - timedelta(days=config.WINDOW_DAYS)).strftime("%Y-%m-%d"),
              "end": end.strftime("%Y-%m-%d")}
    frames = []
    for sub in subs:
        from src.study_data import validate_day
        for a, b in days(window):
            path = os.path.join(base_dir, sub, f"{a}.csv")
            if not os.path.isfile(path):
                raise FileNotFoundError(f"missing expected day {a} for r/{sub} in {base_dir}")
            frames.append(validate_day(path, sub, a, b, light=sub in config.BASELINE_SUBREDDITS))
    return pd.concat(frames, ignore_index=True)


def prepare_rivals(raw):
    """Same cleaning as the main pipeline, then the adapted-VADER score and the talk-target tag."""
    df = basic_clean(raw)
    df["author"] = df["author"].apply(anonymize)
    df = df[df["author"] != "[deleted]"].copy()
    a = adapted_analyzer()
    df["sentiment_adapted"] = df["body_clean"].apply(lambda t: a.polarity_scores(str(t))["compound"])
    sub_a, sub_b = config.SUBREDDITS
    df["talk_target"] = df.apply(lambda r: tag_target(r, sub_a, sub_b), axis=1)
    return df


def headline_metrics(rivals, baseline_authors=None):
    """Return {metric: value} for one window."""
    sub_a, sub_b = config.SUBREDDITS
    m = {}
    for sub in config.SUBREDDITS:
        d = rivals[rivals["subreddit"] == sub]
        m[f"comments[{sub}]"] = len(d)
        m[f"users[{sub}]"] = d["author"].nunique()
        for t in ("self_talk", "rival_talk", "both"):
            m[f"share_{t}[{sub}]"] = (d["talk_target"] == t).mean()
    for row in run_family(rivals, "sentiment_adapted"):
        name = row["comparison"]
        m[f"diff[{name}]"] = row["diff_user_boot"]
        m[f"ci_low[{name}]"] = row["ci_low_user_boot"]
        m[f"ci_high[{name}]"] = row["ci_high_user_boot"]
        m[f"p_user_boot[{name}]"] = row["p_user_boot"]
        m[f"n[{name}]"] = f'{row["n_a"]}/{row["n_b"]}'

    counts = {s: rivals[rivals["subreddit"] == s]["author"].value_counts() for s in config.SUBREDDITS}
    if baseline_authors is not None:
        for sub, g in baseline_authors.groupby("subreddit"):
            counts[sub] = g["author"].value_counts()
    table = baseline_overlap_table(counts, (sub_a, sub_b))
    for _, r in table.iterrows():
        if r["min_comments"] in (1, 2):
            m[f"overlap_pct_of_smaller[{r['pair']}, >={r['min_comments']}]"] = r["pct_of_smaller"]
            m[f"overlap_lift[{r['pair']}, >={r['min_comments']}]"] = r["lift"]
    return m


def main(window_end="2026-10-29"):
    base = f"data/raw/full_{window_end}"
    if not os.path.isdir(base):
        logger.warning(f"{base} not found; collect the replication window first "
                       f"(python -m src.collect_full --window-end {window_end}).")
        return

    # window 1 = the main pipeline's already-processed data
    w1 = pd.read_csv(config.SENTIMENT_PATH)
    base1 = pd.read_csv(config.CLEAN_BASELINE_PATH) if os.path.exists(config.CLEAN_BASELINE_PATH) else None

    # window 2 = raw day files, cleaned the same way
    w2_raw = load_window(base, config.SUBREDDITS)
    w2 = prepare_rivals(w2_raw)
    base2 = None
    if config.BASELINE_SUBREDDITS and all(os.path.isdir(os.path.join(base, s)) for s in config.BASELINE_SUBREDDITS):
        b = load_window(base, config.BASELINE_SUBREDDITS)
        b = b[~b["author"].isin(config.BOT_ACCOUNTS) & b["author"].notna()].copy()
        b["author"] = b["author"].apply(anonymize)
        base2 = b[b["author"] != "[deleted]"]

    m1, m2 = headline_metrics(w1, base1), headline_metrics(w2, base2)
    keys = list(dict.fromkeys(list(m1) + list(m2)))
    out = pd.DataFrame({"metric": keys, "window_main": [m1.get(k) for k in keys],
                        f"window_ending_{window_end}": [m2.get(k) for k in keys]})
    path = f"data/processed/replication_{window_end}.csv"
    out.to_csv(path, index=False)
    logger.info("Replication (main window vs second window):\n" + out.to_string(index=False))


if __name__ == "__main__":
    main(*(sys.argv[1:2]))
