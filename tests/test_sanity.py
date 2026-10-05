import os
import sys

import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import anonymize, compile_alias_regex, get_stopwords
from src.preprocess import clean_text
from src.sentiment import categorize, tag_target
from src.collect_comments import make_slots
from src.network_build import build_reply_graph
from src.topic_modeling import assign_topics, NO_TOPIC
from src.statistical_tests import run_mannwhitney, holm_correct
from src.overlap_analysis import overlap_row
from src.connector_analysis import classify_role


# ---------------- utils / preprocessing ----------------
def test_anonymize_is_deterministic():
    assert anonymize("real_user_123") == anonymize("real_user_123")


def test_anonymize_different_users_differ():
    assert anonymize("alice") != anonymize("bob")


def test_anonymize_handles_deleted():
    assert anonymize("[deleted]") == "[deleted]"
    assert anonymize(None) == "[deleted]"


def test_anonymize_hides_real_name():
    assert "alice" not in anonymize("alice")


def test_clean_text_strips_urls():
    assert "http" not in clean_text("check this out https://example.com/page nice")


def test_clean_text_collapses_whitespace():
    assert clean_text("hello    world\n\n") == "hello world"


def test_clean_text_removes_gif_embeds_and_keeps_link_text():
    assert clean_text("![gif](giphy|abc123|downsized) so good") == "so good"
    assert clean_text("see [this thread](https://reddit.com/x) now") == "see this thread now"


def test_stopwords_include_filler_and_standard_words():
    sw = get_stopwords()
    assert "the" in sw and "lol" in sw and "giphy" in sw


# ---------------- frozen window / stratified sampling ----------------
def test_slots_cover_window_without_gaps_or_overlap():
    slots = make_slots()
    assert slots[0][0] == config.AFTER_TS
    assert slots[-1][1] == config.BEFORE_TS
    for (a1, b1), (a2, b2) in zip(slots, slots[1:]):
        assert b1 == a2
    assert len(slots) == config.WINDOW_DAYS * config.SLOTS_PER_DAY


def test_window_is_frozen_not_relative_to_now():
    import importlib
    first = (config.AFTER_TS, config.BEFORE_TS)
    importlib.reload(config)
    assert (config.AFTER_TS, config.BEFORE_TS) == first


# ---------------- alias matching & target tagging ----------------
def test_alias_regex_matches_whole_words_only():
    rx = compile_alias_regex(["dc", "iron man"])
    assert rx.search("I love DC movies")
    assert rx.search("the new Iron Man suit")
    assert not rx.search("adc is a thing")
    assert not rx.search("abcdc")


def test_sentiment_categorize_thresholds():
    assert categorize(0.5) == "positive"
    assert categorize(-0.5) == "negative"
    assert categorize(0.0) == "neutral"
    assert categorize(0.04) == "neutral"
    assert categorize(0.05) == "positive"


def _row(text, sub="marvelstudios"):
    return pd.Series({"body_clean": text, "subreddit": sub})


def test_tag_target_classifies_four_ways():
    a, b = "marvelstudios", "DC_Cinematic"
    assert tag_target(_row("marvel is doing great this year"), a, b) == "self_talk"
    assert tag_target(_row("dc really nailed this one"), a, b) == "rival_talk"
    assert tag_target(_row("marvel and dc are both having a good year"), a, b) == "both"
    assert tag_target(_row("i love going to the movies"), a, b) == "general"


def test_tag_target_ignores_substring_false_positives():
    a, b = "marvelstudios", "DC_Cinematic"
    assert tag_target(_row("my adc build is broken"), a, b) == "general"


def test_tag_target_is_symmetric_for_the_other_subreddit():
    a, b = "marvelstudios", "DC_Cinematic"
    assert tag_target(_row("batman was great", "DC_Cinematic"), a, b) == "self_talk"
    assert tag_target(_row("the mcu is great", "DC_Cinematic"), a, b) == "rival_talk"


# ---------------- network construction (real function, synthetic data) ----------------
def _fake_data():
    posts = pd.DataFrame({"id": ["p1"], "subreddit": ["s"], "author": ["user_P"]})
    comments = pd.DataFrame({
        "id": ["c1", "c2", "c3", "c4", "c5", "c6"],
        "subreddit": ["s"] * 6,
        "author": ["user_A", "user_B", "user_B", "user_A", "user_C", "user_D"],
        "parent_id": ["t3_p1",      # A -> P   (reply to post)
                      "t1_c1",      # B -> A   (reply to comment)
                      "t1_c2",      # B -> B   (self loop, dropped)
                      "t1_c2",      # A -> B
                      "t1_gone",    # parent not collected, dropped
                      "t3_p1"],     # D -> P
    })
    return comments, posts


