# Extended study: persistence and adjusted comparisons

The initial comparative study measured overlap, sentiment and reply topology.
This extension asks whether overlap persists, whether the same authors express
different overall sentiment across comment categories, and whether apparent
connector representation survives activity adjustment. It uses the existing
56-day corpus. It does not seek a particular direction or a significant result.

## Design and provenance

`advanced_study.json` records settings written before executing the extension.
The extension was motivated by inspecting the first study and is exploratory,
not preregistered. All specified sensitivities are published, including null and
inconvenient outcomes. The manifest records the analysis source, participation
panel fingerprints, content/centrality input hashes and aggregate output hashes.
The report checks output hashes before including the extension.
Public text hashes normalize line endings so Windows and Linux checkouts agree.
`python tools/verify_advanced.py` also reconciles transitions with the original
overlap totals and checks standardized estimates and denominators; CI runs it.

```powershell
.\venv\Scripts\python.exe run_study.py --stage advanced
.\venv\Scripts\python.exe run_study.py --stage report
```

The advanced stage needs the original raw caches and completed pair analyses.
It does not rerun expensive full-network metrics or overwrite annotation sheets.
The original result tables remain intact.

## Participation persistence

For each pair, construct the union of observed users across the two windows.
Classify each window as A-only, B-only, both or neither at thresholds 1, 2 and 5
comments per community. Publish every transition count and row percentage.
At threshold one, neither means no observed activity in this pair. Neither-to-
neither is a structural zero because the cohort is observed somewhere. At higher
thresholds, neither means below threshold and can include active users.

Decompose pooled shared users into four disjoint patterns: shared in both
windows, first only, second only, or neither separately. At threshold one the
last group participates sequentially across the two communities; at higher
thresholds it can also result from accumulating comments across windows.
Pooled percentages and first-window cohort return percentages have different
denominators. Neither identifies fan allegiance or Reddit-wide attrition.

## Activity-standardized return rates

Compare first-window shared users against A-only and B-only users separately.
Outcomes are a second-window appearance anywhere in the pair or in both
communities. Group assignment uses only the first window, avoiding classification
using the future outcome.

Fixed first-window total-comment bins are 1, 2–4, 5–9, 10–19, 20–49, 50–99 and
100+. Retain bins containing both groups and weight their return probabilities
by the pooled distribution in that comparison's common-support population.
Publish stratum sizes/successes, raw rates, adjusted rates, differences and
included cohort sizes. One-comment exclusive users have no shared-user
counterparts and are excluded from the adjusted target. Do not interpret the
raw-adjusted change solely as removing confounding in an unchanged population.

Use 5,000 independent binary-user bootstrap draws within each fixed group/bin
(equivalently binomial draws), holding standardization weights fixed. Percentile
95% intervals are descriptive and unadjusted for multiplicity. Coarse bins,
unobserved interests, activity elsewhere and shared events remain possible
explanations. This is not a causal treatment effect or a measure of platform churn.

## Within-author sentiment

Within each community-period, retain authors with both own-franchise-only and
rival-category comments. Calculate each author's two category means and their
difference, then give authors equal weight. Also publish the comment-weighted
contrast on those same authors to expose weighting effects.

Retain original/adapted VADER, rival-only/any-rival definitions, and minimum
one/three comments in each category: 64 comparisons in total. Use 5,000 paired-
author percentile bootstrap draws and suppress intervals below 20 authors.
Intervals are unadjusted and are not labelled statistically significant. Authors
are resampled with their paired differences intact; thread dependence remains.
The eligible author population differs from the original all-comment contrast.
Within-author comparison does not solve sarcasm, target stance, timing or topic
confounding. It cannot replace human annotation.

The resampling principle follows the paired-observation distinction documented
in [SciPy's bootstrap reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).
The implementation uses bounded batches of NumPy draws over author differences.

## Activity- and degree-matched connector representation

Select the top 20 positive betweenness scores among observed commenters, retaining
every cutoff tie. Parent-only nodes are outside this population. Compare observed
shared-user counts with random selections that preserve the number selected from
each stratum. Match by comment activity alone and by activity plus total directed
degree. Degree is in-degree plus out-degree, with bin lower bounds 0, 2, 5, 10,
20, 50, 100 and 200. Reciprocal partners count in both directed degrees.

Within each stratum, draw the shared-user count from a hypergeometric distribution;
sum across strata for 5,000 null draws. Report exact expected counts, randomized
count ranges, effects in percentage points, and a one-sided plus-one corrected
enrichment probability. Apply Holm across all 32 comparisons: two pairs, two
windows, two communities, two graph variants, two matching definitions.

This tests a conditional exchangeability model within coarse strata. It does not
identify an effect of cross-participation or prove information flows between
subreddits. Selection is small and may have low power. Betweenness is approximate;
the original two-seed stability diagnostic remains relevant. See
[NetworkX's betweenness definition](https://networkx.org/documentation/networkx-3.3/reference/algorithms/generated/networkx.algorithms.centrality.betweenness_centrality.html).

## Why these extensions

More communities would increase breadth, but would not resolve stable-author
differences, activity composition or transient overlap. These extensions directly
address those weaknesses. A causal echo-chamber claim still needs stronger
measurements of opinion similarity and exposure/diffusion. The distinction is
consistent with [Cinelli et al.'s interaction and diffusion framework](https://doi.org/10.1073/pnas.2023301118).

Adding a more complex sentiment model without independent labels would not
establish target-specific accuracy. The existing human annotation protocol remains
the next necessary validation step for stronger attitude claims.
