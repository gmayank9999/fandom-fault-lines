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
