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


def compile_alias_regex(aliases):
    """One case-insensitive regex that matches any alias as a WHOLE word/phrase,
    so 'dc' does not fire inside other words. Returns None for an empty list."""
    import re
    parts = [r"(?<![A-Za-z0-9])" + re.escape(a.lower()) + r"(?![A-Za-z0-9])" for a in aliases if a]
    return re.compile("|".join(parts), re.IGNORECASE) if parts else None


def mentions_any(text, regex):
    return bool(regex is not None and regex.search(str(text)))


def get_stopwords():
    """Full English stopword list plus conversational filler that dominates Reddit text.
    Shared by EDA (keyword lists) and topic modeling so both ignore the same words."""
    from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
    filler = set("like just don didn doesn isn wasn aren wouldn couldn shouldn really got get gets "
                 "think know lol yeah yes thing things going gonna want make way good bad people "
                 "movie movies film films one also even still much many ve ll re let say said "
                 "actually pretty look looks see time gif giphy".split())
    return set(ENGLISH_STOP_WORDS) | filler
