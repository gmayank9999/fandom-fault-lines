"""Comparative analyses. All published tables are aggregates; user tables stay private."""
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import NMF
from sklearn.feature_extraction.text import TfidfVectorizer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import config
from src.preprocess import basic_clean
from src.sentiment import adapted_analyzer
from src.statistical_tests import cluster_bootstrap_diff, holm_correct, run_mannwhitney
from src.study_data import communities, days, cache_path, load_window, raw_parent_lookup, timestamp
from src.study_network import graph_from_comments, metrics, export_gephi
from src.topic_modeling import choose_n_topics, assign_topics
from src.utils import anonymize, anonymize_id, anonymize_fullname, compile_alias_regex, get_stopwords


def valid_users(raw):
    bots = {b.casefold() for b in config.BOT_ACCOUNTS} | {"[removed]", "", "nan"}
    return raw[raw["author"].notna() & ~raw["author"].astype(str).str.casefold().isin(bots)].copy()


def fingerprint(design, pair):
    h = hashlib.sha256(json.dumps(design, sort_keys=True).encode())
    h.update(anonymize("__study_cache_identity_check__").encode())
    repo = Path(__file__).resolve().parents[1]
    sources = [repo / "src" / (name + ".py") for name in
               ("study_analysis", "study_network", "network_analysis", "preprocess",
                "statistical_tests", "utils", "sentiment", "topic_modeling")]
    sources.append(repo / "config.py")
    referenced = set()
    for source in sources:
        h.update(source.read_bytes())
    for w in design["windows"]:
        for sub in pair["communities"]:
            for a, _ in days(w):
                path = cache_path(w, sub, a)
                h.update(path.read_bytes())
                referenced.update(pd.read_csv(path, usecols=["parent_id"])["parent_id"].dropna())
    parents = raw_parent_lookup()
    parents = parents[(parents["kind"] + "_" + parents["id"]).isin(referenced)].sort_values(["kind", "id"])
    h.update(parents.to_csv(index=False).encode())
    return h.hexdigest()


def prepare(raw, pair, design):
    content = basic_clean(raw).copy()
    plain, adapted = SentimentIntensityAnalyzer(), adapted_analyzer()
    regex = {s: compile_alias_regex(design["aliases"][s]) for s in pair["communities"]}
    own = pd.Series(False, index=content.index)
    other = own.copy()
    for sub, rival in (pair["communities"], pair["communities"][::-1]):
        mask = content["subreddit"].eq(sub)
        own.loc[mask] = content.loc[mask, "body_clean"].map(lambda t: bool(regex[sub].search(t)))
        other.loc[mask] = content.loc[mask, "body_clean"].map(lambda t: bool(regex[rival].search(t)))
    content["target"] = np.select([own & other, other, own], ["both", "rival_talk", "self_talk"], default="general")
    content["vader"] = content["body_clean"].map(lambda t: plain.polarity_scores(t)["compound"])
    content["vader_adapted"] = content["body_clean"].map(lambda t: adapted.polarity_scores(t)["compound"])
    content["author"] = content["author"].map(anonymize)
    content["link_id"] = content["link_id"].map(anonymize_fullname)
    content["parent_id"] = content["parent_id"].map(anonymize_fullname)
    content["id"] = content["id"].map(lambda x: anonymize_id(x, "t1"))
    return content


def overlap_counts(counts, a, b, level=1):
    aa, bb = set(counts[a][counts[a] >= level].index), set(counts[b][counts[b] >= level].index)
    shared, union = aa & bb, aa | bb
    return {"community_a": a, "community_b": b, "min_comments": level,
            "users_a": len(aa), "users_b": len(bb), "shared": len(shared),
            "pct_a": 100 * len(shared) / len(aa) if aa else np.nan,
            "pct_b": 100 * len(shared) / len(bb) if bb else np.nan,
            "jaccard_pct": 100 * len(shared) / len(union) if union else np.nan,
            "pct_smaller": 100 * len(shared) / min(len(aa), len(bb)) if aa and bb else np.nan}


