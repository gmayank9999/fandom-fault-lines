import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("visualize")

# Validated categorical palette (slots 1-2 for the two subreddits; colour follows the entity,
# never its rank). Text always wears ink colours, never the series colour.
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
SUB_COLOR = {config.SUBREDDITS[0]: "#2a78d6", config.SUBREDDITS[1]: "#eb6834"}
COMMUNITY_COLORS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
OTHER_GREY = "#b9b8b2"
TARGET_ORDER = ["self_talk", "rival_talk", "both", "general"]


def style(ax, title):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, color=INK, loc="left", fontsize=12)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2)
    ax.yaxis.label.set_color(INK_2)
    ax.xaxis.label.set_color(INK_2)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def new_fig(w, h):
    fig, ax = plt.subplots(figsize=(w, h), facecolor=SURFACE)
    return fig, ax


def legend(ax):
    leg = ax.legend(frameon=False, loc="best")
    for t in leg.get_texts():
        t.set_color(INK)


def sentiment_by_target_chart():
    df = pd.read_csv(config.SENTIMENT_BY_TARGET_PATH)
    fig, ax = new_fig(9, 5)
    width = 0.38
    x = np.arange(len(TARGET_ORDER))
    for i, sub in enumerate(config.SUBREDDITS):
        d = df[df["subreddit"] == sub].set_index("talk_target").reindex(TARGET_ORDER)
        err = 1.96 * d["std"] / np.sqrt(d["count"])
        pos = x + (i - 0.5) * (width + 0.02)
        ax.bar(pos, d["mean"], width, yerr=err, color=SUB_COLOR[sub], label=f"r/{sub}",
               error_kw={"ecolor": INK_2, "elinewidth": 1, "capsize": 3})
    counts = {sub: df[df["subreddit"] == sub].set_index("talk_target")["count"].reindex(TARGET_ORDER)
              for sub in config.SUBREDDITS}
    names = ["about own\nfranchise", "about rival\nfranchise", "about both", "about neither"]
    ax.axhline(0, color=INK_2, linewidth=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{nm}\nn = " + " / ".join(str(int(counts[s].iloc[i])) for s in config.SUBREDDITS)
                        for i, nm in enumerate(names)], fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("mean VADER sentiment (95% CI)")
    style(ax, "Sentiment by what the comment is about")
    legend(ax)
    fig.tight_layout()
    fig.savefig(f"{config.CHARTS_DIR}/chart_sentiment_by_target.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def topic_prevalence_chart():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), facecolor=SURFACE)
    for ax, sub in zip(axes, config.SUBREDDITS):
        path = f"data/processed/topic_summary_{sub}.csv"
        if not os.path.exists(path):
            continue
        s = pd.read_csv(path).sort_values("share")
        labels = [", ".join(str(w).split(", ")[:3]) if tid != -1 else "(too short)"
                  for tid, w in zip(s["topic_id"], s["topic_words"])]
        ax.barh(labels, s["share"] * 100, color=SUB_COLOR[sub])
        for y, v in enumerate(s["share"] * 100):
            ax.text(v + 0.4, y, f"{v:.0f}%", va="center", fontsize=8, color=INK)
        ax.set_xlabel("% of comments")
        style(ax, f"r/{sub}: topic share")
        ax.grid(axis="x", color=GRID, linewidth=0.8)
        ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(f"{config.CHARTS_DIR}/chart_topic_prevalence.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def overlap_chart():
    if not os.path.exists(config.OVERLAP_SUMMARY_PATH):
        return
    df = pd.read_csv(config.OVERLAP_SUMMARY_PATH)
    sub_a, sub_b = config.SUBREDDITS
    fig, ax = new_fig(9, 5)
    x = np.arange(len(df))
    width = 0.38
    for i, sub in enumerate(config.SUBREDDITS):
        pos = x + (i - 0.5) * (width + 0.02)
        vals = df[f"pct_of_{sub}"]
        ax.bar(pos, vals, width, color=SUB_COLOR[sub], label=f"share of r/{sub} users also in the other")
        for xp, v in zip(pos, vals):
            ax.text(xp, v + 0.1, f"{v:.1f}%", ha="center", fontsize=8, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels([d.replace(" (", "\n(") for d in df["definition"]], fontsize=8)
    ax.set_ylabel("% of users")
    style(ax, "Cross-community overlap under three definitions of 'user'")
    legend(ax)
    fig.tight_layout()
    fig.savefig(f"{config.CHARTS_DIR}/chart_overlap.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def network_picture(sub):
    """Static picture of the reply network for the report. Gephi remains the tool for an
    interactive version. For legibility only the 2-core of the largest component is drawn
    (visual filter only: all metrics in the CSVs use the full network)."""
    path = f"{config.NETWORKS_DIR}/network_{sub}_with_communities.gexf"
    if not os.path.exists(path):
        return
    G = nx.read_gexf(path)
    lcc = max(nx.weakly_connected_components(G), key=len)
    H = G.subgraph(lcc).to_undirected()
    H = nx.k_core(nx.Graph(H), 2)
    if H.number_of_nodes() < 3:
        return

    comm = nx.get_node_attributes(H, "community")
    top = [c for c, _ in pd.Series(comm).value_counts().head(len(COMMUNITY_COLORS)).items()]
    color_of = {c: COMMUNITY_COLORS[i] for i, c in enumerate(top)}
    colors = [color_of.get(comm[n], OTHER_GREY) for n in H.nodes()]
    bc = np.array([float(H.nodes[n].get("betweenness_centrality", 0)) for n in H.nodes()])
    sizes = 6 + 900 * (bc / bc.max() if bc.max() > 0 else bc)

    pos = nx.spring_layout(H, seed=42, iterations=80, k=1.2 / np.sqrt(H.number_of_nodes()))
    fig, ax = new_fig(10, 10)
    ax.set_facecolor(SURFACE)
    nx.draw_networkx_edges(H, pos, ax=ax, edge_color="#cfcec8", width=0.3, alpha=0.6)
    nx.draw_networkx_nodes(H, pos, ax=ax, node_color=colors, node_size=sizes, linewidths=0.3,
                           edgecolors=SURFACE)
    ax.set_axis_off()
    ax.set_title(f"r/{sub} reply network: 2-core of largest component ({H.number_of_nodes()} users). "
                 f"Colour = Louvain community (8 largest, grey = others); size = betweenness.",
                 color=INK, loc="left", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{config.CHARTS_DIR}/network_{sub}.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)
    logger.info(f"Saved network picture for r/{sub} ({H.number_of_nodes()} nodes drawn).")


def main():
    os.makedirs(config.CHARTS_DIR, exist_ok=True)
    sentiment_by_target_chart()
    topic_prevalence_chart()
    overlap_chart()
    for sub in config.SUBREDDITS:
        network_picture(sub)
    logger.info("Figures saved to outputs/charts/")


if __name__ == "__main__":
    main()
