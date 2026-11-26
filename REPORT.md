# Fandom Fault Lines

## Comparative longitudinal study

Repository maintainer: **gmayank9999**. Course: Computational Social Media Analysis. This report is generated from the aggregate tables in `outputs/study/tables/`. The original sampled pilot is superseded; its 5% overlap conclusion must not be reused.

## Research design

**Main question:** To what extent do rival fan communities form separate versus overlapping audiences, and how do their content, internal reply structure and cross-group participation boundaries differ? RQ1–RQ3 retain the original content/structure/boundary objectives. RQ4 is an added robustness question; the longitudinal and adjusted analyses strengthen the original three questions.

We compare Marvel/DC and PlayStation/Xbox communities over two adjacent 28-day UTC windows: 3 September–1 October and 1–29 October 2026 (ends exclusive), spanning 56 days. StarWars and lotr provide comparison audiences, not assumed hostile or rivalry-free controls. Pair selection reflects competing franchises/brands; individual users are not classified as fans or opponents. This extension was designed after inspecting the pilot and is exploratory, not preregistered.

1. **RQ1 — Content:** How do topics, franchise mentions and whole-comment sentiment differ across communities and periods?
2. **RQ2 — Structure:** Which users connect observed reply networks, and how sensitive is structure to including replies to posts?
3. **RQ3 — Boundaries:** How much observed participation overlaps, relative to other audience pairs?
4. **RQ4 — Stability:** How do those measurements change with period, duration and sampling effort?

## Data coverage and provenance

| window | subreddit | expected_days | valid_days | rows | complete_files |
| --- | --- | --- | --- | --- | --- |
| sep | marvelstudios | 28 | 28 | 167661 | True |
| sep | DC_Cinematic | 28 | 28 | 88049 | True |
| sep | PS5 | 28 | 28 | 99959 | True |
| sep | xbox | 28 | 28 | 92898 | True |
| sep | StarWars | 28 | 28 | 101882 | True |
| sep | lotr | 28 | 28 | 41004 | True |
| oct | marvelstudios | 28 | 28 | 138911 | True |
| oct | DC_Cinematic | 28 | 28 | 140166 | True |
| oct | PS5 | 28 | 28 | 72109 | True |
| oct | xbox | 28 | 28 | 88966 | True |
| oct | StarWars | 28 | 28 | 99426 | True |
| oct | lotr | 28 | 28 | 37607 | True |

A complete file set means every expected day is present and passes schema, ID and UTC-boundary checks. It does **not** certify that the archive contains every Reddit comment. New downloads record retrieval times and SHA-256 checksums; inherited caches have no historical request manifests. The collector fails on ambiguous timestamp pagination or a safety-cap limit, rather than saving a truncated day.

**Execution status:** Both designated pairs have aggregate analysis outputs.

## Corpus

| pair | window | subreddit | raw_comments | participation_comments | content_comments | commenters | rival_mention_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| consoles | sep | PS5 | 99959 | 98060 | 96515 | 31217 | 3.34 |
| consoles | sep | xbox | 92898 | 90958 | 89870 | 27387 | 6.17 |
| consoles | oct | PS5 | 72109 | 70950 | 69575 | 25665 | 1.92 |
| consoles | oct | xbox | 88966 | 87468 | 86553 | 27055 | 6.23 |
| superheroes | sep | marvelstudios | 167661 | 164337 | 159073 | 47298 | 0.906 |
| superheroes | sep | DC_Cinematic | 88049 | 83745 | 83217 | 21631 | 2.63 |
| superheroes | oct | marvelstudios | 138911 | 137215 | 133558 | 37315 | 0.766 |
| superheroes | oct | DC_Cinematic | 140166 | 134952 | 134151 | 27725 | 3.41 |

Participation retains non-bot commenters even when their text is removed or too short for NLP. Content removes deleted/empty bodies, URLs/embeds, very short and non-letter text. This separates observable participation from usable linguistic evidence. Bot removal is a documented account list, not a comprehensive bot classifier. Counts are archive observations, not Reddit membership estimates.

## RQ3 and RQ4: audience boundaries

| pair | window | users_a | users_b | shared | pct_a | pct_b | jaccard_pct |
| --- | --- | --- | --- | --- | --- | --- | --- |
| consoles | sep | 31217 | 27387 | 2658 | 8.51 | 9.71 | 4.75 |
| consoles | oct | 25665 | 27055 | 2460 | 9.59 | 9.09 | 4.89 |
| consoles | pooled_56d | 46540 | 44309 | 4978 | 10.70 | 11.23 | 5.80 |
| superheroes | sep | 47298 | 21631 | 4378 | 9.26 | 20.24 | 6.78 |
| superheroes | oct | 37315 | 27725 | 4548 | 12.19 | 16.40 | 7.52 |
| superheroes | pooled_56d | 68608 | 39901 | 8807 | 12.84 | 22.07 | 8.83 |

