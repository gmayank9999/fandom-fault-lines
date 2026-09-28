import os
import sys
import pandas as pd
import networkx as nx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("network_build")


def build_reply_graph(comments, posts, subreddit_name):
    sub_comments = comments[comments["subreddit"] == subreddit_name]
    sub_posts = posts[posts["subreddit"] == subreddit_name]

    comment_author_lookup = {("t1_" + str(row["id"])): row["author"] for _, row in sub_comments.iterrows()}
    post_author_lookup = {("t3_" + str(row["id"])): row["author"] for _, row in sub_posts.iterrows()}

    G = nx.DiGraph()
    dropped_self_loops = 0
    dropped_missing_parent = 0

    for _, row in sub_comments.iterrows():
        commenter = row["author"]
        parent_id = str(row["parent_id"])

        if parent_id.startswith("t1_"):
            parent_author = comment_author_lookup.get(parent_id)
        elif parent_id.startswith("t3_"):
            parent_author = post_author_lookup.get(parent_id)
        else:
            parent_author = None

        if parent_author is None:
            dropped_missing_parent += 1
            continue

        if parent_author == commenter:
            dropped_self_loops += 1
            continue

        if G.has_edge(commenter, parent_author):
            G[commenter][parent_author]["weight"] += 1
        else:
            G.add_edge(commenter, parent_author, weight=1)

    total_comments = len(sub_comments)
    resolvable = total_comments - dropped_missing_parent
    coverage_pct = 100 * resolvable / max(total_comments, 1)

    logger.info(f"r/{subreddit_name}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    logger.info(f"  Total comments: {total_comments}")
    logger.info(f"  Comments with resolvable parent: {resolvable}")
    logger.info(f"  Comments with missing parent: {dropped_missing_parent}")
    logger.info(f"  Network coverage: {coverage_pct:.2f}%")
    logger.info(f"  Dropped (self-loops): {dropped_self_loops}")
    return G


def main():
    os.makedirs(config.NETWORKS_DIR, exist_ok=True)
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    posts = pd.read_csv(config.CLEAN_POSTS_PATH)

    for sub in config.SUBREDDITS:
        graph = build_reply_graph(comments, posts, sub)
        nx.write_gexf(graph, f"{config.NETWORKS_DIR}/network_{sub}.gexf")


if __name__ == "__main__":
    main()
