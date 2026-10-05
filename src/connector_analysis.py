import os
import sys
import networkx as nx
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("connector_analysis")

NO_TOPIC = -1


def classify_role(posts_authored, in_weight, out_weight):
    """Why is this user structurally central?
    thread starter: posted threads and receives more replies than they write (central because
                    people reply to them)
    reply bridge:   writes and receives replies about equally / mostly writes (central because
                    they link different threads and people)"""
    if posts_authored > 0 and in_weight > out_weight:
        return "thread starter"
    return "reply bridge"


def profile_connectors(subreddit_name, comments, posts, shared_users):
    cent = pd.read_csv(f"data/processed/centrality_{subreddit_name}.csv")
    comm = pd.read_csv(f"data/processed/communities_{subreddit_name}.csv")
    G = nx.read_gexf(f"{config.NETWORKS_DIR}/network_{subreddit_name}.gexf")

    sub_comments = comments[comments["subreddit"] == subreddit_name]
    sub_posts = posts[posts["subreddit"] == subreddit_name]

    topics_path = f"data/processed/topics_{subreddit_name}.csv"
    if os.path.exists(topics_path):
        sub_comments = sub_comments.merge(pd.read_csv(topics_path), on="id", how="left")
    else:
        sub_comments = sub_comments.assign(topic_id=NO_TOPIC, topic_words="")

    posts_by_user = sub_posts["author"].value_counts()
    comments_by_user = sub_comments["author"].value_counts()
    sentiment_by_user = sub_comments.groupby("author")["sentiment_compound"].mean()
    comm_size = comm["community_id"].map(comm["community_id"].value_counts())
    comm = comm.assign(community_size=comm_size).set_index("user")
    in_w = dict(G.in_degree(weight="weight"))
    out_w = dict(G.out_degree(weight="weight"))

    def modal_topic(user):
        t = sub_comments[(sub_comments["author"] == user) & (sub_comments["topic_id"] != NO_TOPIC)]["topic_words"]
        return t.mode().iloc[0] if not t.mode().empty else "n/a"

    def build(df, scope):
        rows = []
        for rank, (_, r) in enumerate(df.iterrows(), 1):
            u = r["user"]
            posts_n = int(posts_by_user.get(u, 0))
            rows.append({
                "scope": scope, "rank": rank, "user": u,
                "betweenness_centrality": r["betweenness_centrality"],
                "degree_centrality": r["degree_centrality"],
                "replies_received": int(in_w.get(u, 0)), "replies_written": int(out_w.get(u, 0)),
                "posts_authored": posts_n, "comments_authored": int(comments_by_user.get(u, 0)),
                "role": classify_role(posts_n, in_w.get(u, 0), out_w.get(u, 0)),
                "mean_sentiment": sentiment_by_user.get(u),
                "main_topic": modal_topic(u),
                "community_id": comm.loc[u, "community_id"], "community_size": comm.loc[u, "community_size"],
                "also_active_in_rival_sub": u in shared_users,
            })
        return rows

    top = cent.head(config.TOP_CONNECTORS)
    non_posters = cent[~cent["user"].isin(posts_by_user.index)].head(config.TOP_CONNECTORS)
    profile = pd.DataFrame(build(top, "top overall") + build(non_posters, "top excluding post authors"))
    profile.to_csv(f"data/processed/connector_profile_{subreddit_name}.csv", index=False)

    overall = profile[profile["scope"] == "top overall"]
    logger.info(f"r/{subreddit_name}: of the top {len(overall)} structurally central users, "
                f"{(overall['posts_authored'] > 0).sum()} authored at least one post and "
                f"{(overall['role'] == 'thread starter').sum()} are classified as thread starters; "
                f"{overall['also_active_in_rival_sub'].sum()} are also active in the rival subreddit.")
    logger.info(f"r/{subreddit_name} top {config.TOP_CONNECTORS} (overall):\n"
                f"{overall.drop(columns=['scope']).to_string(index=False)}")
    logger.info(f"r/{subreddit_name} top {config.TOP_CONNECTORS} excluding post authors "
                f"(pure reply bridges):\n"
                f"{profile[profile['scope'] != 'top overall'].drop(columns=['scope']).to_string(index=False)}")


def main():
    comments = pd.read_csv(config.SENTIMENT_PATH)
    posts = pd.read_csv(config.CLEAN_POSTS_PATH)
    users = [set(comments[comments["subreddit"] == s]["author"]) - {"[deleted]"} for s in config.SUBREDDITS]
    shared = set.intersection(*users) if len(users) == 2 else set()

    for sub in config.SUBREDDITS:
        profile_connectors(sub, comments, posts, shared)


if __name__ == "__main__":
    main()
