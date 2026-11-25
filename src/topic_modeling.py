import os
import sys
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, get_stopwords

logger = setup_logger("topic_modeling")

N_TOP_WORDS = 8
NO_TOPIC = -1


def assign_topics(topic_matrix, tfidf, min_tokens):
    """Dominant topic per comment. Comments with fewer than `min_tokens` informative tokens
    (e.g. 'lol exactly') carry no topical signal, and argmax of an all-zero row would silently
    dump them into topic 0, so they get NO_TOPIC (-1) instead."""
    dominant = topic_matrix.argmax(axis=1)
    informative_tokens = np.asarray((tfidf > 0).sum(axis=1)).ravel()
    dominant = np.where(informative_tokens >= min_tokens, dominant, NO_TOPIC)
    return dominant


def npmi_coherence(tfidf, topic_components, n_words=10, eps=1e-12):
    """Mean NPMI coherence of the topics' top words, using document co-occurrence in the corpus
    (higher = the top words of a topic really appear together, i.e. the topic is interpretable).
    Used to choose the number of topics instead of fixing it by hand."""
    X = (tfidf > 0).astype(np.float32).tocsc()
    n_docs = X.shape[0]
    scores = []
    for topic in topic_components:
        idx = np.argsort(topic)[-n_words:]
        sub = X[:, idx]
        co = (sub.T @ sub).toarray() / n_docs
        p = np.diag(co).copy()
        vals = []
        for i in range(len(idx)):
            for j in range(i + 1, len(idx)):
                if co[i, j] <= 0:
                    vals.append(-1.0)
                    continue
                pmi = np.log(co[i, j] / (p[i] * p[j] + eps))
                vals.append(pmi / (-np.log(co[i, j] + eps)))
        scores.append(np.mean(vals))
    return float(np.mean(scores))


def choose_n_topics(tfidf, candidates, seed=42):
    """Fit NMF for each candidate K and return (best K, {K: coherence})."""
    results = {}
    for k in candidates:
        nmf = NMF(n_components=k, random_state=seed, init="nndsvda", max_iter=300)
        nmf.fit(tfidf)
        results[k] = npmi_coherence(tfidf, nmf.components_)
        logger.info(f"  K={k}: mean NPMI coherence {results[k]:.4f}")
    return max(results, key=results.get), results


def run_topic_model(comments_subset, subreddit_name):
    if len(comments_subset) < 20:
        logger.warning(f"r/{subreddit_name}: too few comments ({len(comments_subset)}) for topic modeling. Skipping.")
        return None, None

    vectorizer = TfidfVectorizer(max_df=0.5, min_df=5, stop_words=list(get_stopwords()),
                                 ngram_range=(1, 2), max_features=3000,
                                 token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]{2,}\b")
    tfidf = vectorizer.fit_transform(comments_subset["body_clean"].astype(str))

    if config.TOPIC_CANDIDATES:
        n_topics, coherence = choose_n_topics(tfidf, config.TOPIC_CANDIDATES)
        logger.info(f"r/{subreddit_name}: chose K={n_topics} by NPMI coherence {coherence}")
        pd.DataFrame({"subreddit": subreddit_name, "k": list(coherence), "npmi_coherence": list(coherence.values())}
                     ).to_csv(f"data/processed/topic_k_selection_{subreddit_name}.csv", index=False)
    else:
        n_topics = config.N_TOPICS
    nmf = NMF(n_components=n_topics, random_state=42, init="nndsvda", max_iter=500)
    topic_matrix = nmf.fit_transform(tfidf)
    dominant_topic = assign_topics(topic_matrix, tfidf, config.TOPIC_MIN_TOKENS)

    feature_names = vectorizer.get_feature_names_out()
    topic_labels = {NO_TOPIC: "(too short / no topical words)"}
    for topic_idx, topic in enumerate(nmf.components_):
        top_words = [feature_names[i] for i in topic.argsort()[-N_TOP_WORDS:][::-1]]
        topic_labels[topic_idx] = ", ".join(top_words)
        logger.info(f"r/{subreddit_name} Topic {topic_idx}: {topic_labels[topic_idx]}")

    return dominant_topic, topic_labels


def main():
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)

    for sub in config.SUBREDDITS:
        subset = comments[comments["subreddit"] == sub].copy()
        dominant_topic, topic_labels = run_topic_model(subset, sub)
        if dominant_topic is None:
            continue

        subset["topic_id"] = dominant_topic
        subset["topic_words"] = subset["topic_id"].map(topic_labels)
        subset[["id", "topic_id", "topic_words"]].to_csv(f"data/processed/topics_{sub}.csv", index=False)

        summary = (subset.groupby(["topic_id", "topic_words"]).size().reset_index(name="num_comments"))
        summary["share"] = summary["num_comments"] / len(subset)
        summary.to_csv(f"data/processed/topic_summary_{sub}.csv", index=False)
        logger.info(f"r/{sub} topic prevalence:\n{summary.to_string(index=False)}")


if __name__ == "__main__":
    main()
