# Gephi analysis and presentation workflow

## Reproduce native projects without clicking through the UI

An optional helper uses the official Gephi Toolkit 0.11.3 to import full/focus
graphs, verify node/edge/weight totals and directed degrees, recompute weighted
PageRank, run ForceAtlas2 on the focus view, export a PNG and save/reopen a native
two-workspace `.gephi` project. This is actual Gephi engine execution; it is not
a claim that the desktop UI was manually inspected.

Download [the official toolkit JAR](https://github.com/gephi/gephi-toolkit/releases/download/v0.11.3/gephi-toolkit-0.11.3-all.jar)
to `.bin/gephi-toolkit-0.11.3-all.jar`. The helper verifies SHA-256
`3201e7c7a8353963d9dc6c180916f2fee882b72ce3f053d51464ac76863a545b`.
With JDK 17+ installed and `java`/`javac` on PATH, run:

```powershell
.\venv\Scripts\python.exe tools/build_gephi.py
```

Native projects stay in `outputs/study/networks/`; validation results are in
`outputs/study/gephi_validation.csv`; unlabelled images are copied into the public
figures folder. Full-graph imported attributes remain the Python reference.
Gephi's computed PageRank uses its own column. ForceAtlas2 settings: 400 iterations,
seed 42, one thread, Barnes-Hut enabled, scaling 8, gravity 1, edge-weight influence
0.5, LinLog enabled, size adjustment disabled. Supplied spring positions initialize
the display; no graph measurements are computed from those positions.

Use current files in `outputs/study/networks/`, not the superseded pilot exports
in `outputs/networks/`. Names identify pair, period, subreddit and graph definition.
The `*_gephi.csv` aggregate tables document display filters.

## Import and verify

The native project's display workspace further restricts the focus graph to edges
with at least two replies and removes resulting isolates. It is a repeated-reply
backbone for readability, not an unbiased sample. Its counts and filter are in
`gephi_validation.csv`. The FULL workspace is unchanged. ForceAtlas2 coordinates
are uniformly rescaled after layout for export; topology is unaffected.

1. File → Open `*_all_replies_full.gexf` in Gephi. Import as **Directed**; preserve weight.
2. Compare node/edge counts with the matching `*_networks.csv` row.
3. In Data Laboratory inspect `observed_commenter`, `shared_in_pair`, `window`,
   `subreddit`, `comment_count` and `threads_participated`. Parent-only nodes may
   have no observed comments; they are not overlap participants.
4. Save the project under `outputs/study/networks/` as a `.gephi` file.

Alternative: import `*_nodes.csv` as Nodes (`Id` as string), then `*_edges.csv`
as Edges (`Source`, `Target`, `Type=Directed`, numeric `Weight`). Never parse IDs
as numbers. Direction is **replier → author of the parent comment/post**.

## Understand the attributes

| Attribute | Meaning | Limitation |
|---|---|---|
| `in_degree` / `out_degree` | Distinct incoming/outgoing reply partners | Not reply volume |
| `in_strength` / `out_strength` | Replies received/written | Thread starters can dominate |
| `pagerank` | Weighted directed structural attention | Not causal influence |
| `betweenness` | Unweighted directed shortest-path position | Approximated; see seed stability |
| `community` | Weighted Louvain on the reciprocal-sum undirected graph | Not fandom factions |
| `core_number` | Largest undirected k-core containing the user | Not sentiment |
| `participation_coefficient` | Dispersion of weighted ties across communities | Depends on fitted partition |
| `shared_in_pair` | Also commented in the paired subreddit that period | Not allegiance/hostility |

Gephi recalculation may differ through weighting, direction, approximation,
resolution or randomness. Record settings. Python tables are the reproducible
reference. Do not treat reply count as a shortest-path distance: a strong tie would
then become a longer path.

## Make two complementary views

**Internal structure:** color by `community`, size by PageRank or incoming strength
(e.g. 3–25). Keep bulk labels off. Use matching visual conventions across panels;
community 3 in one graph has no relation to community 3 in another.

**Cross-participants:** duplicate the workspace, color by `shared_in_pair` and size
by comment count or PageRank. This locates shared users inside one reply network;
it does not depict cross-subreddit replies.

Run **ForceAtlas2**, with Barnes-Hut optimization for large graphs, until the broad
arrangement stabilizes. Record scaling, gravity, edge-weight influence, LinLog,
overlap options and run time. Apply overlap prevention near the end if helpful.
Distances in the layout are illustrative, not a statistical measurement.

For a quick readable panel use `*_focus.gexf`: it has spring-layout positions,
colors and sizes. It selects the largest weak component's 2-core, capped at 1,200
PageRank-ranked nodes (largest-component fallback when no 2-core exists). Node
metrics still refer to the full graph. Eight display colors repeat if there are
more communities; use Gephi's partition palette for detail. **Do not report metrics
recomputed on the focus graph as full-network results.**

## Test thread-starter effects

Open the corresponding `*_comment_replies_full.gexf` in another workspace. It keeps
only replies to comments, retaining observed commenter isolates. Compare giant
component share, reciprocity, modularity and connector ranks. A disappearing hub
may reflect thread-starting mechanics. Local `*_connectors.csv` tables contain
pseudonymous rankings; inspect thread breadth and compare the two graph definitions.

`outputs/study/*_connector_roles.csv` summarizes cross-participation among the
top positive betweenness, PageRank and incoming-strength scores. All ties at the
20th-score cutoff are retained, so a selected set can exceed 20. Parent-only
accounts are counted separately; shared-user percentages compare observed
commenters with observed commenters. These are descriptive selections, not a
test that cross-participants cause information flow. The main runner generates
them after analysis; `python -m src.study_connectors` rebuilds them from local
centrality files without recomputing networks.

## Export and document

In Preview use thin translucent edges, small arrows and no bulk labels. Refresh,
then export SVG/PDF for the report and PNG for slides. Captions must state:

- Community and exact UTC period.
- Directed-edge and weight definitions.
- Full or filtered graph, with original/displayed node and edge counts.
- Color, size, layout and any changed parameters.
- Structural centrality does not establish influence.

Save the `.gephi` session with the exports. User-level graphs stay local. Publish
aggregate tables and figures without real usernames. See [Gephi documentation](https://docs.gephi.org/).
