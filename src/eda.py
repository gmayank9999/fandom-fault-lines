import os
import re
import sys
from collections import Counter

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("eda")
sns.set_theme(style="whitegrid")

STOPWORDS = set("the a an is are was were be been being and or but if then so to of in on for "
                 "with as it its this that these those i you he she they we my your his her their "
                 "have has had do does did not no just like about".split())


def top_words(text_series, n=20):
    all_words = []
    for text in text_series:
        words = re.findall(r"\b[a-z]{3,}\b", str(text).lower())
        words = [w for w in words if w not in STOPWORDS]
        all_words.extend(words)
    return Counter(all_words).most_common(n)


def main():
    os.makedirs(config.CHARTS_DIR, exist_ok=True)

    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    comments["created_dt"] = pd.to_datetime(comments["created_utc"], unit="s")
    comments["date"] = comments["created_dt"].dt.date

    # ---- Chart 1: activity over time ----
    daily_counts = comments.groupby(["date", "subreddit"]).size().reset_index(name="comment_count")
    plt.figure(figsize=(10, 5))
    sns.lineplot(data=daily_counts, x="date", y="comment_count", hue="subreddit")
    plt.title("Daily Comment Activity by Subreddit")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{config.CHARTS_DIR}/chart_activity_over_time.png")
    plt.close()

    # ---- Chart 2: score distribution ----
    plt.figure(figsize=(8, 5))
    sns.boxplot(data=comments, x="subreddit", y="score")
    plt.title("Comment Score Distribution by Subreddit")
    plt.ylim(comments["score"].quantile(0.01), comments["score"].quantile(0.99))
    plt.tight_layout()
    plt.savefig(f"{config.CHARTS_DIR}/chart_score_distribution.png")
    plt.close()

    logger.info("Charts saved to outputs/charts/")

    # ---- Top keywords per subreddit ----
    for sub in config.SUBREDDITS:
        subset = comments[comments["subreddit"] == sub]["body_clean"]
        logger.info(f"Top words in r/{sub}: {top_words(subset)}")

    # ---- Cross-mention rate ----
    subs = comments["subreddit"].unique()
    if len(subs) == 2:
        sub_a, sub_b = subs
        name_a = sub_a.lower().replace("_", " ")
        name_b = sub_b.lower().replace("_", " ")

        mentions_b_in_a = comments[comments["subreddit"] == sub_a]["body_clean"].str.lower().str.contains(name_b, na=False).sum()
        mentions_a_in_b = comments[comments["subreddit"] == sub_b]["body_clean"].str.lower().str.contains(name_a, na=False).sum()
        total_a = len(comments[comments["subreddit"] == sub_a])
        total_b = len(comments[comments["subreddit"] == sub_b])

        logger.info(f"r/{sub_a} mentions r/{sub_b} in {mentions_b_in_a}/{total_a} comments "
                      f"({100*mentions_b_in_a/max(total_a,1):.1f}%)")
        logger.info(f"r/{sub_b} mentions r/{sub_a} in {mentions_a_in_b}/{total_b} comments "
                      f"({100*mentions_a_in_b/max(total_b,1):.1f}%)")


if __name__ == "__main__":
    main()
