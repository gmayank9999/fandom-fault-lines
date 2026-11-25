"""Exploratory longitudinal, paired-author and activity-adjusted extensions."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.study_analysis import valid_users
from src.study_data import load_window, read_design
from src.statistical_tests import holm_correct
from src.utils import anonymize

STATES = ['neither', 'a_only', 'b_only', 'both']


def bins(values, lower):
    return np.searchsorted(lower, np.asarray(values), side='right') - 1


def participation_panel(frames, pair):
    """One union cohort, retaining zero counts in either observation window."""
    parts = []
    for i, frame in enumerate(frames):
        counts = frame.groupby(['author', 'subreddit']).size().unstack(fill_value=0)
        counts = counts.reindex(columns=pair['communities'], fill_value=0)
        counts.columns = [f'w{i}_a', f'w{i}_b']
        parts.append(counts)
    return pd.concat(parts, axis=1).fillna(0).astype(int)


def state(panel, window, threshold=1):
    a, b = panel[f'w{window}_a'] >= threshold, panel[f'w{window}_b'] >= threshold
    return pd.Series(np.select([a & b, a, b], ['both', 'a_only', 'b_only'], default='neither'), index=panel.index)


def transitions(panel, threshold):
    before, after = state(panel, 0, threshold), state(panel, 1, threshold)
    counts = pd.crosstab(before, after).reindex(index=STATES, columns=STATES, fill_value=0)
    rows = []
    for source in STATES:
        total = int(counts.loc[source].sum())
        for destination in STATES:
            count = int(counts.loc[source, destination])
            rows.append(dict(min_comments=threshold, origin_state=source, destination_state=destination,
                users=count, origin_users=total, origin_pct=100 * count / total if total else np.nan))
    return rows


def persistence(panel, threshold):
    pooled_shared = ((panel.w0_a + panel.w1_a) >= threshold) & ((panel.w0_b + panel.w1_b) >= threshold)
    first, second = state(panel, 0, threshold).eq('both'), state(panel, 1, threshold).eq('both')
    groups = {'both_in_each_window': first & second, 'both_first_window_only': first & ~second,
              'both_second_window_only': ~first & second, 'pooled_only_no_window_both': ~first & ~second}
    denominator = int(pooled_shared.sum())
    return [dict(min_comments=threshold, pattern=name, users=int((mask & pooled_shared).sum()),
        pooled_shared_users=denominator, pct_pooled_shared=100 * (mask & pooled_shared).sum() / denominator if denominator else np.nan)
        for name, mask in groups.items()]


def standardized_retention(panel, settings):
    before, after = state(panel, 0), state(panel, 1)
    band = bins(panel.w0_a + panel.w0_b, settings['activity_bin_lower_bounds'])
    rng = np.random.default_rng(settings['seed'])
    rows, details = [], []
    for reference in ['a_only', 'b_only']:
        for outcome, values in [('observed_in_pair', after.ne('neither')), ('observed_in_both', after.eq('both'))]:
            blocks = []
            for level in sorted(set(band[before.isin(['both', reference])])):
                a, b = (before.eq('both') & (band == level)), (before.eq(reference) & (band == level))
                na, nb = int(a.sum()), int(b.sum())
                ya, yb = int(values[a].sum()), int(values[b].sum())
                details.append(dict(reference=reference, outcome=outcome, activity_bin=int(level),
                    both_users=na, exclusive_users=nb, both_returned=ya, exclusive_returned=yb, common_support=bool(na and nb)))
                if na and nb:
                    blocks.append((na, nb, ya / na, yb / nb))
            base = dict(reference=reference, outcome=outcome, both_users=int(before.eq('both').sum()),
                exclusive_users=int(before.eq(reference).sum()), raw_both_pct=100 * values[before.eq('both')].mean(),
                raw_exclusive_pct=100 * values[before.eq(reference)].mean())
            if not blocks:
                rows.append(dict(**base, common_both_users=0, common_exclusive_users=0,
                    adjusted_both_pct=np.nan, adjusted_exclusive_pct=np.nan, adjusted_difference_pp=np.nan,
                    ci_low_pp=np.nan, ci_high_pp=np.nan))
                continue
            x = np.array(blocks)
            weights = (x[:, 0] + x[:, 1]) / (x[:, 0] + x[:, 1]).sum()
            estimates = (weights[:, None] * x[:, 2:]).sum(axis=0)
            draws = np.zeros(settings['replicates'])
            for weight, (na, nb, pa, pb) in zip(weights, blocks):
                # Resampling binary users within each fixed group/bin is binomial.
                draws += weight * (rng.binomial(na, pa, len(draws)) / na - rng.binomial(nb, pb, len(draws)) / nb)
            low, high = np.quantile(draws, [.025, .975])
            rows.append(dict(**base, common_both_users=int(x[:, 0].sum()),
                common_exclusive_users=int(x[:, 1].sum()), adjusted_both_pct=100 * estimates[0],
                adjusted_exclusive_pct=100 * estimates[1], adjusted_difference_pp=100 * (estimates[0] - estimates[1]),
                ci_low_pp=100 * low, ci_high_pp=100 * high))
    return rows, details


def paired_sentiment(content, settings):
    rng = np.random.default_rng(settings['seed'])
    rows = []
    for (window, sub), group in content.groupby(['window', 'subreddit']):
        for scorer in ['vader', 'vader_adapted']:
            for contrast, targets in [('rival_only', ['rival_talk']), ('any_rival_mention', ['rival_talk', 'both'])]:
                a = group[group.target == 'self_talk'].groupby('author')[scorer].agg(['mean', 'count', 'sum'])
                b = group[group.target.isin(targets)].groupby('author')[scorer].agg(['mean', 'count', 'sum'])
                joined = a.join(b, how='inner', lsuffix='_a', rsuffix='_b')
                for minimum in settings['paired_minimum_comments_per_category']:
                    x = joined[(joined.count_a >= minimum) & (joined.count_b >= minimum)]
                    differences = (x.mean_a - x.mean_b).to_numpy()
                    n = len(x)
                    low, high = np.nan, np.nan
                    if n >= settings['paired_minimum_authors_for_interval']:
                        means = []
                        for start in range(0, settings['replicates'], 32):
                            indexes = rng.integers(0, n, size=(min(32, settings['replicates'] - start), n))
                            means.extend(differences[indexes].mean(axis=1))
                        low, high = np.quantile(means, [.025, .975])
                    rows.append(dict(window=window, subreddit=sub, scorer=scorer, contrast=contrast,
                        min_per_category=minimum, paired_authors=n, own_comments=int(x.count_a.sum()),
                        rival_comments=int(x.count_b.sum()), author_equal_weight_difference=differences.mean() if n else np.nan,
                        author_median_difference=np.median(differences) if n else np.nan,
                        same_authors_comment_weighted_difference=x.sum_a.sum()/x.count_a.sum()-x.sum_b.sum()/x.count_b.sum() if n else np.nan,
                        ci_low=low, ci_high=high, interval='unadjusted descriptive 95% paired-author percentile bootstrap'))
    return rows


def matched_connectors(nodes, settings, matching):
    data = nodes[nodes.observed_commenter.astype(str).str.lower().eq('true')].copy()
    positive = data.loc[data.betweenness > 0, 'betweenness'].sort_values(ascending=False)
    if positive.empty:
        return dict(selected_users=0, observed_shared=0, expected_shared=np.nan, enrichment_p=np.nan,
            observed_shared_pct=np.nan, matched_expected_shared_pct=np.nan, excess_pp=np.nan,
            null_low_shared=np.nan, null_high_shared=np.nan, deterministic_stratum_selected_users=0)
    cutoff = positive.iloc[min(settings['connector_top_k'], len(positive)) - 1]
    selected = data.betweenness.ge(cutoff) & data.betweenness.gt(0)
    shared = data.shared_in_pair.astype(str).str.lower().eq('true')
    activity = bins(data.comment_count, settings['activity_bin_lower_bounds'])
    degree = bins(data.in_degree + data.out_degree, settings['degree_bin_lower_bounds'])
    strata = pd.Series(activity.astype(str), index=data.index)
    if matching == 'activity_and_degree':
        strata += ':' + pd.Series(degree.astype(str), index=data.index)
    rng = np.random.default_rng(settings['seed'])
    draws = np.zeros(settings['replicates'], dtype=int)
    expected, fixed = 0., 0
    for indexes in strata.groupby(strata).groups.values():
        total, successes, take = len(indexes), int(shared.loc[indexes].sum()), int(selected.loc[indexes].sum())
        if not take:
            continue
        expected += take * successes / total
        draws += rng.hypergeometric(successes, total - successes, take, len(draws))
        if successes in (0, total) or take == total:
            fixed += take
    observed, count = int((selected & shared).sum()), int(selected.sum())
    low, high = np.quantile(draws, [.025, .975])
    return dict(selected_users=count, observed_shared=observed, expected_shared=expected,
        observed_shared_pct=100 * observed/count, matched_expected_shared_pct=100 * expected/count,
        excess_pp=100 * (observed-expected)/count, null_low_shared=float(low), null_high_shared=float(high),
        deterministic_stratum_selected_users=fixed,
        enrichment_p=(1+int((draws >= observed).sum()))/(len(draws)+1))


def run(design, settings):
    if len(design['windows']) != 2:
        raise ValueError('Extension requires exactly two ordered windows')
    windows = sorted(design['windows'], key=lambda w: w['start'])
    out = Path(design['output_dir'])
    folder = out / 'advanced'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'manifest.json').unlink(missing_ok=True)
    tables = {k: [] for k in ['transitions', 'persistence', 'retention', 'retention_strata', 'paired_sentiment', 'matched_connectors']}
    inputs = {}
    for pair in design['pairs']:
        print('ADVANCED', pair['id'], flush=True)
        frames = []
        for window in windows:
            raw = valid_users(load_window(window, pair['communities'], light=True))
            raw['author'] = raw.author.map(anonymize)
            frames.append(raw[['author', 'subreddit']])
        panel = participation_panel(frames, pair)
        inputs[pair['id'] + '_participation'] = hashlib.sha256(panel.sort_index().to_csv().encode()).hexdigest()
        for threshold in settings['activity_thresholds']:
            for name, values in [('transitions', transitions(panel, threshold)), ('persistence', persistence(panel, threshold))]:
                tables[name].extend(dict(pair=pair['id'], **r) for r in values)
        retention, details = standardized_retention(panel, settings)
        for name, values in [('retention', retention), ('retention_strata', details)]:
            tables[name].extend(dict(pair=pair['id'], **r) for r in values)
        content_path = out / 'private' / f"{pair['id']}_content.csv.gz"
        inputs[content_path.name] = hashlib.sha256(content_path.read_bytes()).hexdigest()
        content = pd.read_csv(content_path, usecols=['author', 'window', 'subreddit', 'target', 'vader', 'vader_adapted'])
        tables['paired_sentiment'].extend(dict(pair=pair['id'], **r) for r in paired_sentiment(content, settings))
        for window in windows:
            for sub in pair['communities']:
                for variant in settings['connector_variants']:
                    path = out / 'private' / f"{pair['id']}_{window['id']}_{sub}_{variant}_centrality.csv"
                    inputs[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                    nodes = pd.read_csv(path)
                    for matching in settings['connector_matching']:
                        tables['matched_connectors'].append(dict(pair=pair['id'], window=window['id'], subreddit=sub,
                            variant=variant, matching=matching, **matched_connectors(nodes, settings, matching)))
    matched = pd.DataFrame(tables['matched_connectors'])
    matched['enrichment_p_holm'] = holm_correct(matched.enrichment_p.tolist())
    tables['matched_connectors'] = matched
    for name, values in tables.items():
        pd.DataFrame(values).to_csv(folder / (name + '.csv'), index=False)
    manifest = dict(settings=settings, windows=windows, inputs_sha256=inputs,
        checksum_encoding='Source and public CSV: UTF-8 text with universal newlines; private file inputs: raw bytes',
        source_sha256=hashlib.sha256(Path(__file__).read_text(encoding='utf-8').encode()).hexdigest(),
        outputs_sha256={p.name: hashlib.sha256(p.read_text(encoding='utf-8').encode()).hexdigest() for p in folder.glob('*.csv')})
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('COMPLETE advanced study', flush=True)


if __name__ == '__main__':
    run(read_design(), json.loads(Path('advanced_study.json').read_text()))
