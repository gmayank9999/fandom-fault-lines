import argparse

from src import (collect_posts, collect_comments, collect_full, collect_parents, preprocess, eda, topic_modeling,
                 sentiment, statistical_tests, network_build, network_analysis,
                 overlap_analysis, connector_analysis, visualize, gold_set, replication, gephi_export)

STAGES = {
    "collect_posts": collect_posts.main,
    "collect_comments": collect_comments.main,       # legacy: time-slot SAMPLE, kept for reference
    "collect_full": lambda: collect_full.main([]),    # don't reparse the runner's arguments
    "collect_parents": collect_parents.main,
    "preprocess": preprocess.main,
    "eda": eda.main,
    "topic_modeling": topic_modeling.main,
    "sentiment": sentiment.main,
    "statistical_tests": statistical_tests.main,
    "network_build": network_build.main,
    "network_analysis": network_analysis.main,
    "overlap_analysis": overlap_analysis.main,
    "connector_analysis": connector_analysis.main,
    "visualize": visualize.main,
    "gold_eval": gold_set.main,                        # scorer validation against the hand-labelled set
    "replication": replication.main,                   # second-window check (needs data/raw/full_<date>/)
    "gephi_export": gephi_export.main,
}

ORDER = ["collect_posts", "collect_full", "collect_parents", "preprocess", "eda", "topic_modeling",
         "sentiment", "gold_eval", "statistical_tests", "network_build", "network_analysis",
         "overlap_analysis", "connector_analysis", "visualize", "gephi_export", "replication"]


def main():
    parser = argparse.ArgumentParser(description="Fandom Fault Lines pipeline runner")
    parser.add_argument("--stage", choices=list(STAGES.keys()) + ["all"], default="all",
                        help="Which stage to run. Default: all (runs every stage in order).")
    parser.add_argument("--skip-collection", action="store_true",
                        help="With --stage all: reuse the existing raw CSVs instead of re-downloading.")
    args = parser.parse_args()

    if args.stage == "all":
        for stage_name in ORDER:
            if args.skip_collection and stage_name.startswith("collect_"):
                continue
            print(f"\n{'=' * 20} Running stage: {stage_name} {'=' * 20}")
            STAGES[stage_name]()
    else:
        STAGES[args.stage]()


if __name__ == "__main__":
    main()
