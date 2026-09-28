import os
import sys
import networkx as nx
import community as community_louvain
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("network_analysis")


def profile_communities(subreddit_name, community_df):
    """Join community assignments back onto sentiment/topic data so detected
    communities become an interpretable finding, not just a bare count."""
    if not os.path.exists(config.SENTIMENT_PATH):
        logger.warning("comments_with_sentiment.csv not found — run Stage 5 before profiling communities.")
        return

    comments = pd.read_csv(config.SENTIMENT_PATH)
    sub_comments = comments[comments["subreddit"] == subreddit_name]

    merged = sub_comments.merge(
        community_df.rename(columns={"user": "author"}),
        on="author", how="inner"
    )

    agg_kwargs = dict(
        num_users=("author", "nunique"),
        num_comments=("id", "count"),
        mean_sentiment=("sentiment_compound", "mean"),
    )

    # If Stage 4b's topic data exists, merge it in to report each community's
    # modal (most common) topic alongside its sentiment — this is what makes
    # a community profile a real finding instead of just a headcount.
    topics_path = f"data/processed/topics_{subreddit_name}.csv"
    if os.path.exists(topics_path):
        topics = pd.read_csv(topics_path)
        merged = merged.merge(topics, on="id", how="left")

    profile = merged.groupby("community_id").agg(**agg_kwargs).reset_index()

    if "topic_words" in merged.columns:
        modal_topic = merged.groupby("community_id")["topic_words"].agg(
            lambda x: x.mode().iloc[0] if not x.mode().empty else "n/a"
        )
        profile = profile.merge(modal_topic.rename("modal_topic"), on="community_id", how="left")

    profile = profile.sort_values("num_users", ascending=False)
    profile.to_csv(f"data/processed/community_profile_{subreddit_name}.csv", index=False)
    logger.info(f"r/{subreddit_name} community profiles:\n{profile.to_string(index=False)}")


def analyze_network(subreddit_name):
    path = f"{config.NETWORKS_DIR}/network_{subreddit_name}.gexf"
    G = nx.read_gexf(path)

    if G.number_of_nodes() < 3:
        logger.warning(f"r/{subreddit_name}: network too small ({G.number_of_nodes()} nodes) for "
                          f"meaningful centrality analysis. Consider widening WINDOW_DAYS in config.py.")
        return

    degree_cent = nx.degree_centrality(G)

    if G.number_of_nodes() > 5000:
        betweenness_cent = nx.betweenness_centrality(G, k=500, seed=42)
        logger.info(f"r/{subreddit_name}: using approximated betweenness centrality (k=500 sample) "
                      f"due to graph size ({G.number_of_nodes()} nodes).")
    else:
        betweenness_cent = nx.betweenness_centrality(G)

    centrality_df = pd.DataFrame({
        "user": list(degree_cent.keys()),
        "degree_centrality": list(degree_cent.values()),
        "betweenness_centrality": [betweenness_cent[u] for u in degree_cent.keys()],
    }).sort_values("betweenness_centrality", ascending=False)

    centrality_df.to_csv(f"data/processed/centrality_{subreddit_name}.csv", index=False)
    logger.info(f"Top 10 structurally central users in r/{subreddit_name} "
                  f"(highest betweenness centrality in the observed reply network):\n"
                  f"{centrality_df.head(10).to_string(index=False)}")

    G_undirected = G.to_undirected()
    partition = community_louvain.best_partition(G_undirected, weight="weight", random_state=42)

    community_df = pd.DataFrame({
        "user": list(partition.keys()),
        "community_id": list(partition.values()),
    })
    community_df.to_csv(f"data/processed/communities_{subreddit_name}.csv", index=False)

    num_communities = len(set(partition.values()))
    logger.info(f"r/{subreddit_name}: {num_communities} communities detected")
    logger.info(community_df["community_id"].value_counts().to_string())

    nx.set_node_attributes(G, partition, "community")
    nx.write_gexf(G, f"{config.NETWORKS_DIR}/network_{subreddit_name}_with_communities.gexf")

    profile_communities(subreddit_name, community_df)


def main():
    for sub in config.SUBREDDITS:
        analyze_network(sub)


if __name__ == "__main__":
    main()
