import csv
import os
import sys
import time

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
    """Returns (found, failed): ids found, and ids whose request failed after all retries (an API problem,
    not 'deleted'). Ids that the archive simply does not have are neither."""
    endpoint = "comments" if kind == "t1" else "posts"
    found, failed = 0, 0
    for i in range(0, len(ids), BATCH):
        batch = ids[i:i + BATCH]
        data = None
        for _ in range(4):               # request_with_retry gives up after ~1 min; the archive can stay busy longer
            data = request_with_retry(f"{config.BASE_URL}/{endpoint}/ids", {"ids": ",".join(batch)}, logger)
            if data is not None:
                break
            time.sleep(30)
        if data is None:
            failed += len(batch)
            continue
        for item in data.get("data", []):
            writer.writerow({"kind": kind, "id": safe_get(item, "id", ""),
                             "subreddit": safe_get(item, "subreddit", ""),
                             "author": safe_get(item, "author", "[deleted]")})
            found += 1
    return found, failed


def main():
    """Stage 2b. Replies can point at a parent comment or an older post that is not in the collected
    data. Fetch just those parents' authors by id so the reply network does not silently lose those edges.
    Only author ids are kept, no text. Incremental: parents already fetched by an earlier run are kept."""
    comments = pd.read_csv(config.RAW_COMMENTS_PATH)
    posts = pd.read_csv(config.RAW_POSTS_PATH)
    t1, t3 = missing_parent_ids(comments, posts)

    existing = pd.read_csv(config.RAW_PARENTS_PATH, dtype=str) if os.path.exists(config.RAW_PARENTS_PATH)         else pd.DataFrame(columns=PARENT_FIELDS)
    have = set(zip(existing["kind"], existing["id"]))
    t1_todo = [i for i in t1 if ("t1", i) not in have]
    t3_todo = [i for i in t3 if ("t3", i) not in have]
    logger.info(f"Missing parents: {len(t1)} comments, {len(t3)} posts "
                f"({len(t1) - len(t1_todo)} + {len(t3) - len(t3_todo)} already fetched earlier).")

    os.makedirs("data/raw", exist_ok=True)
    with open(config.RAW_PARENTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PARENT_FIELDS)
        writer.writeheader()
        writer.writerows(existing[PARENT_FIELDS].to_dict("records"))
        f1, x1 = fetch_by_ids("t1", t1_todo, writer)
        f3, x3 = fetch_by_ids("t3", t3_todo, writer)
    logger.info(f"FINISHED: found {f1}/{len(t1_todo)} parent comments and {f3}/{len(t3_todo)} parent posts this run; "
                f"{x1 + x3} ids could not be fetched because the API kept failing (re-run to retry them); "
                f"the rest are deleted/removed or absent from the archive.")


if __name__ == "__main__":
    main()
