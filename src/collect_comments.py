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
