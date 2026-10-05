import os
import sys
import pandas as pd
import networkx as nx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("network_build")

COVERAGE_PATH = "data/processed/network_coverage.csv"


def build_reply_graph(comments, posts, subreddit_name, extra_authors=None):
    """Directed weighted graph: edge commenter -> author of the thing replied to, weight = #replies.
    `extra_authors` optionally maps "t1_<id>" / "t3_<id>" -> anonymized author for parents that are
    not in the sample (see collect_parents). Returns (graph, stats dict)."""
    sub_comments = comments[comments["subreddit"] == subreddit_name]
    sub_posts = posts[posts["subreddit"] == subreddit_name]

    extra_authors = extra_authors or {}
    comment_author_lookup = {k: v for k, v in extra_authors.items() if k.startswith("t1_")}
    post_author_lookup = {k: v for k, v in extra_authors.items() if k.startswith("t3_")}
    comment_author_lookup.update(zip("t1_" + sub_comments["id"].astype(str), sub_comments["author"]))
    post_author_lookup.update(zip("t3_" + sub_posts["id"].astype(str), sub_posts["author"]))

    G = nx.DiGraph()
    dropped_self_loops = 0
    missing = {"t1": 0, "t3": 0, "other": 0}
    total = {"t1": 0, "t3": 0, "other": 0}

    for commenter, parent_id in zip(sub_comments["author"], sub_comments["parent_id"].astype(str)):
        if parent_id.startswith("t1_"):
            kind, parent_author = "t1", comment_author_lookup.get(parent_id)
        elif parent_id.startswith("t3_"):
            kind, parent_author = "t3", post_author_lookup.get(parent_id)
        else:
            kind, parent_author = "other", None
        total[kind] += 1

        if parent_author is None:
            missing[kind] += 1
            continue
        if parent_author == commenter:
            dropped_self_loops += 1
            continue

        if G.has_edge(commenter, parent_author):
            G[commenter][parent_author]["weight"] += 1
        else:
            G.add_edge(commenter, parent_author, weight=1)

    total_comments = len(sub_comments)
    dropped_missing_parent = sum(missing.values())
    resolvable = total_comments - dropped_missing_parent
    stats = {
        "subreddit": subreddit_name, "nodes": G.number_of_nodes(), "edges": G.number_of_edges(),
        "total_comments": total_comments, "resolvable_parent": resolvable,
        "missing_parent": dropped_missing_parent,
        "coverage_pct": round(100 * resolvable / max(total_comments, 1), 2),
        "replies_to_posts": total["t3"],
        "coverage_replies_to_posts_pct": round(100 * (total["t3"] - missing["t3"]) / max(total["t3"], 1), 2),
        "replies_to_comments": total["t1"],
        "coverage_replies_to_comments_pct": round(100 * (total["t1"] - missing["t1"]) / max(total["t1"], 1), 2),
        "self_loops_dropped": dropped_self_loops,
    }

    logger.info(f"r/{subreddit_name}: {stats['nodes']} nodes, {stats['edges']} edges")
    logger.info(f"  Total comments: {total_comments}")
    logger.info(f"  Comments with resolvable parent: {resolvable}")
    logger.info(f"  Comments with missing parent: {dropped_missing_parent}")
    logger.info(f"  Network coverage: {stats['coverage_pct']:.2f}%")
    logger.info(f"    replies to posts:    {stats['coverage_replies_to_posts_pct']:.2f}% of {total['t3']}")
    logger.info(f"    replies to comments: {stats['coverage_replies_to_comments_pct']:.2f}% of {total['t1']} "
                f"(parents outside the per-slot sample are looked up by id via collect_parents; the remainder are deleted/removed/bot parents)")
    logger.info(f"  Dropped (self-loops): {dropped_self_loops}")
    return G, stats


def main():
    os.makedirs(config.NETWORKS_DIR, exist_ok=True)
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    posts = pd.read_csv(config.CLEAN_POSTS_PATH)

    extra = None
    if os.path.exists(config.CLEAN_PARENTS_PATH):
        lk = pd.read_csv(config.CLEAN_PARENTS_PATH)
        extra = dict(zip(lk['kind'] + '_' + lk['id'].astype(str), lk['author']))
        logger.info(f'Using author lookup with {len(extra)} ids (sample + fetched parents).')

    all_stats = []
    for sub in config.SUBREDDITS:
        graph, stats = build_reply_graph(comments, posts, sub, extra)
        nx.write_gexf(graph, f"{config.NETWORKS_DIR}/network_{sub}.gexf")
        all_stats.append(stats)
    pd.DataFrame(all_stats).to_csv(COVERAGE_PATH, index=False)


if __name__ == "__main__":
    main()