A/B follow the order in `study.json`: Marvel/DC and PS5/xbox. Percentages use different denominators: shared/A, shared/B, and shared/(A∪B). The 56-day row deduplicates users across periods; it does not add monthly user counts. All activity thresholds (≥1, ≥2, ≥5 comments) appear in the accompanying table. Co-participation alone does not establish allegiance, exposure to opposing opinions, hostility or an echo chamber.

![Overlap](outputs/study/figures/overlap.png)

![Sensitivity](outputs/study/figures/sensitivity.png)

The subsampling experiment deliberately discards comments at fixed fractions, using five deterministic random draws. Its shaded ranges are sensitivity ranges, not confidence intervals. Cumulative 7/14/21/28-day curves show detection changes with duration; these nested windows are not independent observations.

**consoles, 56-day observation:** 4,978 users appear in both communities, representing 10.7% of PS5 commenters and 11.2% of xbox commenters (Jaccard 5.80%). This is a directional, period-specific participation result, not a binary verdict about whether the fandoms are closed.

For consoles, monthly Jaccard changes from 4.75% to 4.89% (+0.14 percentage points). This is a descriptive period comparison; the same people can appear in both windows.

**superheroes, 56-day observation:** 8,807 users appear in both communities, representing 12.8% of marvelstudios commenters and 22.1% of DC_Cinematic commenters (Jaccard 8.83%). This is a directional, period-specific participation result, not a binary verdict about whether the fandoms are closed.

For superheroes, monthly Jaccard changes from 6.78% to 7.52% (+0.74 percentage points). This is a descriptive period comparison; the same people can appear in both windows.

### Comparison audiences

| window | community_a | community_b | shared | pct_smaller | jaccard_pct |
| --- | --- | --- | --- | --- | --- |
| sep | marvelstudios | DC_Cinematic | 4378 | 20.24 | 6.78 |
| sep | marvelstudios | PS5 | 1962 | 6.29 | 2.56 |
| sep | marvelstudios | xbox | 1110 | 4.05 | 1.51 |
| sep | marvelstudios | StarWars | 3742 | 11.63 | 4.94 |
| sep | marvelstudios | lotr | 1057 | 6.05 | 1.66 |
| sep | DC_Cinematic | PS5 | 1028 | 4.75 | 1.98 |
| sep | DC_Cinematic | xbox | 566 | 2.62 | 1.17 |
| sep | DC_Cinematic | StarWars | 1615 | 7.47 | 3.09 |
| sep | DC_Cinematic | lotr | 360 | 2.06 | 0.930 |
| sep | PS5 | xbox | 2658 | 9.71 | 4.75 |
| sep | PS5 | StarWars | 1035 | 3.32 | 1.66 |
| sep | PS5 | lotr | 386 | 2.21 | 0.799 |
| sep | xbox | StarWars | 825 | 3.01 | 1.40 |
| sep | xbox | lotr | 237 | 1.36 | 0.531 |
| sep | StarWars | lotr | 1506 | 8.63 | 3.13 |
| oct | marvelstudios | DC_Cinematic | 4548 | 16.40 | 7.52 |
| oct | marvelstudios | PS5 | 1365 | 5.32 | 2.22 |
| oct | marvelstudios | xbox | 907 | 3.35 | 1.43 |
| oct | marvelstudios | StarWars | 3157 | 9.55 | 4.70 |
| oct | marvelstudios | lotr | 791 | 4.89 | 1.50 |
| oct | DC_Cinematic | PS5 | 1096 | 4.27 | 2.10 |
| oct | DC_Cinematic | xbox | 791 | 2.92 | 1.47 |
| oct | DC_Cinematic | StarWars | 1946 | 7.02 | 3.31 |
| oct | DC_Cinematic | lotr | 439 | 2.72 | 1.01 |
| oct | PS5 | xbox | 2460 | 9.59 | 4.89 |
| oct | PS5 | StarWars | 1181 | 4.60 | 2.05 |
| oct | PS5 | lotr | 315 | 1.95 | 0.759 |
| oct | xbox | StarWars | 1058 | 3.91 | 1.79 |
| oct | xbox | lotr | 256 | 1.58 | 0.596 |
| oct | StarWars | lotr | 1519 | 9.40 | 3.18 |

All pairs use the same participation filtering. We omit the old 'lift' interpretation: choosing the union of a few selected subreddits as the population does not supply a neutral model of all Reddit participation.

![Audience comparison matrix](outputs/study/figures/audience_overlap_matrix.png)

The six-node Gephi files in `outputs/study/aggregate_networks/` represent subreddits, with edge weight equal to Jaccard overlap. They contain only aggregates and are public. These audience-similarity graphs are distinct from user reply networks and do not measure hostility.

In oct, the highest observed Jaccard among the 15 selected audience pairs is marvelstudios/DC_Cinematic (7.52%). This ranking is conditional on the chosen six communities; it is not a Reddit-wide benchmark.

In sep, the highest observed Jaccard among the 15 selected audience pairs is marvelstudios/DC_Cinematic (6.78%). This ranking is conditional on the chosen six communities; it is not a Reddit-wide benchmark.

