"""Provisional evaluation against AI-labelled development examples.

Nothing in a sentiment analysis can be trusted until the scorer is checked against human judgement.
This module (1) draws a stratified sample of comments to label and (2) scores every automatic scorer
against the labels (accuracy, macro-F1, Cohen's kappa).

Files:
  data/gold/gold_to_label.csv   sample with blank label columns   (contains comment text -> git-ignored)
  data/gold/gold_labels.csv     the same rows once labelled        (contains comment text -> git-ignored)
  data/processed/gold_evaluation.csv   scorer agreement metrics    (no text -> committed)

Label columns:
  sentiment     positive | negative | neutral   overall tone of the comment as a reader would judge it
  stance_rival  favourable | hostile | neutral | na
                attitude towards the RIVAL franchise; na when the comment does not talk about it
Run `python -m src.gold_set sample` (or `sample_days` before the full pipeline has run) to draw the sample, `python -m src.gold_set evaluate` to score.
"""
import os
import sys

import pandas as pd
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("gold_set")

GOLD_DIR = "data/gold"
SAMPLE_PATH = f"{GOLD_DIR}/gold_to_label.csv"
LABELS_PATH = f"{GOLD_DIR}/gold_labels.csv"
EVAL_PATH = "data/processed/gold_evaluation.csv"
# comments to draw per subreddit and talk_target; rival-mentioning comments are over-sampled
# because they are rare but are exactly what the research question is about.
STRATA = {"rival_talk": 40, "both": 20, "self_talk": 45, "general": 45}
SCORERS = {"vader": "sentiment_label", "vader_adapted": "sentiment_adapted_label",
           "transformer": "sentiment_transformer_label"}
VALID_SENTIMENT = {"positive", "negative", "neutral"}


def _draw(comments, seed):
    comments = comments[comments["body_clean"].astype(str).str.len().between(15, 600)]
    parts = []
    for sub in config.SUBREDDITS:
        for target, n in STRATA.items():
            pool = comments[(comments["subreddit"] == sub) & (comments["talk_target"] == target)]
            parts.append(pool.sample(min(n, len(pool)), random_state=seed))
    sample = pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)
    out = pd.DataFrame({"gold_id": [f"g{i + 1:03d}" for i in range(len(sample))], "id": sample["id"],
                        "subreddit": sample["subreddit"], "talk_target": sample["talk_target"],
                        "text": sample["body_clean"].astype(str), "sentiment": "", "stance_rival": ""})
    os.makedirs(GOLD_DIR, exist_ok=True)
    out.to_csv(SAMPLE_PATH, index=False)
    logger.info(f"Wrote {len(out)} comments to label -> {SAMPLE_PATH}")
    return out


def make_sample(seed=7):
    """Draw from the finished pipeline output (comments_with_sentiment.csv)."""
    return _draw(pd.read_csv(config.SENTIMENT_PATH), seed)


def make_sample_from_days(seed=7):
    """Draw from whichever day files are already collected (before the full pipeline has run).
    Ids are hashed exactly as preprocess does, so the sample lines up with the final dataset.
    Fine for measuring scorer accuracy; the sample is not meant to estimate population shares."""
    from src.replication import load_window, prepare_rivals
    from src.utils import anonymize_id
    df = prepare_rivals(load_window(config.FULL_RAW_DIR, config.SUBREDDITS))
    df["id"] = [anonymize_id(i, "t1") for i in df["id"]]
    logger.info(f"Drawing from {len(df)} comments in the days collected so far")
    return _draw(df, seed)


HUMAN_PATH = f"{GOLD_DIR}/gold_labels_human.csv"


def human_agreement(labels):
    """The gold labels in this repo were produced by one annotator (an AI assistant), so they need an
    independent check. A person labels ANY subset of gold_to_label.csv (columns gold_id, sentiment with
    values positive/negative/neutral) and saves it as data/gold/gold_labels_human.csv; this returns the
    agreement (accuracy, Cohen's kappa). Kappa >= 0.6 is conventionally 'substantial' agreement."""
    if not os.path.exists(HUMAN_PATH):
        return None
    h = pd.read_csv(HUMAN_PATH)[["gold_id", "sentiment"]].rename(columns={"sentiment": "human"})
    m = labels.merge(h, on="gold_id")
    m = m[m["human"].isin(VALID_SENTIMENT)]
    if len(m) < 20:
        logger.warning(f"Only {len(m)} human labels; need at least 20 for a meaningful agreement figure.")
        return None
    return {"subset": "human vs annotator-1", "scorer": "human_second_annotator", "n": len(m),
            "accuracy": accuracy_score(m["sentiment"], m["human"]),
            "macro_f1": f1_score(m["sentiment"], m["human"], average="macro"),
            "cohen_kappa": cohen_kappa_score(m["sentiment"], m["human"])}