def compare_sentiment(content, pair, n_boot, seed):
    rows = []
    for sub in pair["communities"]:
        for scorer in ("vader", "vader_adapted"):
            for rival_definition, targets in (("rival_only", ["rival_talk"]), ("any_rival_mention", ["rival_talk", "both"])):
                a = content[(content["subreddit"] == sub) & (content["target"] == "self_talk")]
                b = content[(content["subreddit"] == sub) & content["target"].isin(targets)]
                row = {"subreddit": sub, "scorer": scorer, "contrast": rival_definition,
                       **run_mannwhitney(a[scorer], b[scorer], "own-only minus rival-mention sentiment")}
                for cluster in ("author", "link_id"):
                    result = cluster_bootstrap_diff(a, b, scorer, cluster, n_boot=n_boot, seed=seed) if min(len(a), len(b)) >= 5 else None
                    for key in ("diff", "ci_low", "ci_high", "p_boot", "n_clusters"):
                        row[f"{cluster}_{key}"] = result[key] if result else np.nan
                rows.append(row)
    table = pd.DataFrame(rows)
    # One family includes both communities, both mention definitions and both
    # lexicon variants. Do not select the scorer that gives the smallest p.
    for col in ("p_value", "author_p_boot", "link_id_p_boot"):
        table[col + "_holm"] = holm_correct(table[col].tolist())
    table["supported_both_clusterings"] = (pd.to_numeric(table["author_p_boot_holm"]) < .05) & (pd.to_numeric(table["link_id_p_boot_holm"]) < .05)
    return table


