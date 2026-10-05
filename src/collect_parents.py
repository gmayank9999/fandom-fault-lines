import csv
import os
import sys

import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, request_with_retry, safe_get

logger = setup_logger("collect_parents")

PARENT_FIELDS = ["kind", "id", "subreddit", "author"]
BATCH = 100


def missing_parent_ids(comments, posts):
    """Parent ids referenced by the sampled comments that are not themselves in the sample.
    Returns (missing comment ids, missing post ids), bare ids without the t1_/t3_ prefix."""
    have_comments = set(comments["id"].astype(str))
    have_posts = set(posts["id"].astype(str))
    parents = comments["parent_id"].astype(str)
    t1 = {p[3:] for p in parents if p.startswith("t1_")} - have_comments
    t3 = {p[3:] for p in parents if p.startswith("t3_")} - have_posts
    return sorted(t1), sorted(t3)


def fetch_by_ids(kind, ids, writer):
    endpoint = "comments" if kind == "t1" else "posts"
    found = 0
    for i in range(0, len(ids), BATCH):
        batch = ids[i:i + BATCH]
        data = request_with_retry(f"{config.BASE_URL}/{endpoint}/ids", {"ids": ",".join(batch)}, logger)
        for item in (data or {}).get("data", []):
            writer.writerow({"kind": kind, "id": safe_get(item, "id", ""),
                             "subreddit": safe_get(item, "subreddit", ""),
                             "author": safe_get(item, "author", "[deleted]")})
            found += 1
    return found


def main():
    """Stage 2b. Comments are sampled per time slot, so many replies point at a parent comment
    (or an older post) that is not in the sample. Fetch just those parents' authors by id so the
    reply network does not silently lose those edges. Only author ids are kept, no text."""
    comments = pd.read_csv(config.RAW_COMMENTS_PATH)
    posts = pd.read_csv(config.RAW_POSTS_PATH)
    t1, t3 = missing_parent_ids(comments, posts)
    logger.info(f"Missing parents to fetch: {len(t1)} comments, {len(t3)} posts.")

    os.makedirs("data/raw", exist_ok=True)
    with open(config.RAW_PARENTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PARENT_FIELDS)
        writer.writeheader()
        n1 = fetch_by_ids("t1", t1, writer)
        n3 = fetch_by_ids("t3", t3, writer)
    logger.info(f"FINISHED: found {n1}/{len(t1)} parent comments and {n3}/{len(t3)} parent posts "
                f"(the rest were deleted/removed or absent from the archive).")


if __name__ == "__main__":
    main()
