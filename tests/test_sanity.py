import sys
import os
import pandas as pd
import networkx as nx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.utils import anonymize
from src.preprocess import clean_text


def test_anonymize_is_deterministic():
    assert anonymize("real_user_123") == anonymize("real_user_123")

def test_anonymize_different_users_differ():
    assert anonymize("alice") != anonymize("bob")

def test_anonymize_handles_deleted():
    assert anonymize("[deleted]") == "[deleted]"
    assert anonymize(None) == "[deleted]"

def test_clean_text_strips_urls():
    assert "http" not in clean_text("check this out https://example.com/page nice")

def test_clean_text_collapses_whitespace():
    assert clean_text("hello    world\n\n") == "hello world"


def test_overlap_calculation():
    users_a = {"user_1", "user_2", "user_3"}
    users_b = {"user_2", "user_3", "user_4"}
    overlap = users_a & users_b
    union = users_a | users_b
    assert overlap == {"user_2", "user_3"}
    assert len(overlap) / len(union) == 0.5   # Jaccard index


def test_network_construction_drops_self_loops():
    # Manually build the same logic as build_reply_graph() with a tiny fake case:
    # user_A replies to user_B, user_B replies to themself (should be dropped)
    G = nx.DiGraph()
    edges = [("user_A", "user_B"), ("user_B", "user_B")]  # second is a self-loop
    for commenter, parent in edges:
        if commenter == parent:
            continue  # this is exactly the self-loop check in network_build.py
        G.add_edge(commenter, parent)
    assert G.number_of_edges() == 1
    assert not G.has_edge("user_B", "user_B")


def test_sentiment_categorize_thresholds():
    from src.sentiment import categorize
    assert categorize(0.5) == "positive"
    assert categorize(-0.5) == "negative"
    assert categorize(0.0) == "neutral"
    assert categorize(0.04) == "neutral"   # just inside the +/-0.05 neutral band
    assert categorize(0.05) == "positive"  # exactly on the boundary


def test_tag_target_classifies_four_ways():
    from src.sentiment import tag_target
    import config

    row_self = pd.Series({"body_clean": "marvel is doing great this year", "subreddit": "marvelstudios"})
    row_rival = pd.Series({"body_clean": "dc really nailed this one", "subreddit": "marvelstudios"})
    row_both = pd.Series({"body_clean": "marvel and dc are both having a good year", "subreddit": "marvelstudios"})
    row_general = pd.Series({"body_clean": "i love going to the movies", "subreddit": "marvelstudios"})

    sub_a, sub_b = "marvelstudios", "DC_Cinematic"
    assert tag_target(row_self, sub_a, sub_b) == "self_talk"
    assert tag_target(row_rival, sub_a, sub_b) == "rival_talk"
    assert tag_target(row_both, sub_a, sub_b) == "both"
    assert tag_target(row_general, sub_a, sub_b) == "general"
