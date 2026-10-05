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


def make_slots():
    """Cut the frozen window into equal time slots (SLOTS_PER_DAY per day).
    Returns a list of (after_ts, before_ts) pairs, oldest first."""
    slot_seconds = 24 * 60 * 60 // config.SLOTS_PER_DAY
    slots = []
    t = config.AFTER_TS
    while t < config.BEFORE_TS:
        slots.append((t, min(t + slot_seconds, config.BEFORE_TS)))
        t += slot_seconds
    return slots


def collect_slot(subreddit, after_ts, before_ts, writer):
    """Take up to COMMENTS_PER_SLOT comments (newest-first) from one time slot."""
    collected = 0
    current_before = before_ts
    while collected < config.COMMENTS_PER_SLOT:
        limit = min(config.PAGE_LIMIT, config.COMMENTS_PER_SLOT - collected)
        comments = fetch_comments_page(subreddit, current_before, after_ts, limit)
        if not comments:
            break
        oldest_ts = None
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
            if created_utc is not None and (oldest_ts is None or created_utc < oldest_ts):
                oldest_ts = created_utc
        if oldest_ts is None or len(comments) < limit:
            break
        current_before = oldest_ts - 1
    return collected


def collect_subreddit_comments(subreddit, writer):
    slots = make_slots()
    collected = 0
    empty_slots = 0
    for i, (after_ts, before_ts) in enumerate(slots, 1):
        n = collect_slot(subreddit, after_ts, before_ts, writer)
        collected += n
        if n == 0:
            empty_slots += 1
        if i % 14 == 0 or i == len(slots):
            logger.info(f"r/{subreddit}: slot {i}/{len(slots)}, total so far = {collected}")

    logger.info(f"r/{subreddit}: {empty_slots}/{len(slots)} slots returned no comments.")
    if collected < 0.8 * config.TARGET_COMMENTS_PER_SUB:
        logger.warning(f"r/{subreddit}: collected {collected} comments, well below the "
                       f"{config.TARGET_COMMENTS_PER_SUB} upper bound (quiet slots or API gaps).")
    logger.info(f"r/{subreddit}: FINISHED with {collected} comments collected "
                f"(stratified over {len(slots)} time slots).")


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
