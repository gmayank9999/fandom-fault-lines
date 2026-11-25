import numpy as np
import pandas as pd
import pytest

from src.study_advanced import (participation_panel, transitions, persistence,
    standardized_retention, paired_sentiment, matched_connectors, bins)


def settings():
    return dict(seed=42, replicates=500, activity_bin_lower_bounds=[1, 2, 5, 10],
        degree_bin_lower_bounds=[0, 2, 5, 10], connector_top_k=2,
        paired_minimum_comments_per_category=[1, 3], paired_minimum_authors_for_interval=2)


def test_transitions_conserve_cohort_and_distinguish_sequential_overlap():
    first = pd.DataFrame({'author': ['persistent', 'persistent', 'switch', 'depart'],
                          'subreddit': ['A', 'B', 'A', 'A']})
    second = pd.DataFrame({'author': ['persistent', 'persistent', 'switch', 'new'],
                           'subreddit': ['A', 'B', 'B', 'B']})
    panel = participation_panel([first, second], {'communities': ['A', 'B']})
    rows = pd.DataFrame(transitions(panel, 1))
    assert rows.users.sum() == 4
    assert rows.query("origin_state == 'a_only' and destination_state == 'neither'").users.iloc[0] == 1
    assert rows.query("origin_state == 'neither' and destination_state == 'b_only'").users.iloc[0] == 1
    patterns = pd.DataFrame(persistence(panel, 1)).set_index('pattern')
    assert patterns.users.sum() == 2
    assert patterns.loc['both_in_each_window', 'users'] == 1
    assert patterns.loc['pooled_only_no_window_both', 'users'] == 1


def test_retention_adjustment_removes_activity_composition_difference():
    # Both group mostly high activity, exclusive group mostly low activity;
    # identical return probabilities inside each activity stratum.
    rows = []
    for both, low_n, high_n in [(True, 10, 90), (False, 90, 10)]:
        for n, total, return_rate in [(low_n, 2, .2), (high_n, 10, .8)]:
            for i in range(n):
                rows.append(dict(w0_a=total-1 if both else total, w0_b=1 if both else 0,
                                 w1_a=int(i < n*return_rate), w1_b=0))
    results, detail = standardized_retention(pd.DataFrame(rows), settings())
    row = next(r for r in results if r['reference'] == 'a_only' and r['outcome'] == 'observed_in_pair')
    assert row['raw_both_pct'] > row['raw_exclusive_pct'] + 40
    assert row['adjusted_difference_pp'] == pytest.approx(0)
    assert row['common_both_users'] == row['common_exclusive_users'] == 100
    assert bins([1, 2, 4, 5, 10], [1, 2, 5, 10]).tolist() == [0, 1, 1, 2, 3]


def test_paired_sentiment_gives_authors_equal_weight_and_excludes_unpaired():
    rows = []
    for author, count, own, rival in [('heavy', 100, 1., 0.), ('light', 1, -1., 0.)]:
        for target, score in [('self_talk', own), ('rival_talk', rival)]:
            rows.extend(dict(author=author, window='sep', subreddit='A', target=target,
                             vader=score, vader_adapted=score) for _ in range(count))
    rows.append(dict(author='unpaired', window='sep', subreddit='A', target='self_talk', vader=1., vader_adapted=1.))
    result = paired_sentiment(pd.DataFrame(rows), settings())[0]
    assert result['paired_authors'] == 2
    assert result['author_equal_weight_difference'] == 0
    assert result['same_authors_comment_weighted_difference'] == pytest.approx(99/101)
    assert result['ci_low'] <= 0 <= result['ci_high']


def test_connector_null_matches_strata_and_handles_deterministic_groups():
    nodes = pd.DataFrame(dict(observed_commenter=[True]*10, shared_in_pair=[True]*2+[False]*8,
        comment_count=[20]*2+[1]*8, in_degree=[20]*2+[1]*8, out_degree=[2]*10,
        betweenness=[.9, .8]+[.1]*8))
    row = matched_connectors(nodes, settings(), 'activity_and_degree')
    assert row['observed_shared'] == row['expected_shared'] == 2
    assert row['enrichment_p'] == 1 and row['excess_pp'] == 0
    nodes['comment_count'] = 2
    row = matched_connectors(nodes, settings(), 'activity')
    assert row['expected_shared'] == pytest.approx(.4)
    assert row['excess_pp'] == pytest.approx(80)
    assert row['enrichment_p'] >= 1 / (settings()['replicates'] + 1)
    nodes['betweenness'] = 0
    assert matched_connectors(nodes, settings(), 'activity')['selected_users'] == 0


def test_advanced_pipeline_outputs_and_report_rejects_changed_results(tmp_path, monkeypatch):
    import json
    import src.study_advanced as advanced
    from src.study_advanced_report import section
    from src.study_report import markdown_table
    private = tmp_path / 'private'
    private.mkdir()
    (tmp_path / 'figures').mkdir()
    design = dict(output_dir=str(tmp_path), pairs=[dict(id='pair', communities=['A','B'])],
        windows=[dict(id='sep', start='2026-09-03'), dict(id='oct', start='2026-10-01')])
    options = dict(settings(), activity_thresholds=[1,2,5], connector_variants=['all_replies','comment_replies'],
                   connector_matching=['activity','activity_and_degree'])
    raw = pd.DataFrame(dict(author=['shared','shared','onlya','onlyb'], subreddit=['A','B','A','B']))
    monkeypatch.setattr(advanced, 'load_window', lambda *a, **kw: raw.copy())
    monkeypatch.setattr(advanced, 'anonymize', lambda value: value)
    content = []
    nodes = pd.DataFrame(dict(observed_commenter=[True]*3, shared_in_pair=[True,False,False],
        comment_count=[2,2,2], in_degree=[2,1,1], out_degree=[1,1,1], betweenness=[.5,.2,.1]))
    for window in ['sep','oct']:
        for sub in ['A','B']:
            for variant in options['connector_variants']:
                nodes.to_csv(private / f'pair_{window}_{sub}_{variant}_centrality.csv', index=False)
            for author in ['shared','onlya','onlyb']:
                for target, score in [('self_talk',.5),('rival_talk',.2)]:
                    content.append(dict(window=window, subreddit=sub, author=author, target=target,
                                        vader=score, vader_adapted=score))
    pd.DataFrame(content).to_csv(private / 'pair_content.csv.gz', index=False)
    advanced.run(design, options)
    folder = tmp_path / 'advanced'
    assert len(pd.read_csv(folder / 'transitions.csv')) == 48
    assert len(pd.read_csv(folder / 'paired_sentiment.csv')) == 32
    assert len(pd.read_csv(folder / 'matched_connectors.csv')) == 16
    assert (pd.read_csv(folder / 'matched_connectors.csv').enrichment_p_holm <= 1).all()
    manifest = json.loads((folder / 'manifest.json').read_text())
    assert len(manifest['outputs_sha256']) == 6
    for output in folder.glob('*.csv'):
        output.write_bytes(output.read_text(encoding='utf-8').replace('\n', '\r\n').encode('utf-8'))
    assert 'paired authors' in '\n'.join(section(tmp_path, markdown_table)).lower()
    result = folder / 'retention.csv'
    result.write_bytes(result.read_bytes() + b'\n')
    with pytest.raises(ValueError, match='checksum mismatch'):
        section(tmp_path, markdown_table)