STANCE_PATH = "data/processed/stance_summary.csv"


def wilson(k, n, z=1.96):
    """Wilson 95% interval for a proportion k/n (well behaved for small n and extreme proportions)."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / d
    return centre - half, centre + half


def stance_summary(labels, scored):
    """Attitude towards the RIVAL franchise, estimated from the hand-labelled comments that mention it.
    Neither whole-comment sentiment, sentence-level sentiment nor a zero-shot NLI model predicted this
    stance better than always answering 'neutral' (tested on this gold set), so it is NOT scored
    automatically; it is estimated from labelled comments, with an honest confidence interval.
      share_*       share of genuine rival mentions (spurious alias matches, label 'na', removed)
      per_1000      expected number of such comments per 1,000 comments of the subreddit
                    = share of comments that mention the rival (from the full data) x share_*"""
    rows = []
    for sub in config.SUBREDDITS:
        mention_share = (scored[scored["subreddit"] == sub]["talk_target"].isin(["rival_talk", "both"])).mean()
        sub_l = labels[(labels["subreddit"] == sub) & labels["talk_target"].isin(["rival_talk", "both"])]
        genuine = sub_l[sub_l["stance_rival"].isin(["favourable", "hostile", "neutral"])]
        n = len(genuine)
        for stance in ("hostile", "favourable", "neutral"):
            k = int((genuine["stance_rival"] == stance).sum())
            lo, hi = wilson(k, n)
            rows.append({"subreddit": sub, "stance": stance, "n_labelled_mentions": n, "k": k,
                         "share": k / n if n else None, "ci_low": lo, "ci_high": hi,
                         "tagged_mention_share_of_all_comments": mention_share,
                         "label_source": "AI assistant; no independent human validation",
                         "inference_scope": "labelled development sample only; length and stratum selection prevent population extrapolation",
                         "spurious_alias_match_share": float((sub_l["stance_rival"] == "na").mean())})
    out = pd.DataFrame(rows)
    out.to_csv(STANCE_PATH, index=False)
    logger.info("Stance towards the rival franchise (hand-labelled):\n" + out.round(3).to_string(index=False))
    return out


def evaluate():
    labels = pd.read_csv(LABELS_PATH)
    bad = ~labels["sentiment"].isin(VALID_SENTIMENT)
    if bad.any():
        raise ValueError(f"{int(bad.sum())} rows have a missing/invalid sentiment label")
    scored = pd.read_csv(config.SENTIMENT_PATH)
    df = labels.merge(scored[["id"] + [c for c in SCORERS.values() if c in scored]], on="id", how="left")

    rows = []
    for subset_name, sub_df in [("all", df)] + [(f"talk_target={t}", df[df["talk_target"] == t])
                                              for t in STRATA] + \
                               [(f"r/{s}", df[df["subreddit"] == s]) for s in config.SUBREDDITS]:
        for name, col in SCORERS.items():
            if col not in sub_df or sub_df[col].isna().all():
                continue
            available = sub_df[sub_df[col].isin(VALID_SENTIMENT)]
            rows.append({"subset": subset_name, "scorer": name, "n": len(available),
                         "n_labels": len(sub_df), "label_source": "AI assistant; development evaluation",
                         "accuracy": accuracy_score(available["sentiment"], available[col]),
                         "macro_f1": f1_score(available["sentiment"], available[col], labels=sorted(VALID_SENTIMENT), average="macro", zero_division=0),
                         "cohen_kappa": cohen_kappa_score(available["sentiment"], available[col])})
    human = human_agreement(labels)
    if human:
        rows.append(human)
    result = pd.DataFrame(rows)
    result.to_csv(EVAL_PATH, index=False)
    logger.info("Scorer agreement with hand labels:\n" + result.round(3).to_string(index=False))
    logger.info("Label distribution:\n" + df["sentiment"].value_counts().to_string())
    stance_summary(labels, scored)
    if "stance_rival" in df and df["stance_rival"].notna().any():
        logger.info("Stance towards rival (rival_talk + both):\n" +
                    df[df["talk_target"].isin(["rival_talk", "both"])]
                    .groupby(["subreddit", "stance_rival"]).size().to_string())
    return result


def main():
    if os.path.exists(LABELS_PATH):
        evaluate()
    else:
        logger.warning(f"{LABELS_PATH} not found; label {SAMPLE_PATH} first (see module docstring).")


if __name__ == "__main__":
    {"sample": make_sample, "sample_days": make_sample_from_days, "evaluate": evaluate}.get(sys.argv[1] if len(sys.argv) > 1 else "evaluate")()
