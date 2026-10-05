# Fandom Fault Lines

Mapping discourse, sentiment, and community structure in rival fan communities on Reddit.

An end-to-end pipeline that collects, cleans, analyzes, and visualizes discussion
data from two rival subreddits to study whether these communities form separate,
distinct groups or overlapping ones — looking at content (topics/sentiment),
internal structure (key connector users), and cross-group boundaries.

**Case study:** r/marvelstudios vs r/DC_Cinematic (configurable).

## Setup

1. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate       # Mac/Linux
   venv\Scripts\Activate.ps1      # Windows PowerShell
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Adjust subreddits, franchise aliases, or the date window in `config.py` if needed
   (defaults work out of the box, no API keys or credentials required).

## Run

```bash
python run_pipeline.py                          # runs every stage in order (re-downloads data)
python run_pipeline.py --stage all --skip-collection   # re-run analysis on the existing raw CSVs
python run_pipeline.py --stage sentiment        # run a single stage
```

Stage names: `collect_posts`, `collect_comments`, `preprocess`, `eda`,
`topic_modeling`, `sentiment`, `statistical_tests`, `network_build`,
`network_analysis`, `overlap_analysis`, `connector_analysis`, `visualize`.

## Data Source and Sampling

Data comes from [Arctic Shift](https://arctic-shift.photon-reddit.com), a free, public,
no-authentication archive of Reddit's historical public data. No Reddit API credentials
are needed.

- **Frozen window.** The 28-day window is fixed in `config.py` (`WINDOW_END_DATE`), so
  re-running never silently changes the dataset. It ends a few days before collection so
  comment scores have had time to accumulate.
- **Posts:** every post in the window.
- **Comments:** stratified sample. The window is cut into 6-hour slots and up to 90 comments
  are taken from each slot, so the sample covers the whole window evenly (not just its most
  recent hours) and both subreddits span the same dates.

## Pipeline Stages

| Stage | Script | Output |
|---|---|---|
| 1. Post collection | `src/collect_posts.py` | `data/raw/raw_posts.csv` |
| 2. Comment collection | `src/collect_comments.py` | `data/raw/raw_comments.csv` |
| 3. Preprocessing | `src/preprocess.py` | `data/processed/clean_posts.csv`, `clean_comments.csv` |
| 4. Exploratory analysis | `src/eda.py` | `outputs/charts/chart_activity_over_time.png`, `chart_score_distribution.png`, `data/processed/peak_days.csv` |
| 4b. Topic modeling | `src/topic_modeling.py` | `data/processed/topics_<subreddit>.csv`, `topic_summary_<subreddit>.csv` |
| 5. Sentiment analysis | `src/sentiment.py` | `data/processed/comments_with_sentiment.csv`, `sentiment_by_target.csv` |
| 5b. Statistical testing | `src/statistical_tests.py` | `data/processed/statistical_tests.csv` (p-values, Holm-corrected p, effect sizes) |
| 6. Network construction | `src/network_build.py` | `outputs/networks/network_<subreddit>.gexf`, `data/processed/network_coverage.csv` |
| 7. Network analysis | `src/network_analysis.py` | `centrality_`, `communities_`, `community_profile_<subreddit>.csv`, `network_summary.csv` |
| 7b. Connector profiling | `src/connector_analysis.py` | `data/processed/connector_profile_<subreddit>.csv` |
| 8. Gephi visualization | manual, see below | exported network images |
| 9. Overlap analysis | `src/overlap_analysis.py` | `data/processed/overlap_users.csv`, `overlap_summary.csv` |
| 10. Figures | `src/visualize.py` | `outputs/charts/chart_sentiment_by_target.png`, `chart_topic_prevalence.png`, `chart_overlap.png`, `network_<subreddit>.png` |

## Gephi Visualization (Manual, optional)

`src/visualize.py` already renders static network pictures. For an interactive version:

1. Open `outputs/networks/network_<subreddit>_with_communities.gexf` in [Gephi](https://gephi.org/).
2. Appearance → node Color → Partition → `community` attribute.
3. Appearance → node Size → Ranking → `betweenness_centrality`.
4. Layout → ForceAtlas2 → Run for 10-30s → Stop.
5. Preview tab → Export → SVG/PNG.
6. Repeat for the second subreddit.

## Testing

```bash
pytest tests/ -v
```

## Outputs

- `data/processed/` — cleaned, anonymized CSVs (safe to commit; evidence trail for all reported numbers)
- `outputs/charts/` — EDA and result figures
- `outputs/networks/` — Gephi-ready `.gexf` network files
- `logs/pipeline.log` — full run log

## Method notes

- **Target tagging:** each comment is tagged `self_talk` / `rival_talk` / `both` / `general` by
  whole-word matching against `FRANCHISE_ALIASES` in `config.py` (so "dc" never matches inside
  another word).
- **Topics:** TF-IDF + NMF per subreddit. Comments with too few informative words get
  `topic_id = -1` instead of being forced into a topic.
- **Statistics:** Mann-Whitney U tests, reported with the rank-biserial effect size and
  Holm-corrected p-values, plus a robustness run that excludes comments with a VADER score of
  exactly 0 (no sentiment words found).
- **Networks:** nodes are users, edges are replies (weight = number of replies). Users at the
  top of the betweenness ranking are *structurally central in the observed reply network*;
  `connector_profile_*.csv` separates thread starters from pure reply bridges.

## Ethics and Data Handling

- Only public subreddit data is collected, via a free public archive — no private
  or authentication-gated content.
- Usernames are pseudonymized via one-way SHA-256 hashing before any analysis or
  committed storage; no reverse mapping is ever stored.
- `data/raw/` (pre-anonymization) is excluded from version control via
  `.gitignore`; only `data/processed/` (post-anonymization) is committed.
- Findings describe a specific 28-day collection window and Reddit's userbase
  specifically — not a permanent or general characterization of either fandom.
