# IMPLEMENTATION PLAN.md
## Fandom Fault Lines: Mapping Discourse, Sentiment, and Community Structure in Rival Fan Communities on Reddit

**Course:** CSE3729 — Computational Social Media Analysis
**Group 6:** Mayank Gupta (230553), Anurag Kumar (230616), Jhalak Kapila (230576)

---

## 0. How to Use This Document

This is the **single, self-contained source of truth** for this project. It assumes zero prior context — everything needed to build the entire project from an empty folder is in this file: the problem, the goal, the exact dataset and how to reach it, every module's exact responsibility and code, the folder structure, and every known edge case.

This document is written to be handed directly to an AI coding agent (e.g., Claude Code) working locally in VS Code, with the instruction: *"Build this entire project, stage by stage, exactly as specified below."* Each stage has a clear **Definition of Done** so progress can be checked objectively at any point. No Google Colab, no Jupyter notebooks required — this is a local Python project run from the terminal / VS Code.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Goal and Research Questions](#2-goal-and-research-questions)
3. [Data Source — Critical Background](#3-data-source--critical-background)
4. [Tech Stack](#4-tech-stack)
5. [Folder Structure](#5-folder-structure)
6. [Environment Setup](#6-environment-setup)
7. [Configuration](#7-configuration)
8. [Shared Utilities Module](#8-shared-utilities-module)
9. [Stage 1 — Post Collection](#9-stage-1--post-collection)
10. [Stage 2 — Comment Collection](#10-stage-2--comment-collection)
11. [Stage 3 — Preprocessing](#11-stage-3--preprocessing)
12. [Stage 4 — Exploratory Data Analysis](#12-stage-4--exploratory-data-analysis)
12A. [Stage 4b — Topic Modeling](#12a-stage-4b--topic-modeling)
13. [Stage 5 — Sentiment Analysis](#13-stage-5--sentiment-analysis)
13A. [Stage 5b — Statistical Significance Testing](#13a-stage-5b--statistical-significance-testing)
14. [Stage 6 — Network Construction](#14-stage-6--network-construction)
15. [Stage 7 — Network Analysis (Centrality + Community Detection + Content Profiling)](#15-stage-7--network-analysis-centrality--community-detection--content-profiling)
16. [Stage 8 — Gephi Visualization (Manual Step)](#16-stage-8--gephi-visualization-manual-step)
17. [Stage 9 — Cross-Community Overlap Analysis](#17-stage-9--cross-community-overlap-analysis)
17A. [Automated Testing (Synthetic Data)](#17a-automated-testing-synthetic-data)
18. [Stage 10 — Synthesis: Answering RQ1, RQ2, RQ3](#18-stage-10--synthesis-answering-rq1-rq2-rq3)
19. [Pipeline Orchestrator (run everything with one command)](#19-pipeline-orchestrator-run-everything-with-one-command)
20. [Master Edge Case Table](#20-master-edge-case-table)
21. [Validation Checklist](#21-validation-checklist)
22. [README.md Template](#22-readmemd-template)
23. [Build Order for Claude Code (Milestone Checklist)](#23-build-order-for-claude-code-milestone-checklist)
24. [Ethics and Data Handling Summary](#24-ethics-and-data-handling-summary)
25. [Revision Note](#25-revision-note)

---

## 1. Problem Statement

Fan communities built around rival franchises, artists, or creative universes generate large volumes of public discussion online, much of which is defined by opposition to a rival group. This rivalry is widely discussed anecdotally, but rarely studied with structured data: it's unclear whether these communities function as genuinely separate discourse networks (i.e., "echo chambers" with little cross-membership) or whether they substantially overlap in both content and audience. This project treats two rival subreddits as a case study to answer that question systematically, using real data instead of assumption.

**Working case study (change in one config value if needed):** `r/marvelstudios` vs `r/DC_Cinematic`.

## 2. Goal and Research Questions

**Overall goal:** Build an end-to-end pipeline that collects, cleans, analyzes, and visualizes discussion data from two rival Reddit communities, in order to answer:

> **Main RQ:** To what extent do rival fan communities on Reddit form separate, distinct groups versus overlapping ones, and how do their content (sentiment/topics), internal structure (key connector users), and cross-group boundaries differ?

Broken into three measurable sub-questions:

- **RQ1 (Content):** What topics and sentiment characterize how each community discusses itself vs. its rival?
- **RQ2 (Structure):** Which users act as key connectors within each community's discussion network?
- **RQ3 (Boundary):** What proportion of active users participate in both communities?

## 3. Data Source — Critical Background

**Read this section fully before writing any collection code — it explains why the approach here differs from a "standard" PRAW tutorial you might find online.**

### 3.1 Why not PRAW / the official Reddit API

Reddit closed **self-service API application creation** in **November 2025** under its "Responsible Builder Policy." Previously, anyone could register a free "script" app at `reddit.com/prefs/apps` and immediately get a `client_id`/`client_secret` for use with PRAW (Python Reddit API Wrapper). This is no longer possible for new developers — the form now fails silently (page reloads, CAPTCHA resets, no app is created). Reddit's current policy requires explicit approval before API access is granted.

Academic access is theoretically available through the **"Reddit for Researchers" (RFR)** program, but this requires an institutional email, a Principal Investigator affiliated with an accredited university, a detailed research proposal, and proof of ethical review (an IRB approval or exemption letter). This process takes weeks and is designed for funded academic research, not a coursework project on a weekly deadline — **do not attempt this path for this project.**

### 3.2 What we use instead: Arctic Shift

**Arctic Shift** (`https://arctic-shift.photon-reddit.com`) is a free, public, community-run archive that mirrors Reddit's historical public data (posts and comments from 2005 to the present) and serves it over plain HTTP with **no authentication, no API key, and no approval process required.**

**Confirmed working endpoints:**

| Endpoint | Purpose | Key query params |
|---|---|---|
| `GET /api/posts/search` | Search/list posts | `subreddit`, `author`, `after`, `before`, `sort`, `limit`, `title`, `selftext` |
| `GET /api/comments/search` | Search/list comments (flat list) | `subreddit`, `author`, `after`, `before`, `sort`, `limit`, `body`, `link_id`, `parent_id` |

**Important — do NOT use `/api/comments/tree`.** During initial testing, this endpoint returned a nested/hierarchical structure that a flat parser cannot read correctly (it produced rows of all-`None` values). Always use `/api/comments/search` instead — it returns a flat list of comment objects in the same shape as `/api/posts/search`, which is what every script in this plan is built around.

**Response shape (confirmed by live testing):** Both endpoints return JSON of the form:
```json
{ "data": [ { "...fields...": "..." }, { "...fields...": "..." } ] }
```
Post objects include (at least): `id`, `subreddit`, `title`, `author`, `score`, `num_comments`, `created_utc`, `selftext`, `url`, `permalink`.
Comment objects include (at least): `id`, `link_id`, `parent_id`, `author`, `body`, `score`, `created_utc`, `subreddit`.

`parent_id` on a comment is formatted like Reddit's native fullnames: `t3_xxxxx` (parent is a post) or `t1_xxxxx` (parent is another comment) — this is the exact field the network-construction stage depends on.

### 3.3 Known quirks of this data source (read before building)

- **Community-run, not official infrastructure.** Uptime and coverage are not contractually guaranteed. Requests can occasionally fail or time out — all collection code below must retry with backoff, not crash.
- **No live "top of all time" sorting like PRAW's `time_filter`.** `sort=desc` sorts by recency (`created_utc` descending), not by score. To get posts with real engagement, we collect a wide date window and then locally sort/filter by `score`/`num_comments` in pandas — never assume the API sorts by popularity.
- **Pagination is cursor-based via time, not page numbers.** To fetch more than one page (`limit` maxes out around 100 per request), use the `before` parameter set to the `created_utc` of the oldest item from the previous page (minus 1 second to avoid re-fetching the same boundary item), and keep paging backward in time until either the target row count is reached or the response comes back empty/short (meaning you've exhausted that date range).
- **`link_id` on the comments endpoint expects the fullname format** (e.g., `t3_1abcde`), not the bare ID — when filtering comments by a specific post, prefix the post ID with `t3_`. When fetching comments by `subreddit` directly (the primary method used in this plan), this doesn't matter since we're not filtering by `link_id` at collection time.
- **This is intentionally documented as a limitation in the final report** (see Section 24) — it is not a flaw in this project's implementation, it's an honest characteristic of the best available free data source after Reddit's policy change.

## 4. Tech Stack

| Purpose | Tool | Notes |
|---|---|---|
| Language | Python 3.10+ | |
| HTTP requests | `requests` | For Arctic Shift API calls |
| Data handling | `pandas` | |
| Plotting | `matplotlib`, `seaborn` | |
| Sentiment | `vaderSentiment` | Lexicon-based, suited to short informal text |
| Network analysis | `networkx` | Graph construction + centrality |
| Community detection | `python-louvain` (imported as `community`) | Louvain algorithm |
| Network visualization | **Gephi** (separate desktop app, not a Python package) | Manual step, Section 16 |
| Config | Plain Python module (`config.py`) | No secrets needed — see note below |
| No `.env` file needed | Arctic Shift requires no credentials at all | This is a genuine simplification vs. the original PRAW-based plan |

## 5. Folder Structure

Create exactly this structure. Every script below writes to a specific path in this tree — do not deviate from these paths, since later stages read from earlier stages' exact output locations.

```
fandom-fault-lines/
├── README.md
├── IMPLEMENTATION_PLAN.md          # this file
├── requirements.txt
├── .gitignore
├── config.py
├── src/
│   ├── __init__.py
│   ├── utils.py
│   ├── collect_posts.py
│   ├── collect_comments.py
│   ├── preprocess.py
│   ├── eda.py
│   ├── topic_modeling.py           # Stage 4b, Section 12A
│   ├── sentiment.py
│   ├── statistical_tests.py        # Stage 5b, Section 13A
│   ├── network_build.py
│   ├── network_analysis.py
│   └── overlap_analysis.py
├── run_pipeline.py                 # orchestrator, Section 19
├── data/
│   ├── raw/
│   │   ├── raw_posts.csv
│   │   └── raw_comments.csv
│   └── processed/
│       ├── clean_posts.csv
│       ├── clean_comments.csv
│       ├── topics_<subreddit>.csv            # one per subreddit
│       ├── comments_with_sentiment.csv
│       ├── sentiment_by_target.csv
│       ├── statistical_tests.csv
│       ├── centrality_<subreddit>.csv        # one per subreddit
│       ├── communities_<subreddit>.csv       # one per subreddit
│       ├── community_profile_<subreddit>.csv # one per subreddit
│       └── overlap_users.csv
├── outputs/
│   ├── charts/
│   │   ├── chart_activity_over_time.png
│   │   └── chart_score_distribution.png
│   └── networks/
│       ├── network_<subreddit>.gexf
│       └── network_<subreddit>_with_communities.gexf
├── logs/
│   └── pipeline.log
└── tests/
    └── test_sanity.py
```

## 6. Environment Setup

```bash
# 1. Create the project folder and move into it
mkdir fandom-fault-lines
cd fandom-fault-lines

# 2. Create and activate a virtual environment
python3 -m venv venv

# Mac/Linux:
source venv/bin/activate
# Windows (PowerShell):
venv\Scripts\Activate.ps1

# 3. Create requirements.txt (see exact content below), then:
pip install -r requirements.txt
```

**`requirements.txt`** (exact content):
```
requests==2.32.3
pandas==2.2.2
numpy==1.26.4
matplotlib==3.8.4
seaborn==0.13.2
vaderSentiment==3.3.2
networkx==3.3
python-louvain==0.16
scikit-learn==1.5.0
scipy==1.13.0
pytest==8.2.0
```

**`.gitignore`** (exact content):
```
venv/
data/raw/
__pycache__/
*.pyc
logs/
.vscode/
```

**Note on what's committed to Git:** `data/raw/` is excluded because it contains real (pre-anonymization) usernames from Stage 1/2, before Stage 3 anonymizes them. `data/processed/` (post-anonymization) IS safe to commit and should be, since it's your evidence trail. Do not remove `data/processed/` from version control.

## 7. Configuration

**`config.py`** (exact content — this is the only file you should need to edit to change subreddits, dates, or targets):

```python
import time

# ---- Subreddit pair (change these two values for a different case study) ----
SUBREDDIT_A = "marvelstudios"
SUBREDDIT_B = "DC_Cinematic"
SUBREDDITS = [SUBREDDIT_A, SUBREDDIT_B]

# ---- Collection window ----
# A bounded 3-4 week window is used deliberately (see Implementation Plan Section 3)
# rather than "all time", so the sample is defensible and analysis stays manageable.
# Format: Unix timestamps. Example below covers a ~4 week window ending today.
WINDOW_DAYS = 28
BEFORE_TS = int(time.time())                     # now
AFTER_TS = BEFORE_TS - (WINDOW_DAYS * 24 * 60 * 60)

# ---- Collection targets ----
# NOTE: TARGET_POSTS_PER_SUB is intentionally uncapped (float("inf")), not a fixed
# number like 800. A subreddit's post volume in a 28-day window is almost always far
# smaller than its comment volume, so collecting EVERY post in the window (bounded
# only by MAX_PAGES_SAFETY / window exhaustion, not an arbitrary count) maximizes the
# odds that any given comment's parent post was actually collected -- directly reducing
# the "dropped_missing_parent" count in Stage 6's network construction. Comments remain
# capped at TARGET_COMMENTS_PER_SUB since that volume is what the analysis actually runs on.
TARGET_POSTS_PER_SUB = float("inf")  # collect the full window's posts, not a fixed count
TARGET_COMMENTS_PER_SUB = 10000      # aim: 5,000-15,000
PAGE_LIMIT = 100                     # Arctic Shift's practical per-request cap
MAX_PAGES_SAFETY = 150               # hard stop to prevent infinite loops (150 * 100 = 15,000 rows max)

# ---- API ----
BASE_URL = "https://arctic-shift.photon-reddit.com/api"
HEADERS = {"User-Agent": "csma-fandom-project/0.1 (academic project, group 6)"}
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 4
RETRY_BACKOFF_SECONDS = 5           # doubles each retry: 5, 10, 20, 40

# ---- Bot/noise filtering (Stage 3) ----
BOT_ACCOUNTS = {"AutoModerator", "[deleted]", "RemindMeBot", "sneakpeekbot"}
MIN_COMMENT_LENGTH = 3              # characters, after cleaning

# ---- Franchise aliases for self/rival/both/general classification (Stage 5) ----
# EDIT these lists for your actual final subreddit pair -- include the subreddit
# name itself, common nicknames, and major recognizable franchise terms.
FRANCHISE_ALIASES = {
    "marvelstudios": ["marvel", "mcu", "avengers", "kevin feige"],
    "DC_Cinematic":  ["dc", "dceu", "batman", "superman", "james gunn"],
}

# ---- Paths ----
RAW_POSTS_PATH = "data/raw/raw_posts.csv"
RAW_COMMENTS_PATH = "data/raw/raw_comments.csv"
CLEAN_POSTS_PATH = "data/processed/clean_posts.csv"
CLEAN_COMMENTS_PATH = "data/processed/clean_comments.csv"
SENTIMENT_PATH = "data/processed/comments_with_sentiment.csv"
SENTIMENT_BY_TARGET_PATH = "data/processed/sentiment_by_target.csv"
STATISTICAL_TESTS_PATH = "data/processed/statistical_tests.csv"
OVERLAP_PATH = "data/processed/overlap_users.csv"
CHARTS_DIR = "outputs/charts"
NETWORKS_DIR = "outputs/networks"
LOG_PATH = "logs/pipeline.log"
```

## 8. Shared Utilities Module

**`src/utils.py`** (exact content — every other module imports from here; write this file first):

```python
import time
import logging
import hashlib
import requests
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


def setup_logger(name):
    os.makedirs("logs", exist_ok=True)
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        file_handler = logging.FileHandler(config.LOG_PATH)
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    return logger


def request_with_retry(url, params, logger):
    """
    GETs a URL with automatic retry + exponential backoff.
    Returns the parsed JSON dict, or None if all retries are exhausted.
    This is the ONLY place HTTP requests should be made in this project —
    every collection script must route through this function.
    """
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=config.HEADERS,
                                 timeout=config.REQUEST_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                wait = config.RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(f"Rate limited (429). Waiting {wait}s (attempt {attempt}/{config.MAX_RETRIES})")
                time.sleep(wait)
            else:
                logger.warning(f"Non-200 response ({resp.status_code}) for {url} with {params}. "
                                 f"Attempt {attempt}/{config.MAX_RETRIES}")
                time.sleep(config.RETRY_BACKOFF_SECONDS)
        except requests.exceptions.RequestException as e:
            wait = config.RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
            logger.warning(f"Request failed ({e}). Waiting {wait}s (attempt {attempt}/{config.MAX_RETRIES})")
            time.sleep(wait)

    logger.error(f"All {config.MAX_RETRIES} retries exhausted for {url} with params {params}. Giving up on this page.")
    return None


def anonymize(username):
    """
    Deterministic, one-way anonymization: the same real username always maps
    to the same fake ID across every run of this project, but the mapping
    cannot be reversed (SHA-256 is a one-way hash). No lookup table mapping
    back to real usernames is ever stored anywhere.
    """
    if username in (None, "[deleted]", ""):
        return "[deleted]"
    return "user_" + hashlib.sha256(str(username).encode()).hexdigest()[:10]


def safe_get(d, key, default=None):
    """Defensive dict access — Arctic Shift responses occasionally omit fields."""
    if d is None:
        return default
    value = d.get(key, default)
    return value if value is not None else default
```

## 9. Stage 1 — Post Collection

### 9.1 What this stage produces
`data/raw/raw_posts.csv` — target ~500-1000 rows per subreddit, real Reddit post data.

### 9.2 Full script: `src/collect_posts.py`

```python
import csv
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, request_with_retry, safe_get

logger = setup_logger("collect_posts")

POST_FIELDS = ["id", "subreddit", "title", "author", "score",
                "num_comments", "created_utc", "selftext_present", "url"]


def fetch_posts_page(subreddit, before_ts, after_ts, limit):
    url = f"{config.BASE_URL}/posts/search"
    params = {
        "subreddit": subreddit,
        "before": before_ts,
        "after": after_ts,
        "sort": "desc",
        "limit": limit,
    }
    data = request_with_retry(url, params, logger)
    if data is None:
        return []
    return data.get("data", [])


def collect_subreddit_posts(subreddit, writer):
    collected = 0
    current_before = config.BEFORE_TS
    page_count = 0

    while collected < config.TARGET_POSTS_PER_SUB and page_count < config.MAX_PAGES_SAFETY:
        page_count += 1
        posts = fetch_posts_page(subreddit, current_before, config.AFTER_TS, config.PAGE_LIMIT)

        if not posts:
            logger.info(f"r/{subreddit}: no more posts found before ts={current_before}. Stopping pagination.")
            break

        oldest_ts_this_page = None
        for p in posts:
            created_utc = safe_get(p, "created_utc")
            writer.writerow({
                "id": safe_get(p, "id", ""),
                "subreddit": subreddit,
                "title": safe_get(p, "title", ""),
                "author": safe_get(p, "author", "[deleted]"),
                "score": safe_get(p, "score", 0),
                "num_comments": safe_get(p, "num_comments", 0),
                "created_utc": created_utc if created_utc is not None else 0,
                "selftext_present": bool(safe_get(p, "selftext", "")),
                "url": safe_get(p, "url", ""),
            })
            collected += 1
            if created_utc is not None:
                if oldest_ts_this_page is None or created_utc < oldest_ts_this_page:
                    oldest_ts_this_page = created_utc

        logger.info(f"r/{subreddit}: page {page_count}, +{len(posts)} posts, total so far = {collected}")

        if oldest_ts_this_page is None:
            break
        # Page backward in time: next request asks for posts older than the
        # oldest one we just saw (minus 1 second to avoid re-fetching the boundary row).
        current_before = oldest_ts_this_page - 1

        if len(posts) < config.PAGE_LIMIT:
            # Fewer results than requested = we've reached the edge of available data
            # in this window. Stop rather than looping further for no new rows.
            logger.info(f"r/{subreddit}: reached end of available data in window (got {len(posts)} < limit).")
            break

    if collected < config.TARGET_POSTS_PER_SUB:
        logger.warning(f"r/{subreddit}: only collected {collected} posts (target was {config.TARGET_POSTS_PER_SUB}). "
                          f"This can happen if the subreddit has less activity than expected in this window, "
                          f"or if MAX_PAGES_SAFETY was hit. Consider widening WINDOW_DAYS in config.py.")

    logger.info(f"r/{subreddit}: FINISHED with {collected} posts collected.")


def main():
    os.makedirs("data/raw", exist_ok=True)
    with open(config.RAW_POSTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=POST_FIELDS)
        writer.writeheader()
        for sub in config.SUBREDDITS:
            logger.info(f"Starting collection for r/{sub}...")
            collect_subreddit_posts(sub, writer)


if __name__ == "__main__":
    main()
```

### 9.3 Definition of Done
- `data/raw/raw_posts.csv` exists with a header row and non-zero data rows for both subreddits.
- Log output (`logs/pipeline.log`) shows a "FINISHED" line for each subreddit with a row count.
- Manually opening the CSV shows real, readable post titles (not blank/garbled).

## 10. Stage 2 — Comment Collection

### 10.1 What this stage produces
`data/raw/raw_comments.csv` — target ~5,000-15,000 rows per subreddit.

### 10.2 Why this uses `/api/comments/search` filtered by subreddit (not per-post)

Fetching comments per-individual-post (looping over every collected post and querying its comments one at a time) is far slower and burns far more requests than necessary. `/api/comments/search` supports a direct `subreddit` filter, exactly like the posts endpoint, so we page through the *entire subreddit's* comment stream for the same date window in one consistent pass — this also means comments are not artificially limited to only the posts we happened to sample in Stage 1.

### 10.3 Full script: `src/collect_comments.py`

```python
import csv
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, request_with_retry, safe_get

logger = setup_logger("collect_comments")

COMMENT_FIELDS = ["id", "subreddit", "link_id", "parent_id", "author", "body", "score", "created_utc"]


def fetch_comments_page(subreddit, before_ts, after_ts, limit):
    url = f"{config.BASE_URL}/comments/search"
    params = {
        "subreddit": subreddit,
        "before": before_ts,
        "after": after_ts,
        "sort": "desc",
        "limit": limit,
    }
    data = request_with_retry(url, params, logger)
    if data is None:
        return []
    return data.get("data", [])


def collect_subreddit_comments(subreddit, writer):
    collected = 0
    current_before = config.BEFORE_TS
    page_count = 0

    while collected < config.TARGET_COMMENTS_PER_SUB and page_count < config.MAX_PAGES_SAFETY:
        page_count += 1
        comments = fetch_comments_page(subreddit, current_before, config.AFTER_TS, config.PAGE_LIMIT)

        if not comments:
            logger.info(f"r/{subreddit}: no more comments found before ts={current_before}. Stopping pagination.")
            break

        oldest_ts_this_page = None
        for c in comments:
            created_utc = safe_get(c, "created_utc")
            writer.writerow({
                "id": safe_get(c, "id", ""),
                "subreddit": subreddit,
                "link_id": safe_get(c, "link_id", ""),
                "parent_id": safe_get(c, "parent_id", ""),
                "author": safe_get(c, "author", "[deleted]"),
                "body": safe_get(c, "body", ""),
                "score": safe_get(c, "score", 0),
                "created_utc": created_utc if created_utc is not None else 0,
            })
            collected += 1
            if created_utc is not None:
                if oldest_ts_this_page is None or created_utc < oldest_ts_this_page:
                    oldest_ts_this_page = created_utc

        logger.info(f"r/{subreddit}: page {page_count}, +{len(comments)} comments, total so far = {collected}")

        if oldest_ts_this_page is None:
            break
        current_before = oldest_ts_this_page - 1

        if len(comments) < config.PAGE_LIMIT:
            logger.info(f"r/{subreddit}: reached end of available comment data in window.")
            break

    if collected < config.TARGET_COMMENTS_PER_SUB:
        logger.warning(f"r/{subreddit}: only collected {collected} comments (target was {config.TARGET_COMMENTS_PER_SUB}). "
                          f"Consider widening WINDOW_DAYS in config.py if this is far below target.")

    logger.info(f"r/{subreddit}: FINISHED with {collected} comments collected.")


def main():
    os.makedirs("data/raw", exist_ok=True)
    with open(config.RAW_COMMENTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COMMENT_FIELDS)
        writer.writeheader()
        for sub in config.SUBREDDITS:
            logger.info(f"Starting comment collection for r/{sub}...")
            collect_subreddit_comments(sub, writer)


if __name__ == "__main__":
    main()
```

### 10.4 Definition of Done
- `data/raw/raw_comments.csv` exists with real comment bodies and non-empty `parent_id` values in the format `t1_xxx` or `t3_xxx`.
- Row counts logged per subreddit are within a reasonable range of the target (if far short, this is flagged by a warning, not a silent failure).

## 11. Stage 3 — Preprocessing

### 11.1 What this stage produces
`data/processed/clean_posts.csv` and `data/processed/clean_comments.csv` — deduplicated, anonymized, noise-free.

### 11.2 Full script: `src/preprocess.py`

```python
import os
import re
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, anonymize

logger = setup_logger("preprocess")


def clean_text(text):
    text = str(text)
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"&amp;|&gt;|&lt;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def main():
    os.makedirs("data/processed", exist_ok=True)

    posts = pd.read_csv(config.RAW_POSTS_PATH)
    comments = pd.read_csv(config.RAW_COMMENTS_PATH)

    logger.info(f"Raw: {len(posts)} posts, {len(comments)} comments")

    # ---- 1. Drop bot/deleted authors ----
    posts = posts[~posts["author"].isin(config.BOT_ACCOUNTS)]
    comments = comments[~comments["author"].isin(config.BOT_ACCOUNTS)]

    # ---- 2. Drop empty/placeholder comment bodies ----
    comments = comments[comments["body"].notna()]
    comments = comments[~comments["body"].astype(str).isin(["[removed]", "[deleted]", ""])]

    # ---- 3. Drop exact duplicates (can happen at pagination page boundaries) ----
    posts = posts.drop_duplicates(subset="id")
    comments = comments.drop_duplicates(subset="id")

    # ---- 4. Clean comment text ----
    comments["body_clean"] = comments["body"].apply(clean_text)
    comments = comments[comments["body_clean"].str.len() >= config.MIN_COMMENT_LENGTH]

    # ---- 5. Anonymize usernames (deterministic, one-way) ----
    posts["author"] = posts["author"].apply(anonymize)
    comments["author"] = comments["author"].apply(anonymize)

    posts.to_csv(config.CLEAN_POSTS_PATH, index=False)
    comments.to_csv(config.CLEAN_COMMENTS_PATH, index=False)

    logger.info(f"Clean: {len(posts)} posts, {len(comments)} comments")
    logger.info(f"Unique anonymized comment authors: {comments['author'].nunique()}")
    for sub in config.SUBREDDITS:
        logger.info(f"  r/{sub}: {len(posts[posts['subreddit']==sub])} posts, "
                      f"{len(comments[comments['subreddit']==sub])} comments")


if __name__ == "__main__":
    main()
```

### 11.3 Definition of Done
- Row counts drop sensibly from raw → clean (not near-zero, not near-100% retention with zero filtering — spot-check that bot/empty rows were actually removed).
- Opening `clean_comments.csv` shows `author` values in the form `user_xxxxxxxxxx`, never a real Reddit username.

## 12. Stage 4 — Exploratory Data Analysis

### 12.1 What this stage produces
PNG charts in `outputs/charts/`, plus printed keyword/cross-mention summaries.

### 12.2 Full script: `src/eda.py`

```python
import os
import re
import sys
from collections import Counter

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("eda")
sns.set_theme(style="whitegrid")

STOPWORDS = set("the a an is are was were be been being and or but if then so to of in on for "
                 "with as it its this that these those i you he she they we my your his her their "
                 "have has had do does did not no just like about".split())


def top_words(text_series, n=20):
    all_words = []
    for text in text_series:
        words = re.findall(r"\b[a-z]{3,}\b", str(text).lower())
        words = [w for w in words if w not in STOPWORDS]
        all_words.extend(words)
    return Counter(all_words).most_common(n)


def main():
    os.makedirs(config.CHARTS_DIR, exist_ok=True)

    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    comments["created_dt"] = pd.to_datetime(comments["created_utc"], unit="s")
    comments["date"] = comments["created_dt"].dt.date

    # ---- Chart 1: activity over time ----
    daily_counts = comments.groupby(["date", "subreddit"]).size().reset_index(name="comment_count")
    plt.figure(figsize=(10, 5))
    sns.lineplot(data=daily_counts, x="date", y="comment_count", hue="subreddit")
    plt.title("Daily Comment Activity by Subreddit")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f"{config.CHARTS_DIR}/chart_activity_over_time.png")
    plt.close()

    # ---- Chart 2: score distribution ----
    plt.figure(figsize=(8, 5))
    sns.boxplot(data=comments, x="subreddit", y="score")
    plt.title("Comment Score Distribution by Subreddit")
    plt.ylim(comments["score"].quantile(0.01), comments["score"].quantile(0.99))
    plt.tight_layout()
    plt.savefig(f"{config.CHARTS_DIR}/chart_score_distribution.png")
    plt.close()

    logger.info("Charts saved to outputs/charts/")

    # ---- Top keywords per subreddit ----
    for sub in config.SUBREDDITS:
        subset = comments[comments["subreddit"] == sub]["body_clean"]
        logger.info(f"Top words in r/{sub}: {top_words(subset)}")

    # ---- Cross-mention rate ----
    subs = comments["subreddit"].unique()
    if len(subs) == 2:
        sub_a, sub_b = subs
        name_a = sub_a.lower().replace("_", " ")
        name_b = sub_b.lower().replace("_", " ")

        mentions_b_in_a = comments[comments["subreddit"] == sub_a]["body_clean"].str.lower().str.contains(name_b, na=False).sum()
        mentions_a_in_b = comments[comments["subreddit"] == sub_b]["body_clean"].str.lower().str.contains(name_a, na=False).sum()
        total_a = len(comments[comments["subreddit"] == sub_a])
        total_b = len(comments[comments["subreddit"] == sub_b])

        logger.info(f"r/{sub_a} mentions r/{sub_b} in {mentions_b_in_a}/{total_a} comments "
                      f"({100*mentions_b_in_a/max(total_a,1):.1f}%)")
        logger.info(f"r/{sub_b} mentions r/{sub_a} in {mentions_a_in_b}/{total_b} comments "
                      f"({100*mentions_a_in_b/max(total_b,1):.1f}%)")


if __name__ == "__main__":
    main()
```

### 12.3 Definition of Done
- Both PNG files render without errors and contain real data points from both subreddits (not empty axes). Similar-looking distributions between the two communities is a valid finding, not a failure — this checklist item validates that the code ran correctly, not that the result looks "interesting."
- Log shows a non-empty top-words list for each subreddit, with recognizable fandom-relevant words (not just stopwords that slipped through).

## 12A. Stage 4b — Topic Modeling

### 12A.1 Why this stage exists

RQ1 asks what *topics* characterize each community's discourse. Top-word frequency (Stage 4) only shows vocabulary, not underlying themes — "movie, character, actor, trailer" tells you what words appear often, not what the actual discussion *topics* are. This stage adds real topic modeling using TF-IDF + NMF (Non-negative Matrix Factorization) — chosen over LDA because it needs far less tuning, runs faster, and gives equally interpretable topics for a dataset this size.

### 12A.2 What this stage produces
`data/processed/topics_<subreddit>.csv` (dominant topic per comment) plus a printed topic-word summary per subreddit.

### 12A.3 Full script: `src/topic_modeling.py`

```python
import os
import sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("topic_modeling")

N_TOPICS = 5
N_TOP_WORDS = 8


def run_topic_model(comments_subset, subreddit_name):
    if len(comments_subset) < 20:
        logger.warning(f"r/{subreddit_name}: too few comments ({len(comments_subset)}) for topic modeling. Skipping.")
        return None, None

    vectorizer = TfidfVectorizer(max_df=0.9, min_df=5, stop_words="english", max_features=2000)
    tfidf = vectorizer.fit_transform(comments_subset["body_clean"].astype(str))

    nmf = NMF(n_components=N_TOPICS, random_state=42, init="nndsvda", max_iter=400)
    topic_matrix = nmf.fit_transform(tfidf)
    dominant_topic = topic_matrix.argmax(axis=1)

    feature_names = vectorizer.get_feature_names_out()
    topic_labels = {}
    for topic_idx, topic in enumerate(nmf.components_):
        top_words = [feature_names[i] for i in topic.argsort()[-N_TOP_WORDS:][::-1]]
        topic_labels[topic_idx] = ", ".join(top_words)
        logger.info(f"r/{subreddit_name} Topic {topic_idx}: {topic_labels[topic_idx]}")

    return dominant_topic, topic_labels


def main():
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)

    for sub in config.SUBREDDITS:
        subset = comments[comments["subreddit"] == sub].copy()
        dominant_topic, topic_labels = run_topic_model(subset, sub)
        if dominant_topic is None:
            continue

        subset["topic_id"] = dominant_topic
        subset["topic_words"] = subset["topic_id"].map(topic_labels)
        subset[["id", "topic_id", "topic_words"]].to_csv(f"data/processed/topics_{sub}.csv", index=False)

        logger.info(f"r/{sub} topic prevalence:\n{subset['topic_id'].value_counts(normalize=True).to_string()}")


if __name__ == "__main__":
    main()
```

### 12A.4 Definition of Done
- Each subreddit's log shows 5 distinct topics with recognizable, different word groupings. If all 5 topics look nearly identical, try lowering `N_TOPICS` to 3–4 or check that `clean_comments.csv` has enough volume (the function already guards against fewer than 20 comments, but topic quality also degrades well above that floor if the vocabulary is too narrow).
- `topics_<subreddit>.csv` exists for both subreddits with a `topic_id` for every row.

## 13. Stage 5 — Sentiment Analysis

### 13.1 What this stage produces
`data/processed/comments_with_sentiment.csv` and `data/processed/sentiment_by_target.csv`.

### 13.2 Full script: `src/sentiment.py`

**Note on the target classifier below:** this uses a 4-way classification (`self_talk` / `rival_talk` / `both` / `general`) driven by the `FRANCHISE_ALIASES` dictionary in `config.py`, rather than a single-substring match on just the subreddit's name. A single-substring check misclassifies cases like *"DC has nothing to do with this movie"* as rival-talk purely because the word "DC" appears, and forces every comment into a binary self/rival split even when it's about neither (or both) — the alias list and the `both`/`general` categories fix this.

```python
import os
import sys
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("sentiment")


def categorize(score):
    if score >= 0.05:
        return "positive"
    elif score <= -0.05:
        return "negative"
    return "neutral"


def tag_target(row, sub_a, sub_b):
    text = str(row["body_clean"]).lower()
    own_sub = row["subreddit"]
    other_sub = sub_b if own_sub == sub_a else sub_a

    own_aliases = config.FRANCHISE_ALIASES.get(own_sub, [own_sub.lower()])
    other_aliases = config.FRANCHISE_ALIASES.get(other_sub, [other_sub.lower()])

    mentions_own = any(alias in text for alias in own_aliases)
    mentions_other = any(alias in text for alias in other_aliases)

    if mentions_own and mentions_other:
        return "both"
    elif mentions_other:
        return "rival_talk"
    elif mentions_own:
        return "self_talk"
    else:
        return "general"


def main():
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    analyzer = SentimentIntensityAnalyzer()

    comments["sentiment_compound"] = comments["body_clean"].apply(
        lambda t: analyzer.polarity_scores(str(t))["compound"]
    )
    comments["sentiment_label"] = comments["sentiment_compound"].apply(categorize)
    comments.to_csv(config.SENTIMENT_PATH, index=False)

    logger.info("Sentiment distribution by subreddit:")
    logger.info(comments.groupby("subreddit")["sentiment_label"].value_counts(normalize=True).to_string())

    # ---- Pooled baseline: gives every per-community number a reference point ----
    baseline_mean = comments["sentiment_compound"].mean()
    logger.info(f"Pooled baseline sentiment (both communities combined): {baseline_mean:.3f}")
    for sub in config.SUBREDDITS:
        sub_mean = comments[comments["subreddit"] == sub]["sentiment_compound"].mean()
        logger.info(f"  r/{sub}: {sub_mean:.3f} (vs. baseline {baseline_mean:.3f}, "
                      f"delta {sub_mean - baseline_mean:+.3f})")

    # ---- Self/rival/both/general target classification (directly answers RQ1) ----
    subs = comments["subreddit"].unique()
    if len(subs) == 2:
        sub_a, sub_b = subs[0], subs[1]
        comments["talk_target"] = comments.apply(lambda row: tag_target(row, sub_a, sub_b), axis=1)
        summary = comments.groupby(["subreddit", "talk_target"])["sentiment_compound"].agg(["mean", "count"])
        summary.to_csv(config.SENTIMENT_BY_TARGET_PATH)
        logger.info(f"Sentiment by talk target (self/rival/both/general):\n{summary.to_string()}")
        comments.to_csv(config.SENTIMENT_PATH, index=False)  # re-save with talk_target column included
    else:
        logger.warning("Expected exactly 2 subreddits for self/rival sentiment split; found "
                          f"{len(subs)}. Skipping this comparison.")


if __name__ == "__main__":
    main()
```

### 13.3 Definition of Done
- `sentiment_compound` column exists and contains values spread across the -1 to +1 range (not all zeros — all-zero would indicate the sentiment library isn't running correctly).
- `sentiment_by_target.csv` has up to 8 rows (2 subreddits × up to 4 talk targets: self_talk, rival_talk, both, general) with sensible mean values.
- `comments_with_sentiment.csv` includes a `talk_target` column with all four category values represented (not just two) — if you only ever see `self_talk`/`rival_talk` and never `both`/`general`, double-check `FRANCHISE_ALIASES` in `config.py` is populated correctly for your real subreddit pair.

## 13A. Stage 5b — Statistical Significance Testing

### 13A.1 Why this stage exists

Descriptive statistics alone ("Community A's mean sentiment is 0.13, Community B's is 0.07") invite the question *"how do you know that difference isn't just random variation?"* This stage answers that directly with a non-parametric significance test, appropriate for sentiment scores which are not normally distributed.

### 13A.2 What this stage produces
`data/processed/statistical_tests.csv` — one row per comparison, with a test statistic, p-value, and a boolean significance flag.

### 13A.3 Full script: `src/statistical_tests.py`

```python
import os
import sys
import pandas as pd
from scipy.stats import mannwhitneyu

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("statistical_tests")


def run_mannwhitney(group_a, group_b, label):
    if len(group_a) < 5 or len(group_b) < 5:
        return {"comparison": label, "n_a": len(group_a), "n_b": len(group_b),
                "statistic": None, "p_value": None, "significant_at_0.05": None,
                "note": "sample too small"}
    stat, p = mannwhitneyu(group_a, group_b, alternative="two-sided")
    return {"comparison": label, "n_a": len(group_a), "n_b": len(group_b),
            "statistic": stat, "p_value": p, "significant_at_0.05": bool(p < 0.05), "note": ""}


def main():
    comments = pd.read_csv(config.SENTIMENT_PATH)
    subs = comments["subreddit"].unique()
    results = []

    if len(subs) == 2:
        sub_a, sub_b = subs[0], subs[1]

        # Test 1: overall sentiment, community A vs community B
        results.append(run_mannwhitney(
            comments[comments["subreddit"] == sub_a]["sentiment_compound"],
            comments[comments["subreddit"] == sub_b]["sentiment_compound"],
            f"sentiment: r/{sub_a} vs r/{sub_b} (overall)"
        ))

        # Test 2 & 3: within each subreddit, self-talk vs rival-talk sentiment
        for sub in [sub_a, sub_b]:
            sub_data = comments[comments["subreddit"] == sub]
            self_scores = sub_data[sub_data["talk_target"] == "self_talk"]["sentiment_compound"]
            rival_scores = sub_data[sub_data["talk_target"] == "rival_talk"]["sentiment_compound"]
            results.append(run_mannwhitney(self_scores, rival_scores,
                                             f"sentiment: self-talk vs rival-talk within r/{sub}"))

    results_df = pd.DataFrame(results)
    results_df.to_csv(config.STATISTICAL_TESTS_PATH, index=False)
    logger.info(f"\n{results_df.to_string(index=False)}")


if __name__ == "__main__":
    main()
```

### 13A.4 Definition of Done
- `statistical_tests.csv` has one row per comparison with a real (non-null) p-value for every row where both groups had ≥5 samples.
- **Every "Community A is more X than Community B" claim in your final report must cite the p-value from this file** — a comparative claim without this table backing it should not appear in the report.

## 14. Stage 6 — Network Construction

### 14.1 What this stage produces
`outputs/networks/network_<subreddit>.gexf` — one directed, weighted graph per subreddit.

### 14.2 Full script: `src/network_build.py`

```python
import os
import sys
import pandas as pd
import networkx as nx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("network_build")


def build_reply_graph(comments, posts, subreddit_name):
    sub_comments = comments[comments["subreddit"] == subreddit_name]
    sub_posts = posts[posts["subreddit"] == subreddit_name]

    comment_author_lookup = {("t1_" + str(row["id"])): row["author"] for _, row in sub_comments.iterrows()}
    post_author_lookup = {("t3_" + str(row["id"])): row["author"] for _, row in sub_posts.iterrows()}

    G = nx.DiGraph()
    dropped_self_loops = 0
    dropped_missing_parent = 0

    for _, row in sub_comments.iterrows():
        commenter = row["author"]
        parent_id = str(row["parent_id"])

        if parent_id.startswith("t1_"):
            parent_author = comment_author_lookup.get(parent_id)
        elif parent_id.startswith("t3_"):
            parent_author = post_author_lookup.get(parent_id)
        else:
            parent_author = None

        if parent_author is None:
            dropped_missing_parent += 1
            continue

        if parent_author == commenter:
            dropped_self_loops += 1
            continue

        if G.has_edge(commenter, parent_author):
            G[commenter][parent_author]["weight"] += 1
        else:
            G.add_edge(commenter, parent_author, weight=1)

    total_comments = len(sub_comments)
    resolvable = total_comments - dropped_missing_parent
    coverage_pct = 100 * resolvable / max(total_comments, 1)

    logger.info(f"r/{subreddit_name}: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    logger.info(f"  Total comments: {total_comments}")
    logger.info(f"  Comments with resolvable parent: {resolvable}")
    logger.info(f"  Comments with missing parent: {dropped_missing_parent}")
    logger.info(f"  Network coverage: {coverage_pct:.2f}%")
    logger.info(f"  Dropped (self-loops): {dropped_self_loops}")
    return G


def main():
    os.makedirs(config.NETWORKS_DIR, exist_ok=True)
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    posts = pd.read_csv(config.CLEAN_POSTS_PATH)

    for sub in config.SUBREDDITS:
        graph = build_reply_graph(comments, posts, sub)
        nx.write_gexf(graph, f"{config.NETWORKS_DIR}/network_{sub}.gexf")


if __name__ == "__main__":
    main()
```

### 14.3 Definition of Done
- Both `.gexf` files exist and are non-trivial in size (more than a handful of nodes — if near-empty, check that `data/processed/clean_comments.csv` actually has valid `parent_id` values).
- Logged `dropped_missing_parent` and `dropped_self_loops` counts are reasonable (not equal to the total comment count, which would mean something is broken).
- **Report the logged "Network coverage: X%" figure explicitly in your final report** (e.g., *"10,000 comments collected; 8,742 had a resolvable parent; network coverage = 87.42%"*) — this is far more scientifically transparent than simply saying "some edges were dropped," and directly explains any gap between total comments and total network edges. Since Section 7's uncapped `TARGET_POSTS_PER_SUB` is designed to maximize this number, a low coverage percentage (well under ~70%) is worth investigating — check that `WINDOW_DAYS` in `config.py` matches between your posts and comments collection runs.

## 15. Stage 7 — Network Analysis (Centrality + Community Detection + Content Profiling)

### 15.1 What this stage produces
`data/processed/centrality_<subreddit>.csv`, `data/processed/communities_<subreddit>.csv`, `data/processed/community_profile_<subreddit>.csv`, and updated `.gexf` files with a `community` node attribute for Gephi coloring.

**Note on terminology:** users at the top of `centrality_<subreddit>.csv` are described as **"structurally central users (high betweenness centrality in the observed reply network)"**, not as "the most influential users." High betweenness means many shortest paths in the reply graph pass through that node — it does not, on its own, establish social influence. A user could rank highly simply by being a very active commenter whose replies happen to bridge many threads. Keep this distinction in your report's wording.

**Why this stage also profiles communities, not just detects them:** reporting "Louvain detected 7 communities" on its own is not an interpretable finding — it's a number with no meaning attached. This stage joins each detected community's user list back onto the sentiment and topic data from Stages 5 and 4b, so the final output describes what each community actually discusses and how it feels about it (e.g., *"Community 2 (620 users) skews toward Topic 3 [rival criticism] with mean sentiment -0.31, while Community 0 (1,250 users) centers on Topic 1 [casting/actors] at +0.12"*) — turning the network analysis into part of the actual research argument rather than a disconnected diagram.

### 15.2 Full script: `src/network_analysis.py`

```python
import os
import sys
import networkx as nx
import community as community_louvain
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("network_analysis")


def profile_communities(subreddit_name, community_df):
    """Join community assignments back onto sentiment/topic data so detected
    communities become an interpretable finding, not just a bare count."""
    if not os.path.exists(config.SENTIMENT_PATH):
        logger.warning("comments_with_sentiment.csv not found — run Stage 5 before profiling communities.")
        return

    comments = pd.read_csv(config.SENTIMENT_PATH)
    sub_comments = comments[comments["subreddit"] == subreddit_name]

    merged = sub_comments.merge(
        community_df.rename(columns={"user": "author"}),
        on="author", how="inner"
    )

    agg_kwargs = dict(
        num_users=("author", "nunique"),
        num_comments=("id", "count"),
        mean_sentiment=("sentiment_compound", "mean"),
    )

    # If Stage 4b's topic data exists, merge it in to report each community's
    # modal (most common) topic alongside its sentiment — this is what makes
    # a community profile a real finding instead of just a headcount.
    topics_path = f"data/processed/topics_{subreddit_name}.csv"
    if os.path.exists(topics_path):
        topics = pd.read_csv(topics_path)
        merged = merged.merge(topics, on="id", how="left")

    profile = merged.groupby("community_id").agg(**agg_kwargs).reset_index()

    if "topic_words" in merged.columns:
        modal_topic = merged.groupby("community_id")["topic_words"].agg(
            lambda x: x.mode().iloc[0] if not x.mode().empty else "n/a"
        )
        profile = profile.merge(modal_topic.rename("modal_topic"), on="community_id", how="left")

    profile = profile.sort_values("num_users", ascending=False)
    profile.to_csv(f"data/processed/community_profile_{subreddit_name}.csv", index=False)
    logger.info(f"r/{subreddit_name} community profiles:\n{profile.to_string(index=False)}")


def analyze_network(subreddit_name):
    path = f"{config.NETWORKS_DIR}/network_{subreddit_name}.gexf"
    G = nx.read_gexf(path)

    if G.number_of_nodes() < 3:
        logger.warning(f"r/{subreddit_name}: network too small ({G.number_of_nodes()} nodes) for "
                          f"meaningful centrality analysis. Consider widening WINDOW_DAYS in config.py.")
        return

    degree_cent = nx.degree_centrality(G)

    if G.number_of_nodes() > 5000:
        betweenness_cent = nx.betweenness_centrality(G, k=500, seed=42)
        logger.info(f"r/{subreddit_name}: using approximated betweenness centrality (k=500 sample) "
                      f"due to graph size ({G.number_of_nodes()} nodes).")
    else:
        betweenness_cent = nx.betweenness_centrality(G)

    centrality_df = pd.DataFrame({
        "user": list(degree_cent.keys()),
        "degree_centrality": list(degree_cent.values()),
        "betweenness_centrality": [betweenness_cent[u] for u in degree_cent.keys()],
    }).sort_values("betweenness_centrality", ascending=False)

    centrality_df.to_csv(f"data/processed/centrality_{subreddit_name}.csv", index=False)
    logger.info(f"Top 10 structurally central users in r/{subreddit_name} "
                  f"(highest betweenness centrality in the observed reply network):\n"
                  f"{centrality_df.head(10).to_string(index=False)}")

    G_undirected = G.to_undirected()
    partition = community_louvain.best_partition(G_undirected, weight="weight", random_state=42)

    community_df = pd.DataFrame({
        "user": list(partition.keys()),
        "community_id": list(partition.values()),
    })
    community_df.to_csv(f"data/processed/communities_{subreddit_name}.csv", index=False)

    num_communities = len(set(partition.values()))
    logger.info(f"r/{subreddit_name}: {num_communities} communities detected")
    logger.info(community_df["community_id"].value_counts().to_string())

    nx.set_node_attributes(G, partition, "community")
    nx.write_gexf(G, f"{config.NETWORKS_DIR}/network_{subreddit_name}_with_communities.gexf")

    profile_communities(subreddit_name, community_df)


def main():
    for sub in config.SUBREDDITS:
        analyze_network(sub)


if __name__ == "__main__":
    main()
```

### 15.3 Definition of Done
- `centrality_<sub>.csv` and `communities_<sub>.csv` exist for both subreddits with non-empty rows.
- Community detection runs without error and assigns every network node to a community; the number of communities detected is **a finding to report, not a target to hit** — even a single detected community, or one community per node, is a valid (if perhaps unexciting) result as long as the computation itself ran correctly.
- `community_profile_<subreddit>.csv` exists and shows a distinct `mean_sentiment` (and `modal_topic`, if Stage 4b was run first) per community — this is the file you cite when your report says what a given community actually discusses, rather than just how many users it has.

## 16. Stage 8 — Gephi Visualization (Manual Step)

This stage is done in the **Gephi desktop application**, not code — install from [gephi.org](https://gephi.org/).

1. **File → Open** → select `outputs/networks/network_marvelstudios_with_communities.gexf`.
2. **Appearance panel** → node **Color** → **Partition** → select the `community` attribute.
3. **Appearance panel** → node **Size** → **Ranking** → select `betweenness_centrality` if present as an attribute, or compute it natively via **Statistics → Betweenness Centrality**.
4. **Layout panel** → choose **ForceAtlas2** → **Run** → let it settle 10–30 seconds → **Stop**.
5. **Preview tab** → adjust label visibility (turn off for dense graphs) → **Export → SVG/PNG**.
6. Repeat for the second subreddit's file.
7. **If the graph looks like an unreadable "hairball":** use **Filters → Degree Range** to temporarily hide low-degree peripheral nodes for a cleaner screenshot — this is a visual filter only, your computed metrics in the CSVs remain based on the full network.

## 17. Stage 9 — Cross-Community Overlap Analysis

### 17.1 What this stage produces
`data/processed/overlap_users.csv` and a printed overlap summary.

### 17.2 Full script: `src/overlap_analysis.py`

```python
import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("overlap_analysis")


def main():
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    subs = comments["subreddit"].unique()

    if len(subs) != 2:
        logger.error(f"Expected exactly 2 subreddits, found {len(subs)}. Aborting overlap analysis.")
        return

    sub_a, sub_b = subs[0], subs[1]
    users_a = set(comments[comments["subreddit"] == sub_a]["author"]) - {"[deleted]"}
    users_b = set(comments[comments["subreddit"] == sub_b]["author"]) - {"[deleted]"}

    overlap = users_a & users_b
    union = users_a | users_b

    logger.info(f"Unique commenters in r/{sub_a}: {len(users_a)}")
    logger.info(f"Unique commenters in r/{sub_b}: {len(users_b)}")
    logger.info(f"Users active in BOTH: {len(overlap)}")
    logger.info(f"Overlap as % of r/{sub_a}: {100*len(overlap)/max(len(users_a),1):.2f}%")
    logger.info(f"Overlap as % of r/{sub_b}: {100*len(overlap)/max(len(users_b),1):.2f}%")
    logger.info(f"Jaccard index (overlap / union): {100*len(overlap)/max(len(union),1):.2f}%")

    pd.DataFrame({"overlapping_user": list(overlap)}).to_csv(config.OVERLAP_PATH, index=False)


if __name__ == "__main__":
    main()
```

### 17.3 Definition of Done
- `overlap_users.csv` exists (even if it has zero rows — a genuine zero-overlap finding is a valid result, not a bug, as long as you've spot-checked it isn't caused by an anonymization mismatch).
- All three overlap percentages (A%, B%, Jaccard) are logged, not just one.

## 17A. Automated Testing (Synthetic Data)

### 17A.1 Why this matters

These tests check that the pipeline's *logic* is correct, using tiny hand-built inputs — they don't depend on live data collection having happened first, so they run instantly and can be run before, during, or after a real collection run. This is a meaningfully stronger testing approach than only checking that output files exist and are non-empty (file-existence checks catch "did the script crash," not "does the code actually do the right thing").

### 17A.2 Full file: `tests/test_sanity.py`

```python
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
```

Run with `pytest tests/ -v` from the project root.

### 17A.3 Definition of Done
- All tests pass with `pytest tests/ -v` before any stage is considered "complete" — this checks the logic is correct, not merely that files exist on disk.

## 18. Stage 10 — Synthesis: Answering RQ1, RQ2, RQ3

This is a writing stage, done by the team directly, not code. Pull together outputs from earlier stages:

| Research Question | Evidence to cite | Source file(s) |
|---|---|---|
| **RQ1** — content differences | Sentiment comparison, self-talk vs. rival-talk sentiment, top keywords | `sentiment_by_target.csv`, `chart_activity_over_time.png`, EDA log output |
| **RQ2** — internal structure | Top bridge users by betweenness centrality, number of detected communities | `centrality_<sub>.csv`, `communities_<sub>.csv`, Gephi exports |
| **RQ3** — cross-group boundary | Overlap percentage (all three denominators) | `overlap_users.csv`, `overlap_analysis` log output |

## 19. Pipeline Orchestrator (run everything with one command)

**`run_pipeline.py`** (exact content — lets you run the whole pipeline, or a single stage, from the terminal):

```python
import argparse
import sys

from src import (collect_posts, collect_comments, preprocess, eda, topic_modeling,
                  sentiment, statistical_tests, network_build, network_analysis, overlap_analysis)

STAGES = {
    "collect_posts": collect_posts.main,
    "collect_comments": collect_comments.main,
    "preprocess": preprocess.main,
    "eda": eda.main,
    "topic_modeling": topic_modeling.main,
    "sentiment": sentiment.main,
    "statistical_tests": statistical_tests.main,
    "network_build": network_build.main,
    "network_analysis": network_analysis.main,
    "overlap_analysis": overlap_analysis.main,
}

ORDER = ["collect_posts", "collect_comments", "preprocess", "eda", "topic_modeling",
          "sentiment", "statistical_tests", "network_build", "network_analysis", "overlap_analysis"]


def main():
    parser = argparse.ArgumentParser(description="Fandom Fault Lines pipeline runner")
    parser.add_argument("--stage", choices=list(STAGES.keys()) + ["all"], default="all",
                         help="Which stage to run. Default: all (runs every stage in order).")
    args = parser.parse_args()

    if args.stage == "all":
        for stage_name in ORDER:
            print(f"\n{'='*20} Running stage: {stage_name} {'='*20}")
            STAGES[stage_name]()
    else:
        STAGES[args.stage]()


if __name__ == "__main__":
    main()
```

Usage:
```bash
python run_pipeline.py                       # runs everything, in order
python run_pipeline.py --stage collect_posts  # runs just one stage
```

**Note:** `network_analysis` reads `.gexf` files written by `network_build`, so always run `network_build` before `network_analysis` — the `ORDER` list above already enforces this when running `--stage all`.

## 20. Master Edge Case Table

| # | Edge Case | Stage | Impact if Ignored | Mitigation |
|---|---|---|---|---|
| 1 | Reddit's official API requires approval (Nov 2025 policy change) | Data source | Cannot get `client_id`/`client_secret` at all | Use Arctic Shift instead — no auth required (Section 3) |
| 2 | `/api/comments/tree` returns nested, unparseable structure | Comment collection | All-`None` rows, silent data loss | Use `/api/comments/search` exclusively; never use `/tree` |
| 3 | Arctic Shift is community-run, not official infra | All API calls | Occasional timeouts/failures | `request_with_retry()` with exponential backoff in `utils.py` |
| 4 | `sort=desc` sorts by recency, not popularity | Post/comment collection | Freshly-posted content has near-zero score/comments, looks like "no engagement" | Collect a wide window, then sort/filter locally by `score`/`num_comments` in pandas — never assume API-side popularity sorting |
| 5 | Pagination boundary re-fetches the same row twice | Collection | Inflated/duplicate counts | `current_before = oldest_ts_this_page - 1` (subtract 1 second) |
| 6 | Infinite pagination loop if API always returns something | Collection | Script never terminates | `MAX_PAGES_SAFETY` hard cap in `config.py` |
| 7 | Deleted/removed post or comment author | Collection | Missing/`None` author breaks downstream joins | `safe_get()` with explicit `"[deleted]"` default |
| 8 | Bot accounts (AutoModerator etc.) | Preprocessing | Inflates activity/centrality metrics | Explicit blocklist in `config.BOT_ACCOUNTS` |
| 9 | `[removed]`/`[deleted]` comment bodies | Preprocessing | Meaningless sentiment scores | Explicit string filter |
| 10 | Near-empty comment text | Preprocessing | Noise in text/sentiment analysis | `MIN_COMMENT_LENGTH` threshold, applied post-cleaning too |
| 11 | Duplicate rows from re-running collection or pagination overlap | Preprocessing | Inflated counts, skewed network weights | `drop_duplicates` on the unique Reddit `id` |
| 12 | Anonymization must be reproducible across runs but irreversible | Preprocessing | Inconsistent IDs break network edges between runs | Deterministic SHA-256 hash, no lookup table stored |
| 13 | Non-English comments | Preprocessing/EDA | Unreliable sentiment scores | Documented as a limitation, not silently dropped — extend with `langdetect` only if you observe it's a real problem in your specific data |
| 14 | Extreme outlier engagement scores | EDA | Unreadable plots | Percentile-based axis clipping (raw data untouched) |
| 15 | Common stopwords dominating keyword lists | EDA | Uninformative "top words" | Explicit stopword filter in `eda.py` |
| 16 | Subreddit name variants in cross-mention detection | EDA | Undercounted mentions | Manually extend the name-matching logic with common nicknames for your real subreddit pair (e.g., "mcu", "dceu") |
| 17 | Sarcasm in sentiment scoring | Sentiment | VADER misclassifies sarcastic comments | Documented as a known limitation of lexicon-based tools (Section 24) — not something to "fix" in code |
| 18 | Sentiment near the neutral threshold | Sentiment | Naive 0-cutoff miscategorizes borderline comments | ±0.05 VADER-recommended band used in `categorize()` |
| 19 | Comment replying to a deleted/uncollected parent | Network construction | `KeyError` on lookup | `.get()` with `None` fallback; edge dropped and counted in logs |
| 20 | Self-loops (user replies to their own comment) | Network construction | Inflates own centrality artificially | Explicitly detected and excluded, with a count logged |
| 21 | Repeated interactions between the same pair of users | Network construction | Ambiguous — one edge or many? | Single weighted edge (`weight` = interaction count) |
| 22 | Top-level comments (reply to post, not another comment) | Network construction | Wrong lookup table used if not handled | `t1_`/`t3_` prefix branching in `build_reply_graph()` |
| 23 | Network too small for centrality (e.g., after heavy filtering) | Network analysis | Errors or meaningless output | Explicit size check with a warning |
| 24 | Betweenness centrality is slow on large graphs | Network analysis | Impractically long runtime | Sampling approximation (`k=500`) above 5,000 nodes |
| 25 | Louvain requires an undirected graph | Network analysis | Wrong/errored results on a `DiGraph` | Explicit `.to_undirected()` before running Louvain |
| 26 | Louvain is non-deterministic by default | Network analysis | Irreproducible community splits between runs | Fixed `random_state=42` |
| 27 | Disconnected graph components | Network analysis | Some naive implementations mishandle this | `networkx` handles disconnected graphs correctly by design — no special handling needed, but note fragmentation if severe |
| 28 | Dense/unreadable Gephi visualization | Visualization | Illegible figure for the report | Degree-range filtering for the *visual only*; metrics remain computed on the full network |
| 29 | `[deleted]` treated as a real overlapping "user" | Overlap analysis | Falsely inflates overlap % | Explicitly excluded before set intersection |
| 30 | Ambiguous denominator for "% overlap" | Overlap analysis | Cherry-picking the most dramatic number | Report all three (A%, B%, Jaccard) — never just one |
| 31 | Imbalanced dataset sizes between the two subreddits | All stages | Raw counts mislead comparison | Always compare rates/percentages, never raw counts, between the two communities |
| 32 | Committing raw (non-anonymized) data to Git | Repo/ethics | Real usernames exposed publicly | `.gitignore` excludes `data/raw/`; only `data/processed/` is committed |
| 33 | `link_id`/`parent_id` fullname prefix mismatch (`t1_`/`t3_`) | Network construction | Silent lookup failures if prefixes are stripped or mismatched | Prefixes are added explicitly and consistently when building lookup dictionaries |

## 21. Validation Checklist

**After Stages 1–2 (data collection):**
- [ ] `data/raw/raw_posts.csv` and `data/raw/raw_comments.csv` exist with row counts reasonably close to targets in `config.py`
- [ ] `logs/pipeline.log` shows "FINISHED" lines for both subreddits in both collection stages, with no unhandled tracebacks
- [ ] Manually spot-check 5 rows of each raw CSV — real, readable post titles and comment text

**After Stages 3–5b (preprocessing, EDA, topic modeling, sentiment, statistical testing):**
- [ ] `data/processed/clean_*.csv` show a sensible (not near-zero, not near-100%) row count drop from raw
- [ ] Spot-check `clean_comments.csv` — `author` values look like `user_xxxxxxxxxx`, never a real username
- [ ] Both EDA chart PNGs render without errors and contain real data points (not empty axes) — similar-looking distributions between the two communities is a valid finding, not a failure; this checks that the code ran correctly, not that the result looks "interesting"
- [ ] `topics_<subreddit>.csv` exists for both subreddits with 5 distinct, recognizable topic-word groupings logged
- [ ] `sentiment_compound` values are spread across a real range, not all zero or all identical
- [ ] `comments_with_sentiment.csv` includes all four `talk_target` values (self_talk, rival_talk, both, general), not just two
- [ ] `statistical_tests.csv` has a non-null p-value for every comparison with ≥5 samples per group

**After Stages 6–9 (network, overlap, testing):**
- [ ] Both `.gexf` files open correctly in Gephi and show more than a handful of nodes
- [ ] Logged "Network coverage: X%" figure is noted for your report — a low percentage (well under ~70%) is worth investigating before treating the network as representative
- [ ] `centrality_*.csv`, `communities_*.csv`, and `community_profile_*.csv` exist and are non-empty for both subreddits — community detection runs without error and produces at least 1 community per subreddit; the actual count is a finding to report, not a target to hit
- [ ] `overlap_users.csv` exists; if it's genuinely empty, this has been spot-checked as a real finding, not a bug
- [ ] `pytest tests/ -v` passes with all tests green
- [ ] Every number you plan to quote in your report (e.g., "12% overlap", "top structurally central users", "p = 0.03") is traceable to a specific file you can open live during viva

## 22. README.md Template

```markdown
# Fandom Fault Lines

Computational Social Media Analysis project (CSE3729) studying discourse, sentiment,
and community structure across two rival Reddit fan communities.

## Setup
1. `python3 -m venv venv && source venv/bin/activate` (or `venv\Scripts\Activate.ps1` on Windows)
2. `pip install -r requirements.txt`
3. Adjust subreddits/dates/targets in `config.py` if needed (defaults work out of the box, no API keys required)

## Run
`python run_pipeline.py` runs every stage in order. Use `--stage <name>` to run just one
(see `run_pipeline.py` for the full list of stage names).

## Data Source
Reddit's self-service API app creation was closed in November 2025. This project uses
[Arctic Shift](https://arctic-shift.photon-reddit.com), a free, public, no-auth archive
of Reddit data, instead of PRAW. See IMPLEMENTATION_PLAN.md Section 3 for full details.

## Outputs
- `data/processed/` — cleaned, anonymized CSVs (safe to commit)
- `outputs/charts/` — EDA visualizations
- `outputs/networks/` — Gephi-ready `.gexf` network files
- `logs/pipeline.log` — full run log
```

## 23. Build Order for Claude Code (Milestone Checklist)

Build in exactly this order — each milestone depends on the previous one's output files existing:

1. [ ] Create folder structure (Section 5) and `.gitignore`
2. [ ] Write `requirements.txt`, create venv, install
3. [ ] Write `config.py` (Section 7) exactly as specified
4. [ ] Write `src/utils.py` (Section 8) — everything else depends on this
5. [ ] Write and run `src/collect_posts.py` — verify `data/raw/raw_posts.csv` against Definition of Done (9.3)
6. [ ] Write and run `src/collect_comments.py` — verify against Definition of Done (10.4)
7. [ ] Write and run `src/preprocess.py` — verify against Definition of Done (11.3)
8. [ ] Write and run `src/eda.py` — verify against Definition of Done (12.3)
9. [ ] Write and run `src/topic_modeling.py` — verify against Definition of Done (12A.4)
10. [ ] Write and run `src/sentiment.py` (with the 4-way self/rival/both/general classifier) — verify against Definition of Done (13.3)
11. [ ] Write and run `src/statistical_tests.py` — verify against Definition of Done (13A.4)
12. [ ] Write and run `src/network_build.py` — verify against Definition of Done (14.3), including the logged network coverage %
13. [ ] Write and run `src/network_analysis.py` (including `profile_communities()`) — verify against Definition of Done (15.3)
14. [ ] Write and run `src/overlap_analysis.py` — verify against Definition of Done (17.3)
15. [ ] Write `run_pipeline.py` and confirm `python run_pipeline.py` runs all 10 stages end-to-end without manual intervention
16. [ ] Write `tests/test_sanity.py` (Section 17A.2) with the full synthetic-data unit test suite and confirm `pytest tests/ -v` passes
17. [ ] Write `README.md` from the template (Section 22)
18. [ ] Manual step: open both `.gexf` files in Gephi and export visualizations (Section 16) — this step is outside Claude Code's scope, flag it back to the user
19. [ ] Manual step: team writes the Synthesis section (Section 18) answering RQ1/RQ2/RQ3 using the generated files, citing p-values from `statistical_tests.csv` and community profiles from `community_profile_<subreddit>.csv` — also outside Claude Code's scope

## 24. Ethics and Data Handling Summary

- All data is collected from **public** subreddits only, via a free, public archive — no private, quarantined, or authentication-gated content is accessed.
- Usernames are anonymized via one-way SHA-256 hashing **before** any analysis, visualization, or committed storage — the mapping from anonymized ID back to real username is never stored anywhere, by design.
- No attempt is made to identify, contact, or de-anonymize any individual user.
- Known limitations to state plainly in the final report, not glossed over:
  - Reddit's user base skews younger, male, and English-speaking/US-centric — findings describe *Reddit fandom discourse specifically*, not fan behavior generally.
  - VADER sentiment scoring does not reliably detect sarcasm — a known, documented limitation of lexicon-based sentiment tools.
  - The reply network is necessarily incomplete wherever a parent comment fell outside the collected window or was deleted before collection — report the exact "network coverage %" figure logged in Stage 6 rather than only saying "some edges were dropped."
  - **Sampling rule, stated explicitly:** posts and comments were collected in reverse-chronological order within a fixed ~28-day window, until either the target volume was reached or the window was exhausted. This is a **time-bounded convenience sample**, not a random sample of all Reddit activity — it captures everything in the window up to the volume cap, not a statistically random subset of it. State this plainly if asked "why these 10,000 comments specifically?"
  - **Event-window confounding:** the ~28-day window may coincide with a specific triggering event (a trailer release, casting announcement, etc.) rather than capturing "typical" baseline community behavior. Check `chart_activity_over_time.png` for activity spikes, cross-reference the dates against any known franchise announcements, and name any such event explicitly in your report rather than treating the window as representative of year-round fandom behavior.
  - Findings describe a specific ~4-week window; fandom sentiment can shift significantly around different events, so results should not be read as a permanent characterization of either community.
  - The data source (Arctic Shift) is a free, community-run archive, not official Reddit infrastructure — coverage and uptime are not contractually guaranteed, which is why all collection code includes retry logic and explicit logging of any shortfall against collection targets.
  - Usernames are **pseudonymized** using deterministic SHA-256 hashing with no stored reverse mapping — not strictly "irreversible" in the absolute sense, since a specific known candidate username could technically be re-hashed and compared. This is standard, defensible pseudonymization for a project handling only public comment text, not a claim of cryptographic anonymity.
  - Users identified as "structurally central" via betweenness centrality are central **in the observed reply network only** — this reflects position in the graph of who-replied-to-whom, not verified social influence, expertise, or community standing. Avoid the word "influential" for these users in your report; use "structurally central" or "high-betweenness."

---

## 25. Revision Note

This plan went through two rounds of external methodological review. The first round identified six real gaps: no actual topic analysis (only word frequency), a too-simple self/rival substring classifier, no statistical significance testing, no link between network communities and content, incomplete network parent-coverage, and a weak test suite. Those fixes were initially added as a bolt-on "Section 25 addendum" layered on top of the original stages — which, on reflection, was a poor way to present the update: a second review of that version correctly pointed out that reading the base stages in isolation made it look like nothing had changed, since the addendum's overrides weren't visible from within the stages themselves.

**This version fixes that presentation problem, not just the methodology.** Every fix from the review is now merged directly into its relevant stage, in place, rather than living in a separate section that contradicts or silently overrides the main body:

- **Topic modeling** is now Stage 4b (Section 12A), sitting directly between EDA and Sentiment where it belongs in the pipeline.
- **Statistical testing** is now Stage 5b (Section 13A), directly after Sentiment.
- **The 4-way self/rival/both/general classifier with franchise aliases** is the actual `tag_target()` function shown in Stage 5 (Section 13.2) and in `config.py` (Section 7) — there is no separate, older version elsewhere in this document anymore.
- **Community content profiling** (`profile_communities()`) is written directly into Stage 7's `network_analysis.py` (Section 15.2), not described separately.
- **Network parent-coverage** is addressed two ways, both inline: `config.py` (Section 7) now collects the full post window rather than a fixed cap, and Stage 6 (Section 14.2/14.3) explicitly computes and logs a "network coverage %" figure.
- **The real synthetic-data test suite** is Section 17A, positioned right after Stage 9, with the folder structure (Section 5) and Build Order (Section 23) both referencing it directly — no separate "replaces the placeholder" note needed, because there is no placeholder version left in this document.
- **Terminology fixes** (structurally central vs. influential, pseudonymized vs. irreversible, observed active commenters vs. users belonging to communities) are folded into the wording of Sections 13–15 and 24 directly, not listed as a separate substitution table.

If you (or a reviewer) read this document top to bottom, every stage now reflects the final, current method on first read — there is nothing later in the document that quietly overrides something you already read earlier.
