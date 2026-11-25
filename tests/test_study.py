import json
from pathlib import Path

import networkx as nx
import pandas as pd
import pytest

from src.study_data import load_window, timestamp, validate_day, read_design, Archive
from src.study_network import graph_from_comments, export_gephi
from src.study_analysis import overlap_counts, valid_users, prepare
from src.network_analysis import undirected_sum
from src.collect_full import collect_day
from src.utils import anonymize


def test_sum_reciprocal_reply_weights():
    g = nx.DiGraph()
    g.add_edge("a", "b", weight=7)
    g.add_edge("b", "a", weight=3)
    g.add_node("isolated")
    u = undirected_sum(g)
    assert u["a"]["b"]["weight"] == 10
    assert len(u) == 3


def test_network_conserves_events_and_preserves_isolates():
    comments = pd.DataFrame({"author": ["a", "b", "b", "c", "d"],
                             "parent_id": ["t3_post", "t1_a", "t1_a", "t1_c", "t1_missing"]})
    lookup = {"t3_post": "p", "t1_a": "a", "t1_c": "c"}
    graph, stats = graph_from_comments(comments, lookup)
    assert stats["reply_events"] + stats["self_replies_removed"] + stats["missing_parent"] == len(comments)
    assert graph["b"]["a"]["weight"] == 2
    assert graph.has_node("d") and graph.degree("d") == 0
    replies, s = graph_from_comments(comments, lookup, comment_only=True)
    assert not replies.has_node("p") and s["excluded_top_level"] == 1


def test_missing_users_are_not_one_synthetic_account():
    assert anonymize(float("nan")) == "[deleted]"
    assert anonymize("[removed]") == "[deleted]"
    raw = pd.DataFrame({"author": [None, "AutoModerator", "automoderator", "[deleted]", "real"]})
    assert valid_users(raw)["author"].tolist() == ["real"]


def test_validation_rejects_boundary_leak_and_duplicate_ids(tmp_path):
    path = tmp_path / "day.csv"
    df = pd.DataFrame({"id": ["x"], "subreddit": ["A"], "author": ["u"], "created_utc": [200]})
    df.to_csv(path, index=False)
    with pytest.raises(ValueError, match="outside"):
        validate_day(path, "A", 100, 200, light=True)
    pd.concat([df, df]).to_csv(path, index=False)
    with pytest.raises(ValueError, match="duplicate"):
        validate_day(path, "A", 100, 300, light=True)


