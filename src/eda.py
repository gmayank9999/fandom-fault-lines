import os
import re
import sys
from collections import Counter

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, compile_alias_regex, get_stopwords

logger = setup_logger("eda")
sns.set_theme(style="whitegrid")

STOPWORDS = get_stopwords()


def top_words(text_series, n=20):
    all_words = []
    for text in text_series:
        words = re.findall(r"\b[a-z]{3,}\b", str(text).lower())
        all_words.extend(w for w in words if w not in STOPWORDS)
    return Counter(all_words).most_common(n)


def main():
    os.makedirs(config.CHARTS_DIR, exist_ok=True)

    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    posts = pd.read_csv(config.CLEAN_POSTS_PATH)
    posts["date"] = pd.to_datetime(posts["created_utc"], unit="s").dt.date

    # ---- Chart 1: activity over time ----
    # Comments are sampled evenly per time slot BY DESIGN, so their daily counts are flat and say
    # nothing about activity. Real activity = posts per day and the comments those posts received.
    daily = posts.groupby(["date", "subreddit"]).agg(posts=("id", "count"),
                                                     comments_received=("num_comments", "sum")).reset_index()
    fig, axes = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    sns.lineplot(data=daily, x="date", y="posts", hue="subreddit", ax=axes[0])
    axes[0].set_title("Posts per day (full 28-day window)")
    sns.lineplot(data=daily, x="date", y="comments_received", hue="subreddit", ax=axes[1])
    axes[1].set_title("Comments received by posts created that day")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{config.CHARTS_DIR}/chart_activity_over_time.png")
    plt.close()

    # ---- Peak days: name the event behind each spike (event-window confounding check) ----
    rows = []
    for sub in config.SUBREDDITS:
        d = daily[daily["subreddit"] == sub].sort_values("comments_received", ascending=False).head(3)
        for _, r in d.iterrows():
            day_posts = posts[(posts["subreddit"] == sub) & (posts["date"] == r["date"])]
            top = day_posts.sort_values("num_comments", ascending=False).iloc[0]
            rows.append({"subreddit": sub, "date": r["date"], "posts_that_day": int(r["posts"]),
                         "comments_received": int(r["comments_received"]),
                         "top_post_title": top["title"], "top_post_num_comments": int(top["num_comments"])})
    peak = pd.DataFrame(rows)
    peak.to_csv(config.PEAK_DAYS_PATH, index=False)
    logger.info(f"Peak activity days (check these against known announcements):\n{peak.to_string(index=False)}")

    # ---- Chart 2: score distributions (comments and posts, log scale) ----
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, df, name in [(axes[0], comments, "Comment"), (axes[1], posts, "Post")]:
        plot_df = df.assign(log_score=df["score"].clip(lower=0) + 1)
        sns.boxplot(data=plot_df, x="subreddit", y="log_score", ax=ax)
        ax.set_yscale("log")
        ax.set_ylabel("score + 1 (log scale)")
        ax.set_title(f"{name} score distribution")
    plt.tight_layout()
    plt.savefig(f"{config.CHARTS_DIR}/chart_score_distribution.png")
    plt.close()
    logger.info(f"Median comment score: {comments.groupby('subreddit')['score'].median().to_dict()}")
    logger.info(f"Median post score: {posts.groupby('subreddit')['score'].median().to_dict()}")
    logger.info("Charts saved to outputs/charts/")

    # ---- Top keywords per subreddit ----
    for sub in config.SUBREDDITS:
        subset = comments[comments["subreddit"] == sub]["body_clean"]
        logger.info(f"Top words in r/{sub}: {top_words(subset)}")

    # ---- Cross-mention rate (uses the franchise aliases, whole-word matching) ----
    if len(config.SUBREDDITS) == 2:
        sub_a, sub_b = config.SUBREDDITS
        for own, other in [(sub_a, sub_b), (sub_b, sub_a)]:
            rx = compile_alias_regex(config.FRANCHISE_ALIASES[other])
            subset = comments[comments["subreddit"] == own]["body_clean"].astype(str)
            n = int(subset.apply(lambda t: bool(rx.search(t))).sum())
            logger.info(f"r/{own} comments mentioning {other}'s franchise terms: {n}/{len(subset)} "
                        f"({100 * n / max(len(subset), 1):.1f}%)")


if __name__ == "__main__":
    main()
