"""Stage 2 (full): collect EVERY comment in the frozen window, not a sample.

Why: a per-slot sample kept only ~6% (Marvel) / ~12% (DC) of comments and only the newest
minutes of each 6-hour slot. Overlap, reply-network structure and sentiment were all biased by that.
This stage pages through each UTC day completely and writes one file per (subreddit, day), so an
interrupted run resumes where it stopped.

Rival subreddits keep all fields. Baseline (non-rival) subreddits keep only id/author/time, which is
all the overlap baseline needs.
"""
import argparse
import csv
import os
import sys
import time

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger, request_with_retry, safe_get

logger = setup_logger("collect_full")

FULL_FIELDS = ["id", "subreddit", "link_id", "parent_id", "author", "body", "score", "created_utc"]
LIGHT_FIELDS = ["id", "subreddit", "author", "created_utc"]
DAY = 24 * 60 * 60
MAX_PAGES_PER_DAY = 400          # 40,000 comments/day safety cap


def day_chunks(after_ts=None, before_ts=None):
    after_ts = config.AFTER_TS if after_ts is None else after_ts
    before_ts = config.BEFORE_TS if before_ts is None else before_ts
    t = after_ts
    while t < before_ts:
        yield t, min(t + DAY, before_ts)
        t += DAY


def chunk_path(subreddit, after_ts, base_dir=None):
    return os.path.join(base_dir or config.FULL_RAW_DIR, subreddit, f"{after_ts}.csv")


