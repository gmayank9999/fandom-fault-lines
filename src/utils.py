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


_SALT = None


def _get_salt():
    """Secret salt for all hashing. Kept in data/raw/.salt (git-ignored) so that nobody holding only the
    published tables can recompute a hash from a guessed username or a Reddit comment/post id.
    Created on first use. Override with the FFL_SALT environment variable."""
    global _SALT
    if _SALT is None:
        _SALT = os.environ.get("FFL_SALT")
        if not _SALT:
            path = os.path.join("data", "raw", ".salt")
            if os.path.exists(path):
                _SALT = open(path, encoding="utf-8").read().strip()
            else:
                import secrets
                os.makedirs(os.path.dirname(path), exist_ok=True)
                _SALT = secrets.token_hex(16)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(_SALT)
    return _SALT


def _digest(kind, value):
    return hashlib.sha256((_get_salt() + "|" + kind + "|" + str(value)).encode()).hexdigest()[:10]


def anonymize(username):
    """
    Salted, one-way pseudonymization: the same username always maps to the same id on a given
    machine (so networks and overlap work), but without the secret salt the mapping cannot be
    recomputed from a guessed username. No lookup table back to real usernames is ever stored.
    """
    if not isinstance(username, str) or username.strip().lower() in ("[deleted]", "[removed]", "", "nan"):
        return "[deleted]"
    return "user_" + _digest("user", username.strip())


def anonymize_id(raw_id, kind="id"):
    """Salted hash for Reddit post/comment ids. Raw ids are dangerous to publish: reddit.com/comments/<id>
    resolves to the real author. The same id always hashes to the same value, so joins still work."""
    if raw_id in (None, ""):
        return ""
    return "h" + _digest(kind, raw_id)


def anonymize_fullname(fullname):
    """'t1_abc' / 't3_abc' -> 't1_<hash>' / 't3_<hash>' (prefix kept so the network code can still tell
    comment parents from post parents). Anything else becomes ''."""
    fullname = str(fullname)
    if fullname[:3] in ("t1_", "t3_"):
        return fullname[:3] + anonymize_id(fullname[3:], fullname[:2])
    return ""


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