## RQ2: reply-network structure

| window | subreddit | nodes | edges | resolved_parent_pct | largest_component_pct | reciprocity | modularity_weighted | modularity_excess |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sep | PS5 | 32104 | 86348 | 99.75 | 96.57 | 0.243 | 0.521 | 0.029 |
| sep | xbox | 28390 | 80906 | 99.90 | 98.61 | 0.249 | 0.494 | 0.035 |
| oct | PS5 | 26332 | 62263 | 99.18 | 96.94 | 0.252 | 0.582 | 0.034 |
| oct | xbox | 27960 | 77402 | 99.40 | 98.75 | 0.269 | 0.518 | 0.040 |
| sep | marvelstudios | 49487 | 147982 | 99.88 | 95.83 | 0.217 | 0.458 | 0.023 |
| sep | DC_Cinematic | 22130 | 71108 | 99.95 | 98.59 | 0.275 | 0.474 | 0.042 |
| oct | marvelstudios | 39205 | 121963 | 99.64 | 96.04 | 0.240 | 0.463 | 0.036 |
| oct | DC_Cinematic | 28104 | 111636 | 99.66 | 99.23 | 0.294 | 0.407 | 0.026 |

A directed edge runs from the replier to the parent author; weight counts replies. Self-replies are excluded and counted, and isolated observed commenters remain nodes. Parent-only nodes are marked separately. Missing parents reduce coverage and are reported, not imputed. Reciprocal edge weights are summed for the undirected Louvain projection. Weighted PageRank, in/out degree, strengths, k-core and participation coefficient supplement directed, unweighted betweenness (reply frequency is not a distance).

The null comparison uses **unweighted observed modularity versus unweighted rewired modularity**. Each uses the same degree sequence with 10 requested rewires. The excess is descriptive, not a significance test; this small null ensemble cannot support a precise tail probability. Separate comment-to-comment graphs remove thread-starting hubs as a sensitivity analysis. Centrality denotes structural position, not influence. Approximate betweenness is checked with two seeds; top-20 set overlap is supplied in the network table.

![Network null](outputs/study/figures/network_null.png)

### Gephi deliverables

Full and display-filtered GEXF files and node/edge CSVs are in `outputs/study/networks/` locally. See [GEPHI_GUIDE.md](GEPHI_GUIDE.md) for import settings, metric definitions, layout and export steps. Network files contain pseudonymous user-level information and are excluded from Git. All reported metrics use full graphs; filtered visualizations are never used to estimate population structure.

### Removing replies to posts

| window | subreddit | all_replies | comment_replies |
| --- | --- | --- | --- |
| oct | DC_Cinematic | 99.23 | 69.31 |
| oct | PS5 | 96.94 | 71.68 |
| oct | marvelstudios | 96.04 | 64.89 |
| oct | xbox | 98.75 | 60.87 |
| sep | DC_Cinematic | 98.59 | 64.66 |
| sep | PS5 | 96.57 | 69.53 |
| sep | marvelstudios | 95.83 | 59.31 |
| sep | xbox | 98.61 | 53.33 |

Differences in largest-component coverage quantify how much connectivity depends on replies to thread starters. Both graph variants retain observed commenters, so an isolated user is included in the denominator.

### Cross-participants among structural connectors

| window | subreddit | observed_shared_pct | selected_nodes | selected_parent_only_nodes | selected_shared_pct_of_observed | selected_observed_median_threads |
| --- | --- | --- | --- | --- | --- | --- |
| sep | PS5 | 8.51 | 20 | 0 | 10.00 | 40.00 |
| sep | xbox | 9.71 | 20 | 0 | 30.00 | 39.50 |
| oct | PS5 | 9.59 | 20 | 0 | 30.00 | 24.00 |
| oct | xbox | 9.09 | 20 | 0 | 35.00 | 55.50 |
| sep | marvelstudios | 9.26 | 20 | 0 | 25.00 | 70.50 |
| sep | DC_Cinematic | 20.24 | 20 | 0 | 30.00 | 58.50 |
| oct | marvelstudios | 12.19 | 20 | 0 | 15.00 | 94.50 |
| oct | DC_Cinematic | 16.40 | 20 | 0 | 15.00 | 68.50 |

The selection contains the top 20 positive betweenness scores, including every tie at the cutoff. Shared-participant percentages use observed commenters as their denominator; parent-only nodes are shown separately. The baseline is all observed commenters in that community-period. PageRank, incoming-strength and comment-only variants are in the connector-role tables. These are descriptive role comparisons, not a significance test or proof that an account transmits ideas between subreddits. Approximate betweenness rankings can change with the sampling seed.

These unadjusted connector percentages must be read with the activity- and degree-matched comparison in the extended analysis below; prolific activity can explain apparent overrepresentation.

### Native Gephi verification

