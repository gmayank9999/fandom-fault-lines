"""Explicit study windows, validated day caches and resumable archive collection.

Archive completeness is not Reddit completeness. Legacy day files have no request
manifest and are labelled as such; new files get checksums and retrieval times.
"""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

import config
from src.collect_full import DAY, FULL_FIELDS, LIGHT_FIELDS, day_chunks


def timestamp(date):
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())


def read_design(path="study.json"):
    design = json.loads(Path(path).read_text(encoding="utf-8"))
    names = [s for p in design["pairs"] for s in p["communities"]]
    if len(set(names)) != len(names):
        raise ValueError("A community may belong to only one study pair")
    windows = sorted((timestamp(w["start"]), timestamp(w["end"])) for w in design["windows"])
    if any(a >= b or (b - a) % DAY for a, b in windows):
        raise ValueError("Windows must contain positive whole UTC days")
    if any(b > c for (_, b), (c, _) in zip(windows, windows[1:])):
        raise ValueError("Study windows must not overlap")
    return design


def communities(design):
    return [s for p in design["pairs"] for s in p["communities"]]


def days(window):
    return list(day_chunks(timestamp(window["start"]), timestamp(window["end"])))


def cache_path(window, sub, day):
    legacy = Path(window.get("legacy_cache", "data/raw/absent")) / sub / f"{day}.csv"
    return legacy if legacy.is_file() else Path("data/raw/study") / sub / f"{day}.csv"


def validate_day(path, sub, start, end, light=False):
    df = pd.read_csv(path, dtype={"id": str, "link_id": str, "parent_id": str})
    required = LIGHT_FIELDS if light else FULL_FIELDS
    if not set(required) <= set(df):
        raise ValueError(f"{path}: missing columns {set(required) - set(df)}")
    if df["id"].isna().any() or df["id"].duplicated().any():
        raise ValueError(f"{path}: missing/duplicate IDs")
    if not df["subreddit"].str.casefold().eq(sub.casefold()).all():
        raise ValueError(f"{path}: wrong subreddit")
    if not pd.to_numeric(df["created_utc"], errors="coerce").between(start, end - 1).all():
        raise ValueError(f"{path}: timestamps outside declared UTC day")
    df["subreddit"] = sub
    return df


def load_window(window, subs, light=False):
    frames = []
    for sub in subs:
        for a, b in days(window):
            path = cache_path(window, sub, a)
            if not path.is_file():
                raise FileNotFoundError(f"Missing {sub} {datetime.fromtimestamp(a, timezone.utc).date()}; run collection")
            frames.append(validate_day(path, sub, a, b, light))
    result = pd.concat(frames, ignore_index=True)
    if result.duplicated(["subreddit", "id"]).any():
        raise ValueError("Duplicate IDs across day files")
    return result


class Archive:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(config.HEADERS)

    def get(self, endpoint, params):
        for attempt in range(6):
            try:
                r = self.session.get(f"{config.BASE_URL}/{endpoint}", params=params, timeout=35)
                if r.status_code == 200:
                    data = r.json()
                    if not isinstance(data.get("data"), list):
                        raise ValueError("Archive response has no data array")
                    return data["data"]
                if r.status_code not in (422, 429, 500, 502, 503, 504):
                    r.raise_for_status()
                delay = min(20, 2 ** attempt)
                if r.status_code == 429:
                    delay = min(60, max(delay, float(r.headers.get("Retry-After", delay))))
            except (requests.ConnectionError, requests.Timeout):
                delay = min(20, 2 ** attempt)
            time.sleep(delay)
        raise RuntimeError(f"Archive unavailable: {endpoint}; no complete-day marker written")

    def collect_day(self, sub, start, end, light=False):
        fields = LIGHT_FIELDS if light else FULL_FIELDS
        request_fields = [f for f in fields if f != "subreddit"]
        seen, rows, before = set(), [], end
        for _ in range(1000):
            page = self.get("comments/search", {"subreddit": sub, "before": before,
                            "sort": "desc", "limit": 100, "fields": ",".join(request_fields)})
            if not page:
                return pd.DataFrame(rows, columns=fields)
            oldest = min(int(c["created_utc"]) for c in page)
            new = 0
            for c in page:
                if not start <= int(c["created_utc"]) < end or c["id"] in seen:
                    continue
                rows.append({**{f: c.get(f) for f in request_fields}, "subreddit": sub})
                seen.add(c["id"])
                new += 1
            if len(page) < 100 or oldest < start:
                return pd.DataFrame(rows, columns=fields)
            if not new and all(int(c["created_utc"]) == oldest for c in page):
                raise RuntimeError("100+ comments at one second: timestamp cursor cannot guarantee coverage")
            before = oldest + 1 if new else oldest
        raise RuntimeError("Page cap reached; refusing to save an incomplete day")


