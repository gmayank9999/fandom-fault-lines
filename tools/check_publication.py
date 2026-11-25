"""Reject private data paths and identifying/text columns in published aggregates."""
import argparse
import csv
import io
from pathlib import Path
import subprocess

PRIVATE_PREFIXES = ("data/raw/", "data/gold/", "data/processed/", "outputs/study/private/",
                    "outputs/study/networks/", "outputs/study/cache/", "logs/", ".bin/")
PRIVATE_COLUMNS = {"author", "body", "body_clean", "text", "parent_id", "link_id", "user", "id",
                   "overlapping_user", "annotation_id", "comment_id"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracked", action="store_true", help="Check current tracked tree (CI); default is staged additions/modifications")
    args = parser.parse_args()
    command = ["git", "ls-files"] if args.tracked else ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"]
    paths = subprocess.check_output(command, text=True).splitlines()
    errors = []
    for path in paths:
        if path.startswith(PRIVATE_PREFIXES):
            errors.append(f"Private path: {path}")
        if path.startswith("outputs/study/") and path.endswith(".csv"):
            content = Path(path).read_text(encoding="utf-8") if args.tracked else subprocess.check_output(["git", "show", ":" + path], text=True, encoding="utf-8")
            columns = next(csv.reader(io.StringIO(content)), [])
            forbidden = {c.lower() for c in columns} & PRIVATE_COLUMNS
            if {"source", "target"} <= {c.lower() for c in columns}:
                forbidden.add("source/target edge list")
            if forbidden:
                errors.append(f"User/text columns {forbidden}: {path}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Publication check passed: {len(paths)} {'tracked' if args.tracked else 'staged'} files; no private paths or row-level identifying columns.")


if __name__ == "__main__":
    main()
