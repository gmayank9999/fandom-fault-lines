import argparse
import sys

from src import (collect_posts, collect_comments, preprocess, eda, topic_modeling,
                  sentiment, statistical_tests, network_build, network_analysis, overlap_analysis)

STAGES = {
    "collect_posts": collect_posts.main,
    "collect_comments": collect_comments.main,
    "preprocess": preprocess.main,
    "eda": eda.main,
    "topic_modeling": topic_modeling.main,
    "sentiment": sentiment.main,
    "statistical_tests": statistical_tests.main,
    "network_build": network_build.main,
    "network_analysis": network_analysis.main,
    "overlap_analysis": overlap_analysis.main,
}

ORDER = ["collect_posts", "collect_comments", "preprocess", "eda", "topic_modeling",
          "sentiment", "statistical_tests", "network_build", "network_analysis", "overlap_analysis"]


def main():
    parser = argparse.ArgumentParser(description="Fandom Fault Lines pipeline runner")
    parser.add_argument("--stage", choices=list(STAGES.keys()) + ["all"], default="all",
                         help="Which stage to run. Default: all (runs every stage in order).")
    args = parser.parse_args()

    if args.stage == "all":
        for stage_name in ORDER:
            print(f"\n{'='*20} Running stage: {stage_name} {'='*20}")
            STAGES[stage_name]()
    else:
        STAGES[args.stage]()


if __name__ == "__main__":
    main()