| window | subreddit | nodes | edges | degree_mismatches | project_reopened |
| --- | --- | --- | --- | --- | --- |
| sep | PS5 | 32104 | 86348 | 0 | True |
| sep | xbox | 28390 | 80906 | 0 | True |
| oct | PS5 | 26332 | 62263 | 0 | True |
| oct | xbox | 27960 | 77402 | 0 | True |
| sep | marvelstudios | 49487 | 147982 | 0 | True |
| sep | DC_Cinematic | 22130 | 71108 | 0 | True |
| oct | marvelstudios | 39205 | 121963 | 0 | True |
| oct | DC_Cinematic | 28104 | 111636 | 0 | True |

The official Gephi Toolkit imported the full graphs, verified directed degrees and total reply weight, recomputed weighted PageRank, generated ForceAtlas2 display layouts and saved/reopened native two-workspace projects. These are engine-verified artifacts; desktop GUI inspection was unavailable because desktop automation failed to initialize.

![Gephi display: PS5, sep](outputs/study/figures/gephi_consoles_sep_PS5_all_replies.png)

*r/PS5, sep: focus with directed weights ≥2 and resulting isolates removed; ForceAtlas2 (400 iterations, seed 42); size reflects incoming reply strength; colors follow the imported Louvain communities with an eight-color repeating palette. Shown: 728 nodes and 1,551 edges; full graph: 32,104 nodes and 86,348 edges. No user labels are displayed.*

![Gephi display: xbox, sep](outputs/study/figures/gephi_consoles_sep_xbox_all_replies.png)

*r/xbox, sep: focus with directed weights ≥2 and resulting isolates removed; ForceAtlas2 (400 iterations, seed 42); size reflects incoming reply strength; colors follow the imported Louvain communities with an eight-color repeating palette. Shown: 767 nodes and 1,677 edges; full graph: 28,390 nodes and 80,906 edges. No user labels are displayed.*

![Gephi display: PS5, oct](outputs/study/figures/gephi_consoles_oct_PS5_all_replies.png)

*r/PS5, oct: focus with directed weights ≥2 and resulting isolates removed; ForceAtlas2 (400 iterations, seed 42); size reflects incoming reply strength; colors follow the imported Louvain communities with an eight-color repeating palette. Shown: 650 nodes and 1,109 edges; full graph: 26,332 nodes and 62,263 edges. No user labels are displayed.*

![Gephi display: xbox, oct](outputs/study/figures/gephi_consoles_oct_xbox_all_replies.png)

*r/xbox, oct: focus with directed weights ≥2 and resulting isolates removed; ForceAtlas2 (400 iterations, seed 42); size reflects incoming reply strength; colors follow the imported Louvain communities with an eight-color repeating palette. Shown: 756 nodes and 1,575 edges; full graph: 27,960 nodes and 77,402 edges. No user labels are displayed.*

![Gephi display: marvelstudios, sep](outputs/study/figures/gephi_superheroes_sep_marvelstudios_all_replies.png)

*r/marvelstudios, sep: focus with directed weights ≥2 and resulting isolates removed; ForceAtlas2 (400 iterations, seed 42); size reflects incoming reply strength; colors follow the imported Louvain communities with an eight-color repeating palette. Shown: 844 nodes and 2,411 edges; full graph: 49,487 nodes and 147,982 edges. No user labels are displayed.*

![Gephi display: DC_Cinematic, sep](outputs/study/figures/gephi_superheroes_sep_DC_Cinematic_all_replies.png)

*r/DC_Cinematic, sep: focus with directed weights ≥2 and resulting isolates removed; ForceAtlas2 (400 iterations, seed 42); size reflects incoming reply strength; colors follow the imported Louvain communities with an eight-color repeating palette. Shown: 898 nodes and 2,714 edges; full graph: 22,130 nodes and 71,108 edges. No user labels are displayed.*

![Gephi display: marvelstudios, oct](outputs/study/figures/gephi_superheroes_oct_marvelstudios_all_replies.png)

*r/marvelstudios, oct: focus with directed weights ≥2 and resulting isolates removed; ForceAtlas2 (400 iterations, seed 42); size reflects incoming reply strength; colors follow the imported Louvain communities with an eight-color repeating palette. Shown: 834 nodes and 2,256 edges; full graph: 39,205 nodes and 121,963 edges. No user labels are displayed.*

![Gephi display: DC_Cinematic, oct](outputs/study/figures/gephi_superheroes_oct_DC_Cinematic_all_replies.png)

*r/DC_Cinematic, oct: focus with directed weights ≥2 and resulting isolates removed; ForceAtlas2 (400 iterations, seed 42); size reflects incoming reply strength; colors follow the imported Louvain communities with an eight-color repeating palette. Shown: 986 nodes and 4,350 edges; full graph: 28,104 nodes and 111,636 edges. No user labels are displayed.*

## RQ1: content and sentiment

