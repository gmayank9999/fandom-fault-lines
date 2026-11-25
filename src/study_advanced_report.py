"""Figures and interpretation for the separately specified exploratory extension."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def section(out, table):
    folder = Path(out) / 'advanced'
    if not (folder / 'manifest.json').exists():
        return []
    import hashlib
    import json
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['outputs_sha256'].items():
        if hashlib.sha256((folder / name).read_text(encoding='utf-8').encode()).hexdigest() != expected:
            raise ValueError(f'Advanced result checksum mismatch: {name}; rerun --stage advanced')
    transition = pd.read_csv(folder / 'transitions.csv')
    persistence = pd.read_csv(folder / 'persistence.csv')
    retention = pd.read_csv(folder / 'retention.csv')
    paired = pd.read_csv(folder / 'paired_sentiment.csv')
    connectors = pd.read_csv(folder / 'matched_connectors.csv')
    figures = Path(out) / 'figures'
    pairs = list(transition.pair.unique())
    names = {'superheroes': ('Marvel', 'DC'), 'consoles': ('PS5', 'Xbox')}
    states = ['neither', 'a_only', 'b_only', 'both']
    labels = ['Below threshold\nin both', 'A only', 'B only', 'Both']
    fig, axes = plt.subplots(1, len(pairs), figsize=(6 * len(pairs), 5), squeeze=False)
    for ax, pair in zip(axes[0], pairs):
        a, b = names.get(pair, ('A', 'B'))
        labels = ['No observed\nactivity', f'{a} only', f'{b} only', 'Both']
        rows = transition[(transition.pair == pair) & (transition.min_comments == 1)]
        matrix = rows.pivot(index='origin_state', columns='destination_state', values='origin_pct').reindex(index=states, columns=states)
        ax.imshow(matrix, vmin=0, vmax=100, cmap='Blues')
        for i in range(4):
            for j in range(4):
                val = matrix.iloc[i, j]
                ax.text(j, i, f'{val:.1f}%', ha='center', va='center', color='white' if val > 55 else '#18212b')
        ax.set_xticks(range(4), labels, fontsize=9)
        ax.set_yticks(range(4), labels, fontsize=9)
        ax.set_xlabel('Second window'); ax.set_ylabel('First window')
        ax.set_title(f'{pair}: participation transitions\nRow percentages; minimum one comment', fontsize=11)
    fig.tight_layout(); fig.savefig(figures / 'participation_transitions.png', dpi=180); plt.close(fig)

    primary = retention[retention.outcome == 'observed_in_pair'].copy()
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    positions = np.arange(len(primary))
    for ax, prefix, title in zip(axes, ['raw', 'adjusted'], ['Observed return rates', 'Standardized for first-window activity']):
        ax.barh(positions-.17, primary[prefix+'_both_pct'], .34, label='Initially both', color='#2563a6')
        ax.barh(positions+.17, primary[prefix+'_exclusive_pct'], .34, label='Initially exclusive', color='#c35b26')
        ax.set_yticks(positions, [f"{r.pair}: both vs {names.get(r.pair, ('A','B'))[int(r.reference == 'b_only')]} only"
                                for r in primary.itertuples()], fontsize=9)
        ax.set_xlim(0,100); ax.set_xlabel('Observed again anywhere in the pair (%)'); ax.set_title(title)
        ax.set_ylim(-.6, len(primary)+.2)
        ax.legend(frameon=False, fontsize=9)
    fig.tight_layout(); fig.savefig(figures / 'activity_adjusted_retention.png', dpi=180); plt.close(fig)

    main = paired[(paired.scorer == 'vader_adapted') & (paired.contrast == 'any_rival_mention') & (paired.min_per_category == 1)]
    fig, ax = plt.subplots(figsize=(10, 5))
    for y, r in enumerate(main.itertuples()):
        ax.plot([r.ci_low, r.ci_high], [y, y], color='#2563a6', linewidth=2)
        ax.scatter([r.author_equal_weight_difference], [y], color='#2563a6', s=30)
    ax.set_yticks(range(len(main)), [f'{r.subreddit}, {r.window} (n={r.paired_authors})' for r in main.itertuples()])
    ax.axvline(0,color='#666',linewidth=1)
    ax.set_xlabel('Within-author mean sentiment: own-only minus rival-mentioning')
    ax.set_title('Paired authors; unadjusted descriptive 95% bootstrap intervals', fontsize=11)
    fig.tight_layout(); fig.savefig(figures / 'within_author_sentiment.png', dpi=180); plt.close(fig)

    matched = connectors[(connectors.variant == 'all_replies') & (connectors.matching == 'activity_and_degree')]
    fig, ax = plt.subplots(figsize=(10, 5))
    y = np.arange(len(matched))
    ax.barh(y-.17, matched.observed_shared_pct, .34, label='Observed among top betweenness', color='#2563a6')
    ax.barh(y+.17, matched.matched_expected_shared_pct, .34, label='Activity + degree matched expectation', color='#c35b26')
    ax.set_yticks(y, [f'{r.subreddit}, {r.window}' for r in matched.itertuples()]); ax.set_xlim(0,100)
    ax.set_xlabel('Shared participants in selected set (%)'); ax.legend(frameon=False, fontsize=9)
    ax.set_title('Connector representation after conditioning on activity and degree', fontsize=11)
    fig.tight_layout(); fig.savefig(figures / 'matched_connectors.png', dpi=180); plt.close(fig)

    result = ['## Extended analysis: persistence, composition and connector roles',
        'These analyses were specified in `advanced_study.json` after inspecting the original results and before '
        'running this extension. They are exploratory, not preregistered. All use the existing two observation windows; '
        'they do not add new communities or establish a causal effect of rivalry.',
        '### Are shared audiences persistent?',
        'A/B follow `study.json`: Marvel/DC and PS5/xbox. Each person in the union of the two windows is classified '
        'by their observed activity in each period. The neither-to-neither cell is a structural zero at the one-comment '
        'threshold because this is an observed union cohort. The first-window neither row describes later arrivals; '
        'it is not a return rate for all Reddit users. At stricter thresholds, neither means below threshold in both communities.',
        '![Participation transitions](outputs/study/figures/participation_transitions.png)',
        table(persistence[persistence.min_comments == 1][['pair','pattern','users','pct_pooled_shared']]),
        'Pooled overlap is decomposed into users active in both communities in each window, in just one window, '
        'or only across the combined period. At threshold one, the last category represents sequential participation '
        'with no within-window overlap; at higher thresholds it can also reflect activity accumulating across periods. '
        'Results at two and five comments per community are retained in the extension tables. Absence means no observed '
        'activity in this pair during that window, not leaving Reddit or changing allegiance.',
        'The persistent percentage above uses all pooled shared users as its denominator. A different question is '
        'what fraction of first-window shared users are shared again: read the both-to-both cell of the transition '
        'matrix for that conditional percentage. These denominators must not be interchanged.',
        '### Does the return-rate difference survive activity adjustment?',
        table(primary[['pair','reference','raw_both_pct','raw_exclusive_pct','adjusted_both_pct','adjusted_exclusive_pct',
                       'adjusted_difference_pp','ci_low_pp','ci_high_pp']]),
        '![Adjusted retention](outputs/study/figures/activity_adjusted_retention.png)',
        'Both versus A-only and both versus B-only are separate first-window cohort comparisons. Return means at least '
        'one observed comment anywhere in the pair during the second window. Adjustment uses fixed bins of total '
        'first-window comments: 1, 2–4, 5–9, 10–19, 20–49, 50–99, and 100+. Each comparison uses the pooled '
        'activity distribution of groups within common-support bins as its target. The groups differ in their raw '
        'activity composition; users outside common support do not contribute to adjusted rates. Counts and exclusions '
        'are in retention.csv and retention_strata.csv. Intervals resample binary outcomes within fixed group/bin '
        'sample sizes, with weights held fixed (5,000 draws). These are unadjusted descriptive 95% intervals. '
        'Coarse bins leave residual confounding; this association does not show that cross-participation causes retention.',
        table(primary[['pair','reference','both_users','exclusive_users','common_both_users','common_exclusive_users']]),
        'In particular, an initially shared user must have at least two comments. One-comment exclusive users '
        'have no shared-user counterpart and are excluded from the standardized target. Thus raw-versus-adjusted '
        'differences reflect both activity standardization and a restriction to common support.',
        '### Does the sentiment difference persist within the same authors?',
        table(main[['window','subreddit','paired_authors','author_equal_weight_difference','ci_low','ci_high']]),
        '![Within-author sentiment](outputs/study/figures/within_author_sentiment.png)',
        'Only authors with both own-only and rival-mentioning comments in the same community-period enter this comparison. '
        'Each author contributes one difference between their category mean scores, and authors receive equal weight. '
        'This addresses stable differences between authors and prolific-user weighting, while changing the population '
        'to authors who wrote both kinds of comment. It does not control topic, thread, timing, sarcasm or target stance. '
        'The 95% percentile intervals resample paired authors 5,000 times; they are not adjusted for multiple comparisons '
        'and are not labelled significant. Original/adapted VADER, rival-only/any-rival definitions, and minimum '
        'one/three comments in each category are all retained. Fewer than 20 eligible authors yields no interval.',
        '### Are cross-participants unusually common among connectors after matching?',
        table(matched[['window','subreddit','selected_users','observed_shared_pct','matched_expected_shared_pct',
                       'excess_pp','enrichment_p_holm']]),
        '![Matched connector comparison](outputs/study/figures/matched_connectors.png)',
        'Selection uses the top 20 positive betweenness scores among observed commenters, retaining cutoff ties. '
        'Within fixed bins of comment count and total directed degree (in-degree plus out-degree), random selections '
        'preserve the number selected from every stratum. The sum of stratum-specific hypergeometric draws gives a '
        'conditional null for the number of shared participants. Degree bin lower bounds are 0, 2, 5, 10, 20, 50, '
        '100 and 200. The one-sided enrichment probability uses a plus-one correction and 5,000 draws; Holm adjustment '
        'covers all 32 community-period/network-variant/matching comparisons. Activity-only matching and comment-only '
        'networks are retained as sensitivities. Exchangeability within coarse bins is an assumption, not random assignment. '
        'Matching cannot remove unmeasured differences, and approximate betweenness ranking uncertainty remains. '
        'The null ranges describe randomized selected counts, not confidence intervals for population effects. '
        'A top-20 selection has limited power; failure to detect enrichment does not establish equivalence or no role for shared users.']
    for pair in pairs:
        p = persistence[(persistence.pair == pair) & (persistence.min_comments == 1)].set_index('pattern')
        result.append(f"**{pair}:** {int(p.loc['both_in_each_window','users']):,} of "
            f"{int(p.iloc[0].pooled_shared_users):,} pooled shared users appear in both communities in each window "
            f"({p.loc['both_in_each_window','pct_pooled_shared']:.1f}%). "
            f"{p.loc['pooled_only_no_window_both','pct_pooled_shared']:.1f}% have only sequential cross-window participation.")
    supported = int((connectors.enrichment_p_holm < .05).sum())
    result.append(f"Across all 32 specified connector comparisons, {supported} meet the Holm-adjusted .05 enrichment "
        'threshold. Read this together with the effect sizes and alternative matching definitions; an unadjusted '
        'top-20 percentage alone cannot establish unusual connector representation.')
    return result