def fetch_page(subreddit, before_ts, fields):
    # No `after` bound: results arrive newest-first, so the caller stops when it passes the start of the
    # day. Sending both bounds made the archive time out ("Timeout. Maybe slow down a bit", HTTP 422)
    # on narrow ranges, while an open-ended query is a simple fast index scan.
    params = {"subreddit": subreddit, "before": before_ts,
              "sort": "desc", "limit": config.PAGE_LIMIT, "fields": ",".join(fields)}
    # The archive answers HTTP 422 "Timeout. Maybe slow down a bit" for roughly a third of requests when
    # it is busy, and the same request succeeds moments later. A short wait that grows only while the
    # failures persist recovers far faster than request_with_retry's flat 5 s.
    for attempt in range(40):
        try:
            resp = requests.get(f"{config.BASE_URL}/comments/search", params=params, headers=config.HEADERS,
                                timeout=config.REQUEST_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                return resp.json().get("data", [])
            wait = min(1.5 + attempt, 20)
        except requests.exceptions.RequestException as e:
            logger.warning(f"r/{subreddit}: request error ({e})")
            wait = min(3 + attempt, 30)
        time.sleep(wait)
    logger.error(f"r/{subreddit}: page failed 40 times in a row (before={before_ts})")
    return None


def collect_day(subreddit, after_ts, before_ts, light):
    fields = LIGHT_FIELDS if light else FULL_FIELDS
    request_fields = [f for f in fields if f != "subreddit"]
    seen, rows = set(), []
    current_before = before_ts
    for _ in range(MAX_PAGES_PER_DAY):
        page = fetch_page(subreddit, current_before, request_fields)
        if page is None:
            raise RuntimeError(f"r/{subreddit} {after_ts}: API gave up; chunk NOT written (re-run to resume)")
        if not page:
            break
        new = 0
        oldest = min(int(safe_get(c, "created_utc", before_ts)) for c in page)
        for c in page:
            cid = safe_get(c, "id", "")
            if cid in seen or not after_ts <= int(safe_get(c, "created_utc", 0)) < before_ts:
                continue
            seen.add(cid)
            new += 1
            row = {"subreddit": subreddit}
            for f in request_fields:
                row[f] = safe_get(c, f, "" if f in ("body", "author", "link_id", "parent_id", "id") else 0)
            rows.append(row)
        if len(page) < config.PAGE_LIMIT or oldest < after_ts:
            break                      # end of the archive's data, or we have passed the start of the day
        # before is exclusive: use oldest+1 so comments sharing the oldest second are not lost;
        # duplicates are removed through `seen`. If a whole page was already seen, step back 1s.
        if not new and all(int(c["created_utc"]) == oldest for c in page):
            raise RuntimeError("Timestamp-saturated page: cannot prove complete collection; chunk NOT written")
        current_before = oldest + 1 if new else oldest
    else:
        raise RuntimeError("Page safety cap reached; incomplete chunk NOT written")
    return rows, fields


def collect_subreddit(subreddit, light, window=None, base_dir=None, reverse=False):
    """window: optional (after_ts, before_ts) for a replication window; default is the frozen main window."""
    base_dir = base_dir or config.FULL_RAW_DIR
    os.makedirs(os.path.join(base_dir, subreddit), exist_ok=True)
    total = 0
    chunks = list(day_chunks(*(window or (None, None))))
    order = list(enumerate(chunks, 1))
    for i, (a, b) in (reversed(order) if reverse else order):
        path = chunk_path(subreddit, a, base_dir)
        if os.path.exists(path):
            continue
        rows, fields = collect_day(subreddit, a, b, light)
        tmp = path + ".tmp"
        with open(tmp, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        os.replace(tmp, path)            # a chunk file exists only if the day finished completely
        total += len(rows)
        logger.info(f"r/{subreddit}: day {i}/{len(chunks)} -> {len(rows)} comments")
    logger.info(f"r/{subreddit}: FINISHED (this run wrote {total} comments)")


def expected_days():
    return len(list(day_chunks()))


def merge_raw():
    """Concatenate the per-day files into the pipeline's raw inputs:
    raw_comments.csv (rival subreddits, all fields) and raw_baseline_authors.csv (baselines, light)."""
    import glob
    import pandas as pd

    def load(sub):
        files = [chunk_path(sub, a) for a, _ in day_chunks()]
        if not all(os.path.isfile(f) for f in files):
            raise RuntimeError(f"r/{sub}: missing expected day files; "
                               f"finish collection before merging")
        return pd.concat((pd.read_csv(f, dtype={"id": str}) for f in files), ignore_index=True)

    rivals = pd.concat([load(s) for s in config.SUBREDDITS], ignore_index=True)
    rivals = rivals.drop_duplicates(subset=["subreddit", "id"])
    rivals[FULL_FIELDS].to_csv(config.RAW_COMMENTS_PATH, index=False)
    logger.info(f"raw_comments.csv: {rivals.groupby('subreddit').size().to_dict()}")
    if config.BASELINE_SUBREDDITS:
        try:
            base = pd.concat([load(s) for s in config.BASELINE_SUBREDDITS], ignore_index=True)
        except RuntimeError as e:
            # The baselines only feed the overlap comparison; the rest of the analysis does not need them.
            logger.warning(f"Baseline subreddits not fully collected yet ({e}); skipping raw_baseline_authors.csv")
            return
        base = base.drop_duplicates(subset=["subreddit", "id"])
        base[LIGHT_FIELDS].to_csv(config.RAW_BASELINE_PATH, index=False)
        logger.info(f"raw_baseline_authors.csv: {base.groupby('subreddit').size().to_dict()}")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--subreddit", help="collect just this one (default: rivals then baselines)")
    p.add_argument("--reverse", action="store_true",
                   help="work through the days newest-first (a second worker can share a slow subreddit)")
    p.add_argument("--merge-only", action="store_true", help="just merge existing day files")
    p.add_argument("--window-end", help="replication window: UTC date (YYYY-MM-DD, exclusive) the 28-day "
                                        "window ends on; files go to data/raw/full_<date>/ and no merge is done")
    args = p.parse_args(argv)
    if args.merge_only:
        merge_raw()
        return
    jobs = [(s, False) for s in config.SUBREDDITS] + [(s, True) for s in config.BASELINE_SUBREDDITS]
    if args.subreddit:
        jobs = [(s, light) for s, light in jobs if s == args.subreddit]
    if args.window_end:
        import calendar
        import datetime as dt
        end = calendar.timegm(dt.datetime.strptime(args.window_end, "%Y-%m-%d").timetuple())
        window = (end - config.WINDOW_DAYS * DAY, end)
        base = f"data/raw/full_{args.window_end}"
        for sub, light in jobs:
            collect_subreddit(sub, light, window, base, args.reverse)
        return
    for sub, light in jobs:
        collect_subreddit(sub, light, reverse=args.reverse)
    if not args.subreddit and not args.reverse:
        merge_raw()


if __name__ == "__main__":
    main()