| window | subreddit | n_a | n_b | effect_size_r | author_diff | author_ci_low | author_ci_high | supported_both_clusterings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| sep | PS5 | 10267 | 3219 | -0.032 | -0.032 | -0.058 | -0.004 | False |
| sep | xbox | 16881 | 5546 | 0.003 | 0.012 | -0.014 | 0.046 | False |
| oct | PS5 | 5780 | 1335 | 0.024 | 0.029 | -0.010 | 0.066 | False |
| oct | xbox | 16532 | 5391 | -0.031 | -0.017 | -0.042 | 0.014 | False |
| sep | marvelstudios | 36584 | 1441 | -0.030 | -0.031 | -0.057 | -0.002 | False |
| sep | DC_Cinematic | 17442 | 2187 | -0.118 | -0.101 | -0.127 | -0.076 | True |
| oct | marvelstudios | 28267 | 1023 | -0.046 | -0.046 | -0.076 | -0.014 | True |
| oct | DC_Cinematic | 27083 | 4573 | -0.076 | -0.066 | -0.083 | -0.048 | True |

Positive differences mean own-franchise-only comments score more positively than rival-mentioning comments. These are **whole-comment sentiment** measurements, not target-specific attitudes. For example, a negative comment can criticise one's own franchise while praising the rival. Alias matches measure explicit mentions and can miss implicit references or include ambiguous ones.

Both original and domain-adapted VADER are reported, including rival-only and any-rival-mention definitions. Removing plot/franchise words can also remove real negative language; adaptation is a sensitivity analysis, not established ground truth. Comparisons report rank-biserial effects, independent user- and thread-cluster bootstraps, and Holm adjustment over all scorer/definition/community contrasts within a pair-period. This does not implement simultaneous two-way clustering and does not remove temporal confounding.

Topics use a shared TF-IDF/NMF model for each pair across both periods, with balanced training allocation by community-period. Candidate K values are compared by in-sample NPMI coherence; this is an exploratory heuristic, not held-out validation. Per-period topic proportions and weekly mention/sentiment trends are in the tables.

Across the 8 displayed community-period comparisons, 3 meet the Holm-adjusted threshold in both clustering sensitivities: 3 have a negative own-minus-rival difference and 0 a positive difference. A negative difference means rival-mentioning comments score more positively on average, which does not support interpreting mentions as automatically hostile. Statistical separation does not establish a practically large effect or a valid stance measurement.

Between 31.7% and 37.4% of content comments across the reported community-periods have insufficient topical vocabulary and remain unassigned (topic -1). Topic proportions retain those comments in their denominators; topic keywords are model summaries requiring interpretation, not validated human categories. Some factors capture generic conversation or moderation boilerplate; they must not be relabelled as rivalry themes without text review.

![Weekly content](outputs/study/figures/weekly_content.png)

![Topics in marvelstudios](outputs/study/figures/topics_superheroes_marvelstudios.png)

![Topics in DC_Cinematic](outputs/study/figures/topics_superheroes_DC_Cinematic.png)

![Topics in PS5](outputs/study/figures/topics_consoles_PS5.png)

![Topics in xbox](outputs/study/figures/topics_consoles_xbox.png)

## Extended analysis: persistence, composition and connector roles

These analyses were specified in `advanced_study.json` after inspecting the original results and before running this extension. They are exploratory, not preregistered. All use the existing two observation windows; they do not add new communities or establish a causal effect of rivalry.

### Are shared audiences persistent?

A/B follow `study.json`: Marvel/DC and PS5/xbox. Each person in the union of the two windows is classified by their observed activity in each period. The neither-to-neither cell is a structural zero at the one-comment threshold because this is an observed union cohort. The first-window neither row describes later arrivals; it is not a return rate for all Reddit users. At stricter thresholds, neither means below threshold in both communities.

![Participation transitions](outputs/study/figures/participation_transitions.png)

| pair | pattern | users | pct_pooled_shared |
| --- | --- | --- | --- |
| superheroes | both_in_each_window | 1577 | 17.91 |
| superheroes | both_first_window_only | 2801 | 31.80 |
| superheroes | both_second_window_only | 2971 | 33.73 |
| superheroes | pooled_only_no_window_both | 1458 | 16.56 |
| consoles | both_in_each_window | 945 | 18.98 |
| consoles | both_first_window_only | 1713 | 34.41 |
| consoles | both_second_window_only | 1515 | 30.43 |
| consoles | pooled_only_no_window_both | 805 | 16.17 |

Pooled overlap is decomposed into users active in both communities in each window, in just one window, or only across the combined period. At threshold one, the last category represents sequential participation with no within-window overlap; at higher thresholds it can also reflect activity accumulating across periods. Results at two and five comments per community are retained in the extension tables. Absence means no observed activity in this pair during that window, not leaving Reddit or changing allegiance.

The persistent percentage above uses all pooled shared users as its denominator. A different question is what fraction of first-window shared users are shared again: read the both-to-both cell of the transition matrix for that conditional percentage. These denominators must not be interchanged.

### Does the return-rate difference survive activity adjustment?

