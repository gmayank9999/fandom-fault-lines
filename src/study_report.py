"""Generate the study write-up and figures directly from checked aggregate tables."""
from pathlib import Path
import importlib.metadata
import json
import subprocess
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import networkx as nx

from src.study_data import inventory


def markdown_table(df):
    """No optional tabulate dependency; escape pipes and missing values."""
    def fmt(x):
        if pd.isna(x):
            return "—"
        if isinstance(x, (float, np.floating)):
            return f"{x:,.3f}" if abs(x) < 1 else f"{x:,.2f}"
        return str(x).replace("|", "/").replace("\n", " ")
    return "\n".join(["| " + " | ".join(map(str, df.columns)) + " |",
                       "| " + " | ".join(["---"] * len(df.columns)) + " |"] +
                      ["| " + " | ".join(fmt(x) for x in row) + " |" for row in df.itertuples(index=False, name=None)])


def load(out, name):
    frames = []
    for path in sorted((out / "tables").glob(f"*_{name}.csv")):
        if path.name == "all_pair_overlap.csv":
            continue
        try:
            frame = pd.read_csv(path)
            if "pair" not in frame:
                frame["pair"] = path.name.removesuffix(f"_{name}.csv")
            frames.append(frame)
        except pd.errors.EmptyDataError:
            continue
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def plots(out):
    folder = out / "figures"
    folder.mkdir(exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb"})
    colors = ["#2563a6", "#c35b26", "#23846d", "#8361a8"]
    overlap = load(out, "overlap")
    if not overlap.empty:
        rows = overlap[overlap["min_comments"] == 1]
        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(rows))
        ax.bar(x - .18, rows["pct_a"], width=.36, label="Share of community A", color=colors[0])
        ax.bar(x + .18, rows["pct_b"], width=.36, label="Share of community B", color=colors[1])
        ax.set_xticks(x, [f"{r.pair}\n{r.window}" for r in rows.itertuples()])
        ax.set_ylabel("Commenters also seen in the other community (%)")
        ax.set_title("Observed audience overlap depends on denominator and window", loc="left")
        ax.legend(frameon=False)
        ax.grid(axis="y", alpha=.2)
        ax.set_axisbelow(True)
        fig.tight_layout()
        fig.savefig(folder / "overlap.png", dpi=180)
        plt.close(fig)
    sampling = load(out, "sampling")
    duration = load(out, "duration")
    if not sampling.empty and not duration.empty:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
        for i, ((pair, window), g) in enumerate(sampling.groupby(["pair", "window"])):
            summary = g.groupby("fraction")["jaccard_pct"].agg(["mean", "min", "max"])
            col = colors[i % len(colors)]
            axes[0].plot(summary.index * 100, summary["mean"], marker="o", color=col, label=f"{pair}, {window}")
            axes[0].fill_between(summary.index * 100, summary["min"], summary["max"], color=col, alpha=.15)
        for i, ((pair, window), g) in enumerate(duration.groupby(["pair", "window"])):
            axes[1].plot(g["days"], g["jaccard_pct"], marker="o", color=colors[i % len(colors)], label=f"{pair}, {window}")
        axes[0].set(xlabel="Comments retained by random subsampling (%)", ylabel="Jaccard overlap (%)", title="Sampling sensitivity (shading: range of 5 runs)")
        axes[1].set(xlabel="Observed days from window start", ylabel="Jaccard overlap (%)", title="Duration sensitivity (nested cumulative windows)")
        for ax in axes:
            ax.legend(frameon=False, fontsize=8)
            ax.grid(alpha=.2)
        fig.tight_layout()
        fig.savefig(folder / "sensitivity.png", dpi=180)
        plt.close(fig)
    net = load(out, "networks")
    if not net.empty:
        rows = net[net["variant"] == "all_replies"]
        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(rows))
        ax.bar(x - .18, rows["modularity_unweighted"], .36, label="Observed unweighted topology", color=colors[0])
        ax.bar(x + .18, rows["null_mean"], .36, yerr=rows["null_sd"], label="Degree-preserving null mean ± SD", color=colors[1], capsize=3)
        ax.set_xticks(x, [f"{r.subreddit}\n{r.window}" for r in rows.itertuples()], rotation=15)
        ax.set(ylabel="Louvain modularity Q", title="Compare like with like: observed and randomized unweighted networks")
        ax.legend(frameon=False, fontsize=9)
        fig.tight_layout()
        fig.savefig(folder / "network_null.png", dpi=180)
        plt.close(fig)
    weekly = load(out, "weekly")
    if not weekly.empty:
        fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
        for i, ((pair, sub), group) in enumerate(weekly.groupby(["pair", "subreddit"])):
            g = group.assign(study_week=group["week"] + group["window"].map({"sep": 0, "oct": 4}))
            g = g.sort_values("study_week")
            axes[0].plot(g["study_week"], g["rival_mention_share"] * 100, marker="o", color=colors[i % 4], label=sub)
            axes[1].plot(g["study_week"], g["adapted_mean"], marker="o", color=colors[i % 4], label=sub)
        axes[0].set(ylabel="Comments mentioning rival (%)", title="Explicit rival mentions over eight weeks")
        axes[1].set(ylabel="Mean adapted VADER score", title="Whole-comment tone (not rival-directed stance)")
        for ax in axes:
            ax.set_xlabel("Study week (week 1 begins 3 September 2026)")
            ax.axvline(4.5, color="#888888", linestyle="--", linewidth=.8)
            ax.legend(frameon=False, fontsize=8)
            ax.grid(alpha=.2)
        fig.tight_layout()
        fig.savefig(folder / "weekly_content.png", dpi=180)
        plt.close(fig)
    topic_table = load(out, "topics")
    if not topic_table.empty:
        for pair, rows in topic_table.groupby("pair"):
            for sub, d in rows.groupby("subreddit"):
                fig, ax = plt.subplots(figsize=(10, 5))
                pivot = d.pivot(index="topic", columns="window", values="share_pct").fillna(0)
                labels = d.drop_duplicates("topic").set_index("topic")["words"]
                y = np.arange(len(pivot))
                for j, window in enumerate(pivot.columns):
                    ax.barh(y + (j - .5) * .36, pivot[window], height=.34, label=window, color=colors[j])
                ax.set_yticks(y, ["Too little topical vocabulary" if i == -1 else ", ".join(labels[i].split(", ")[:4]) for i in pivot.index], fontsize=9)
                ax.set(xlabel="Share of usable content comments (%)", title=f"r/{sub}: shared-model topic prevalence")
                ax.legend(frameon=False)
                ax.grid(axis="x", alpha=.2)
                ax.set_axisbelow(True)
                fig.tight_layout()
                fig.savefig(folder / f"topics_{pair}_{sub}.png", dpi=180)
                plt.close(fig)
    baseline = out / "tables" / "all_pair_overlap.csv"
    if baseline.exists():
        data = pd.read_csv(baseline)
        data = data[data["min_comments"] == 1]
        windows = sorted(data["window"].unique(), key=lambda w: {"sep": 0, "oct": 1}.get(w, 2))
        fig, axes = plt.subplots(1, len(windows), figsize=(6.5 * len(windows), 6), squeeze=False)
        aggregate_dir = out / "aggregate_networks"
        aggregate_dir.mkdir(exist_ok=True)
        maximum = data["jaccard_pct"].max()
        for ax, window in zip(axes[0], windows):
            rows = data[data["window"] == window]
            names = list(dict.fromkeys(rows["community_a"].tolist() + rows["community_b"].tolist()))
            matrix = pd.DataFrame(np.nan, index=names, columns=names)
            graph = nx.Graph(period=window, meaning="audience co-participation similarity, not reply edges or hostility")
            for r in rows.itertuples():
                matrix.loc[r.community_a, r.community_b] = matrix.loc[r.community_b, r.community_a] = r.jaccard_pct
                graph.add_node(r.community_a, label=r.community_a, observed_commenters=int(r.users_a))
                graph.add_node(r.community_b, label=r.community_b, observed_commenters=int(r.users_b))
                graph.add_edge(r.community_a, r.community_b, weight=float(r.jaccard_pct), shared_commenters=int(r.shared))
            nx.write_gexf(graph, aggregate_dir / f"audience_overlap_{window}.gexf")
            heat = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=maximum)
            ax.set_xticks(range(len(names)), names, rotation=45, ha="right", fontsize=9)
            ax.set_yticks(range(len(names)), names, fontsize=9)
            for i in range(len(names)):
                for j in range(len(names)):
                    if i != j:
                        value = matrix.iloc[i, j]
                        ax.text(j, i, f"{value:.1f}", ha="center", va="center", color="white" if value > .55 * maximum else "#18212b", fontsize=9)
            ax.set_title(f"{window}: pairwise Jaccard overlap (%)", loc="left")
        fig.colorbar(heat, ax=axes.ravel().tolist(), shrink=.65, label="Shared commenters / union (%)", pad=.02)
        fig.subplots_adjust(bottom=.25, left=.12, right=.86, wspace=.55)
        fig.savefig(folder / "audience_overlap_matrix.png", dpi=180)
        plt.close(fig)