def collect(design, selected=None, workers=2):
    from concurrent.futures import ThreadPoolExecutor, as_completed
    rivals = communities(design)
    jobs = []
    for window in design["windows"]:
        for sub in rivals + design["baselines"]:
            if selected and sub not in selected:
                continue
            for a, b in days(window):
                path = cache_path(window, sub, a)
                if path.is_file():
                    validate_day(path, sub, a, b, sub not in rivals)
                    continue
                jobs.append((window, sub, a, b, path))

    def fetch(job):
        window, sub, a, b, path = job
        api = Archive()  # one HTTP session per task, never shared between threads
        df = api.collect_day(sub, a, b, sub not in rivals)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        df.to_csv(tmp, index=False)
        validate_day(tmp, sub, a, b, sub not in rivals)
        tmp.replace(path)
        path.with_suffix(".json").write_text(json.dumps({
            "retrieved_utc": datetime.now(timezone.utc).isoformat(), "rows": len(df),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "start": a, "end": b,
            "source": config.BASE_URL, "pagination": "exclusive timestamp with boundary overlap"
        }, indent=2), encoding="utf-8")
        print(f"COLLECTED {window['id']} {sub} {datetime.fromtimestamp(a, timezone.utc).date()} {len(df)}", flush=True)

    # Bounded concurrency; each request respects 429/Retry-After independently.
    failures = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, j): j for j in jobs}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as exc:
                failures.append(str(exc))
                print(f"FAILED DAY {futures[future][1:4]}: {exc}", flush=True)
    if failures:
        raise RuntimeError(f"{len(failures)} incomplete days; rerun to retry: {failures[0]}")
    api = Archive()
    for window in design["windows"]:
        for sub in rivals:
            if not selected or sub in selected:
                collect_parent_authors(api, window, sub)


def raw_parent_lookup():
    frames = []
    for path in (Path(config.RAW_PARENTS_PATH), Path("data/raw/study/parents.csv")):
        if path.is_file():
            frames.append(pd.read_csv(path, dtype=str)[["kind", "id", "author"]])
    if Path(config.RAW_POSTS_PATH).is_file():
        posts = pd.read_csv(config.RAW_POSTS_PATH, dtype={"id": str})
        frames.append(posts[["id", "author"]].assign(kind="t3"))
    return pd.concat(frames, ignore_index=True).drop_duplicates(["kind", "id"]) if frames else pd.DataFrame(columns=["kind", "id", "author"])


def collect_parent_authors(api, window, sub):
    raw = load_window(window, [sub])
    parents = raw_parent_lookup()
    known = set(parents["kind"] + "_" + parents["id"])
    known.update("t1_" + raw["id"])
    missing = set(raw["parent_id"].dropna()) - known
    path = Path("data/raw/study/parents.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    for kind, endpoint in (("t1", "comments"), ("t3", "posts")):
        ids = sorted(p[3:] for p in missing if p.startswith(kind + "_"))
        for i in range(0, len(ids), 500):
            batch = ids[i:i + 500]
            data = api.get(endpoint + "/ids", {"ids": ",".join(batch), "fields": "id,author"})
            found = {d["id"]: d.get("author") for d in data}
            # Absent IDs remain explicitly unresolved; they are never invented.
            add = pd.DataFrame([{"kind": kind, "id": key, "author": found.get(key)} for key in batch])
            parents = pd.concat([parents, add], ignore_index=True).drop_duplicates(["kind", "id"])
            temp = path.with_suffix(".tmp")
            parents.to_csv(temp, index=False)
            temp.replace(path)
    print(f"PARENTS {window['id']} {sub}: checked {len(missing)} out-of-window IDs", flush=True)


def inventory(design):
    rows = []
    rivals = communities(design)
    for window in design["windows"]:
        for sub in rivals + design["baselines"]:
            present, count, errors, new = 0, 0, [], 0
            for a, b in days(window):
                path = cache_path(window, sub, a)
                if not path.is_file():
                    continue
                try:
                    df = validate_day(path, sub, a, b, sub not in rivals)
                    meta = path.with_suffix(".json")
                    if meta.is_file():
                        manifest = json.loads(meta.read_text(encoding="utf-8"))
                        if manifest["sha256"] != hashlib.sha256(path.read_bytes()).hexdigest():
                            raise ValueError("checksum mismatch")
                        new += 1
                    present += 1
                    count += len(df)
                except ValueError as e:
                    errors.append(str(e))
            rows.append({"window": window["id"], "start_utc": window["start"], "end_utc_exclusive": window["end"],
                         "subreddit": sub, "expected_days": len(days(window)), "valid_days": present,
                         "rows": count, "manifest_days": new, "complete_files": present == len(days(window)),
                         "provenance": "request manifest" if present and new == present else "includes legacy cache without request manifest",
                         "errors": " | ".join(errors)})
    return pd.DataFrame(rows)