def topics(content, design):
    """One pooled pair model across both periods, so topic IDs are comparable."""
    rng_seed = design["seed"]
    # Equal training allocation per community/window prevents the larger side
    # from defining the whole vocabulary; all content is transformed afterward.
    n = max(20, design["topic_training_limit"] // content.groupby(["subreddit", "window"]).ngroups)
    train = pd.concat([g.sample(min(len(g), n), random_state=rng_seed) for _, g in content.groupby(["subreddit", "window"])])
    vector = TfidfVectorizer(max_df=.8, min_df=5, max_features=3000, ngram_range=(1, 2),
                             stop_words=sorted(get_stopwords()), token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z]{2,}\b")
    try:
        xtrain = vector.fit_transform(train["body_clean"])
    except ValueError:
        return pd.DataFrame(), pd.DataFrame()
    candidates = [k for k in design["topic_candidates"] if k <= min(xtrain.shape)]
    if not candidates:
        return pd.DataFrame(), pd.DataFrame()
    best, coherence = choose_n_topics(xtrain, candidates, rng_seed)
    model = NMF(n_components=best, random_state=rng_seed, init="nndsvda", max_iter=500).fit(xtrain)
    matrix = vector.transform(content["body_clean"])
    assigned = assign_topics(model.transform(matrix), matrix, config.TOPIC_MIN_TOKENS)
    words = vector.get_feature_names_out()
    labels = {i: ", ".join(words[np.argsort(component)[-8:][::-1]]) for i, component in enumerate(model.components_)}
    labels[-1] = "insufficient topical vocabulary"
    content["topic"] = assigned
    summary = content.groupby(["window", "subreddit", "topic"]).size().rename("comments").reset_index()
    summary["share_pct"] = summary["comments"] / summary.groupby(["window", "subreddit"])["comments"].transform("sum") * 100
    summary["words"] = summary["topic"].map(labels)
    selection = pd.DataFrame([{"k": k, "npmi": v, "selected": k == best, "training_comments": len(train)} for k, v in coherence.items()])
    return summary, selection


def analyze_pair(design, pair):
    out = Path(design["output_dir"])
    table_dir, private = out / "tables", out / "private"
    table_dir.mkdir(exist_ok=True)
    private.mkdir(exist_ok=True)
    digest = fingerprint(design, pair)
    marker = private / f"{pair['id']}_complete.json"
    if marker.exists():
        previous = json.loads(marker.read_text())
        products = previous.get("products", {})
        if previous["fingerprint"] == digest and products and all(
                (out / name).exists() and hashlib.sha256((out / name).read_bytes()).hexdigest() == sha
                for name, sha in products.items()):
            print(f"REUSING verified analysis {pair['id']}", flush=True)
            return
    print(f"ANALYZING {pair['id']}", flush=True)
    frames = [load_window(w, pair["communities"]).assign(window=w["id"]) for w in design["windows"]]
    raw = pd.concat(frames, ignore_index=True)
    if raw["id"].duplicated().any():
        raise ValueError("A comment ID occurs in multiple study windows/communities")
    # Overlap and networks use identifiable public comments regardless of body
    # removal/length. Content filtering must not manufacture group separation.
    participation = valid_users(raw).drop_duplicates("id").copy()
    raw_lookup = dict(zip("t1_" + participation["id"], participation["author"]))
    p = valid_users(raw_parent_lookup())
    raw_lookup.update(dict(zip(p["kind"] + "_" + p["id"], p["author"])))
    lookup = {anonymize_fullname(k): anonymize(v) for k, v in raw_lookup.items()}
    participation["author"] = participation["author"].map(anonymize)
    participation["parent_id"] = participation["parent_id"].map(anonymize_fullname)
    participation["link_id"] = participation["link_id"].map(anonymize_fullname)
    prepared_path = private / f"{pair['id']}_content.csv.gz"
    prepared_marker = private / f"{pair['id']}_content.sha256"
    if prepared_path.exists() and prepared_marker.exists() and prepared_marker.read_text() == digest:
        content = pd.read_csv(prepared_path)
    else:
        content = prepare(raw, pair, design)
        content.to_csv(prepared_path, index=False, compression="gzip")
        prepared_marker.write_text(digest)
    print(f"SCORED {pair['id']}: {len(content)} content comments", flush=True)
    topic_summary, selection = topics(content, design)
    topic_summary.to_csv(table_dir / f"{pair['id']}_topics.csv", index=False)
    selection.to_csv(table_dir / f"{pair['id']}_topic_selection.csv", index=False)
    tables = {name: [] for name in ("corpus", "overlap", "sentiment", "tests", "networks", "gephi", "weekly", "duration", "sampling")}
    for window in design["windows"]:
        wid = window["id"]
        c = content[content["window"] == wid].copy()
        users = participation[participation["window"] == wid]
        counts = {s: users[users["subreddit"] == s]["author"].value_counts() for s in pair["communities"]}
        shared = set(counts[pair["communities"][0]].index) & set(counts[pair["communities"][1]].index)
        for sub in pair["communities"]:
            subset = c[c["subreddit"] == sub]
            all_users = users[users["subreddit"] == sub]
            tables["corpus"].append({"window": wid, "subreddit": sub,
                "raw_comments": int(((raw["window"] == wid) & (raw["subreddit"] == sub)).sum()),
                "participation_comments": len(all_users), "content_comments": len(subset),
                "commenters": len(counts[sub]), "content_commenters": subset["author"].nunique(),
                "rival_mention_pct": 100 * subset["target"].isin(["rival_talk", "both"]).mean(),
                "shared_users_comment_share_pct": 100 * all_users["author"].isin(shared).mean()})
            for target, group in subset.groupby("target"):
                tables["sentiment"].append({"window": wid, "subreddit": sub, "target": target,
                    "n": len(group), "mean_vader": group["vader"].mean(),
                    "mean_vader_adapted": group["vader_adapted"].mean(),
                    "zero_vader_pct": 100 * group["vader"].eq(0).mean()})
            for comment_only in (False, True):
                variant = "comment_replies" if comment_only else "all_replies"
                print(f"NETWORK {pair['id']} {wid} {sub} {variant}", flush=True)
                graph, coverage = graph_from_comments(all_users, lookup, comment_only)
                result, nodes, graph = metrics(graph, design["network"], design["seed"], expensive=not comment_only)
                tables["networks"].append({"window": wid, "subreddit": sub, "variant": variant, **coverage, **result})
                thread_counts = all_users.groupby("author")["link_id"].nunique()
                for node in graph:
                    graph.nodes[node].update(shared_in_pair=node in shared, subreddit=sub,
                        window=wid, threads_participated=int(thread_counts.get(node, 0)),
                        observed_commenter=node in counts[sub].index,
                        comment_count=int(counts[sub].get(node, 0)))
                stem = f"{pair['id']}_{wid}_{sub}_{variant}"
                if not comment_only:
                    tables["gephi"].append({"window": wid, "subreddit": sub,
                        **export_gephi(graph, out / "networks", stem, design["network"]["layout_node_limit"], design["seed"])})
                else:
                    import networkx as nx
                    nx.write_gexf(graph, out / "networks" / f"{stem}_full.gexf")
                nodes = pd.DataFrame([{"Id": node, **attrs} for node, attrs in graph.nodes(data=True)])
                nodes.to_csv(private / f"{stem}_centrality.csv", index=False)
                if not nodes.empty:
                    nodes.sort_values("betweenness", ascending=False).head(30).to_csv(private / f"{stem}_connectors.csv", index=False)
        for level in (1, 2, 5):
            tables["overlap"].append({"window": wid, **overlap_counts(counts, *pair["communities"], level)})
        test = compare_sentiment(c, pair, design["bootstrap_replicates"], design["seed"]).assign(window=wid)
        tables["tests"].extend(test.to_dict("records"))
        window_days = (timestamp(window["end"]) - timestamp(window["start"])) // 86400
        for day_count in sorted({d for d in (7, 14, 21, window_days) if d <= window_days}):
            stop = timestamp(window["start"]) + day_count * 86400
            u = users[users["created_utc"] < stop]
            cs = {s: u[u["subreddit"] == s]["author"].value_counts() for s in pair["communities"]}
            tables["duration"].append({"window": wid, "days": day_count, **overlap_counts(cs, *pair["communities"])})
        for frac in (.1, .25, .5, 1.):
            for replicate in range(5 if frac < 1 else 1):
                sampled = users.groupby("subreddit", group_keys=False).sample(frac=frac, random_state=design["seed"] + replicate)
                cs = {s: sampled[sampled["subreddit"] == s]["author"].value_counts() for s in pair["communities"]}
                tables["sampling"].append({"window": wid, "fraction": frac, "replicate": replicate, **overlap_counts(cs, *pair["communities"])})
        c["week"] = ((c["created_utc"] - timestamp(window["start"])) // (7 * 86400)).astype(int) + 1
        c["rival_mention"] = c["target"].isin(["rival_talk", "both"])
        weekly = c.groupby(["subreddit", "week"]).agg(comments=("id", "size"), rival_mention_share=("rival_mention", "mean"), adapted_mean=("vader_adapted", "mean")).reset_index().assign(window=wid)
        tables["weekly"].extend(weekly.to_dict("records"))
    pooled_counts = {s: participation[participation["subreddit"] == s]["author"].value_counts() for s in pair["communities"]}
    for level in (1, 2, 5):
        tables["overlap"].append({"window": "pooled_56d", **overlap_counts(pooled_counts, *pair["communities"], level)})
    for name, rows in tables.items():
        pd.DataFrame(rows).assign(pair=pair["id"]).to_csv(table_dir / f"{pair['id']}_{name}.csv", index=False)
    product_paths = list(table_dir.glob(f"{pair['id']}_*.csv")) + list((out / "networks").glob(f"{pair['id']}_*"))
    products = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in product_paths}
    marker.write_text(json.dumps({"fingerprint": digest, "design": design, "products": products}, indent=2), encoding="utf-8")
    print(f"COMPLETE {pair['id']}", flush=True)


def analyze_baselines(design):
    rows = []
    for window in design["windows"]:
        counts = {}
        for sub in communities(design) + design["baselines"]:
            raw = valid_users(load_window(window, [sub], light=True))
            counts[sub] = raw["author"].map(anonymize).value_counts()
        for a, b in itertools.combinations(counts, 2):
            for k in (1, 2, 5):
                row = overlap_counts(counts, a, b, k)
                row["window"] = window["id"]
                row["designated_pair"] = any(set(p["communities"]) == {a, b} for p in design["pairs"])
                rows.append(row)
    pd.DataFrame(rows).to_csv(Path(design["output_dir"]) / "tables" / "all_pair_overlap.csv", index=False)


def analyze(design):
    # Each complete pair can be analyzed while another is still collecting.
    for pair in design["pairs"]:
        try:
            analyze_pair(design, pair)
        except FileNotFoundError as exc:
            print(f"PENDING {pair['id']}: {exc}", flush=True)
    try:
        analyze_baselines(design)
    except FileNotFoundError as exc:
        print(f"PENDING baseline comparison: {exc}", flush=True)