| pair | reference | raw_both_pct | raw_exclusive_pct | adjusted_both_pct | adjusted_exclusive_pct | adjusted_difference_pp | ci_low_pp | ci_high_pp |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| superheroes | a_only | 75.29 | 34.12 | 68.97 | 55.88 | 13.08 | 11.39 | 14.74 |
| superheroes | b_only | 75.29 | 42.89 | 70.71 | 63.49 | 7.23 | 5.50 | 8.92 |
| consoles | a_only | 77.13 | 32.93 | 68.79 | 53.50 | 15.28 | 13.02 | 17.49 |
| consoles | b_only | 77.13 | 35.91 | 68.99 | 58.04 | 10.95 | 8.84 | 13.17 |

![Adjusted retention](outputs/study/figures/activity_adjusted_retention.png)

Both versus A-only and both versus B-only are separate first-window cohort comparisons. Return means at least one observed comment anywhere in the pair during the second window. Adjustment uses fixed bins of total first-window comments: 1, 2–4, 5–9, 10–19, 20–49, 50–99, and 100+. Each comparison uses the pooled activity distribution of groups within common-support bins as its target. The groups differ in their raw activity composition; users outside common support do not contribute to adjusted rates. Counts and exclusions are in retention.csv and retention_strata.csv. Intervals resample binary outcomes within fixed group/bin sample sizes, with weights held fixed (5,000 draws). These are unadjusted descriptive 95% intervals. Coarse bins leave residual confounding; this association does not show that cross-participation causes retention.

| pair | reference | both_users | exclusive_users | common_both_users | common_exclusive_users |
| --- | --- | --- | --- | --- | --- |
| superheroes | a_only | 4378 | 42920 | 4378 | 17764 |
| superheroes | b_only | 4378 | 17253 | 4378 | 7496 |
| consoles | a_only | 2658 | 28559 | 2658 | 11976 |
| consoles | b_only | 2658 | 24729 | 2658 | 10279 |

In particular, an initially shared user must have at least two comments. One-comment exclusive users have no shared-user counterpart and are excluded from the standardized target. Thus raw-versus-adjusted differences reflect both activity standardization and a restriction to common support.

### Does the sentiment difference persist within the same authors?

| window | subreddit | paired_authors | author_equal_weight_difference | ci_low | ci_high |
| --- | --- | --- | --- | --- | --- |
| oct | DC_Cinematic | 1719 | -0.051 | -0.079 | -0.022 |
| oct | marvelstudios | 517 | -0.030 | -0.077 | 0.020 |
| sep | DC_Cinematic | 878 | -0.076 | -0.114 | -0.037 |
| sep | marvelstudios | 706 | -0.027 | -0.069 | 0.014 |
| oct | PS5 | 365 | -0.018 | -0.077 | 0.040 |
| oct | xbox | 1548 | -0.022 | -0.049 | 0.007 |
| sep | PS5 | 832 | -0.055 | -0.095 | -0.015 |
| sep | xbox | 1539 | -0.022 | -0.049 | 0.006 |

![Within-author sentiment](outputs/study/figures/within_author_sentiment.png)

Only authors with both own-only and rival-mentioning comments in the same community-period enter this comparison. Each author contributes one difference between their category mean scores, and authors receive equal weight. This addresses stable differences between authors and prolific-user weighting, while changing the population to authors who wrote both kinds of comment. It does not control topic, thread, timing, sarcasm or target stance. The 95% percentile intervals resample paired authors 5,000 times; they are not adjusted for multiple comparisons and are not labelled significant. Original/adapted VADER, rival-only/any-rival definitions, and minimum one/three comments in each category are all retained. Fewer than 20 eligible authors yields no interval.

### Are cross-participants unusually common among connectors after matching?

| window | subreddit | selected_users | observed_shared_pct | matched_expected_shared_pct | excess_pp | enrichment_p_holm |
| --- | --- | --- | --- | --- | --- | --- |
| sep | marvelstudios | 20 | 25.00 | 19.74 | 5.26 | 1.00 |
| sep | DC_Cinematic | 20 | 30.00 | 26.79 | 3.21 | 1.00 |
| oct | marvelstudios | 20 | 15.00 | 17.71 | -2.71 | 1.00 |
| oct | DC_Cinematic | 20 | 15.00 | 28.93 | -13.93 | 1.00 |
| sep | PS5 | 20 | 10.00 | 23.85 | -13.85 | 1.00 |
| sep | xbox | 20 | 30.00 | 34.95 | -4.95 | 1.00 |
| oct | PS5 | 20 | 30.00 | 34.35 | -4.35 | 1.00 |
| oct | xbox | 20 | 35.00 | 28.88 | 6.12 | 1.00 |

![Matched connector comparison](outputs/study/figures/matched_connectors.png)

Selection uses the top 20 positive betweenness scores among observed commenters, retaining cutoff ties. Within fixed bins of comment count and total directed degree (in-degree plus out-degree), random selections preserve the number selected from every stratum. The sum of stratum-specific hypergeometric draws gives a conditional null for the number of shared participants. Degree bin lower bounds are 0, 2, 5, 10, 20, 50, 100 and 200. The one-sided enrichment probability uses a plus-one correction and 5,000 draws; Holm adjustment covers all 32 community-period/network-variant/matching comparisons. Activity-only matching and comment-only networks are retained as sensitivities. Exchangeability within coarse bins is an assumption, not random assignment. Matching cannot remove unmeasured differences, and approximate betweenness ranking uncertainty remains. The null ranges describe randomized selected counts, not confidence intervals for population effects. A top-20 selection has limited power; failure to detect enrichment does not establish equivalence or no role for shared users.

