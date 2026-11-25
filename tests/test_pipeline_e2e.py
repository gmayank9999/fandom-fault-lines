"""End-to-end test: run the real stages, in order, on a tiny synthetic dataset in a temp directory.

The unit tests in test_sanity.py check functions in isolation. This one checks the hand-offs between
stages (file names, columns, hashed ids still joining up) and the privacy guarantees of the outputs.
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

POS = ["great", "love", "amazing", "awesome"]
NEG = ["terrible", "awful", "boring", "hate"]
A_WORDS = ["marvel", "mcu", "avengers"]
B_WORDS = ["dc", "batman", "superman"]


def _synthetic(rng):
    posts, comments = [], []
    t0 = config.AFTER_TS + 1000
    for sub, own, other in (("marvelstudios", A_WORDS, B_WORDS), ("DC_Cinematic", B_WORDS, A_WORDS)):
        for i in range(25):
            posts.append({"id": f"p{sub[:2]}{i}", "subreddit": sub, "title": f"thread {i}", "author": f"poster_{sub[:2]}{i % 7}",
                          "score": 5, "num_comments": 6, "created_utc": t0 + i * 600, "selftext_present": False,
                          "url": f"https://www.reddit.com/r/{sub}/comments/p{sub[:2]}{i}/x/"})
        ids = []
        for n in range(220):
            post = f"p{sub[:2]}{rng.integers(25)}"
            parent = f"t1_{ids[rng.integers(len(ids))]}" if ids and rng.random() < 0.6 else f"t3_{post}"
            topic = [own, other, own + other, ["film"]][rng.choice(4, p=[0.4, 0.1, 0.05, 0.45])]
            words = list(rng.choice(topic, 2)) + list(rng.choice(POS + NEG, 3)) + ["really", "movie", "scene"]
            # a pool of 40 users per sub, 15 of them shared across both subs
            user = f"shared_{rng.integers(15)}" if rng.random() < 0.2 else f"{sub[:2]}_user_{rng.integers(40)}"
            cid = f"c{sub[:2]}{n}"
            ids.append(cid)
            comments.append({"id": cid, "subreddit": sub, "link_id": f"t3_{post}", "parent_id": parent,
                             "author": user, "body": " ".join(words) + " https://example.com", "score": int(rng.integers(1, 30)),
                             "created_utc": t0 + n * 500})
    comments.append({"id": "bot1", "subreddit": "marvelstudios", "link_id": "t3_x", "parent_id": "t3_x",
                     "author": "AutoModerator", "body": "I am a bot", "score": 1, "created_utc": t0})
    return pd.DataFrame(posts), pd.DataFrame(comments)


@pytest.fixture()
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "USE_TRANSFORMER", False)
    monkeypatch.setattr(config, "TOPIC_CANDIDATES", [2, 3])
    monkeypatch.setattr(config, "MIN_COMMUNITY_SIZE", 3)
    monkeypatch.setattr(config, "BETWEENNESS_EXACT_MAX_NODES", 10000)
    monkeypatch.setattr(config, "PRIMARY_SCORER", "sentiment_adapted")
    import src.utils as u
    monkeypatch.setattr(u, "_SALT", "test-salt")
    for d in ("data/raw", "data/processed", "outputs/charts", "outputs/networks", "logs"):
        os.makedirs(d)
    rng = np.random.default_rng(0)
    posts, comments = _synthetic(rng)
    posts.to_csv(config.RAW_POSTS_PATH, index=False)
    comments.to_csv(config.RAW_COMMENTS_PATH, index=False)
    base = pd.DataFrame([{"id": f"b{i}", "subreddit": s, "author": f"{s[:2]}_user_{i % 30}" if i % 4 else f"shared_{i % 15}",
                          "created_utc": 1} for s in ("StarWars", "lotr") for i in range(200)])
    base.to_csv(config.RAW_BASELINE_PATH, index=False)
    return tmp_path


def test_pipeline_runs_end_to_end_and_protects_identities(workdir):
    from src import (preprocess, topic_modeling, sentiment, statistical_tests, network_build,
                     network_analysis, overlap_analysis, connector_analysis)
    preprocess.main()
    topic_modeling.main()
    sentiment.main()
    statistical_tests.main()
    network_build.main()
    network_analysis.main()
    overlap_analysis.main()
    connector_analysis.main()

    clean = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    posts = pd.read_csv(config.CLEAN_POSTS_PATH)

    # --- bots removed, text cleaned, nothing identifying left ---
    assert "AutoModerator" not in set(clean["author"])
    assert not clean["body_clean"].str.contains("http").any()
    assert "body" not in clean.columns and "url" not in posts.columns
    assert clean["author"].str.startswith("user_").all()
    assert not clean["id"].str.startswith("c").any()                     # raw ids are hashed
    assert clean["id"].str.startswith("h").all() and posts["id"].str.startswith("h").all()
    assert set(clean["parent_id"].str[:3]) <= {"t1_", "t3_"}
    for f in (config.OVERLAP_PATH, "data/processed/centrality_marvelstudios.csv", "data/processed/parent_authors.csv",
              config.CLEAN_BASELINE_PATH):
        text = open(f, encoding="utf-8").read()
        assert "marvelstudios_user" not in text and "shared_" not in text and "poster_" not in text

    # --- hashed ids still join: the reply network is built from them ---
    cov = pd.read_csv("data/processed/network_coverage.csv")
    assert (cov["coverage_pct"] > 95).all(), cov.to_string()
    assert (cov["edges"] > 50).all()

    # --- sentiment & tests ---
    s = pd.read_csv(config.SENTIMENT_PATH)
    assert {"sentiment_compound", "sentiment_adapted", "talk_target"} <= set(s.columns)
    assert set(s["talk_target"]) == {"self_talk", "rival_talk", "both", "general"}
    tests = pd.read_csv(config.STATISTICAL_TESTS_PATH)
    assert {"p_holm", "p_user_boot", "p_thread_boot", "survives_clustering", "scorer"} <= set(tests.columns)
    assert tests["p_value"].notna().any()

    # --- overlap, with a baseline ---
    summary = pd.read_csv(config.OVERLAP_SUMMARY_PATH)
    assert len(summary) == 3 and (summary["users_in_both"] > 0).all()
    base = pd.read_csv(config.OVERLAP_BASELINE_PATH)
    assert base["is_rival_pair"].sum() == 3                               # one rival pair x three activity levels
    assert {"marvelstudios + DC_Cinematic", "StarWars + lotr"} <= set(base["pair"])

    # --- network analysis incl. the null model ---
    net = pd.read_csv("data/processed/network_summary.csv")
    assert {"modularity", "modularity_null_mean", "modularity_excess"} <= set(net.columns)
    prof = pd.read_csv("data/processed/connector_profile_marvelstudios.csv")
    assert "threads_participated" in prof.columns and (prof["threads_participated"] >= 1).all()


def test_pipeline_is_deterministic(workdir):
    from src import preprocess, sentiment
    preprocess.main()
    sentiment.main()
    first = pd.read_csv(config.SENTIMENT_PATH)
    sentiment.main()
    pd.testing.assert_frame_equal(first, pd.read_csv(config.SENTIMENT_PATH))


@pytest.mark.skipif(os.environ.get("FFL_MODEL_TEST") != "1", reason="Opt-in real model test: set FFL_MODEL_TEST=1 (downloads model if absent)")
def test_transformer_stage_scores_a_capped_subset_and_caches(workdir, monkeypatch):
    pytest.importorskip("torch")
    pytest.importorskip("transformers")
    from src import preprocess, sentiment, statistical_tests
    monkeypatch.setattr(config, "USE_TRANSFORMER", True)
    monkeypatch.setattr(config, "TRANSFORMER_CAP_PER_STRATUM", {"self_talk": 12, "general": 12})
    monkeypatch.setattr(config, "TRANSFORMER_SCORES_PATH", "data/processed/transformer_scores.csv")
    preprocess.main()
    sentiment.main()
    s = pd.read_csv(config.SENTIMENT_PATH)

    scored = s["sentiment_transformer"].notna()
    # every rival-mentioning comment is scored; the big groups are capped per subreddit (+/- hash sampling)
    assert scored[s["talk_target"].isin(["rival_talk", "both"])].all()
    for (sub, target), g in s[s["talk_target"].isin(["self_talk", "general"])].groupby(["subreddit", "talk_target"]):
        assert 0 < g["sentiment_transformer"].notna().sum() < len(g)
    assert set(s.loc[scored, "sentiment_transformer_label"]) <= {"negative", "neutral", "positive"}
    assert s.loc[~scored, "sentiment_transformer_label"].isna().all()
    assert s.loc[scored, "sentiment_transformer"].between(-1, 1).all()

    # second run: nothing new to score, identical values (read from the cache)
    cache_before = pd.read_csv(config.TRANSFORMER_SCORES_PATH)
    sentiment.main()
    pd.testing.assert_frame_equal(s, pd.read_csv(config.SENTIMENT_PATH))
    assert len(pd.read_csv(config.TRANSFORMER_SCORES_PATH)) == len(cache_before)

    # the tests use only the scored comments and skip the unrepresentative "overall" comparison
    statistical_tests.main()
    t = pd.read_csv(config.STATISTICAL_TESTS_PATH)
    tf = t[t["scorer"] == "sentiment_transformer"]
    assert len(tf) == 4 and not tf["comparison"].str.startswith("overall").any()
