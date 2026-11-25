import os
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

# ---- Full-window collection (Stage 2 full) and overlap baseline ----
FULL_RAW_DIR = "data/raw/full"       # one CSV per subreddit per UTC day (resumable)
# Non-rival subreddits collected over the same window, authors only, to give the Marvel-DC overlap
# a baseline: "is 5% low or normal for two big film/TV-franchise subreddits?"
BASELINE_SUBREDDITS = ["StarWars", "lotr"]

# ---- API ----
BASE_URL = "https://arctic-shift.photon-reddit.com/api"
HEADERS = {"User-Agent": "csma-fandom-project/0.1 (academic project, group 6)"}
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 4
RETRY_BACKOFF_SECONDS = 5           # doubles each retry: 5, 10, 20, 40

# ---- Bot/noise filtering (Stage 3) ----
BOT_ACCOUNTS = {"AutoModerator", "[deleted]", "RemindMeBot", "sneakpeekbot",
                # found by profiling the most active accounts of the full data (bot names, templated output)
                "_pixelcounterbot_", "Hi_Im_Dadbot", "SokkaHaikuBot", "auddbot", "rammus-bot", "reaporbot"}
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

# ---- Sentiment ----
# VADER's word list scores many franchise / plot words as emotional ("doom" -1.7, "war" -2.9,
# "villain" -2.6, "kill" -3.7, "marvel" +1.8, "hero" +2.6). In a window full of Doctor Doom,
# Secret Wars and Lanterns threads this creates a fake negative tone. The adapted scorer removes
# these words from the lexicon; both scorers are kept and compared against a hand-labelled set.
DOMAIN_NEUTRAL_WORDS = [
    "doom", "war", "wars", "villain", "villains", "kill", "killed", "killing", "kills", "dark", "evil",
    "invasion", "strange", "joker", "death", "dead", "die", "died", "dies", "fight", "fights", "fighting",
    "destroy", "destroyed", "super", "wonder", "marvel", "marvels", "hero", "heroes", "black", "steel",
    "power", "powers", "powerful", "justice", "legend", "legends", "victory", "battle", "weapon",
    "crisis", "ghost", "angel", "demon", "monster", "terror", "mad", "crazy", "sin", "sinestro",
]
# Transformer sentiment (scores cached by hashed comment id in data/processed/transformer_scores.csv).
# Provisional choice by agreement with an AI-labelled development set (NOT human validation):
#   plain VADER kappa 0.16, domain-adapted VADER 0.21, transformer (3-class argmax, untuned) kappa 0.54.
PRIMARY_SCORER = "sentiment_transformer"
USE_TRANSFORMER = os.environ.get("FFL_TRANSFORMER", "1") == "1"   # FFL_TRANSFORMER=0 skips the slow model
TRANSFORMER_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
# CPU inference is ~15 comments/s. Every rival-mentioning comment is scored (rival_talk, both); the big
# groups are capped at a fixed random sample PER SUBREDDIT, which gives stable means (SE ~ 0.005).
TRANSFORMER_CAP_PER_STRATUM = {"self_talk": 8000, "general": 4000}
TRANSFORMER_MAX_LEN = 128
TRANSFORMER_BATCH = 64
TRANSFORMER_SCORES_PATH = "data/processed/transformer_scores.csv"

# ---- Topic modeling / network analysis settings ----
N_TOPICS = 8                         # used only if TOPIC_CANDIDATES is empty
TOPIC_CANDIDATES = [6, 8, 10, 12, 16]   # K is chosen per subreddit by NPMI coherence
TOPIC_MIN_TOKENS = 4                 # comments with fewer informative tokens get topic_id = -1
MIN_COMMUNITY_SIZE = 10              # communities below this are reported as "fragments"
BETWEENNESS_SAMPLE_K = 2000          # sampled betweenness above this many nodes
BETWEENNESS_EXACT_MAX_NODES = 2000
TOP_CONNECTORS = 20

# ---- Paths ----
RAW_POSTS_PATH = "data/raw/raw_posts.csv"
RAW_COMMENTS_PATH = "data/raw/raw_comments.csv"
RAW_PARENTS_PATH = "data/raw/raw_parents.csv"
RAW_BASELINE_PATH = "data/raw/raw_baseline_authors.csv"
CLEAN_BASELINE_PATH = "data/processed/baseline_authors.csv"
CLEAN_PARENTS_PATH = "data/processed/parent_authors.csv"
CLEAN_POSTS_PATH = "data/processed/clean_posts.csv"
CLEAN_COMMENTS_PATH = "data/processed/clean_comments.csv"
SENTIMENT_PATH = "data/processed/comments_with_sentiment.csv"
SENTIMENT_BY_TARGET_PATH = "data/processed/sentiment_by_target.csv"
STATISTICAL_TESTS_PATH = "data/processed/statistical_tests.csv"
OVERLAP_PATH = "data/processed/overlap_users.csv"
OVERLAP_SUMMARY_PATH = "data/processed/overlap_summary.csv"
OVERLAP_BASELINE_PATH = "data/processed/overlap_baseline.csv"
PEAK_DAYS_PATH = "data/processed/peak_days.csv"
CHARTS_DIR = "outputs/charts"
NETWORKS_DIR = "outputs/networks"
LOG_PATH = "logs/pipeline.log"