def test_build_reply_graph_edges_weights_and_drops():
    comments, posts = _fake_data()
    G, stats = build_reply_graph(comments, posts, "s")
    assert set(G.edges()) == {("user_A", "user_P"), ("user_B", "user_A"),
                              ("user_A", "user_B"), ("user_D", "user_P")}
    assert not G.has_edge("user_B", "user_B")
    assert stats["self_loops_dropped"] == 1
    assert stats["missing_parent"] == 1
    assert stats["resolvable_parent"] == 5
    assert stats["coverage_pct"] == pytest.approx(100 * 5 / 6, abs=0.01)
    assert stats["coverage_replies_to_posts_pct"] == 100.0


def test_build_reply_graph_counts_repeat_replies_as_weight():
    comments, posts = _fake_data()
    extra = pd.DataFrame({"id": ["c7"], "subreddit": ["s"], "author": ["user_A"], "parent_id": ["t3_p1"]})
    G, _ = build_reply_graph(pd.concat([comments, extra]), posts, "s")
    assert G["user_A"]["user_P"]["weight"] == 2


# ---------------- topic modeling ----------------
def test_assign_topics_gives_uninformative_comments_no_topic():
    topic_matrix = np.array([[0.9, 0.1], [0.0, 0.0], [0.2, 0.8]])
    tfidf = sp.csr_matrix(np.array([[1, 1, 1, 1], [0, 0, 0, 0], [1, 1, 1, 0]], dtype=float))
    out = assign_topics(topic_matrix, tfidf, min_tokens=3)
    assert list(out) == [0, NO_TOPIC, 1]


# ---------------- statistics ----------------
def test_mannwhitney_effect_size_sign_and_range():
    high = pd.Series([0.8, 0.7, 0.9, 0.6, 0.75, 0.85])
    low = pd.Series([-0.5, -0.4, -0.6, -0.3, -0.55, -0.45])
    res = run_mannwhitney(high, low, "x")
    assert res["effect_size_r"] == pytest.approx(1.0)
    assert run_mannwhitney(low, high, "x")["effect_size_r"] == pytest.approx(-1.0)
    assert res["p_value"] < 0.05


def test_mannwhitney_small_sample_returns_none():
    res = run_mannwhitney(pd.Series([0.1, 0.2]), pd.Series([0.3] * 10), "x")
    assert res["p_value"] is None and res["note"] == "sample too small"


def test_holm_correction_is_monotone_and_skips_none():
    adj = holm_correct([0.01, None, 0.04, 0.03])
    assert adj[1] is None
    assert adj[0] == pytest.approx(0.03)        # 3 * 0.01
    assert adj[3] == pytest.approx(0.06)        # 2 * 0.03
    assert adj[2] == pytest.approx(0.06)        # max(prev, 1 * 0.04)
    assert all(a >= p for a, p in zip([adj[0], adj[3], adj[2]], [0.01, 0.03, 0.04]))


# ---------------- overlap ----------------
def test_overlap_row_reports_all_three_denominators():
    row = overlap_row("test", {"u1", "u2", "u3"}, {"u2", "u3", "u4"}, "A", "B")
    assert row["users_in_both"] == 2
    assert row["pct_of_A"] == pytest.approx(66.67, abs=0.01)
    assert row["pct_of_B"] == pytest.approx(66.67, abs=0.01)
    assert row["jaccard_pct"] == 50.0


def test_overlap_handles_empty_sets():
    row = overlap_row("test", set(), set(), "A", "B")
    assert row["users_in_both"] == 0 and row["jaccard_pct"] == 0


# ---------------- connectors ----------------
def test_classify_role():
    assert classify_role(posts_authored=3, in_weight=40, out_weight=2) == "thread starter"
    assert classify_role(posts_authored=0, in_weight=40, out_weight=2) == "reply bridge"
    assert classify_role(posts_authored=3, in_weight=2, out_weight=40) == "reply bridge"


# ---------------- parent lookup (collect_parents / network coverage) ----------------
def test_extra_authors_resolve_parents_outside_the_sample():
    comments, posts = _fake_data()
    # c5 replied to t1_gone, which is not in the sample but was fetched by id
    G, stats = build_reply_graph(comments, posts, "s", extra_authors={"t1_gone": "user_X"})
    assert G.has_edge("user_C", "user_X")
    assert stats["missing_parent"] == 0
    assert stats["coverage_pct"] == 100.0


def test_missing_parent_ids_finds_only_out_of_sample_parents():
    from src.collect_parents import missing_parent_ids
    comments, posts = _fake_data()
    t1, t3 = missing_parent_ids(comments, posts)
    assert t1 == ["gone"] and t3 == []
