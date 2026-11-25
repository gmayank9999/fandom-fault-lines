"""Publish aggregate connector roles without exposing individual account IDs."""
from pathlib import Path

import pandas as pd

from src.study_data import read_design


def summarize_nodes(nodes, top_k=20):
    observed = nodes["observed_commenter"].astype(str).str.lower().eq("true")
    shared = nodes["shared_in_pair"].astype(str).str.lower().eq("true")
    rows = []
    for metric in ("betweenness", "pagerank", "in_strength"):
        values = pd.to_numeric(nodes[metric], errors="coerce")
        positive = values[values > 0].sort_values(ascending=False)
        cutoff = positive.iloc[min(top_k, len(positive)) - 1] if len(positive) else float("nan")
        selected = (values > 0) & (values >= cutoff)
        selected_observed = selected & observed
        rows.append({
            "ranking": metric, "top_requested": top_k, "cutoff_value": cutoff,
            "selection": "positive scores; include every tie at the cutoff",
            "observed_commenters": int(observed.sum()),
            "observed_shared_pct": 100 * shared[observed].mean(),
            "selected_nodes": int(selected.sum()),
            "selected_observed_commenters": int(selected_observed.sum()),
            "selected_parent_only_nodes": int((selected & ~observed).sum()),
            "selected_shared_commenters": int((selected_observed & shared).sum()),
            "selected_shared_pct_of_observed": 100 * shared[selected_observed].mean(),
            "selected_observed_median_threads": nodes.loc[selected_observed, "threads_participated"].median(),
            "selected_observed_median_participation_coefficient": nodes.loc[selected_observed, "participation_coefficient"].median(),
        })
    return rows


def summarize(design):
    out = Path(design["output_dir"])
    for pair in design["pairs"]:
        rows = []
        for window in design["windows"]:
            for sub in pair["communities"]:
                for variant in ("all_replies", "comment_replies"):
                    source = out / "private" / f"{pair['id']}_{window['id']}_{sub}_{variant}_centrality.csv"
                    if not source.exists():
                        rows = []
                        break
                    nodes = pd.read_csv(source)
                    rows.extend({"pair": pair["id"], "window": window["id"], "subreddit": sub,
                                 "variant": variant, **r} for r in summarize_nodes(nodes))
        expected = len(design["windows"]) * len(pair["communities"]) * 2 * 3
        if len(rows) == expected:
            pd.DataFrame(rows).to_csv(out / f"{pair['id']}_connector_roles.csv", index=False)


if __name__ == "__main__":
    summarize(read_design())
