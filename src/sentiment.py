import hashlib
import os
import sys
from functools import lru_cache

import numpy as np
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, compile_alias_regex

logger = setup_logger("sentiment")


@lru_cache(maxsize=None)
def adapted_analyzer():
    """VADER with franchise/plot words removed from the lexicon (see DOMAIN_NEUTRAL_WORDS in config)."""
    a = SentimentIntensityAnalyzer()
    for w in config.DOMAIN_NEUTRAL_WORDS:
        a.lexicon.pop(w, None)
    return a


def transformer_scores(comments, score_mask=None):
    """P(positive) - P(negative) from a RoBERTa model trained on social-media text, computed once per
    comment and cached by (hashed) id so reruns and later stages do not repeat the slow inference.
    Returns a DataFrame (sentiment_transformer = P(pos)-P(neg), sentiment_transformer_label = argmax class) indexed like `comments`, or None if torch/transformers are not installed."""
    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
    except ImportError:
        logger.warning("torch/transformers not installed: skipping transformer sentiment.")
        return None
    cache = pd.read_csv(config.TRANSFORMER_SCORES_PATH) if os.path.exists(config.TRANSFORMER_SCORES_PATH)         else pd.DataFrame(columns=["id", "p_neg", "p_neu", "p_pos"])
    wanted = comments if score_mask is None else comments[score_mask]
    todo = wanted[~wanted["id"].isin(set(cache["id"]))][["id", "body_clean"]]
    logger.info(f"Transformer sentiment: {len(cache)} cached, {len(todo)} to score.")
    if len(todo):
        tok = AutoTokenizer.from_pretrained(config.TRANSFORMER_MODEL)
        model = AutoModelForSequenceClassification.from_pretrained(config.TRANSFORMER_MODEL).eval()
        labels = {v.lower(): k for k, v in model.config.id2label.items()}
        pos, neg, neu = labels["positive"], labels["negative"], labels["neutral"]
        torch.set_num_threads(os.cpu_count() or 4)
        todo = todo.assign(n=todo["body_clean"].astype(str).str.len()).sort_values("n")   # batch similar lengths
        out, ids = [], todo["id"].tolist()          # out: rows of (p_neg, p_neu, p_pos)
        texts = todo["body_clean"].astype(str).tolist()
        bs = config.TRANSFORMER_BATCH
        for i in range(0, len(texts), bs):
            enc = tok(texts[i:i + bs], truncation=True, max_length=config.TRANSFORMER_MAX_LEN,
                      padding=True, return_tensors="pt")
            with torch.no_grad():
                p = torch.softmax(model(**enc).logits, dim=-1)
            out.extend(p[:, [neg, neu, pos]].tolist())
            if (i // bs) % 200 == 0:
                logger.info(f"  transformer: {i + len(texts[i:i + bs])}/{len(texts)}")
                _append(cache, _prob_frame(ids[:len(out)], out)).to_csv(config.TRANSFORMER_SCORES_PATH, index=False)  # checkpoint
        cache = _append(cache, _prob_frame(ids, out))
        cache.to_csv(config.TRANSFORMER_SCORES_PATH, index=False)
    cache = cache.drop_duplicates("id").set_index("id").reindex(comments["id"])
    return pd.DataFrame({"sentiment_transformer": (cache["p_pos"] - cache["p_neg"]).to_numpy(),
                         "sentiment_transformer_label": _argmax_label(cache).to_numpy()}, index=comments.index)


def _append(cache, new):
    return new if cache.empty else pd.concat([cache, new], ignore_index=True)


def _prob_frame(ids, rows):
    return pd.DataFrame(rows, columns=["p_neg", "p_neu", "p_pos"]).assign(id=ids)[["id", "p_neg", "p_neu", "p_pos"]]


def _argmax_label(probs):
    """The model's own 3-class decision. No tuned neutral band: choosing a threshold on a small
    hand-labelled set would just fit that set."""
    names = np.array(["negative", "neutral", "positive"])
    arr = probs[["p_neg", "p_neu", "p_pos"]].to_numpy(dtype=float)
    lab = pd.Series(names[np.nan_to_num(arr, nan=-1).argmax(1)], index=probs.index, dtype=object)
    lab[np.isnan(arr).any(1)] = None
    return lab


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


def transformer_mask(comments):
    """Which comments get transformer scores. CPU inference is slow (~15 comments/s): score every
    rival-mentioning comment, a capped random sample of the big groups (config.TRANSFORMER_CAP_PER_STRATUM)
    and the hand-labelled gold set. Everything else keeps NaN and is ignored by the tests.
    Needs comments["talk_target"]; the sampling is deterministic (hash of the comment id)."""
    mask = comments["talk_target"].isin(["rival_talk", "both"])
    u = comments["id"].map(lambda i: int(hashlib.md5(i.encode()).hexdigest(), 16) % 100000 / 100000)
    for (sub, target), g in comments.groupby(["subreddit", "talk_target"]):
        cap = config.TRANSFORMER_CAP_PER_STRATUM.get(target)
        if cap:
            mask.loc[g.index] |= u.loc[g.index] < min(1.0, cap / len(g))
    gold_path = "data/gold/gold_to_label.csv"
    if os.path.exists(gold_path):
        mask |= comments["id"].isin(set(pd.read_csv(gold_path)["id"]))
    return mask


def tag_all(comments):
    sub_a, sub_b = config.SUBREDDITS
    return comments.apply(lambda row: tag_target(row, sub_a, sub_b), axis=1)


def build_transformer_cache():
    """`python -m src.sentiment --cache-only`: score the selected comments and update the cache, without
    touching any pipeline output. Lets the slow part run in the background while other stages proceed."""
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    comments["talk_target"] = tag_all(comments)
    transformer_scores(comments, transformer_mask(comments))


def main():
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    analyzer = SentimentIntensityAnalyzer()

    comments["sentiment_compound"] = comments["body_clean"].apply(
        lambda t: analyzer.polarity_scores(str(t))["compound"]
    )
    comments["sentiment_label"] = comments["sentiment_compound"].apply(categorize)
    adapted = adapted_analyzer()
    comments["sentiment_adapted"] = comments["body_clean"].apply(
        lambda t: adapted.polarity_scores(str(t))["compound"])
    comments["sentiment_adapted_label"] = comments["sentiment_adapted"].apply(categorize)
    if len(config.SUBREDDITS) == 2:
        comments["talk_target"] = tag_all(comments)

    if config.USE_TRANSFORMER:
        ts = transformer_scores(comments, transformer_mask(comments))
        if ts is not None:
            comments["sentiment_transformer"] = ts["sentiment_transformer"]
            comments["sentiment_transformer_label"] = ts["sentiment_transformer_label"]

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
        grp = comments.groupby(["subreddit", "talk_target"])
        summary = grp["sentiment_compound"].agg(mean="mean", std="std", count="count")   # plain VADER
        for col, tag in (("sentiment_adapted", "adapted"), ("sentiment_transformer", "transformer")):
            if col in comments:
                summary[f"mean_{tag}"] = grp[col].mean()
                summary[f"std_{tag}"] = grp[col].std()
                summary[f"count_{tag}"] = grp[col].count()      # transformer scores only a subset
        summary["share_of_subreddit"] = summary["count"] / summary.groupby(level=0)["count"].transform("sum")
        summary.to_csv(config.SENTIMENT_BY_TARGET_PATH)
        logger.info(f"Sentiment by talk target (self/rival/both/general):\n{summary.to_string()}")
    else:
        logger.warning(f"Expected exactly 2 subreddits for the self/rival split; found "
                       f"{len(config.SUBREDDITS)}. Skipping this comparison.")

    comments.to_csv(config.SENTIMENT_PATH, index=False)


if __name__ == "__main__":
    build_transformer_cache() if "--cache-only" in sys.argv else main()
