# Fandom Fault Lines: understand and defend the project

We ask whether rival-brand discussion spaces are separate audiences, overlapping
audiences, or something in between. Marvel/DC is compared with PlayStation/Xbox
over two consecutive four-week periods, with Star Wars and LOTR as other audiences.
Actual findings are in [REPORT.md](REPORT.md).

## Why the original result changed

The pilot sampled the latest comments inside time slots. It missed most interactions.
A person active in both communities could easily appear in only one sample, lowering
observed overlap. Sampling also broke reply chains and changed network shape. The
old 5% headline is therefore superseded. More observations improve coverage; they
do not guarantee a stronger rivalry effect.

## Four complementary measurements

**Content:** brand mentions, topics and whole-comment sentiment. A negative comment
can criticise Marvel while praising DC. Therefore sentiment is not rival-directed
hostility. Titles such as Secret Wars also contain emotionally scored words; we
compare original and adapted VADER instead of assuming either is ground truth.

**Network:** users are nodes; A replying to B creates A → B. Five replies give
weight five. PageRank measures structural attention, betweenness measures
shortest-path position, and Louvain finds linked groups. None proves influence or
ideology. Removing replies to posts tests whether thread starters explain hubs.

**Overlap:** if 20 of 100 users in A also appear among 200 users in B, overlap is
20% of A, 10% of B, and 20/(100+200−20)=7.14% of their union (Jaccard). Name the
denominator. Participation in two spaces does not mean liking or endorsing both.

**Time:** compare two 28-day periods and the deduplicated 56-day population.
Changes may reflect news, releases or moderation. We measure change, not its cause.

## What makes this defensible?

We check expected days and UTC bounds, report unresolved parents, preserve isolates,
sum reciprocal weights, compare equivalent observed/randomized networks and check
betweenness across seeds. Full-network measurements stay separate from filtered
Gephi pictures. Duration and subsampling experiments expose observation sensitivity.

The remaining human task is independent annotation. Claude's labels cannot be
presented as a human gold standard. See [ANNOTATION_GUIDE.md](ANNOTATION_GUIDE.md).

## Presentation order

1. Research questions and why two rivalries improve on one case.
2. Communities, dates, actual coverage and filtering.
3. The pilot's sampling problem and sensitivity experiment.
4. Content results, distinguishing sentiment from stance.
5. Gephi full/focus views and comment-only sensitivity networks.
6. Overlap with explicit denominators and comparison audiences.
7. Temporal stability, uncertainty, outstanding validation and limits.

Use current generated figures, not old screenshots. A mixed or null finding is
valid research. Low overlap alone is not evidence of an echo chamber. Historical
write-ups in `docs/archive/` are retained only for traceability.