**superheroes:** 1,577 of 8,807 pooled shared users appear in both communities in each window (17.9%). 16.6% have only sequential cross-window participation.

**consoles:** 945 of 4,978 pooled shared users appear in both communities in each window (19.0%). 16.2% have only sequential cross-window participation.

Across all 32 specified connector comparisons, 0 meet the Holm-adjusted .05 enrichment threshold. Read this together with the effect sizes and alternative matching definitions; an unadjusted top-20 percentage alone cannot establish unusual connector representation.

## Network construction audit and observed interaction across prior participation groups

All 16 original graphs were independently reconstructed from raw comment records using a parent-author join and grouped counts. Every saved directed edge, reply weight and node set matched. Where both comment records were available, the audit checked that the parent belongs to the same thread; top-level comments reference their thread post. This verifies consistency with the local archive records, not completeness or correctness of the archive itself.

| window | subreddit | variant | edges | incorrect_or_missing_edges | extra_edges | node_set_difference |
| --- | --- | --- | --- | --- | --- | --- |
| sep | marvelstudios | all_replies | 147982 | 0 | 0 | 0 |
| sep | DC_Cinematic | all_replies | 71108 | 0 | 0 | 0 |
| sep | marvelstudios | comment_replies | 77474 | 0 | 0 | 0 |
| sep | DC_Cinematic | comment_replies | 40848 | 0 | 0 | 0 |
| oct | marvelstudios | all_replies | 121963 | 0 | 0 | 0 |
| oct | DC_Cinematic | all_replies | 111636 | 0 | 0 | 0 |
| oct | marvelstudios | comment_replies | 69141 | 0 | 0 | 0 |
| oct | DC_Cinematic | comment_replies | 69853 | 0 | 0 | 0 |
| sep | PS5 | all_replies | 86348 | 0 | 0 | 0 |
| sep | xbox | all_replies | 80906 | 0 | 0 | 0 |
| sep | PS5 | comment_replies | 58038 | 0 | 0 | 0 |
| sep | xbox | comment_replies | 39161 | 0 | 0 | 0 |
| oct | PS5 | all_replies | 62263 | 0 | 0 | 0 |
| oct | xbox | all_replies | 77402 | 0 | 0 | 0 |
| oct | PS5 | comment_replies | 43258 | 0 | 0 | 0 |
| oct | xbox | comment_replies | 42264 | 0 | 0 | 0 |

### From membership overlap to observed replies

Users are labelled from the first window only: A-only, B-only, both, or unobserved. These are participation categories, not fan allegiance, opinion or hostility. We then combine the two communities' second-window reply graphs by merging identical account identifiers and summing only observed reply weights. Each edge retains its separate community-A/community-B reply counts. Shared membership creates no artificial edges. The same ordered dyad present in both layers is one combined dyad, with its reply events summed.

A reply between prior A-only and prior B-only participants is direct observed interaction between those participation groups in the second window. It occurs inside a subreddit thread; it is not a comment physically replying across subreddits and does not establish information diffusion.

| pair | variant | total | known_prior_endpoint_pct | prior_exclusive_opposite_count | prior_exclusive_opposite_pct_all | categorical_assortativity_known |
| --- | --- | --- | --- | --- | --- | --- |
| superheroes | all_replies | 270,428.00 | 47.95 | 7,428.00 | 2.75 | 0.348 |
| superheroes | comment_replies | 167,617.00 | 52.50 | 4,908.00 | 2.93 | 0.347 |
| consoles | all_replies | 156,727.00 | 45.63 | 3,438.00 | 2.19 | 0.349 |
| consoles | comment_replies | 98,796.00 | 50.09 | 2,240.00 | 2.27 | 0.387 |

![Prior participation mixing](outputs/study/figures/prior_participation_mixing.png)

The matrix retains unobserved endpoints explicitly. Known-prior-endpoint coverage is the fraction of reply events for which both accounts were observed in the pair during the first window. The categorical assortativity coefficient is calculated only on that known subset: (observed same-group fraction minus the row/column marginal expectation) divided by (one minus that expectation). It is descriptive, with no null-model significance claim. It measures mixing by prior participation, not ideological homophily. Full matrices are also provided separately for each subreddit and for unweighted ordered dyads. Comment-only variants remove replies to original posts.

### Separate subreddit layers versus their combination

