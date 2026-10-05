import time

# ---- Subreddit pair (change these two values for a different case study) ----
SUBREDDIT_A = "marvelstudios"
SUBREDDIT_B = "DC_Cinematic"
SUBREDDITS = [SUBREDDIT_A, SUBREDDIT_B]

# ---- Collection window ----
# The window is FROZEN to fixed UTC dates so re-running the pipeline never silently
# changes the dataset. It ends a few days before collection so that comment scores have
# had time to accumulate (very fresh comments are archived with score ~1).
import calendar
import datetime as _dt

WINDOW_DAYS = 28
WINDOW_END_DATE = _dt.datetime(2026, 10, 1)      # exclusive end, UTC midnight
BEFORE_TS = calendar.timegm(WINDOW_END_DATE.timetuple())
AFTER_TS = BEFORE_TS - (WINDOW_DAYS * 24 * 60 * 60)

# ---- Collection targets ----
# Posts: every post in the window (uncapped; bounded only by MAX_PAGES_SAFETY).
# Comments: STRATIFIED over the window. The window is cut into equal time slots and up to
# COMMENTS_PER_SLOT comments are taken (newest-first) from each slot, so the sample covers
# the whole window evenly instead of only its most recent hours. 28 days * 4 slots/day
# * 90 per slot ~= 10,000 comments per subreddit.
TARGET_POSTS_PER_SUB = float("inf")
SLOTS_PER_DAY = 4                    # 6-hour slots -> also spreads over time of day
COMMENTS_PER_SLOT = 90
TARGET_COMMENTS_PER_SUB = WINDOW_DAYS * SLOTS_PER_DAY * COMMENTS_PER_SLOT   # upper bound
PAGE_LIMIT = 100                     # Arctic Shift's practical per-request cap
MAX_PAGES_SAFETY = 150               # hard stop for post pagination

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
# Matched as WHOLE WORDS / phrases (regex word boundaries), case-insensitive, so "dc" does
# not fire inside other words. Ambiguous shared names (spider-man, doom, flash) are left out
# on purpose. Extend these for a different subreddit pair.
FRANCHISE_ALIASES = {
    "marvelstudios": ["marvel", "mcu", "avengers", "kevin feige", "feige", "iron man",
                      "captain america", "thor", "hulk", "loki", "thanos", "x-men",
                      "fantastic four", "guardians of the galaxy", "doctor strange",
                      "black panther", "disney+"],
    "DC_Cinematic":  ["dc", "dceu", "dcu", "batman", "superman", "supergirl", "james gunn",
                      "gunn", "wonder woman", "green lantern", "justice league", "joker",
                      "aquaman", "peacemaker", "lex luthor", "snyder", "zack snyder"],
}

# ---- Topic modeling / network analysis settings ----
N_TOPICS = 8
TOPIC_MIN_TOKENS = 4                 # comments with fewer informative tokens get topic_id = -1
MIN_COMMUNITY_SIZE = 10              # communities below this are reported as "fragments"
BETWEENNESS_SAMPLE_K = 2000          # sampled betweenness above this many nodes
BETWEENNESS_EXACT_MAX_NODES = 2000
TOP_CONNECTORS = 20

# ---- Paths ----
RAW_POSTS_PATH = "data/raw/raw_posts.csv"
RAW_COMMENTS_PATH = "data/raw/raw_comments.csv"
RAW_PARENTS_PATH = "data/raw/raw_parents.csv"
CLEAN_PARENTS_PATH = "data/processed/parent_authors.csv"
CLEAN_POSTS_PATH = "data/processed/clean_posts.csv"
CLEAN_COMMENTS_PATH = "data/processed/clean_comments.csv"
SENTIMENT_PATH = "data/processed/comments_with_sentiment.csv"
SENTIMENT_BY_TARGET_PATH = "data/processed/sentiment_by_target.csv"
STATISTICAL_TESTS_PATH = "data/processed/statistical_tests.csv"
OVERLAP_PATH = "data/processed/overlap_users.csv"
OVERLAP_SUMMARY_PATH = "data/processed/overlap_summary.csv"
PEAK_DAYS_PATH = "data/processed/peak_days.csv"
CHARTS_DIR = "outputs/charts"
NETWORKS_DIR = "outputs/networks"
LOG_PATH = "logs/pipeline.log"
