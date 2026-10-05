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


def run_topic_model(comments_subset, subreddit_name):
    if len(comments_subset) < 20:
        logger.warning(f"r/{subreddit_name}: too few comments ({len(comments_subset)}) for topic modeling. Skipping.")
        return None, None

    vectorizer = TfidfVectorizer(max_df=0.5, min_df=5, stop_words=list(get_stopwords()),
                                 ngram_range=(1, 2), max_features=3000,
                                 token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]{2,}\b")
    tfidf = vectorizer.fit_transform(comments_subset["body_clean"].astype(str))

    nmf = NMF(n_components=config.N_TOPICS, random_state=42, init="nndsvda", max_iter=500)
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
