import os
import sys
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.utils import setup_logger

logger = setup_logger("overlap_analysis")


def main():
    comments = pd.read_csv(config.CLEAN_COMMENTS_PATH)
    subs = comments["subreddit"].unique()

    if len(subs) != 2:
        logger.error(f"Expected exactly 2 subreddits, found {len(subs)}. Aborting overlap analysis.")
        return

    sub_a, sub_b = subs[0], subs[1]
    users_a = set(comments[comments["subreddit"] == sub_a]["author"]) - {"[deleted]"}
    users_b = set(comments[comments["subreddit"] == sub_b]["author"]) - {"[deleted]"}

    overlap = users_a & users_b
    union = users_a | users_b

    logger.info(f"Unique commenters in r/{sub_a}: {len(users_a)}")
    logger.info(f"Unique commenters in r/{sub_b}: {len(users_b)}")
    logger.info(f"Users active in BOTH: {len(overlap)}")
    logger.info(f"Overlap as % of r/{sub_a}: {100*len(overlap)/max(len(users_a),1):.2f}%")
    logger.info(f"Overlap as % of r/{sub_b}: {100*len(overlap)/max(len(users_b),1):.2f}%")
    logger.info(f"Jaccard index (overlap / union): {100*len(overlap)/max(len(union),1):.2f}%")

    pd.DataFrame({"overlapping_user": list(overlap)}).to_csv(config.OVERLAP_PATH, index=False)


if __name__ == "__main__":
    main()