def report(design):
    out = Path(design["output_dir"])
    status = inventory(design)
    status.to_csv(out / "collection_inventory.csv", index=False)
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        revision = "unavailable"
    runs = {}
    for pair in design["pairs"]:
        marker = out / "private" / f"{pair['id']}_complete.json"
        if marker.exists():
            data = json.loads(marker.read_text())
            runs[pair["id"]] = {"input_and_code_fingerprint": data["fingerprint"],
                                "aggregate_sha256": {k: v for k, v in data.get("products", {}).items() if k.startswith("tables")}}
    (out / "run_manifest.json").write_text(json.dumps({
        "report_generated_utc": datetime.now(timezone.utc).isoformat(), "git_revision_at_report": revision,
        "design": design, "completed_analysis_runs": runs,
        "packages": {p: importlib.metadata.version(p) for p in ("pandas", "numpy", "networkx", "scipy", "scikit-learn", "vaderSentiment")},
        "note": "Legacy caches lack retrieval manifests. Run fingerprints include data, methods and pseudonymization identity."
    }, indent=2), encoding="utf-8")
    plots(out)
    corpus, overlap, network = (load(out, n) for n in ("corpus", "overlap", "networks"))
    sections = ["# Fandom Fault Lines", "## Comparative longitudinal study",
        "Repository maintainer: **gmayank9999**. Course: Computational Social Media Analysis. "
        "This report is generated from the aggregate tables in `outputs/study/tables/`. "
        "The original sampled pilot is superseded; its 5% overlap conclusion must not be reused.",
        "## Research design",
        "We compare Marvel/DC and PlayStation/Xbox communities over two adjacent 28-day UTC windows: "
        "3 September–1 October and 1–29 October 2026 (ends exclusive), spanning 56 days. "
        "StarWars and lotr provide comparison audiences, not assumed hostile or rivalry-free controls. "
        "Pair selection reflects competing franchises/brands; individual users are not classified as fans or opponents. "
        "This extension was designed after inspecting the pilot and is exploratory, not preregistered.",
        "1. **RQ1 — Content:** How do topics, franchise mentions and whole-comment sentiment differ across communities and periods?\n"
        "2. **RQ2 — Structure:** Which users connect observed reply networks, and how sensitive is structure to including replies to posts?\n"
        "3. **RQ3 — Boundaries:** How much observed participation overlaps, relative to other audience pairs?\n"
        "4. **RQ4 — Stability:** How do those measurements change with period, duration and sampling effort?",
        "## Data coverage and provenance",
        markdown_table(status[["window", "subreddit", "expected_days", "valid_days", "rows", "complete_files"]]),
        "A complete file set means every expected day is present and passes schema, ID and UTC-boundary checks. "
        "It does **not** certify that the archive contains every Reddit comment. New downloads record retrieval times "
        "and SHA-256 checksums; inherited caches have no historical request manifests. The collector fails on ambiguous "
        "timestamp pagination or a safety-cap limit, rather than saving a truncated day."]
    analyzed = set(corpus["pair"]) if not corpus.empty else set()
    pending = [p["id"] for p in design["pairs"] if p["id"] not in analyzed]
    sections += ["**Execution status:** " + ("Analysis pending for " + ", ".join(pending) + ". No conclusions are reported for missing comparisons." if pending else "Both designated pairs have aggregate analysis outputs.")]
    if not corpus.empty:
        sections += ["## Corpus", markdown_table(corpus[["pair", "window", "subreddit", "raw_comments", "participation_comments", "content_comments", "commenters", "rival_mention_pct"]]),
            "Participation retains non-bot commenters even when their text is removed or too short for NLP. "
            "Content removes deleted/empty bodies, URLs/embeds, very short and non-letter text. This separates "
            "observable participation from usable linguistic evidence. Bot removal is a documented account list, "
            "not a comprehensive bot classifier. Counts are archive observations, not Reddit membership estimates."]
    if not overlap.empty:
        one = overlap[overlap["min_comments"] == 1]
        sections += ["## RQ3 and RQ4: audience boundaries", markdown_table(one[["pair", "window", "users_a", "users_b", "shared", "pct_a", "pct_b", "jaccard_pct"]]),
            "A/B follow the order in `study.json`: Marvel/DC and PS5/xbox. Percentages use different denominators: "
            "shared/A, shared/B, and shared/(A∪B). The 56-day row deduplicates users across periods; it does not add monthly user counts. "
            "All activity thresholds (≥1, ≥2, ≥5 comments) appear in the accompanying table. Co-participation alone "
            "does not establish allegiance, exposure to opposing opinions, hostility or an echo chamber.",
            "![Overlap](outputs/study/figures/overlap.png)",
            "![Sensitivity](outputs/study/figures/sensitivity.png)",
            "The subsampling experiment deliberately discards comments at fixed fractions, using five deterministic "
            "random draws. Its shaded ranges are sensitivity ranges, not confidence intervals. Cumulative 7/14/21/28-day "
            "curves show detection changes with duration; these nested windows are not independent observations."]
        for pair, rows in one.groupby("pair"):
            pooled = rows[rows["window"] == "pooled_56d"]
            if not pooled.empty:
                r = pooled.iloc[0]
                sections += [f"**{pair}, 56-day observation:** {int(r['shared']):,} users appear in both communities, "
                    f"representing {r['pct_a']:.1f}% of {r['community_a']} commenters and {r['pct_b']:.1f}% of "
                    f"{r['community_b']} commenters (Jaccard {r['jaccard_pct']:.2f}%). "
                    "This is a directional, period-specific participation result, not a binary verdict about whether the fandoms are closed."]
            monthly = rows[rows["window"].isin([w["id"] for w in design["windows"]])]
            monthly = monthly.set_index("window").reindex([w["id"] for w in design["windows"]]).dropna(subset=["jaccard_pct"])
            if len(monthly) >= 2:
                first, last = monthly.iloc[0], monthly.iloc[-1]
                change = last["jaccard_pct"] - first["jaccard_pct"]
                sections += [f"For {pair}, monthly Jaccard changes from {first['jaccard_pct']:.2f}% to "
                    f"{last['jaccard_pct']:.2f}% ({change:+.2f} percentage points). "
                    "This is a descriptive period comparison; the same people can appear in both windows."]
    baseline = out / "tables" / "all_pair_overlap.csv"
    if baseline.exists():
        b = pd.read_csv(baseline)
        sections += ["### Comparison audiences", markdown_table(b[b["min_comments"] == 1][["window", "community_a", "community_b", "shared", "pct_smaller", "jaccard_pct"]]),
            "All pairs use the same participation filtering. We omit the old 'lift' interpretation: choosing the union "
            "of a few selected subreddits as the population does not supply a neutral model of all Reddit participation."]
        sections += ["![Audience comparison matrix](outputs/study/figures/audience_overlap_matrix.png)",
            "The six-node Gephi files in `outputs/study/aggregate_networks/` represent subreddits, "
            "with edge weight equal to Jaccard overlap. They contain only aggregates and are public. "
            "These audience-similarity graphs are distinct from user reply networks and do not measure hostility."]
        for window, rows in b[b["min_comments"] == 1].groupby("window"):
            ranked = rows.sort_values("jaccard_pct", ascending=False)
            leader = ranked.iloc[0]
            sections += [f"In {window}, the highest observed Jaccard among the {len(rows)} selected audience pairs is "
                f"{leader['community_a']}/{leader['community_b']} ({leader['jaccard_pct']:.2f}%). "
                "This ranking is conditional on the chosen six communities; it is not a Reddit-wide benchmark."]
    else:
        sections += ["### Comparison audiences", "The full comparison-audience table is pending collection of all designated communities in both windows."]
    if not network.empty:
        main = network[network["variant"] == "all_replies"]
        sections += ["## RQ2: reply-network structure", markdown_table(main[["window", "subreddit", "nodes", "edges", "resolved_parent_pct", "largest_component_pct", "reciprocity", "modularity_weighted", "modularity_excess"]]),
            "A directed edge runs from the replier to the parent author; weight counts replies. Self-replies are "
            "excluded and counted, and isolated observed commenters remain nodes. Parent-only nodes are marked separately. "
            "Missing parents reduce coverage and are reported, not imputed. Reciprocal edge weights are summed for "
            "the undirected Louvain projection. Weighted PageRank, in/out degree, strengths, k-core and participation "
            "coefficient supplement directed, unweighted betweenness (reply frequency is not a distance).",
            "The null comparison uses **unweighted observed modularity versus unweighted rewired modularity**. "
            f"Each uses the same degree sequence with {design['network']['null_replicates']} requested rewires. "
            "The excess is descriptive, not a significance test; this small null ensemble cannot support a precise tail probability. "
            "Separate comment-to-comment graphs remove thread-starting hubs as a sensitivity analysis. "
            "Centrality denotes structural position, not influence. Approximate betweenness is checked with two seeds; "
            "top-20 set overlap is supplied in the network table.",
            "![Network null](outputs/study/figures/network_null.png)",
            "### Gephi deliverables", "Full and display-filtered GEXF files and node/edge CSVs are in `outputs/study/networks/` "
            "locally. See [GEPHI_GUIDE.md](GEPHI_GUIDE.md) for import settings, metric definitions, layout and export steps. "
            "Network files contain pseudonymous user-level information and are excluded from Git. "
            "All reported metrics use full graphs; filtered visualizations are never used to estimate population structure."]
        sensitivity = network.pivot(index=["window", "subreddit"], columns="variant", values="largest_component_pct").reset_index()
        sections += ["### Removing replies to posts", markdown_table(sensitivity),
            "Differences in largest-component coverage quantify how much connectivity depends on replies to thread starters. "
            "Both graph variants retain observed commenters, so an isolated user is included in the denominator."]
        validation = out / "gephi_validation.csv"
        if validation.exists():
            checked = pd.read_csv(validation)
            sections += ["### Native Gephi verification", markdown_table(checked[["window", "subreddit", "nodes", "edges", "degree_mismatches", "project_reopened"]]),
                "The official Gephi Toolkit imported the full graphs, verified directed degrees and total reply weight, "
                "recomputed weighted PageRank, generated ForceAtlas2 display layouts and saved/reopened native two-workspace projects. "
                "These are engine-verified artifacts; desktop GUI inspection was unavailable because desktop automation failed to initialize."]
            for r in checked.itertuples():
                path = f"outputs/study/figures/gephi_{r.pair}_{r.window}_{r.subreddit}_all_replies.png"
                sections += [f"![Gephi display: {r.subreddit}, {r.window}]({path})",
                    f"*r/{r.subreddit}, {r.window}: focus with directed weights ≥2 and resulting isolates removed; ForceAtlas2 (400 iterations, seed 42); "
                    "size reflects incoming reply strength; colors follow the imported Louvain communities with an eight-color repeating palette. "
                    f"Shown: {int(r.display_nodes):,} nodes and {int(r.display_edges):,} edges; "
                    f"full graph: {int(r.nodes):,} nodes and {int(r.edges):,} edges. No user labels are displayed.*"]
    tests = load(out, "tests")
    if not tests.empty:
        primary = tests[(tests["scorer"] == "vader_adapted") & (tests["contrast"] == "any_rival_mention")]
        sections += ["## RQ1: content and sentiment", markdown_table(primary[["window", "subreddit", "n_a", "n_b", "effect_size_r", "author_diff", "author_ci_low", "author_ci_high", "supported_both_clusterings"]]),
            "Positive differences mean own-franchise-only comments score more positively than rival-mentioning comments. "
            "These are **whole-comment sentiment** measurements, not target-specific attitudes. For example, a negative "
            "comment can criticise one's own franchise while praising the rival. Alias matches measure explicit mentions "
            "and can miss implicit references or include ambiguous ones.",
            "Both original and domain-adapted VADER are reported, including rival-only and any-rival-mention definitions. "
            "Removing plot/franchise words can also remove real negative language; adaptation is a sensitivity analysis, "
            "not established ground truth. Comparisons report rank-biserial effects, independent user- and thread-cluster "
            "bootstraps, and Holm adjustment over all scorer/definition/community contrasts within a pair-period. "
            "This does not implement simultaneous two-way clustering and does not remove temporal confounding.",
            "Topics use a shared TF-IDF/NMF model for each pair across both periods, with balanced training allocation "
            "by community-period. Candidate K values are compared by in-sample NPMI coherence; this is an exploratory "
            "heuristic, not held-out validation. Per-period topic proportions and weekly mention/sentiment trends are in the tables."]
        supported = primary[primary["supported_both_clusterings"] == True]
        negative = int((supported["author_diff"] < 0).sum())
        positive = int((supported["author_diff"] > 0).sum())
        sections += [f"Across the {len(primary)} displayed community-period comparisons, {len(supported)} meet the "
            f"Holm-adjusted threshold in both clustering sensitivities: {negative} have a negative own-minus-rival "
            f"difference and {positive} a positive difference. A negative difference means rival-mentioning comments "
            "score more positively on average, which does not support interpreting mentions as automatically hostile. "
            "Statistical separation does not establish a practically large effect or a valid stance measurement."]
        topic_rows = load(out, "topics")
        if not topic_rows.empty:
            unassigned = topic_rows[topic_rows["topic"] == -1]
            if not unassigned.empty:
                sections += [f"Between {unassigned['share_pct'].min():.1f}% and {unassigned['share_pct'].max():.1f}% "
                    "of content comments across the reported community-periods have insufficient topical vocabulary "
                    "and remain unassigned (topic -1). Topic proportions retain those comments in their denominators; "
                    "topic keywords are model summaries requiring interpretation, not validated human categories."]
        sections += ["![Weekly content](outputs/study/figures/weekly_content.png)"]
        for pair in design["pairs"]:
            for sub in pair["communities"]:
                chart = out / "figures" / f"topics_{pair['id']}_{sub}.png"
                if chart.exists():
                    sections += [f"![Topics in {sub}]({chart.as_posix()})"]
    sections += ["## Validation still needed before submission",
        "The inherited 300-example sentiment development set was labelled by an AI assistant. It is **not a human gold standard**, "
        "and selecting a model on that same set does not establish held-out accuracy. It was also length-restricted and "
        "stratified, so its stance proportions cannot be extrapolated to all comments. No population hostility rate is claimed. "
        "Use [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md) for a blinded independent human check. "
        "Record actual individual contributions separately; the previous autogenerated contribution table is not evidence of who did what.",
        "## Limitations and interpretation",
        "Two purposively selected rivalries and two adjacent windows cannot identify a general causal effect of rivalry. "
        "Archive omissions, moderation, bot detection, language filtering, asymmetric alias vocabularies and event-driven "
        "activity affect measurement. Baseline audiences differ in size and subject matter. Network topology reflects reply/thread "
        "mechanics as well as social organization. More data improves observable coverage; it does not guarantee stronger "
        "effects or validate an echo-chamber claim. Null and mixed findings are valid outcomes.",
        "## Reproduction and sources",
        "Run `python run_study.py --stage all` to collect, analyze and regenerate this report. "
        "Use `--stage inventory` to audit coverage, `--stage analyze` to reuse local raw caches, and `--stage report` "
        "to rebuild figures/report from aggregates. Fixed dates and seeds are in `study.json`.",
        "- [Arctic Shift API and pagination documentation](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)\n"
        "- [NetworkX reciprocal-edge conversion semantics](https://networkx.org/documentation/stable/reference/classes/generated/networkx.DiGraph.to_undirected.html)\n"
        "- [Gephi documentation](https://docs.gephi.org/)\n"
        "- [VADER original paper](https://ojs.aaai.org/index.php/ICWSM/article/view/14550)\n"
        "- [The echo chamber effect on social media](https://doi.org/10.1073/pnas.2023301118)"]
    Path("REPORT.md").write_text("\n\n".join(sections) + "\n", encoding="utf-8")
    print("Generated REPORT.md and aggregate figures", flush=True)
