> **SUPERSEDED PILOT — NOT CURRENT RESULTS.** Historical handoff text retained for audit only.
> Use the root EXPLANATION.md and REPORT.md for the corrected study.

# Fandom Fault Lines — The Complete Explanation

**Course:** CSE3729 — Computational Social Media Analysis
**Group 6:** Mayank Gupta (230553), Anurag Kumar (230616), Jhalak Kapila (230576)
**Repository:** https://github.com/gmayank9999/fandom-fault-lines

This document explains the whole project from zero. It assumes you know nothing about Reddit, data science, or network analysis. Every technical term is explained the first time it appears, and there is a glossary at the end. Read Part 1 and Part 2 first; the rest can be read in any order.

---

## Table of contents

1. [The project in one page](#part-1-the-project-in-one-page)
2. [Background you need (Reddit, subreddits, comments)](#part-2-background-you-need)
3. [The research questions](#part-3-the-research-questions)
4. [Where the data comes from](#part-4-where-the-data-comes-from)
5. [The pipeline: stage by stage](#part-5-the-pipeline-stage-by-stage)
6. [Every code file explained](#part-6-every-code-file-explained)
7. [Every data file explained](#part-7-every-data-file-explained)
8. [Every output file explained (charts, networks)](#part-8-every-output-file-explained)
9. [The results, with analysis](#part-9-the-results-with-analysis)
10. [The answer to the main research question](#part-10-the-answer-to-the-main-research-question)
11. [What went wrong first and how we fixed it](#part-11-what-went-wrong-first-and-how-we-fixed-it)
12. [Strengths and weaknesses (honest assessment)](#part-12-strengths-and-weaknesses)
13. [How to present this to your teacher](#part-13-how-to-present-this-to-your-teacher)
14. [Questions your teacher may ask, with answers](#part-14-questions-your-teacher-may-ask)
15. [How to run everything](#part-15-how-to-run-everything)
16. [Glossary](#part-16-glossary)

---

# Part 1: The project in one page

**Fandom Fault Lines** studies two rival fan communities on Reddit — **r/marvelstudios** (Marvel fans) and **r/DC_Cinematic** (DC fans) — and asks one question:

> Are these two rival fan communities really separate groups ("echo chambers") with little in common, or do they overlap — in what they talk about, how they feel, how they are organised inside, and in who participates?

To answer it we built a **pipeline**: a chain of Python programs where each one takes the previous one's output.

1. **Collect** 28 days of public posts and comments from both subreddits.
2. **Clean** the data (remove bots and junk, hide usernames).
3. **Explore** it (charts, common words, busiest days).
4. **Find topics** (what are people talking about?).
5. **Measure sentiment** (positive or negative?) and **who each comment is about** (own franchise, rival franchise, both, neither).
6. **Test statistically** whether differences are real or just chance.
7. **Build a reply network** (who replies to whom) for each community and find the key "connector" users and the sub-groups.
8. **Measure overlap** (how many people are active in both communities).
9. **Draw figures** for the report.

**What we found, in four sentences:**
- The two audiences are **mostly separate**: only about 5% of users appear in both.
- Each community mostly talks about **its own universe** (Marvel: Avengers, Doomsday; DC: Green Lantern, Superman, Gunn's DCU), and only about 1% of comments are about the rival.
- There is **no strong sign of hostility**: neither community is clearly more negative about its rival than about itself. The only result that survives every statistical check is that DC fans are slightly warmer about their own franchise than Marvel fans are.
- Inside each community the reply network is built around a few **thread-starting hubs**, not around separate "tribes".

---

# Part 2: Background you need

## 2.1 What is Reddit?
Reddit is a website made of thousands of topic forums called **subreddits**. Each subreddit has a name that starts with `r/`, for example `r/marvelstudios`. Anyone can read them; users with accounts can post and comment.

## 2.2 Posts, comments, replies
- A **post** (also called a "submission" or "thread") starts a discussion. It has a title, an author, a **score**, and a count of comments (`num_comments`).
- A **comment** is a reaction to a post. A comment can also be a **reply to another comment**, so discussions form a tree.
- **Score** is roughly "upvotes minus downvotes". Most comments score 1 (the default for your own comment) and a few go very high.
- Each item has an **ID** (e.g. `p7h3l9o`) and a **timestamp** `created_utc` (seconds since 1 Jan 1970, UTC, called a *Unix timestamp*).

## 2.3 The `parent_id` field (very important for this project)
Every comment stores what it replied to in `parent_id`:
- `t3_abc123` means "I replied directly to **post** abc123" (the `t3_` prefix means "this is a post").
- `t1_xyz789` means "I replied to **comment** xyz789" (`t1_` means "this is a comment").

This single field is what lets us build the "who replied to whom" network.

## 2.4 What is a "fandom" rivalry, and why study it?
People often say Marvel fans and DC fans dislike each other. That is an anecdote. This project checks it with data: do they actually mingle, share topics, and insult each other, or do they live in separate worlds?

## 2.5 What does "computational social media analysis" mean?
Using programs to study human behaviour from social media data: counting, measuring sentiment, finding topics, building networks, and testing hypotheses statistically — instead of reading thousands of comments by hand.

---

# Part 3: The research questions

The **main research question (Main RQ)**:

> To what extent do rival fan communities on Reddit form separate, distinct groups versus overlapping ones, and how do their content (sentiment/topics), internal structure (key connector users), and cross-group boundaries differ?

It is split into three measurable sub-questions:

| RQ | Plain-English question | What we measure | Where the evidence is |
|---|---|---|---|
| **RQ1 – Content** | What do they talk about, and how positive/negative are they about themselves vs their rival? | Topic modeling, VADER sentiment, "who is the comment about" tagging, significance tests | `topic_summary_*.csv`, `sentiment_by_target.csv`, `statistical_tests.csv`, EDA log |
| **RQ2 – Structure** | Who are the key connector users inside each community, and how is each community organised? | Reply network, centrality, community detection, connector profiles | `centrality_*.csv`, `communities_*.csv`, `community_profile_*.csv`, `connector_profile_*.csv`, `network_summary.csv` |
| **RQ3 – Boundary** | What proportion of users take part in both communities? | Set overlap of users | `overlap_summary.csv`, `overlap_users.csv` |

---

# Part 4: Where the data comes from

## 4.1 Why not Reddit's official API?
Normally researchers use Reddit's API through a library called PRAW. According to the project plan, Reddit closed self-service API application creation in **November 2025** and now requires approval (and the academic "Reddit for Researchers" route needs an institutional review and takes weeks). So that route was not practical for a coursework project.

## 4.2 What we use instead: Arctic Shift
**Arctic Shift** (`https://arctic-shift.photon-reddit.com`) is a free, public, community-run archive of Reddit posts and comments. It needs **no login and no API key**. We use these endpoints:

| Endpoint | What it returns |
|---|---|
| `/api/posts/search` | posts of a subreddit between two timestamps |
| `/api/comments/search` | comments of a subreddit between two timestamps |
| `/api/comments/ids` | specific comments by ID (used to fetch missing parent comments) |
| `/api/posts/ids` | specific posts by ID |

Limits we handle: it returns at most ~100 items per request, it sorts by time (not popularity), it is community-run so requests sometimes fail (we retry automatically), and we deliberately do **not** use `/api/comments/tree` because its nested format broke our parser.

## 4.3 The sampling design (very important to explain)
- **Window:** exactly **28 days, 3 Sep 2026 → 1 Oct 2026 (UTC)**. This is **frozen in `config.py`**, so re-running never changes the dataset. It ends a few days before collection so that comment scores have had time to accumulate (very fresh comments are archived with a score of about 1).
- **Posts:** **every** post in the window (about 4,050 for Marvel and 2,030 for DC before cleaning).
- **Comments: stratified sample.** The 28 days are cut into **112 time slots of 6 hours** (28 days × 4 slots per day). From each slot we take up to **90 comments** (newest first). That gives about **10,080 comments per subreddit**, spread evenly over the whole window.

**Why stratified?** Our first attempt just took the newest 10,000 comments. That only covered the last 35 hours for Marvel and 4 days for DC, so the two communities were measured over *different* time periods and Marvel's sample was dominated by one busy day. Stratified sampling fixes both problems. *Stratified sampling* means: divide the population into groups (here, time slots) and sample from each group, so every group is represented.

**Honest caveat:** this is a **sample**, not every comment. Some numbers (especially overlap) are therefore *lower bounds* on the true values.

## 4.4 Parent lookup (why we fetch extra comments)
Because we only sample about 90 comments per slot, a sampled comment often replies to a parent comment that is **not** in our sample. Without that parent we do not know who was replied to, so we could not draw the network edge. After sampling, only ~57–59% of replies could be linked. The `collect_parents` stage fetches just those **7,271 missing parent comments and 185 missing parent posts by ID** (only the author's name is kept, no text). Coverage rose to **99.9%**.

## 4.5 Ethics and privacy
- Only **public** subreddits are used.
- Usernames are replaced by one-way **SHA-256 hashes** (e.g. `user_bbc5241347`) before anything is analysed or committed. The same person always gets the same fake ID, so we can still count them and link their comments, but the real name is not stored.
- The **raw data with real usernames** (`data/raw/`) is excluded from git via `.gitignore`. A backup of the first run is kept in `data/raw/backup_run1/` (also ignored).
- This is *pseudonymization*, not perfect anonymity: someone who already guesses a username can hash it and check. That is stated honestly as a limitation.

---

# Part 5: The pipeline, stage by stage

```
 Arctic Shift API
       │
 [1]  collect_posts.py      → data/raw/raw_posts.csv
 [2]  collect_comments.py   → data/raw/raw_comments.csv      (stratified sample)
 [2b] collect_parents.py    → data/raw/raw_parents.csv       (authors of missing parents)
       │              (raw files contain real usernames: NOT in git)
 [3]  preprocess.py         → clean_posts.csv, clean_comments.csv, parent_authors.csv
       │
       ├─[4]  eda.py               → charts, peak_days.csv, top words, cross-mentions
       ├─[4b] topic_modeling.py    → topics_<sub>.csv, topic_summary_<sub>.csv
       ├─[5]  sentiment.py         → comments_with_sentiment.csv, sentiment_by_target.csv
       │        └─[5b] statistical_tests.py → statistical_tests.csv
       ├─[6]  network_build.py     → network_<sub>.gexf, network_coverage.csv
       │        ├─[7]  network_analysis.py   → centrality, communities, community_profile, network_summary
       │        │        └─[7b] connector_analysis.py → connector_profile_<sub>.csv
       │        └─[8]  Gephi (manual) / gephi_export.py → *_core_for_gephi.gexf
       ├─[9]  overlap_analysis.py  → overlap_summary.csv, overlap_users.csv
       └─[10] visualize.py         → charts + network pictures
```

`run_pipeline.py` runs all stages in order (or one stage at a time).

---

# Part 6: Every code file explained

All code is in Python. Libraries used: `requests` (web requests), `pandas` (tables), `numpy` (numbers), `matplotlib`/`seaborn` (charts), `vaderSentiment` (sentiment), `scikit-learn` (topic modeling), `scipy` (statistics), `networkx` (graphs), `python-louvain` (communities), `pytest` (tests).

## 6.1 `config.py` — the control panel
The one file you edit to change the project. Nothing else needs to change for a new case study.

- **Subreddits:** `SUBREDDIT_A = "marvelstudios"`, `SUBREDDIT_B = "DC_Cinematic"`.
- **Window:** `WINDOW_DAYS = 28`, `WINDOW_END_DATE = 2026-10-01`. `BEFORE_TS` and `AFTER_TS` are the window's end and start as Unix timestamps. Because the end date is fixed (not "now"), the dataset never silently changes.
- **Collection targets:** `TARGET_POSTS_PER_SUB = infinity` (take all posts), `SLOTS_PER_DAY = 4`, `COMMENTS_PER_SLOT = 90`, `TARGET_COMMENTS_PER_SUB = 10,080`. `PAGE_LIMIT = 100` is the API's per-request cap; `MAX_PAGES_SAFETY = 150` stops post pagination from looping forever.
- **API settings:** `BASE_URL`, a polite `User-Agent`, `REQUEST_TIMEOUT_SECONDS = 30`, `MAX_RETRIES = 4`, `RETRY_BACKOFF_SECONDS = 5` (waits 5, 10, 20, 40 s).
- **Cleaning:** `BOT_ACCOUNTS` = `AutoModerator`, `[deleted]`, `RemindMeBot`, `sneakpeekbot`; `MIN_COMMENT_LENGTH = 3`.
- **`FRANCHISE_ALIASES`:** the word lists that decide whether a comment is about Marvel or DC.
  - Marvel: marvel, mcu, avengers, kevin feige, feige, iron man, captain america, thor, hulk, loki, thanos, x-men, fantastic four, guardians of the galaxy, doctor strange, black panther, disney+.
  - DC: dc, dceu, dcu, batman, superman, supergirl, james gunn, gunn, wonder woman, green lantern, justice league, joker, aquaman, peacemaker, lex luthor, snyder, zack snyder.
  - Ambiguous words shared by both companies (spider-man, doom, flash) are left out on purpose.
- **Analysis settings:** `N_TOPICS = 8`, `TOPIC_MIN_TOKENS = 4`, `MIN_COMMUNITY_SIZE = 10`, `BETWEENNESS_SAMPLE_K = 2000`, `BETWEENNESS_EXACT_MAX_NODES = 2000`, `TOP_CONNECTORS = 20`.
- **File paths** for every input and output.

## 6.2 `src/utils.py` — shared helper functions
Every other module imports from here.
- `setup_logger(name)` — creates a logger that prints to the screen and also writes to `logs/pipeline.log`. A *logger* is a program's diary: it records what happened and when.
- `request_with_retry(url, params, logger)` — the **only** place that talks to the internet. It sends a GET request; if the server answers 200 it returns the JSON; if it says 429 ("too many requests") it waits and retries with *exponential backoff* (wait 5, then 10, 20, 40 seconds); other errors are retried too. After 4 failures it logs an error and returns `None` instead of crashing.
- `anonymize(username)` — returns `"user_" + first 10 characters of SHA-256(username)`. `[deleted]`, empty or `None` return `"[deleted]"`.
- `safe_get(d, key, default)` — reads a dictionary field without crashing when the field is missing.
- `compile_alias_regex(aliases)` — builds one regular expression that matches any alias **as a whole word or phrase** (so "dc" matches "DC movies" but not "adc" or "abcdc"). A *regular expression* is a pattern for searching text.
- `mentions_any(text, regex)` — True if the pattern matches.
- `get_stopwords()` — the shared list of words to ignore: the standard English list (the, is, and…) plus Reddit filler (lol, yeah, like, movie, giphy…).

## 6.3 `src/collect_posts.py` — Stage 1
Downloads all posts in the window for each subreddit.
1. Requests 100 posts at a time from `/posts/search`, newest first.
2. Writes each post's `id, subreddit, title, author, score, num_comments, created_utc, selftext_present, url` to the CSV.
3. **Pages backward in time**: the next request asks for posts older than the oldest one just seen (minus 1 second so the boundary post is not fetched twice).
4. Stops when a page is empty, shorter than 100, the window start is reached, or the safety cap is hit.
Result: 4,050 Marvel + 2,030 DC raw posts.

## 6.4 `src/collect_comments.py` — Stage 2
Implements the **stratified sample** (Section 4.3).
- `make_slots()` — cuts the window into 112 consecutive 6-hour `(after, before)` pairs with no gaps and no overlaps.
- `collect_slot(...)` — fetches up to 90 comments from one slot (newest first), paging if needed.
- `collect_subreddit_comments(...)` — loops through all slots, logs progress, counts empty slots, and warns if the total is well below the target.
Result: 10,080 comments per subreddit; all 112 slots returned data for both.

## 6.5 `src/collect_parents.py` — Stage 2b
- `missing_parent_ids(comments, posts)` — finds parent IDs referenced by `parent_id` that are not in the sample (`t1_` ones → comments, `t3_` ones → posts).
- `fetch_by_ids(kind, ids, writer)` — fetches them in batches of 100 from `/comments/ids` or `/posts/ids` and stores only `kind, id, subreddit, author`.
Result: found 7,271 / 7,271 parent comments and 185 / 185 parent posts.

## 6.6 `src/preprocess.py` — Stage 3 (cleaning and anonymising)
- `clean_text(text)` removes, in order: Reddit GIF/image embeds like `![gif](giphy|abc)`; markdown links `[text](url)` (keeping the text); web addresses; HTML leftovers (`&amp;`, `&gt;`, `&lt;`); and collapses repeated whitespace.
- `main()`:
  0. Builds the **author lookup** (`parent_authors.csv`): every `id → author` we know (sample + fetched parents), minus bots, with names anonymised. The network stage uses this.
  1. Drops posts/comments by bot accounts or `[deleted]`.
  2. Drops comments whose body is empty, `[removed]` or `[deleted]`.
  3. Drops duplicate IDs.
  4. Cleans text into a new column `body_clean`; drops comments shorter than 3 characters or containing no letters (emoji-only).
  5. Anonymises every author name.
Result: 6,080 → **5,914 posts** and 20,160 → **19,094 comments** (Marvel 9,552; DC 9,542; 10,910 unique commenters).

## 6.7 `src/eda.py` — Stage 4 (exploratory data analysis)
*EDA* means "get to know the data before testing anything".
- Chart 1, `chart_activity_over_time.png`: **posts per day** and **comments received by posts created that day**. (Daily counts of our *sampled* comments would be flat by design, so activity is measured from posts instead.)
- `peak_days.csv`: for each subreddit, the top 3 busiest days and the post with most comments that day. This lets us **name the real-world event** behind each spike.
- Chart 2, `chart_score_distribution.png`: box plots of comment and post scores on a log scale.
- Top 20 words per subreddit (after removing stopwords).
- **Cross-mention rate**: share of each community's comments that mention the *other* franchise's alias words.

## 6.8 `src/topic_modeling.py` — Stage 4b
Finds **what people talk about** using **TF-IDF + NMF** (explained in Part 16). For each subreddit separately:
1. `TfidfVectorizer` converts comments into number vectors, ignoring stopwords, words in over 50% of comments, words in fewer than 5 comments, allowing one- and two-word phrases ("green lantern"), max 3,000 features.
2. `NMF` with 8 components finds 8 topics.
3. `assign_topics(...)` gives each comment its strongest topic — **except** comments with fewer than 4 informative words, which get `topic_id = -1` ("too short / no topical words"). (Before this fix, such comments were silently dumped into topic 0.)
4. Writes `topics_<sub>.csv` (one row per comment) and `topic_summary_<sub>.csv` (one row per topic with its share).

## 6.9 `src/sentiment.py` — Stage 5
- `categorize(score)`: `≥ 0.05` → "positive", `≤ −0.05` → "negative", otherwise "neutral" (a ±0.05 neutral band recommended for VADER).
- `tag_target(row, sub_a, sub_b)`: decides **who a comment is about** using whole-word alias matching:
  - mentions own + rival franchise → `both`
  - only rival → `rival_talk`
  - only own → `self_talk`
  - neither → `general`
- `main()`: runs VADER on every `body_clean`, logs label shares, pooled baseline, share of exact-zero scores (23.8%), tags targets, and saves `comments_with_sentiment.csv` and `sentiment_by_target.csv` (mean, standard deviation, count, share for each subreddit × target).

## 6.10 `src/statistical_tests.py` — Stage 5b
- `run_mannwhitney(a, b, label)`: runs the **Mann-Whitney U test** and computes the **effect size** `r = 2U/(n_a·n_b) − 1` (rank-biserial correlation). Returns "sample too small" if either group has fewer than 5 values.
- `holm_correct(p_values)`: **Holm-Bonferroni correction** for running many tests at once.
- `run_family(comments, suffix)`: five comparisons (overall; self vs rival in Marvel; self vs rival in DC; rival-talk Marvel vs DC; self-talk Marvel vs DC).
- `main()`: runs the family on all comments, then again on the **robustness set** that excludes comments with VADER score exactly 0, and saves 10 rows.

## 6.11 `src/network_build.py` — Stage 6
`build_reply_graph(comments, posts, subreddit, extra_authors)` builds a **directed weighted graph** (explained in Part 16):
- For each comment, find the author of what it replied to: look the `parent_id` up in a dictionary (`t1_…` → comment authors; `t3_…` → post authors), using the sample plus the fetched parents.
- Add an edge **commenter → parent author**. If the edge already exists, add 1 to its **weight** (number of replies).
- Skip **self-replies** (someone replying to themself) and count them; count replies whose parent is unknown.
- Returns the graph and statistics (nodes, edges, coverage %, coverage split by replying-to-posts vs replying-to-comments).
`main()` saves `network_<sub>.gexf` and `network_coverage.csv`.

## 6.12 `src/network_analysis.py` — Stage 7
`analyze_network(subreddit)`:
1. Computes **degree centrality** and **betweenness centrality** (Part 16). With over 2,000 nodes betweenness is **approximated** by sampling 2,000 source nodes (`k=2000`, seed 42) because exact computation is very slow.
2. Finds **weakly connected components** and the **largest component**.
3. Runs **Louvain** community detection (on the undirected, weighted version; seed 42 so it is reproducible) and computes **modularity**.
4. Saves `centrality_<sub>.csv`, `communities_<sub>.csv`, and a `…_with_communities.gexf` graph in which each node carries `community` and `betweenness_centrality` attributes.
`profile_communities(...)` joins each community back to the comments: for communities with **at least 10 users** it reports users, comments, mean sentiment, share of negative comments, share of rival-talk, the most common topic and the **distinctive topic** (the topic most *over-represented* compared with the whole subreddit — "lift"; needs at least 5 comments).
`main()` also writes `network_summary.csv`.

## 6.13 `src/connector_analysis.py` — Stage 7b
For the top 20 users by betweenness (and separately the top 20 who never authored a post):
- replies received / written (weighted in- and out-degree), posts authored, comments authored, mean sentiment, main topic, community and its size, and whether the user is also active in the rival subreddit;
- `classify_role(posts_authored, in_weight, out_weight)`: **"thread starter"** if the user posted threads *and* receives more replies than they write; otherwise **"reply bridge"**.
Saves `connector_profile_<sub>.csv` (40 rows: 20 + 20).

## 6.14 `src/overlap_analysis.py` — Stage 9
- `overlap_row(...)`: for two sets of users computes users in both, % of A, % of B, and the **Jaccard index** (shared ÷ total distinct).
- `main()` reports three definitions — **commenters** (≥1 comment), **active users** (commented or posted), **repeat commenters** (≥2 comments in that subreddit) — writes `overlap_summary.csv`, and writes `overlap_users.csv` with each shared user's comment counts, mean sentiment and rival-talk counts in each community. It also logs how much of each community's comments the shared users write.

## 6.15 `src/visualize.py` — Stage 10
Draws `chart_sentiment_by_target.png`, `chart_topic_prevalence.png`, `chart_overlap.png` and `network_<sub>.png` (a picture of the dense core of each network). Colours: a colour-blind-checked palette; Marvel is always blue and DC always orange.

## 6.16 `src/gephi_export.py`
Writes `network_<sub>_core_for_gephi.gexf`: the dense core (2-core of the largest component), with layout positions, node size (betweenness) and node colour (community) already set, so it opens in Gephi as a readable picture with no manual filtering.

## 6.17 `run_pipeline.py`
Runs the stages in order. `python run_pipeline.py` = everything; `--stage <name>` = one stage; `--skip-collection` = skip the three download stages and reuse existing raw files.

## 6.18 `tests/test_sanity.py` — 26 automated tests
They run the real functions on tiny made-up data, so they check the **logic**, not just that files exist. They cover: anonymisation (deterministic, hides names, handles deleted); text cleaning (URLs, whitespace, GIF embeds, markdown links); stopwords; time slots (no gaps/overlaps; window is frozen); alias matching (whole words only); sentiment thresholds; four-way target tagging (including false-positive cases); network construction (edges, weights, self-loops, coverage numbers, parent lookup); topic assignment of uninformative comments; Mann-Whitney effect size sign and small samples; Holm correction; overlap maths; connector roles; missing-parent detection. Run with `pytest tests/ -v`.

## 6.19 Other files
- `requirements.txt` — pinned library versions so the project installs the same everywhere.
- `.gitignore` — keeps `venv/`, `data/raw/`, logs, `.claude/` and the local plan file out of git.
- `README.md` — short setup/run guide.
- `IMPLEMENTATION_PLAN.md` — the original blueprint. **It is local-only (not on GitHub) and now describes the *older* design** (10 stages, newest-first sampling). The code and README are the source of truth.
- `logs/pipeline.log` — diary of every run (not committed).

---

# Part 7: Every data file explained

*Row counts below are real rows. Note: opening a CSV in a text editor can show more lines than rows because comment text sometimes contains line breaks.*

## 7.1 Raw data (`data/raw/`, NOT on GitHub, real usernames)
| File | Rows | Columns | Meaning |
|---|---|---|---|
| `raw_posts.csv` | 6,080 | id, subreddit, title, author, score, num_comments, created_utc, selftext_present, url | All posts in the window |
| `raw_comments.csv` | 20,160 | id, subreddit, link_id, parent_id, author, body, score, created_utc | The stratified comment sample. `link_id` = the post the comment is under; `parent_id` = what it replied to |
| `raw_parents.csv` | 7,456 | kind, id, subreddit, author | Authors of the parents fetched by ID (7,271 comments + 185 posts) |
| `backup_run1/` | — | — | The first run's raw files, kept as a backup (ignored by git) |

## 7.2 Cleaned data (`data/processed/`, anonymised, on GitHub)
| File | Rows | Key columns | Meaning |
|---|---|---|---|
| `clean_posts.csv` | 5,914 | same as raw posts | Posts after removing bots/duplicates, with anonymous authors |
| `clean_comments.csv` | 19,094 | + `body_clean` | Cleaned comments; `body_clean` is the text used for all analysis |
| `parent_authors.csv` | 32,848 | kind, id, author | Lookup "this comment/post id was written by this anonymous user" — used to build edges |
| `comments_with_sentiment.csv` | 19,094 | + `sentiment_compound`, `sentiment_label`, `talk_target` | Each comment with its VADER score (−1…+1), label and who it is about |

## 7.3 Topic files
| File | Rows | Meaning |
|---|---|---|
| `topics_marvelstudios.csv`, `topics_DC_Cinematic.csv` | 9,552 / 9,542 | For each comment: `topic_id` (0–7, or −1 = too short) and the `topic_words` |
| `topic_summary_<sub>.csv` | 9 each | One row per topic: id, top words, number of comments, share |

## 7.4 Statistics and sentiment summaries
| File | Rows | Meaning |
|---|---|---|
| `sentiment_by_target.csv` | 8 | Mean, standard deviation, count and share for each subreddit × {self_talk, rival_talk, both, general} |
| `statistical_tests.csv` | 10 | One row per test: n of each group, medians, U statistic, `p_value`, `effect_size_r`, `p_holm`, and significance flags |
| `peak_days.csv` | 6 | The three busiest days per subreddit with the most-discussed post that day |

## 7.5 Network files
| File | Rows | Meaning |
|---|---|---|
| `network_coverage.csv` | 2 | Nodes, edges, comments, how many had a known parent, coverage %, split by reply type, self-loops dropped |
| `network_summary.csv` | 2 | Nodes, edges, density, number of components, largest component size/%, number of communities, modularity, betweenness method |
| `centrality_<sub>.csv` | 8,307 / 6,626 | Every user: `degree_centrality`, `betweenness_centrality` (sorted high → low) |
| `communities_<sub>.csv` | 8,307 / 6,626 | Every user's `community_id` and whether they are in the largest component |
| `community_profile_<sub>.csv` | 54 / 48 | One row per community of ≥ 10 users: users, comments, mean sentiment, share negative, share rival-talk, modal topic, distinctive topic and its lift |
| `connector_profile_<sub>.csv` | 40 each | Top-20 central users (scope "top overall") plus top-20 non-post-authors (scope "top excluding post authors") with role and statistics |

## 7.6 Overlap files
| File | Rows | Meaning |
|---|---|---|
| `overlap_summary.csv` | 3 | The three overlap definitions with counts, percentages and Jaccard |
| `overlap_users.csv` | 306 | Each user active in both subreddits: comments, mean sentiment and rival-talk count per subreddit |

---

# Part 8: Every output file explained

## 8.1 Charts (`outputs/charts/`)
| File | What it shows | How to read it |
|---|---|---|
| `chart_activity_over_time.png` | Top: posts per day. Bottom: comments received by posts created that day, for both subreddits over the 28 days | Marvel is busier overall. Peaks show event days (see peak_days.csv) |
| `chart_score_distribution.png` | Box plots of comment and post scores (log scale) | Most scores are tiny; a few are huge. This chart is generic and not central to the research questions |
| `chart_sentiment_by_target.png` | Mean sentiment for own-franchise, rival, both, neither talk, with 95% confidence bars and sample sizes | The most important result chart; wide bars on small groups show uncertainty |
| `chart_topic_prevalence.png` | Share of comments in each topic, per subreddit | Shows each community's content, and the 35% "too short" group |
| `chart_overlap.png` | % of each community's users also active in the other, under 3 definitions | Shows overlap is small (about 5%) however you define "user" |
| `network_marvelstudios.png`, `network_DC_Cinematic.png` | Picture of each reply network's dense core | Colour = community (8 largest; grey = others); size = betweenness |

## 8.2 Network files (`outputs/networks/`) — format **GEXF**
GEXF is the graph file format that Gephi opens.
| File | Meaning |
|---|---|
| `network_<sub>.gexf` | The reply network: nodes = anonymous users, directed edges with `weight` |
| `network_<sub>_with_communities.gexf` | The same, with `community` and `betweenness_centrality` stored on each node |
| `network_<sub>_core_for_gephi.gexf` | Dense core only (Marvel 1,657 users, 3,260 edges; DC 1,805 users, 4,261 edges), pre-laid-out, coloured and sized for Gephi |

## 8.3 Gephi pictures
You exported two Gephi pictures from the `core_for_gephi` files. Marvel shows one dominant big hub plus a few others; DC shows several hubs of comparable size. In both, communities form around hubs.

---

# Part 9: The results, with analysis

## 9.1 The dataset at a glance
| | r/marvelstudios | r/DC_Cinematic |
|---|---|---|
| Posts (clean) | 3,949 | 1,965 |
| Comments (clean) | 9,552 | 9,542 |
| Unique commenters (both subs combined) | 10,910 | |
| Period | 3 Sep – 1 Oct 2026 | same |

Marvel is the busier subreddit: about 100–200 posts per day vs 50–110 for DC.

## 9.2 Peak activity — which real-world events dominate?
| Subreddit | Date | Posts that day | Comments received | Most-discussed post |
|---|---|---|---|---|
| Marvel | Sep 5 | 138 | 8,194 | "How Would You Make This Movie Better?" (1,068 comments) |
| Marvel | Sep 9 | 170 | 8,038 | A thread asking someone to explain Doctor Doom's power level (1,187) |
| Marvel | Sep 23 | 159 | 7,767 | "What would ruin Avengers: Doomsday to you?" (1,650) |
| DC | Sep 3 | 73 | 5,351 | A thread about a *Lanterns* writer's interview (1,220) |
| DC | Sep 7 | 102 | 4,743 | "Is that new Lanterns show worth the watch?" (1,203) |
| DC | Sep 21 | 110 | 4,560 | *Lanterns* S01E06 episode discussion megathread (1,240) |

**Analysis:** DC's busiest days are all about HBO's *Lanterns* series, which is why Hal Jordan and Green Lantern dominate DC's vocabulary. Marvel's are about Doomsday/Doctor Doom hype. This is **event-window confounding**: these 28 days are not a "typical" month, so findings describe *this* month, not fandom behaviour in general. State this openly.

## 9.3 Most common words (after removing stopwords)
- **Marvel:** man (700), mcu (597), marvel (581), avengers (474), tony (447), character (424), thor (420), loki (403), doom (388), thanos (382), hulk (370), endgame (362), doomsday (304)…
- **DC:** hal (1,234), superman (871), john (806), batman (702), ring (544), lantern (464), green (458), lanterns (432), episode (371), gunn (351), snyder (322), dcu (311)…

**Analysis:** each community's vocabulary is dominated by its own universe, and the Lanterns show (hal, john, ring, lantern, episode) is visible in DC's words.

## 9.4 Cross-mentions
- Marvel comments mentioning DC alias words: **85 of 9,552 = 0.9%**.
- DC comments mentioning Marvel alias words: **269 of 9,542 = 2.8%**.

**Analysis:** direct references to the rival are rare in both. DC fans mention Marvel about three times as often as Marvel fans mention DC. (The alias lists are not identical in length and breadth, so treat the ratio as a rough indication.)

## 9.5 Topics (RQ1)
Share of each subreddit's comments (topic −1 = comment too short to assign a topic).

**r/marvelstudios**
| Topic | Top words | Share |
|---|---|---|
| 0 | avengers, endgame, thanos, hulk, new, right, war, infinity | 36.2% |
| −1 | (too short / no topical words) | 35.8% |
| 7 | mcu, comics, characters, character, best, love, definitely, favorite | 6.1% |
| 5 | marvel, captain, captain marvel, america, captain america, disney, best, watch | 4.8% |
| 3 | thor, loki, love, thunder, ragnarok, gorr, god | 4.7% |
| 1 | man, spider, spider man, iron, iron man, ant, ant man, peter | 4.4% |
| 2 | doom, tony, stark, variant, rdj, mask, tony stark | 2.9% |
| 4 | did, power, did watch, literally, watch, job, dad, knew | 2.6% |
| 6 | secret, wars, secret wars, doomsday, secret invasion, invasion | 2.4% |

**r/DC_Cinematic**
| Topic | Top words | Share |
|---|---|---|
| 5 | gunn, character, right, dcu, mean, point, snyder, sure | 38.2% |
| −1 | (too short / no topical words) | 34.8% |
| 0 | hal, john, ring, guy, sinestro, guardians, manhunter, jordan | 8.1% |
| 1 | superman, man, supergirl, steel, man steel, clark, zod, peacemaker | 4.4% |
| 3 | green, lantern, green lantern, lanterns, comics, power, guy | 4.1% |
| 2 | batman, dcu, suit, dark, best, dark knight, knight, bruce | 3.5% |
| 4 | did, watch, did watch, use, happen, marvel, job, lmao | 3.0% |
| 6 | better, dceu, agree, supergirl, probably, villain, suit | 2.0% |
| 7 | love, hate, agree, cool, real, man, design, series | 1.8% |

**Analysis:**
- Each community discusses its **own universe**: Marvel looks back at the Avengers era (Endgame/Thanos) and ahead to Doomsday/Secret Wars/Doctor Doom; DC is deep in the *Lanterns* show (topics 0 and 3 together ≈ 12%) plus Superman, Batman and Gunn's DCU.
- The two big topics (about 36–38%) are fairly **broad**, and about **35% of comments are too short** to assign a topic. So topics describe themes, not sharp categories. This is a limitation of topic models on very short text.

## 9.6 Sentiment (RQ1)
**VADER scores** are −1 (most negative) to +1 (most positive).
- Mean sentiment: **Marvel 0.066, DC 0.084** (pooled baseline 0.075).
- Share positive / neutral / negative: Marvel **42.7% / 26.9% / 30.5%**; DC **45.3% / 23.7% / 31.0%**.
- **23.8%** of comments score exactly 0 (VADER found no sentiment words).

**Sentiment by who the comment is about**
| Talk target | Marvel mean (n) | DC mean (n) |
|---|---|---|
| About own franchise (`self_talk`) | 0.090 (2,267) | 0.147 (2,115) |
| About rival franchise (`rival_talk`) | 0.095 (53) | 0.291 (118) |
| About both | 0.367 (32) | 0.413 (151) |
| About neither (`general`) | 0.057 (7,200) | 0.055 (7,158) |

**Share of each community's comments:** Marvel: self 23.7%, rival 0.55%, both 0.34%, neither 75.4%. DC: self 22.2%, rival 1.24%, both 1.58%, neither 75.0%.

**Analysis:**
- About **three quarters of comments are about neither franchise by name** (they discuss specific scenes, actors and episodes without using the alias words).
- **Rival talk is tiny** (0.6% and 1.2%), so any statement about how fans feel about the rival rests on very few comments (53 and 118).
- Comments mentioning *both* franchises are the most positive: people comparing the two often say nice things about both.

## 9.7 Statistical tests (RQ1)
Ten rows: five comparisons, each run on all comments and again excluding VADER-zero comments (the "robustness" check).

| Comparison | n | p-value | Effect size r | Holm p | Significant after Holm? |
|---|---|---|---|---|---|
| Overall sentiment, Marvel vs DC | 9,552 / 9,542 | 0.0074 | −0.022 | 0.052 | **No** |
| Marvel fans: own vs rival talk | 2,267 / 53 | 0.90 | +0.010 | 1.00 | **No** |
| DC fans: own vs rival talk | 2,115 / 118 | 0.0057 | −0.151 | 0.046 | Borderline (yes here; **no** in the robustness run, 0.058) |
| Rival talk: Marvel-about-DC vs DC-about-Marvel | 53 / 118 | 0.0096 | −0.248 | 0.058 | **No** |
| Own-franchise talk: Marvel vs DC | 2,267 / 2,115 | 0.0010 | −0.057 | 0.010 | **Yes** (also yes in robustness: 0.0129) |

Robustness run (excluding score = 0): p-values 0.0189, 0.853, 0.0101, 0.0659, 0.0014 with Holm 0.075, 1.0, 0.058, 0.198, 0.0129.

**How to read the effect size:** `r` close to 0 means no difference; the chance a random comment from group A is more positive than one from group B is about (1 + r) / 2.
- Own-franchise Marvel vs DC: r = −0.057 → a random DC comment is more positive about **52.9%** of the time (vs 47.1%). **A real but very small difference.**
- DC fans own vs rival: r = −0.151 → a rival-talk comment is more positive about 57.5% of the time.

**Analysis (the honest conclusion):**
1. **Only one result passes every check:** DC fans are slightly warmer when talking about their own franchise than Marvel fans are. The effect is small.
2. **Neither community is measurably *colder* toward its rival.** Marvel fans show no difference between self-talk and rival-talk (p = 0.90). DC fans' comments about Marvel are actually *more* positive than about DC — borderline and not robust.
3. The rival-talk groups are small, so their comparisons are uncertain.
4. We **do not** claim "Marvel fans are hostile to DC": the first run suggested that, but it disappeared once the data was fixed (see Part 11).

## 9.8 The reply networks (RQ2)
| | Marvel | DC |
|---|---|---|
| Users (nodes) | 8,307 | 6,626 |
| Reply links (edges) | 9,199 | 8,950 |
| Network coverage | 99.92% | 99.98% |
| Replies to posts / to comments | 4,274 / 5,278 | 3,847 / 5,695 |
| Self-replies dropped | 26 | 32 |
| Density | 0.000133 | 0.000204 |
| Weakly connected components | 997 | 481 |
| Largest component | 5,968 users (71.8%) | 5,505 users (83.1%) |
| Communities found (Louvain) | 1,050 | 528 |
| Communities with ≥ 10 users | 54 | 48 |
| Modularity | 0.85 | 0.77 |
| Dense core drawn in the pictures | 1,657 users, 3,260 edges | 1,805 users, 4,261 edges |

**Analysis:**
- **Coverage ~99.9%** means almost every comment could be placed in the network — the data is trustworthy for this analysis.
- **Very sparse** (density near 0.0001): of all possible pairs of users, almost none ever replied to each other. Normal for a huge discussion forum.
- **Hundreds of components:** most users are in the main conversation, but many only exchanged a reply or two on their own. DC is more tightly connected (83% vs 72%).
- **Modularity 0.85 / 0.77** is high (above ~0.3 is usually "clustered"), but replies naturally group by thread, so high modularity is expected in reply networks and does **not** mean strong rival tribes inside each subreddit.

## 9.9 The key connector users (RQ2)
*Betweenness* high = the user sits on many shortest paths between other users. We call them **"structurally central"**, **not** "influential" (we did not measure influence).

| Top 20 by betweenness | Marvel | DC |
|---|---|---|
| Highest betweenness value | 0.0152 | 0.0179 |
| Authored at least one post | 13 of 20 | 15 of 20 |
| Classified "thread starter" | 9 of 20 | 14 of 20 |
| Median replies received | 16.5 | 38.5 |
| Also active in the rival subreddit | 2 of 20 | 2 of 20 |

Top 20 **excluding post authors** ("pure reply bridges"): median 11 comments each (Marvel) and 14 (DC).

**Analysis:**
- **Most central users are thread starters:** they are central because many people reply to their posts, not because they link different groups. This is stronger in DC (14 of 20), where a few posters receive very many replies (e.g. the top DC user received 122 replies).
- Betweenness values are low for everyone (≤ 0.018): **no single user dominates** either network.
- Betweenness uses a 2,000-node sample, so rankings are approximate.

## 9.10 The communities inside each network
For communities with ≥ 10 users: Marvel 54 communities covering 4,751 users (mean sentiment from −0.07 to +0.23); DC 48 communities covering 4,528 users (−0.08 to +0.19). Each subreddit's communities have **8 different "distinctive topics"**.

**Examples:** a Marvel community of about 209 users is distinctively about Spider-Man / Iron Man / Ant-Man; another, about 154 users with a lift of 5.2, is about Doom / Tony Stark / RDJ (the "Tony Stark as Doom" casting talk). In DC, communities are distinctively about Superman/Supergirl, Hal Jordan/Sinestro, Batman/DCU, and Green Lantern.

**Analysis:** communities are **discussion circles around a subject or a hub**. They do not split a subreddit into rival factions. Their sentiments differ only modestly.
*Lift* = (share of this community's comments on a topic) ÷ (share of the whole subreddit's comments on that topic). Lift above 1 means over-represented.

## 9.11 What the network pictures show
- **Hub-and-spoke:** a few big nodes (high betweenness) with many small nodes around them.
- **Communities form around hubs:** same-coloured small nodes cluster near big hubs.
- **No separated blocs:** colours are intermixed across the core.
- **Marvel:** one dominant big hub plus a few; **DC:** several hubs of comparable size (consistent with 14/20 thread starters).
- **Caveats:** colours show only the 8 largest communities (the biggest white/grey hubs belong to other communities); distances in a force-directed layout are only roughly meaningful; sizes are relative to each graph's own maximum, so you cannot compare node sizes between the two pictures.

## 9.12 Overlap (RQ3)
| Definition | Marvel users | DC users | In both | % of Marvel | % of DC | Jaccard |
|---|---|---|---|---|---|---|
| Commenters (≥ 1 comment) | 6,040 | 5,176 | **306** | 5.07% | 5.91% | 2.80% |
| Active users (commented or posted) | 7,942 | 6,028 | 410 | 5.16% | 6.80% | 3.02% |
| Repeat commenters (≥ 2 comments) | 1,513 | 1,595 | 73 | 4.82% | 4.58% | 2.41% |

**The 306 shared users:**
- They write **6.6%** of Marvel's comments and **8.5%** of DC's.
- Mean sentiment of shared users vs others: 0.082 vs 0.065 (Marvel), 0.091 vs 0.083 (DC) — almost identical.
- Their share of rival-talk comments: 1.1% vs 0.5% (Marvel), 1.5% vs 1.2% (DC) — slightly higher, still tiny.
- Typical shared user: **1 comment in each subreddit** (median); about **143 of the 306** have 4 or more comments in total.

**Analysis:** about **5% of users cross over**, whichever definition you use. **Jaccard ≈ 2.8%** means that of all distinct users in either community only about 3 in 100 are in both. Most crossers are casual visitors, not people who live in both worlds. Because comments are a sample, true overlap is somewhat higher, so this is a **lower bound** — but not dramatically.

---

# Part 10: The answer to the main research question

> *To what extent do rival fan communities form separate groups versus overlapping ones?*

**The communities are separate in audience and in subject, but they are not hostile.**
- **Audience (RQ3):** only about 5% of users appear in both (Jaccard ≈ 3%) — largely separate.
- **Content (RQ1):** each talks about its own universe; only about 1% of comments are about the rival; 75% of comments name neither franchise. Neither community is measurably colder toward its rival. The only robust difference is that DC fans are slightly warmer about their own franchise.
- **Structure (RQ2):** inside each community, activity is organised around thread-starting hubs and many small discussion circles, not rival factions.

So the "echo chamber" description fits for **audience and topic**, but **not** for hostility: the rivalry looks more like parallel conversations than a fight.

---

# Part 11: What went wrong first and how we fixed it

This story is a **strength** — it shows scientific honesty. Tell it in your presentation.

| First version | Problem | Fix |
|---|---|---|
| Took the newest 10,000 comments | Covered only 35 hours (Marvel) and 4 days (DC): different periods, one busy day dominated Marvel | Frozen 28-day window + stratified sampling over 112 time slots |
| Fresh data | Comment scores were all ~1 (no votes yet) | Window ends days before collection |
| Stratified sampling alone | Network coverage fell to 57–59% (missing parents) | `collect_parents` stage → 99.9% coverage |
| Cross-mention rate | Searched for the literal text "dc cinematic": gave 0% | Uses the franchise alias lists → 0.9% / 2.8% |
| Alias matching | "dc" matched inside other words | Whole-word regular expression matching |
| Keyword lists | Full of "all, would, what…" | Shared stopword list |
| Topics | Catch-all topic; GIF markup became its own topic; empty comments forced into topic 0 | GIF stripping; topic −1 for uninformative comments; 8 topics |
| Statistics | p-values only | Effect sizes, Holm correction, robustness rerun |
| Communities | All shared the same "modal topic" | Added "distinctive topic" via lift; small fragments excluded |
| Weak tests | 9 tests, some only rebuilt the logic | 26 tests on the real functions |

**Biggest lesson:** the first run's headline — "Marvel fans are much colder about DC (p = 0.0000045)" — **did not survive the fixes** (it became p = 0.90). It was caused by a biased 35-hour sample, a crude tagger and a small sample. We reported the corrected result. Never quote the old claim.

---

# Part 12: Strengths and weaknesses

## Strengths
- A complete, reproducible, modular pipeline (13 stages, one config file, one-command runner).
- Careful sampling and a **frozen** window; 99.9% network coverage.
- Real statistics: non-parametric test, effect sizes, multiple-comparison correction, robustness check.
- Content *and* structure *and* overlap studied together, with communities linked back to content.
- Careful wording ("structurally central", "pseudonymized"), limitations stated, privacy handled.
- 26 passing tests; clean git history; every number traceable to a file.

## Weaknesses (be ready to say these yourselves)
1. **One 28-day window**, dominated by single events (*Lanterns* for DC, *Doomsday* talk for Marvel).
2. **VADER** cannot detect sarcasm, and 23.8% of comments score exactly 0.
3. **Rival-talk samples are small** (53 and 118 comments).
4. **~35% of comments are too short** for a topic, and two topics (36–38%) are broad.
5. Louvain finds **hundreds of tiny fragment communities**; high modularity is partly an artefact of thread structure.
6. Overlap is a **lower bound** (sampled comments).
7. Alias-based tagging is crude: it misses comments that discuss the franchise without naming it, and the two alias lists differ in length.
8. Only **two communities**: a case study, not a general law.
9. Reddit's users skew young, male, English-speaking — findings describe Reddit fandom only.
10. Betweenness is **approximate** (2,000-node sample).

---

# Part 13: How to present this to your teacher

## 13.1 Suggested 10-slide structure
1. **Title + problem:** "Are rival fandoms echo chambers?"
2. **Research questions:** main RQ + RQ1/2/3.
3. **Data and ethics:** Arctic Shift, 28-day frozen window, stratified sampling, anonymisation.
4. **Pipeline diagram** (the figure in Part 5).
5. **RQ1 – content:** topic chart + sentiment-by-target chart.
6. **RQ1 – statistics:** the table in 9.7 and the message "only one robust effect, and it is small".
7. **RQ2 – structure:** the two Gephi network pictures + connector facts (hubs are thread starters).
8. **RQ3 – overlap:** overlap chart (≈ 5%).
9. **Conclusion:** separate audiences, own-universe talk, no hostility.
10. **Limitations and what we corrected** (the Part 11 story) + future work.

## 13.2 A 5-minute demo you can run live
```bash
venv\Scripts\Activate.ps1
python -m pytest tests/ -v                      # 26 green tests in ~2 seconds
python run_pipeline.py --stage sentiment        # prints the sentiment tables
python run_pipeline.py --stage statistical_tests
python run_pipeline.py --stage overlap_analysis # prints the three overlap percentages
```
Then open `outputs/charts/` and `data/processed/statistical_tests.csv`.
> ⚠️ **Do not run `python run_pipeline.py` without `--skip-collection`, and do not run `collect_*` stages before the demo.** They re-download data (about 15 minutes) and overwrite the raw files. (The window is frozen, so the results would be nearly identical, but the API could return slightly different data.)

## 13.3 Tips
- **Lead with the story**: "We expected hostile echo chambers; we found separate but not hostile communities."
- **Say the correction story** — it shows rigour.
- **Be precise with wording:** "structurally central" not "influential"; "borderline" not "significant" when Holm says so.
- **Trace every number** to a file: open the CSV live when asked.

---

# Part 14: Questions your teacher may ask

**Q1. Why Reddit and why these two subreddits?**
Reddit discussion is public and organised by community, which makes group comparison possible. Marvel vs DC is a famous rivalry, and both communities are large and active, giving enough data.

**Q2. Why not use the Reddit API?**
Self-service API app creation was closed in Nov 2025 and academic access needs weeks of approval. We used Arctic Shift, a free public archive, with retry logic because it is community-run.

**Q3. Is the data a random sample? Is it representative?**
Posts: all of them in the window. Comments: a **time-stratified sample** (90 per six-hour slot), so every period is represented, but it is not a random sample of all comments. It describes one 28-day window only.

**Q4. Why a 28-day window and why those dates?**
Long enough for patterns, short enough to manage. It is frozen so results are reproducible, and ends days before collection so scores had time to build up.

**Q5. How did you handle privacy?**
Public data only, usernames hashed with SHA-256 before analysis, raw data kept out of git, no attempt to identify anyone.

**Q6. What is VADER and why use it?**
A rule-based sentiment tool built for short, informal social-media text (see glossary). It is fast, needs no training, and is a standard baseline. It cannot detect sarcasm.

**Q7. How do you know a sentiment difference is real?**
We use the Mann-Whitney U test (suited to non-normal scores), report effect sizes, correct for multiple tests with Holm, and rerun without comments VADER scored exactly 0.

**Q8. Your p-value is small but you say it is not important. Why?**
With thousands of comments even tiny differences become "significant". The effect size (r = −0.057) shows the difference is very small (a random DC comment is more positive only 53% of the time vs 47%).

**Q9. What is betweenness centrality and why do you not say "influential"?**
It counts how many shortest paths between pairs of users pass through a user. It describes **position** in the reply network, not social influence or expertise.

**Q10. What does modularity of 0.85 mean? Is that strong community structure?**
It is high, but reply networks are thread-shaped, so high modularity is expected. We interpret communities as discussion circles, not factions.

**Q11. Why do you say only about 5% overlap — could it be higher?**
Yes. Comments are a sample, so we undercount users who appear in both. We report three definitions and call it a lower bound.

**Q12. What was your biggest mistake?**
Our first run concluded Marvel fans were much colder about DC. It came from a biased 35-hour sample and a crude tagger. After fixing the sampling and tagging, the effect vanished. We report the corrected result.

**Q13. Why 8 topics? Why not 5 or 20?**
8 gave distinct, interpretable topics without too many tiny ones. The number is a setting in `config.py`; we judged it by reading the topic words.

**Q14. What is NMF and how is it different from LDA?**
Both find topics. NMF factorises a TF-IDF matrix into non-negative parts, is faster, needs less tuning and gives interpretable topics at this data size (see glossary).

**Q15. 35% of comments have no topic. Isn't that a failure?**
Those comments are too short to carry topical words (e.g. "lol exactly"). Forcing them into a topic would be wrong, so we label them −1 and say so openly.

**Q16. How could you improve the project?**
Validate VADER against a transformer model or hand-labelled comments; add stance detection for rival talk (supportive vs critical); add a second event window or a second rivalry pair; use exact betweenness.

**Q17. Is the code reproducible?**
Yes: frozen window, seeds fixed for NMF, Louvain and betweenness, pinned library versions, one command to rerun, 26 tests.

**Q18. What does "the audiences are separate" mean practically?**
Around 95 of every 100 users in one community never commented in the other during the window.

---

# Part 15: How to run everything

## 15.1 Setup (Windows PowerShell)
```powershell
cd D:\Mayank\FandomFaultLines
python -m venv venv                 # only the first time
venv\Scripts\Activate.ps1
pip install -r requirements.txt     # only the first time
```

## 15.2 Run
```powershell
python run_pipeline.py --stage all --skip-collection   # re-run all analysis on existing raw data
python run_pipeline.py --stage <name>                  # one stage
python -m pytest tests/ -v                             # run tests
python src/gephi_export.py                             # regenerate the Gephi core files
```
Stage names: `collect_posts`, `collect_comments`, `collect_parents`, `preprocess`, `eda`, `topic_modeling`, `sentiment`, `statistical_tests`, `network_build`, `network_analysis`, `overlap_analysis`, `connector_analysis`, `visualize`.

## 15.3 Gephi (manual step, optional)
1. Open `outputs/networks/network_<sub>_core_for_gephi.gexf` in Gephi.
2. It opens already laid out, coloured by community and sized by betweenness.
3. Preview tab → untick *Show Labels* → Refresh → Export PNG.

---

# Part 16: Glossary

**Alias list** — a list of words (marvel, mcu, thor…) used to decide whether a comment is about a franchise.

**API** — a way for programs to request data from a website.

**Arctic Shift** — a free public archive of Reddit data that needs no login.

**Backoff (exponential)** — waiting longer after each failed request (5 s, 10 s, 20 s, 40 s) so we do not hammer a server.

**Betweenness centrality** — for each user, the (normalised) share of shortest paths between all pairs of other users that pass through them. High = a bridge or hub position. We approximate it with 2,000 sampled sources.

**Bot** — an automated account (e.g. AutoModerator). We remove them because they are not real fans and distort counts.

**Boxplot** — a chart showing the middle 50% of values as a box, the median as a line, and outliers as dots.

**Centrality** — a family of measures of how "important" a node's position is in a network.

**Community (network)** — a group of nodes more densely connected to each other than to the rest of the network.

**Component (weakly connected)** — a group of users who are all linked to each other through some chain of replies, ignoring direction. A "giant component" is the biggest one.

**Confidence interval (95% CI)** — a range likely to contain the true average; the error bars on the sentiment chart.

**Coverage (network)** — share of comments whose parent (the thing replied to) is known, so an edge could be drawn. Ours: 99.9%.

**CSV** — a plain-text table file (comma-separated values) that opens in Excel.

**Degree centrality** — the share of other users a user is directly connected to.

**Density** — what fraction of all possible links actually exist. Ours: about 0.0001–0.0002 (very sparse).

**Directed graph** — a network where links have a direction (A replied to B is not the same as B replied to A).

**Distinctive topic / lift** — the topic most over-represented in a community compared with the whole subreddit; lift = community share ÷ subreddit share.

**EDA (exploratory data analysis)** — looking at the data (charts, counts, common words) before formal testing.

**Echo chamber** — a group that mostly interacts with people who agree with it and rarely with outsiders.

**Edge** — a link in a network (here: "user A replied to user B").

**Effect size** — how *big* a difference is, as opposed to whether it is statistically detectable. Ours: rank-biserial correlation r.

**Event-window confounding** — when a short time window is dominated by one event (like a TV show finale), making results unrepresentative.

**ForceAtlas2** — a layout algorithm in Gephi that pulls linked nodes together and pushes others apart.

**Frozen window** — fixed start and end dates so the dataset never changes silently.

**GEXF** — the file format Gephi reads for graphs.

**Gephi** — a free desktop program for visualising networks.

**Git / GitHub** — version control for code, and the website that hosts it.

**Graph** — the maths word for a network: nodes and edges.

**Hash / SHA-256** — a one-way scrambling function: the same input always gives the same output but you cannot go back from output to input. Used to hide usernames.

**Holm (Holm-Bonferroni) correction** — a way to adjust p-values when running many tests at once, so you do not get false "significant" results just from trying many tests.

**Jaccard index** — shared members ÷ total distinct members of two groups. 0% = no overlap, 100% = identical groups. Ours: about 2.8%.

**k-core (2-core)** — the part of a network left after repeatedly removing nodes with fewer than k connections. We use it only to draw a cleaner picture.

**Lexicon** — a dictionary (here, of words with sentiment scores).

**Logger / log** — the program's diary file (`logs/pipeline.log`).

**Louvain algorithm** — a fast method for finding communities by repeatedly grouping nodes to maximise modularity.

**Mann-Whitney U test** — a test that checks whether values from one group tend to be larger than from another, without assuming a bell-shaped distribution.

**Modularity** — a score (up to 1) of how much more densely connected communities are than expected by chance.

**NMF (non-negative matrix factorization)** — a technique that breaks a big word-by-comment table into a few "topics" (word groups) and each comment's mix of them, using only non-negative numbers so topics are additive and readable.

**Node** — a point in a network (here, a user).

**p-value** — the probability of seeing a difference at least this large if there were truly no difference. Small (< 0.05) suggests the difference is not just chance. It does **not** tell you how large or important the difference is.

**Pagination** — fetching a long list in pages (100 at a time).

**PRAW** — the Python library for Reddit's official API (not used here).

**Pseudonymization** — replacing identifying names with fake IDs while keeping the ability to link the same person's records.

**Rank-biserial correlation (r)** — the effect size we use; (1 + r) ÷ 2 is roughly the chance that a random value from group A beats one from group B.

**Regular expression (regex)** — a text-search pattern; ours matches whole words only.

**Reproducibility** — being able to rerun the project and get the same results (fixed dates, seeds, pinned versions).

**Robustness check** — rerunning an analysis under a slightly different setting (here, excluding zero-score comments) to see whether conclusions hold.

**Sample / stratified sample** — a subset of the data / a subset taken evenly from each time slot.

**Score (Reddit)** — roughly upvotes minus downvotes.

**Self-loop** — a user replying to themself; removed from the network.

**Sentiment analysis** — measuring whether text expresses positive or negative feeling.

**Significance (statistical)** — evidence that a difference is unlikely to be just chance (usually p < 0.05). **Not** the same as being large or important.

**Stopwords** — very common words (the, is, and…) ignored in word counts and topics.

**Subreddit** — a topic forum on Reddit, named `r/...`.

**TF-IDF** — a way to turn text into numbers: a word scores high in a comment if it appears often there (term frequency) but is rare across all comments (inverse document frequency), so distinctive words stand out and common words fade.

**Thread starter** — in our connector analysis, a user who authored posts and receives more replies than they write.

**Topic modeling** — automatically discovering groups of words that tend to appear together (themes) in many comments.

**Unix timestamp** — a time as the number of seconds since 1 January 1970 UTC.

**VADER (Valence Aware Dictionary and sEntiment Reasoner)** — a rule-based sentiment tool built for social-media text. It has a lexicon of about 7,500 words and emoticons, each rated by human judges from −4 (very negative) to +4 (very positive). For a text it adds up word scores and adjusts them with rules: negation ("not good" flips), intensifiers ("very good" is stronger), capital letters and exclamation marks (stronger), and "but" (the part after it counts more). The sum is squashed into a **compound score** between −1 and +1. We treat ≥ 0.05 as positive, ≤ −0.05 as negative and in between as neutral. **Limits:** it cannot detect sarcasm, and gives exactly 0 when it recognises no sentiment words (23.8% of our comments).

**Weight (edge weight)** — a number on a link; ours is how many times one user replied to another.

---

*End of document.*
