import os
import sys
import networkx as nx
import community as community_louvain
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("network_analysis")

NETWORK_SUMMARY_PATH = "data/processed/network_summary.csv"
NO_TOPIC = -1


def profile_communities(subreddit_name, community_df):
    """Join community assignments back onto sentiment/topic data. Only communities with at least
    MIN_COMMUNITY_SIZE users are profiled; smaller ones are fragments (mostly tiny disconnected
    reply pairs) and are summarised as a count instead of padding the table."""
    if not os.path.exists(config.SENTIMENT_PATH):
        logger.warning("comments_with_sentiment.csv not found - run Stage 5 before profiling communities.")
        return

    comments = pd.read_csv(config.SENTIMENT_PATH)
    sub_comments = comments[comments["subreddit"] == subreddit_name]

    sizes = community_df["community_id"].value_counts()
    keep = set(sizes[sizes >= config.MIN_COMMUNITY_SIZE].index)
    community_df = community_df[community_df["community_id"].isin(keep)]

    merged = sub_comments.merge(community_df[["user", "community_id"]].rename(columns={"user": "author"}),
                                on="author", how="inner")

    topics_path = f"data/processed/topics_{subreddit_name}.csv"
    has_topics = os.path.exists(topics_path)
    if has_topics:
        merged = merged.merge(pd.read_csv(topics_path), on="id", how="left")

    profile = merged.groupby("community_id").agg(
        num_users=("author", "nunique"),
        num_comments=("id", "count"),
        mean_sentiment=("sentiment_compound", "mean"),
        share_negative=("sentiment_label", lambda s: (s == "negative").mean()),
        share_rival_talk=("talk_target", lambda s: (s == "rival_talk").mean()),
    ).reset_index()

    if has_topics:
        topical = merged[merged["topic_id"] != NO_TOPIC]

        def modal(col):
            return topical.groupby("community_id")[col].agg(
                lambda x: x.mode().iloc[0] if not x.mode().empty else "n/a")

        def modal_share(col):
            return topical.groupby("community_id")[col].agg(lambda x: x.value_counts(normalize=True).iloc[0])

        profile = profile.merge(modal("topic_words").rename("modal_topic"), on="community_id", how="left")
        profile = profile.merge(modal_share("topic_words").rename("modal_topic_share"),
                                on="community_id", how="left")

        # The modal topic is usually just the subreddit's biggest topic, so it barely separates
        # communities. The distinctive topic is the one most OVER-represented in the community
        # relative to the whole subreddit (lift > 1), needing at least 5 comments to count.
        all_topics = pd.read_csv(topics_path)
        baseline = all_topics[all_topics["topic_id"] != NO_TOPIC]["topic_words"].value_counts(normalize=True)

        def distinctive(group):
            counts = group["topic_words"].value_counts()
            counts = counts[counts >= 5]
            if counts.empty:
                return pd.Series({"distinctive_topic": "n/a", "distinctive_topic_lift": float("nan")})
            lift = (counts / len(group)) / baseline.reindex(counts.index)
            return pd.Series({"distinctive_topic": lift.idxmax(), "distinctive_topic_lift": lift.max()})

        dist = topical.groupby("community_id")[["topic_words"]].apply(distinctive).reset_index()
        profile = profile.merge(dist, on="community_id", how="left")

    profile = profile.sort_values("num_users", ascending=False)
    profile.to_csv(f"data/processed/community_profile_{subreddit_name}.csv", index=False)
    logger.info(f"r/{subreddit_name} community profiles (communities with >= {config.MIN_COMMUNITY_SIZE} users):\n"
                f"{profile.to_string(index=False)}")


def analyze_network(subreddit_name):
    path = f"{config.NETWORKS_DIR}/network_{subreddit_name}.gexf"
    G = nx.read_gexf(path)
    n = G.number_of_nodes()

    if n < 3:
        logger.warning(f"r/{subreddit_name}: network too small ({n} nodes) for meaningful centrality analysis.")
        return None

    degree_cent = nx.degree_centrality(G)

    if n > config.BETWEENNESS_EXACT_MAX_NODES:
        betweenness_cent = nx.betweenness_centrality(G, k=min(config.BETWEENNESS_SAMPLE_K, n), seed=42)
        method = f"approximated (k={config.BETWEENNESS_SAMPLE_K} sampled sources)"
    else:
        betweenness_cent = nx.betweenness_centrality(G)
        method = "exact"
    logger.info(f"r/{subreddit_name}: betweenness centrality {method} on {n} nodes.")

    centrality_df = pd.DataFrame({
        "user": list(degree_cent.keys()),
        "degree_centrality": list(degree_cent.values()),
        "betweenness_centrality": [betweenness_cent[u] for u in degree_cent.keys()],
    }).sort_values("betweenness_centrality", ascending=False)
    centrality_df.to_csv(f"data/processed/centrality_{subreddit_name}.csv", index=False)
    logger.info(f"Top 10 structurally central users in r/{subreddit_name} "
                f"(highest betweenness centrality in the observed reply network):\n"
                f"{centrality_df.head(10).to_string(index=False)}")

    components = list(nx.weakly_connected_components(G))
    lcc = max(components, key=len)
    logger.info(f"r/{subreddit_name}: {len(components)} weakly connected components; "
                f"largest has {len(lcc)} users ({100 * len(lcc) / n:.1f}% of the network).")

    G_undirected = G.to_undirected()
    partition = community_louvain.best_partition(G_undirected, weight="weight", random_state=42)
    modularity = community_louvain.modularity(partition, G_undirected, weight="weight")

    community_df = pd.DataFrame({"user": list(partition.keys()), "community_id": list(partition.values())})
    community_df["in_largest_component"] = community_df["user"].isin(lcc)
    community_df.to_csv(f"data/processed/communities_{subreddit_name}.csv", index=False)

    sizes = community_df["community_id"].value_counts()
    big = int((sizes >= config.MIN_COMMUNITY_SIZE).sum())
    logger.info(f"r/{subreddit_name}: {len(sizes)} communities detected, modularity Q = {modularity:.3f}; "
                f"{big} have >= {config.MIN_COMMUNITY_SIZE} users, {len(sizes) - big} are smaller fragments.")
    logger.info(sizes.head(15).to_string())

    nx.set_node_attributes(G, partition, "community")
    nx.set_node_attributes(G, betweenness_cent, "betweenness_centrality")
    nx.write_gexf(G, f"{config.NETWORKS_DIR}/network_{subreddit_name}_with_communities.gexf")

    profile_communities(subreddit_name, community_df)

    return {
        "subreddit": subreddit_name, "nodes": n, "edges": G.number_of_edges(),
        "density": round(nx.density(G), 6),
        "weakly_connected_components": len(components),
        "largest_component_users": len(lcc), "largest_component_pct": round(100 * len(lcc) / n, 2),
        "communities_total": len(sizes), "communities_min_size": big,
        "modularity": round(modularity, 4), "betweenness_method": method,
    }


def main():
    rows = [analyze_network(sub) for sub in config.SUBREDDITS]
    rows = [r for r in rows if r]
    if rows:
        pd.DataFrame(rows).to_csv(NETWORK_SUMMARY_PATH, index=False)


if __name__ == "__main__":
    main()
