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
3. Adjust subreddits, date window, or collection targets in `config.py` if needed
   (defaults work out of the box, no API keys or credentials required).

## Run

```bash
python run_pipeline.py                       # runs every stage in order
python run_pipeline.py --stage collect_posts # run a single stage
```

Available stage names: `collect_posts`, `collect_comments`, `preprocess`, `eda`,
`topic_modeling`, `sentiment`, `statistical_tests`, `network_build`,
`network_analysis`, `overlap_analysis`.

## Data Source

Data is collected from [Arctic Shift](https://arctic-shift.photon-reddit.com), a
free, public, no-authentication archive of Reddit's historical public data. No
Reddit API credentials are needed.

## Pipeline Stages

| Stage | Script | Output |
|---|---|---|
| 1. Post collection | `src/collect_posts.py` | `data/raw/raw_posts.csv` |
| 2. Comment collection | `src/collect_comments.py` | `data/raw/raw_comments.csv` |
| 3. Preprocessing | `src/preprocess.py` | `data/processed/clean_posts.csv`, `clean_comments.csv` |
| 4. Exploratory analysis | `src/eda.py` | `outputs/charts/*.png` |
| 4b. Topic modeling | `src/topic_modeling.py` | `data/processed/topics_<subreddit>.csv` |
| 5. Sentiment analysis | `src/sentiment.py` | `data/processed/comments_with_sentiment.csv`, `sentiment_by_target.csv` |
| 5b. Statistical testing | `src/statistical_tests.py` | `data/processed/statistical_tests.csv` |
| 6. Network construction | `src/network_build.py` | `outputs/networks/network_<subreddit>.gexf` |
| 7. Network analysis | `src/network_analysis.py` | `data/processed/centrality_<subreddit>.csv`, `communities_<subreddit>.csv`, `community_profile_<subreddit>.csv` |
| 8. Gephi visualization | manual, see below | exported network images |
| 9. Overlap analysis | `src/overlap_analysis.py` | `data/processed/overlap_users.csv` |

## Gephi Visualization (Manual)

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
- `outputs/charts/` — EDA visualizations
- `outputs/networks/` — Gephi-ready `.gexf` network files
- `logs/pipeline.log` — full run log

## Ethics and Data Handling

- Only public subreddit data is collected, via a free public archive — no private
  or authentication-gated content.
- Usernames are anonymized via one-way SHA-256 hashing before any analysis or
  committed storage; no reverse mapping is ever stored.
- `data/raw/` (pre-anonymization) is excluded from version control via
  `.gitignore`; only `data/processed/` (post-anonymization) is committed.
- Findings describe a specific ~4-week collection window and Reddit's userbase
  specifically — not a permanent or general characterization of either fandom.
