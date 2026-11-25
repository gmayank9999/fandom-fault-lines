"""Reply-network measurements and Gephi exports with explicit graph semantics."""
from pathlib import Path

import community as louvain
import networkx as nx
import numpy as np
import pandas as pd

from src.network_analysis import undirected_sum, null_modularity
from src.gephi_export import PALETTE, _rgb


def graph_from_comments(comments, author_lookup, comment_only=False):
    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(set(comments["author"])))
    missing, self_replies, excluded = 0, 0, 0
    for author, parent in zip(comments["author"], comments["parent_id"]):
        if comment_only and not str(parent).startswith("t1_"):
            excluded += 1
            continue
        other = author_lookup.get(parent)
        if not other or other == "[deleted]":
            missing += 1
            continue
        if author == other:
            self_replies += 1
            continue
        if graph.has_edge(author, other):
            graph[author][other]["weight"] += 1
        else:
            graph.add_edge(author, other, weight=1)
    eligible = len(comments) - excluded
    return graph, {"eligible_comments": eligible, "missing_parent": missing,
                   "resolved_parent_pct": 100 * (eligible - missing) / eligible if eligible else np.nan,
                   "self_replies_removed": self_replies,
                   "reply_events": int(graph.size(weight="weight")), "excluded_top_level": excluded}


def metrics(graph, settings, seed=42, expensive=True):
    n, m = len(graph), graph.number_of_edges()
    result = {"nodes": n, "edges": m, "isolates": nx.number_of_isolates(graph),
              "density": nx.density(graph), "reciprocity": nx.reciprocity(graph) if m else np.nan}
    if not n or not m:
        return result, pd.DataFrame(), graph
    undirected = undirected_sum(graph)
    components = list(nx.connected_components(undirected))
    result.update(weak_components=len(components), largest_component_pct=100 * max(map(len, components)) / n,
                  transitivity=nx.transitivity(undirected), mean_clustering=nx.average_clustering(undirected))
    partition = louvain.best_partition(undirected, weight="weight", random_state=seed)
    result["modularity_weighted"] = louvain.modularity(partition, undirected, weight="weight")
    result["communities"] = len(set(partition.values()))
    if expensive:
        topology = nx.Graph()
        topology.add_nodes_from(undirected)
        topology.add_edges_from(undirected.edges())
        tp = louvain.best_partition(topology, random_state=seed)
        observed = louvain.modularity(tp, topology)
        mean, sd = null_modularity(topology, settings["null_replicates"], seed)
        result.update(modularity_unweighted=observed, null_mean=mean, null_sd=sd,
                      modularity_excess=observed - mean, null_requested=settings["null_replicates"],
                      null_interpretation="descriptive topology null; no significance claim")
    k = min(n, settings["betweenness_sources"])
    bc = nx.betweenness_centrality(graph, k=k if k < n else None, seed=seed, weight=None)
    result["betweenness_sources"] = k
    # A different seed quantifies approximation stability, rather than silently
    # interpreting a tiny rank difference as a meaningful connector distinction.
    if expensive and k < n:
        bc2 = nx.betweenness_centrality(graph, k=k, seed=seed + 1, weight=None)
        top1 = set(sorted(bc, key=bc.get, reverse=True)[:20])
        top2 = set(sorted(bc2, key=bc2.get, reverse=True)[:20])
        result["top20_betweenness_seed_overlap"] = len(top1 & top2) / len(top1 | top2)
    pagerank = nx.pagerank(graph, weight="weight")
    core = nx.core_number(undirected)
    strength_in, strength_out = dict(graph.in_degree(weight="weight")), dict(graph.out_degree(weight="weight"))
    rows = []
    for node in sorted(graph):
        weights = {}
        for neighbor, edge in undirected[node].items():
            c = partition[neighbor]
            weights[c] = weights.get(c, 0) + edge["weight"]
        total = sum(weights.values())
        participation = 1 - sum((w / total) ** 2 for w in weights.values()) if total else 0
        attrs = {"community": int(partition[node]), "betweenness": float(bc[node]),
                 "pagerank": float(pagerank[node]), "in_degree": graph.in_degree(node),
                 "out_degree": graph.out_degree(node), "in_strength": float(strength_in[node]),
                 "out_strength": float(strength_out[node]), "core_number": int(core[node]),
                 "participation_coefficient": float(participation)}
        graph.nodes[node].update(attrs)
        rows.append({"Id": node, **attrs})
    return result, pd.DataFrame(rows), graph


def export_gephi(graph, folder, stem, node_limit=1200, seed=42):
    """Full directed graph + CSVs; bounded visual focus for a readable preview.

    No claimed ForceAtlas2 layout: positions are a deterministic spring layout.
    Gephi can recompute ForceAtlas2 on either file.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    nx.write_gexf(graph, folder / f"{stem}_full.gexf")
    pd.DataFrame([{"Id": n, "Label": n, **a} for n, a in graph.nodes(data=True)]).to_csv(folder / f"{stem}_nodes.csv", index=False)
    pd.DataFrame([{"Source": a, "Target": b, "Type": "Directed", "Weight": d["weight"]}
                  for a, b, d in graph.edges(data=True)], columns=["Source", "Target", "Type", "Weight"]).to_csv(folder / f"{stem}_edges.csv", index=False)
    if not len(graph) or not graph.number_of_edges():
        return {"file": stem, "full_nodes": len(graph), "full_edges": graph.number_of_edges(), "focus_nodes": 0, "focus_edges": 0}
    ug = undirected_sum(graph)
    largest = max(nx.connected_components(ug), key=len)
    focus = nx.k_core(ug.subgraph(largest), k=2)
    if not len(focus):
        focus = ug.subgraph(largest).copy()
    if len(focus) > node_limit:
        keep = sorted(focus, key=lambda n: (-graph.nodes[n].get("pagerank", 0), n))[:node_limit]
        focus = focus.subgraph(keep).copy()
    shown = graph.subgraph(focus).copy()
    pos = nx.spring_layout(focus, seed=seed, iterations=40, weight="weight")
    for node in shown:
        attrs = shown.nodes[node]
        attrs["viz"] = {"position": {"x": float(pos[node][0]) * 1000, "y": float(pos[node][1]) * 1000, "z": 0.0},
                        "color": _rgb(PALETTE[int(attrs.get("community", 0)) % len(PALETTE)]),
                        "size": float(3 + 3 * np.log1p(attrs.get("in_strength", 0)))}
    nx.write_gexf(shown, folder / f"{stem}_focus.gexf")
    return {"file": stem, "full_nodes": len(graph), "full_edges": graph.number_of_edges(),
            "focus_nodes": len(shown), "focus_edges": shown.number_of_edges(),
            "filter": "largest weak component, 2-core; capped by PageRank for display only",
            "layout": "NetworkX spring; seed=" + str(seed), "metrics_scope": "full graph"}
