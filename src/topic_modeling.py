import os
import sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("topic_modeling")

N_TOPICS = 5
N_TOP_WORDS = 8


def run_topic_model(comments_subset, subreddit_name):
    if len(comments_subset) < 20:
        logger.warning(f"r/{subreddit_name}: too few comments ({len(comments_subset)}) for topic modeling. Skipping.")
        return None, None

    vectorizer = TfidfVectorizer(max_df=0.9, min_df=5, stop_words="english", max_features=2000)
    tfidf = vectorizer.fit_transform(comments_subset["body_clean"].astype(str))

    nmf = NMF(n_components=N_TOPICS, random_state=42, init="nndsvda", max_iter=400)
    topic_matrix = nmf.fit_transform(tfidf)
    dominant_topic = topic_matrix.argmax(axis=1)

    feature_names = vectorizer.get_feature_names_out()
    topic_labels = {}
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

        logger.info(f"r/{sub} topic prevalence:\n{subset['topic_id'].value_counts(normalize=True).to_string()}")


if __name__ == "__main__":
    main()
