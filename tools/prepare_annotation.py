"""Create two blinded human-annotation sheets with blank labels, kept locally."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.study_data import read_design


def make_sheets(design, per_stratum=8):
    output = Path("data/gold/study")
    output.mkdir(parents=True, exist_ok=True)
    if any(output.glob("annotator_*.csv")):
        raise FileExistsError("Annotation sheets already exist; refusing to overwrite possible human work")
    samples, metadata = [], []
    for pair in design["pairs"]:
        cache = Path(design["output_dir"]) / "private" / f"{pair['id']}_content.csv.gz"
        marker = cache.with_name(f"{pair['id']}_complete.json")
        if not marker.exists():
            raise FileNotFoundError(f"Complete analysis for {pair['id']} before drawing annotations")
        data = pd.read_csv(cache)
        for (sub, window, target), group in data.groupby(["subreddit", "window", "target"]):
            n = min(per_stratum, len(group))
            sample = group.sample(n, random_state=design["seed"])
            rival = next(s for s in pair["communities"] if s != sub)
            for r in sample.itertuples():
                code = "a" + hashlib.sha256(f"{pair['id']}:{r.id}".encode()).hexdigest()[:12]
                samples.append({"annotation_id": code, "subreddit": sub, "specified_rival": rival,
                                "text": r.body_clean, "sentiment": "", "stance_rival": "", "notes": ""})
                metadata.append({"annotation_id": code, "comment_id": r.id, "pair": pair["id"],
                                 "window": window, "subreddit": sub, "target_stratum": target,
                                 "population_n": len(group), "sample_n": n, "inclusion_probability": n / len(group),
                                 "source_fingerprint": json.loads(marker.read_text())["fingerprint"]})
    rows = pd.DataFrame(samples)
    if rows["annotation_id"].duplicated().any():
        raise ValueError("Duplicate annotation IDs")
    for i, name in enumerate(("a", "b")):
        rows.sample(frac=1, random_state=design["seed"] + i).to_csv(output / f"annotator_{name}.csv", index=False)
    pd.DataFrame(metadata).to_csv(output / "sampling_metadata.csv", index=False)
    (output / "README.txt").write_text(
        "Label independently; do not view the other rater's sheet or sampling metadata first.\n"
        "sentiment: positive / neutral-or-mixed / negative / uncertain\n"
        "stance_rival: favourable / hostile / neutral-or-mixed / not-mentioned / uncertain\n"
        "This is a human pilot. Freeze the codebook before drawing a separate held-out evaluation set.\n"
        "Do not claim held-out validation after using this pilot to modify a model.\n", encoding="utf-8")
    print(f"Prepared {len(rows)} shuffled rows per rater in {output}; all labels blank.")
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-stratum", type=int, default=8)
    args = parser.parse_args()
    if args.per_stratum < 1:
        parser.error("--per-stratum must be positive")
    make_sheets(read_design(), args.per_stratum)
