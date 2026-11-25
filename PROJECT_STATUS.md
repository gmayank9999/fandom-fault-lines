# Project audit and delivery status

## Assessment

The project had a functioning modular pilot and 43 passing tests, but the working
tree mixed three generations of outputs: an older sampled report, full-window
analysis results, and unfinished replication work. It was not a coherent final
submission. The main weaknesses were measurement validity and stale reporting,
not a failure to find a sufficiently dramatic rivalry effect.

## Audit findings and work performed

| Finding | Action |
|---|---|
| Latest-per-slot sampling missed most comments and reply edges | Current study uses expected full archive day files; adds sampling/duration sensitivity |
| Report still claimed ~5% overlap despite newer full-data results | Superseded report archived; current report generated from aggregate tables |
| One pair and one short period | Added console-brand comparison and two consecutive 28-day windows |
| Partial replication could be analyzed as a full window | Exact expected filenames and UTC-boundary checks |
| Collector could silently return after a page cap or API failure | Fail explicitly; incomplete days are not installed |
| Orchestrator passed its CLI arguments into the collector parser | Collector receives its own empty argument list |
| Missing authors could become a single `nan` user | Missing/deleted/bot authors filtered explicitly |
| Reciprocal directed weights lost during undirected conversion | Explicit sum of both directions |
| Weighted observed modularity compared with partly unweighted rewires | Equivalent unweighted topology/null comparison; weighted modularity reported separately |
| Isolated observed commenters disappeared | Retained as nodes |
| Connector role conflated with starting popular threads | Comment-only sensitivity graphs and additional centrality/breadth attributes |
| Whole-comment sentiment interpreted as rival stance | Explicit distinction; both lexicon variants reported as sensitivities |
| AI labels described as hand-labelled validation | Label provenance disclosed; human protocol supplied; population stance extrapolation removed |
| Large bootstrap arrays and zero-filled empty resamples | Batched memory use, undefined resamples excluded, finite bootstrap p-value resolution |
| Cluster significance lacked multiple-testing adjustment | Holm adjustment applied to cluster probabilities |
| Baselines used different text filters from target communities | Current overlap uses consistent participation filtering across all communities |
| Independently fitted topic IDs could not be compared over time | Shared pair-level topic model with balanced training allocation |
| Searchable text/IDs had been committed | New publishing policy keeps raw/text/user-level outputs local; history is not rewritten |

## Canonical implementation

`run_study.py`, `study.json`, and `src/study_*.py` implement the comparative study.
The original runner remains for reproducibility and optional transformer experiments.
Public deliverables are aggregate tables, figures, documentation and code. Detailed
Gephi networks and connector IDs remain local and reproducible.

## Execution evidence

See `outputs/study/collection_inventory.csv` for collected versus expected days and
provenance, and `REPORT.md` for available analysis. A configured dataset is never
reported as a completed finding. Per-pair private markers fingerprint source/data
and checksum output artifacts before they may be reused.

The offline regression suite covers collectors, preprocessing, statistics, weights,
graph conservation, Gephi round trips and pipeline integration. The pretrained-model
integration test is separately opt-in; it passed in the initial inherited-suite run.

## Remaining research limitations

- Independent blinded human annotation is required before claiming validated
  sentiment or target-specific hostility. It cannot be fabricated by an assistant.
- Archive completeness is not verified Reddit completeness; inherited day caches
  lack request manifests. Zero/missing archive activity is not proof of no activity.
- Two purposively chosen rivalries and adjacent windows are exploratory, not causal.
- Approximate centrality and small random-rewiring ensembles have explicit limits.
- Earlier Git history still contains published text. Ordinary new commits cannot
  remove it; no force push or history rewrite has been performed.
- Historic team-contribution prose was generated previously and is not evidence of
  work performed. Verify actual course contributions before submission.
