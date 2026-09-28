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
