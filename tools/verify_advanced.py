"""Check published extension aggregates against the original study totals."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    out = Path('outputs/study')
    folder = out / 'advanced'
    manifest = json.loads((folder / 'manifest.json').read_text())
    assert manifest['source_sha256'] == hashlib.sha256(Path('src/study_advanced.py').read_text(encoding='utf-8').encode()).hexdigest()
    for name, sha in manifest['outputs_sha256'].items():
        assert sha == hashlib.sha256((folder / name).read_text(encoding='utf-8').encode()).hexdigest(), name
    transitions = pd.read_csv(folder / 'transitions.csv')
    persistence = pd.read_csv(folder / 'persistence.csv')
    retention = pd.read_csv(folder / 'retention.csv')
    strata = pd.read_csv(folder / 'retention_strata.csv')
    paired = pd.read_csv(folder / 'paired_sentiment.csv')
    matched = pd.read_csv(folder / 'matched_connectors.csv')
    assert (len(transitions), len(persistence), len(retention), len(paired), len(matched)) == (96, 24, 8, 64, 32)
    for pair in transitions.pair.unique():
        overlap = pd.read_csv(out / 'tables' / f'{pair}_overlap.csv')
        for threshold in [1, 2, 5]:
            t = transitions[(transitions.pair == pair) & (transitions.min_comments == threshold)]
            p = persistence[(persistence.pair == pair) & (persistence.min_comments == threshold)]
            o = overlap[overlap.min_comments == threshold].set_index('window')
            assert p.users.sum() == o.loc['pooled_56d', 'shared']
            assert t[t.origin_state == 'both'].users.sum() == o.loc['sep', 'shared']
            assert t[t.destination_state == 'both'].users.sum() == o.loc['oct', 'shared']
            assert np.allclose(t.groupby('origin_state').users.sum(), t.groupby('origin_state').origin_users.first())
            positive = t[t.origin_users > 0]
            assert np.allclose(positive.groupby('origin_state').origin_pct.sum(), 100)
    for r in retention.itertuples():
        x = strata[(strata.pair == r.pair) & (strata.reference == r.reference) & (strata.outcome == r.outcome)]
        assert x.both_users.sum() == r.both_users and x.exclusive_users.sum() == r.exclusive_users
        common = x[x.common_support]
        assert common.both_users.sum() == r.common_both_users
        assert common.exclusive_users.sum() == r.common_exclusive_users
        weights = (common.both_users + common.exclusive_users) / (common.both_users + common.exclusive_users).sum()
        expected = 100 * (weights * (common.both_returned/common.both_users - common.exclusive_returned/common.exclusive_users)).sum()
        assert np.isclose(expected, r.adjusted_difference_pp)
        assert r.ci_low_pp <= r.adjusted_difference_pp <= r.ci_high_pp
    assert ((matched.enrichment_p_holm >= matched.enrichment_p) & (matched.enrichment_p_holm <= 1)).all()
    assert (paired.own_comments >= paired.paired_authors * paired.min_per_category).all()
    assert (paired.rival_comments >= paired.paired_authors * paired.min_per_category).all()
    assert paired.loc[paired.paired_authors < 20, ['ci_low','ci_high']].isna().all().all()
    print('PASS: extension hashes, 96 transition cells, pooled/monthly cohort conservation,')
    print('common-support standardization, 64 paired-author contrasts and 32 corrected connector comparisons.')


if __name__ == '__main__':
    main()
