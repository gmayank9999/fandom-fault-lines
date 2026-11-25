# Fandom Fault Lines

A comparative, longitudinal Computational Social Media Analysis project studying
discussion, reply networks and audience overlap across rival entertainment brands.

**Design:** Marvel/DC (`marvelstudios`, `DC_Cinematic`) and PlayStation/Xbox (`PS5`,
`xbox`), with `StarWars` and `lotr` as comparison audiences. Two adjacent 28-day
periods span **3 September–29 October 2026** (UTC; end exclusive).
Dates, pairs, dictionaries and analysis settings live in [study.json](study.json).

The original ~19,000-comment pilot was sampling-sensitive. Its 5% overlap headline
is superseded. The expanded archive contains **1,168,638 comment records across
all 336 expected community-day files**. See the inventory for per-period coverage
and provenance; complete archive files do not guarantee complete Reddit coverage.

## Start here

- [Research report](REPORT.md), generated from aggregate results.
- [Audit and remaining work](PROJECT_STATUS.md).
- [Plain-language explanation](EXPLANATION.md).
- [Gephi workflow](GEPHI_GUIDE.md).
- [Independent annotation protocol](ANNOTATION_GUIDE.md).
- [Extended analysis methods](ADVANCED_METHODS.md): persistence, adjusted return rates, paired authors and matched connectors.
- [Collection inventory](outputs/study/collection_inventory.csv).

## Setup and run

Python 3.11 is the tested environment. The comparative pipeline needs core
dependencies only; the inherited transformer experiment is optional.

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-core.txt
.\venv\Scripts\python.exe run_study.py --stage inventory
.\venv\Scripts\python.exe run_study.py --stage all
```

Collection can take hours. Completed daily files are reused. Default concurrency
is two; `--workers 1` is available for a busy archive and four is the maximum.
Do not run multiple collectors against the same cache simultaneously.

```powershell
.\venv\Scripts\python.exe run_study.py --stage collect
.\venv\Scripts\python.exe run_study.py --stage analyze
.\venv\Scripts\python.exe run_study.py --stage advanced
.\venv\Scripts\python.exe run_study.py --stage report
.\venv\Scripts\python.exe -m pytest tests -q
```

`--subreddit PS5` limits collection to one community. Analysis processes complete
pairs while other communities are still collecting. The default tests are offline;
set `$env:FFL_MODEL_TEST = '1'` to enable the real-model integration test.

## Methods

- Exact expected day files, UTC bounds, duplicate IDs, schema checks and new-download
  checksums. Request failures, ambiguous pagination and safety caps fail explicitly.
- Participation includes identifiable non-bot commenters regardless of usable text;
  NLP uses cleaned content. Neither implies fandom membership.
- Pair-specific mention dictionaries, original/adapted VADER sensitivity, balanced
  pooled NMF topics across both periods, weekly trends. Sentiment is not stance.
- Effect sizes, user and thread cluster bootstraps, Holm correction across scorers
  and mention definitions. These are exploratory comparisons, not preregistered tests.
- Directed reply-count networks, preserved isolates, summed reciprocal weights,
  weighted Louvain/PageRank, unweighted directed betweenness, k-core, degree/strength
  and participation coefficients. Comment-only graphs test thread-starter effects.
- Equivalent unweighted observed/randomized network comparison. Small null ensembles
  are descriptive; no precise null-model p-values are claimed.
- Both directional overlap percentages and Jaccard; thresholds of 1/2/5 comments;
  all audience pairs; duration and random-subsampling sensitivity.
- Inherited sentiment annotations are AI-generated development labels. Independent
  human validation remains necessary; the pipeline never invents human annotations.

## Outputs and privacy

| Location | Contents | Git |
|---|---|---|
| `outputs/study/collection_inventory.csv` | Expected/valid days, counts, provenance | Published |
| `outputs/study/tables/` | Aggregate results and sensitivity analyses | Published |
| `outputs/study/figures/` | Report figures | Published |
| `outputs/study/aggregate_networks/` | Six-community audience-overlap GEXF graphs | Published |
| `outputs/study/gephi_validation.csv` | Native Gephi import and project-reopen checks | Published |
| `outputs/study/*_connector_roles.csv` | Aggregate connector roles and cross-participation | Published |
| `outputs/study/advanced/` | Longitudinal and adjusted comparisons, settings/input/output hashes | Published |
| `outputs/study/networks/` | Full/focus GEXF, node/edge CSVs, Gephi sessions | Local |
| `outputs/study/private/` | Text caches, pseudonymous connectors, run markers | Local |
| `data/raw/`, `data/gold/` | Original data, salt, annotation texts/labels | Local |

Pseudonymization is not anonymity. Searchable text and raw IDs are not published.
Old commits included searchable comment text: removing files in new commits does
**not** erase that history. No history rewrite or force push is performed.

## Original pipeline

`run_pipeline.py` remains available for the original single-window experiment,
including optional RoBERTa scoring. Install `requirements.txt` for that experiment
(CPU wheels: `https://download.pytorch.org/whl/cpu`). On PowerShell,
`$env:FFL_TRANSFORMER = '0'` skips inference. Its outputs under `data/processed/`,
`outputs/charts/` and `outputs/networks/` are local legacy artifacts, not current
study results. Historical reports in `docs/archive/` are superseded.

Public archive: [Arctic Shift](https://github.com/ArthurHeitmann/arctic_shift).
Archive completeness is not Reddit completeness. Low overlap, negative sentiment
and structural centrality cannot alone prove echo chambers, hostility or influence.