| pair | variant | layer | known_prior_endpoint_pct | categorical_assortativity_known |
| --- | --- | --- | --- | --- |
| superheroes | all_replies | marvelstudios | 49.49 | 0.012 |
| superheroes | all_replies | DC_Cinematic | 46.39 | 0.001 |
| superheroes | all_replies | combined | 47.95 | 0.348 |
| superheroes | comment_replies | marvelstudios | 56.44 | 0.013 |
| superheroes | comment_replies | DC_Cinematic | 48.96 | 0.003 |
| superheroes | comment_replies | combined | 52.50 | 0.347 |
| consoles | all_replies | PS5 | 48.75 | 0.003 |
| consoles | all_replies | xbox | 43.10 | 0.040 |
| consoles | all_replies | combined | 45.63 | 0.349 |
| consoles | comment_replies | PS5 | 48.89 | 0.013 |
| consoles | comment_replies | xbox | 51.30 | 0.032 |
| consoles | comment_replies | combined | 50.09 | 0.387 |

A combined coefficient can be much larger than either layer coefficient because different prior groups participate in different subreddit layers. This aggregation effect means combined segregation cannot automatically be interpreted as selective avoidance of particular users inside a discussion space. All coefficients here use prior participation categories and omit unknown endpoints; they do not measure opinions.

### Combined Gephi exports

| pair | window | variant | full_nodes | full_edges | full_reply_events | display_nodes | display_edges |
| --- | --- | --- | --- | --- | --- | --- | --- |
| superheroes | oct | all_replies | 62620 | 233557 | 270428 | 997 | 15053 |
| superheroes | oct | comment_replies | 61356 | 138992 | 167617 | 982 | 10533 |
| consoles | oct | all_replies | 51782 | 139519 | 156727 | 993 | 7638 |
| consoles | oct | comment_replies | 50692 | 85515 | 98796 | 950 | 5343 |

Local files `outputs/study/networks/combined_*_full.gexf` preserve all observed nodes and edges. The focus files cap nodes by combined PageRank and retain the largest weak component of that cap; these are display-only selections. Node colors encode prior participation: blue A-only, orange B-only, green both, grey unobserved. Node size encodes incoming reply strength. Group labels and per-layer edge weights are available in the Gephi data table. No conclusion is drawn from layout distance.

Native combined projects were saved and reopened by the official Gephi Toolkit, with node/edge/weight and directed-degree checks. Their ForceAtlas2 display further keeps repeated replies (weight at least two) and removes resulting isolates; full workspaces remain intact.

| pair | variant | nodes | edges | degree_mismatches | project_reopened |
| --- | --- | --- | --- | --- | --- |
| superheroes | all_replies | 62620 | 233557 | 0 | True |
| superheroes | comment_replies | 61356 | 138992 | 0 | True |
| consoles | all_replies | 51782 | 139519 | 0 | True |
| consoles | comment_replies | 50692 | 85515 | 0 | True |

![Combined superheroes comment-reply network](outputs/study/figures/gephi_combined_superheroes_oct_comment_replies.png)

*Prior-participation colors; ForceAtlas2 400 iterations, seed 42. Display: 782 nodes/2,801 edges; full: 61,356 nodes/138,992 edges. Layout is illustrative.*

![Combined consoles comment-reply network](outputs/study/figures/gephi_combined_consoles_oct_comment_replies.png)

*Prior-participation colors; ForceAtlas2 400 iterations, seed 42. Display: 577 nodes/1,058 edges; full: 50,692 nodes/85,515 edges. Layout is illustrative.*

## Validation still needed before submission

The inherited 300-example sentiment development set was labelled by an AI assistant. It is **not a human gold standard**, and selecting a model on that same set does not establish held-out accuracy. It was also length-restricted and stratified, so its stance proportions cannot be extrapolated to all comments. No population hostility rate is claimed. Use [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md) for a blinded independent human check. Record actual individual contributions separately; the previous autogenerated contribution table is not evidence of who did what.

## Limitations and interpretation

Two purposively selected rivalries and two adjacent windows cannot identify a general causal effect of rivalry. Archive omissions, moderation, bot detection, language filtering, asymmetric alias vocabularies and event-driven activity affect measurement. Baseline audiences differ in size and subject matter. Network topology reflects reply/thread mechanics as well as social organization. More data improves observable coverage; it does not guarantee stronger effects or validate an echo-chamber claim. Null and mixed findings are valid outcomes.

## Reproduction and sources

Run `python run_study.py --stage all` to collect, analyze and regenerate this report. Use `--stage inventory` to audit coverage, `--stage analyze` to reuse local raw caches, and `--stage report` to rebuild figures/report from aggregates. Fixed dates and seeds are in `study.json`.

- [Arctic Shift API and pagination documentation](https://github.com/ArthurHeitmann/arctic_shift/blob/master/api/README.md)
- [NetworkX reciprocal-edge conversion semantics](https://networkx.org/documentation/stable/reference/classes/generated/networkx.DiGraph.to_undirected.html)
- [Gephi documentation](https://docs.gephi.org/)
- [VADER original paper](https://ojs.aaai.org/index.php/ICWSM/article/view/14550)
- [The echo chamber effect on social media](https://doi.org/10.1073/pnas.2023301118)
