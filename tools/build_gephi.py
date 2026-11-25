"""Build native Gephi projects and images using the official optional toolkit.

Download the pinned jar to .bin/ from the official release, then run this script
with the project's Python interpreter. Requires a JDK 17+ on PATH. Raw graph
artifacts remain local; validation summaries and unlabeled figures are published.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
JAR = ROOT / ".bin/gephi-toolkit-0.11.3-all.jar"
EXPECTED_SHA256 = "3201e7c7a8353963d9dc6c180916f2fee882b72ce3f053d51464ac76863a545b"


def main():
    if not JAR.exists() or hashlib.sha256(JAR.read_bytes()).hexdigest() != EXPECTED_SHA256:
        raise RuntimeError("Missing or unexpected Gephi Toolkit jar. See GEPHI_GUIDE.md for the official pinned download.")
    subprocess.run(["javac", "-encoding", "UTF-8", "-cp", str(JAR), str(ROOT / "tools/GephiStudy.java")], check=True)
    out = ROOT / "outputs/study"
    (out / "figures").mkdir(exist_ok=True)
    results = []
    for table in sorted((out / "tables").glob("*_networks.csv")):
        rows = pd.read_csv(table)
        for r in rows[rows["variant"] == "all_replies"].itertuples():
            stem = f"{r.pair}_{r.window}_{r.subreddit}_all_replies"
            full, focus = (out / "networks" / (stem + suffix) for suffix in ("_full.gexf", "_focus.gexf"))
            native = out / "networks" / (stem + "_native")
            result_file = Path(str(native) + "_validation.json")
            sha = hashlib.sha256(full.read_bytes() + focus.read_bytes() + (ROOT / "tools/GephiStudy.java").read_bytes()).hexdigest()
            reuse = False
            if result_file.exists():
                previous = json.loads(result_file.read_text())
                reuse = previous.get("source_sha256") == sha and Path(str(native) + ".gephi").exists()
            if not reuse:
                print(f"GEPHI {stem}", flush=True)
                subprocess.run(["java", "-Xmx3g", "-Djava.awt.headless=true", "-cp", str(JAR) + (";" if sys.platform == "win32" else ":") + str(ROOT / "tools"),
                    "GephiStudy", str(full), str(focus), str(native), str(r.nodes), str(r.edges), str(r.reply_events)], check=True)
                previous = json.loads(result_file.read_text())
                previous["source_sha256"] = sha
                result_file.write_text(json.dumps(previous, indent=2))
            image_path = Path(str(native) + ".png")
            (out / "figures" / f"gephi_{stem}.png").write_bytes(image_path.read_bytes())
            results.append({"pair": r.pair, "window": r.window, "subreddit": r.subreddit, **previous})
            pd.DataFrame(results).to_csv(out / "gephi_validation.csv", index=False)


if __name__ == "__main__":
    main()
