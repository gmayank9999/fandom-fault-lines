import os
import sys

import networkx as nx
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("gephi_export")

PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
GREY = "#b9b8b2"


def _rgb(hex_color):
    return {"r": int(hex_color[1:3], 16), "g": int(hex_color[3:5], 16),
            "b": int(hex_color[5:7], 16), "a": 1.0}


def export_core(subreddit):
    """Write a Gephi-ready file of the dense core (2-core of the largest component), with layout
    positions, node size = betweenness and colour = Louvain community (8 largest, grey = others)
    already set, so it opens as a readable picture without any filtering in Gephi.
    This is a visual filter only: all metrics in the CSVs use the full network."""
    src = f"{config.NETWORKS_DIR}/network_{subreddit}_with_communities.gexf"
    G = nx.read_gexf(src)
    lcc = max(nx.weakly_connected_components(G), key=len)
    core = nx.k_core(nx.Graph(G.subgraph(lcc).to_undirected()), 2)
    H = G.subgraph(core.nodes()).copy()

    community = nx.get_node_attributes(H, "community")
    top = list(pd.Series(community).value_counts().head(len(PALETTE)).index)
    color = {c: PALETTE[i] for i, c in enumerate(top)}
    betweenness = np.array([float(H.nodes[n].get("betweenness_centrality", 0)) for n in H.nodes()])
    scale = betweenness.max() if betweenness.max() > 0 else 1.0
    pos = nx.spring_layout(core, seed=42, iterations=100, k=1.5 / np.sqrt(core.number_of_nodes()))

    for node, b in zip(H.nodes(), betweenness):
        x, y = pos[node]
        H.nodes[node]["viz"] = {
            "position": {"x": float(x) * 1000, "y": float(y) * 1000, "z": 0.0},
            "size": float(5 + 45 * (b / scale)),
            "color": _rgb(color.get(community[node], GREY)),
        }

    out = f"{config.NETWORKS_DIR}/network_{subreddit}_core_for_gephi.gexf"
    nx.write_gexf(H, out)
    logger.info(f"r/{subreddit}: wrote {out} ({H.number_of_nodes()} nodes, {H.number_of_edges()} edges)")


def main():
    for sub in config.SUBREDDITS:
        export_core(sub)


if __name__ == "__main__":
    main()
