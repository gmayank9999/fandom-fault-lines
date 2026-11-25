"""Comparative study runner. Never changes the original pilot's input paths."""
import argparse
from pathlib import Path
from src.study_data import read_design, collect, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design", default="study.json")
    parser.add_argument("--stage", choices=["inventory", "collect", "analyze", "report", "all"], default="inventory")
    parser.add_argument("--subreddit", action="append")
    parser.add_argument("--workers", type=int, choices=[1, 2, 4], default=2,
                        help="Bounded archive download concurrency (default 2)")
    args = parser.parse_args()
    design = read_design(args.design)
    out = Path(design["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    if args.stage in ("collect", "all"):
        collect(design, args.subreddit, args.workers)
    status = inventory(design)
    status.to_csv(out / "collection_inventory.csv", index=False)
    print(status.to_string(index=False), flush=True)
    if args.stage in ("analyze", "all"):
        from src.study_analysis import analyze
        analyze(design)
    if args.stage in ("report", "all"):
        from src.study_report import report
        report(design)


if __name__ == "__main__":
    main()