def test_replication_requires_every_expected_day(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    w = {"id": "x", "start": "2026-09-03", "end": "2026-09-05", "legacy_cache": "old"}
    folder = Path("old/A")
    folder.mkdir(parents=True)
    t = timestamp(w["start"])
    pd.DataFrame({"id": ["x"], "author": ["a"], "subreddit": ["A"], "created_utc": [t]}).to_csv(folder / f"{t}.csv", index=False)
    with pytest.raises(FileNotFoundError, match="Missing"):
        load_window(w, ["A"], light=True)


def test_pagination_safety_cap_cannot_be_a_complete_day(monkeypatch):
    import src.collect_full as cf
    import config
    monkeypatch.setattr(cf, "MAX_PAGES_PER_DAY", 1)
    monkeypatch.setattr(config, "PAGE_LIMIT", 2)
    monkeypatch.setattr(cf, "fetch_page", lambda *args: [{"id": "a", "created_utc": 190}, {"id": "b", "created_utc": 180}])
    with pytest.raises(RuntimeError, match="safety cap"):
        collect_day("A", 100, 200, True)


def test_saturated_second_fails_loudly(monkeypatch):
    api = Archive()
    monkeypatch.setattr(api, "get", lambda *args: [{"id": str(i), "created_utc": 150} for i in range(100)])
    with pytest.raises(RuntimeError, match="timestamp"):
        api.collect_day("A", 100, 200, light=True)


def test_gephi_round_trip_preserves_direction_weight_and_handles_empty(tmp_path):
    graph = nx.DiGraph()
    graph.add_edge("user_a", "user_b", weight=4)
    graph.nodes["user_a"].update(community=0, pagerank=.2, in_strength=1.)
    graph.nodes["user_b"].update(community=1, pagerank=.8, in_strength=4.)
    meta = export_gephi(graph, tmp_path, "test")
    loaded = nx.read_gexf(tmp_path / "test_full.gexf")
    assert loaded.is_directed() and loaded["user_a"]["user_b"]["weight"] == 4
    assert meta["full_nodes"] == 2
    assert export_gephi(nx.DiGraph(), tmp_path, "empty")["focus_nodes"] == 0


def test_overlap_uses_explicit_denominators():
    counts = {"A": pd.Series({"one": 5, "shared": 2}), "B": pd.Series({"shared": 2})}
    row = overlap_counts(counts, "A", "B")
    assert row["pct_a"] == 50 and row["pct_b"] == 100 and row["jaccard_pct"] == 50
    assert overlap_counts(counts, "A", "B", 5)["shared"] == 0


def test_console_mentions_are_pair_specific():
    d = read_design()
    pair = d["pairs"][1]
    raw = pd.DataFrame({"id": ["a", "b", "c"], "author": ["u"] * 3,
        "subreddit": ["PS5", "PS5", "xbox"], "parent_id": ["t3_p"] * 3, "link_id": ["t3_p"] * 3,
        "body": ["I love Xbox games", "PlayStation and Xbox are great", "Sony made a terrible decision"]})
    out = prepare(raw, pair, d)
    assert out["target"].tolist() == ["rival_talk", "both", "rival_talk"]


def test_comparative_pipeline_end_to_end(tmp_path, monkeypatch):
    from src.study_analysis import analyze_pair
    from src.study_report import report
    from src.collect_full import FULL_FIELDS
    import src.utils as utils
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(utils, "_SALT", "synthetic-test-only")
    pair = {"id": "testpair", "communities": ["A", "B"]}
    design = {"seed": 42, "pairs": [pair], "baselines": [], "output_dir": "outputs/study",
              "aliases": {"A": ["alpha"], "B": ["beta"]},
              "windows": [{"id": "sep", "start": "2026-09-03", "end": "2026-09-04"},
                          {"id": "oct", "start": "2026-10-01", "end": "2026-10-02"}],
              "network": {"betweenness_sources": 8, "null_replicates": 2, "layout_node_limit": 30},
              "bootstrap_replicates": 50, "topic_candidates": [2], "topic_training_limit": 100}
    Path(design["output_dir"]).mkdir(parents=True)
    for w in design["windows"]:
        t = timestamp(w["start"])
        for sub in ["A", "B"]:
            rows = []
            for i in range(60):
                cid = f"{sub}{t}{i}"
                parent = f"t1_{sub}{t}{max(i-1,0)}"
                body = ["alpha great wonderful acting scenes", "beta awful boring acting scenes", "alpha beta story amazing actors", "interesting screenplay character music scene"][i % 4]
                rows.append(dict(zip(FULL_FIELDS, [cid, sub, f"t3_{sub}thread{i%4}", parent, f"shared_{i%10}", body, 1, t + i])))
            folder = Path("data/raw/study") / sub
            folder.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows).to_csv(folder / f"{t}.csv", index=False)
    analyze_pair(design, pair)
    overlap = pd.read_csv("outputs/study/tables/testpair_overlap.csv")
    assert (overlap["shared"] == 10).all()
    network = pd.read_csv("outputs/study/tables/testpair_networks.csv")
    assert len(network) == 8 and (network["resolved_parent_pct"] == 100).all()
    centrality = pd.read_csv("outputs/study/private/testpair_sep_A_all_replies_connectors.csv")
    assert {"threads_participated", "shared_in_pair"} <= set(centrality)
    marker = Path("outputs/study/private/testpair_complete.json")
    first_mtime = marker.stat().st_mtime_ns
    analyze_pair(design, pair)
    assert marker.stat().st_mtime_ns == first_mtime  # cache validates actual output hashes
    report(design)
    assert "AI assistant" in Path("REPORT.md").read_text(encoding="utf-8")
    assert Path("outputs/study/figures/overlap.png").is_file()
    for path in Path("outputs/study/tables").glob("*.csv"):
        assert "shared_" not in path.read_text(encoding="utf-8").replace("shared_users_comment_share_pct", "")
