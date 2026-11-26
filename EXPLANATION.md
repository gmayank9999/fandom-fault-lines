# Fandom Fault Lines: understand and defend the project

We ask whether rival-brand discussion spaces are separate audiences, overlapping
audiences, or something in between. Marvel/DC is compared with PlayStation/Xbox
over two consecutive four-week periods, with Star Wars and LOTR as other audiences.
Actual findings are in [REPORT.md](REPORT.md).

For an ordered mentor presentation, use [MENTOR_STORY.md](MENTOR_STORY.md).
The latest network review independently reconstructs all original edges and adds
second-window combined pair graphs colored by first-window participation. Their
combined assortativity is about 0.35, while coefficients within individual
subreddit layers are much smaller. This distinction matters: segregation between
discussion spaces is not automatically selective avoidance inside a space.
These are participation labels, not opinions; only approximately 46–48% of
all-reply events have both endpoints observed in the first window.

The extension adds three checks: follow the same users across windows, compare
sentiment within the same authors, and compare connectors against people with
similar activity and degree. See [ADVANCED_METHODS.md](ADVANCED_METHODS.md).

Only 17.9% of pooled Marvel/DC shared participants and 19.0% of pooled console
shared participants appear in both communities in each window. This differs from
the conditional return question: about 36% of first-window shared users are shared
again in the second window. Pooled overlap is not persistent overlap.

Initially shared users have higher next-window return rates. Standardizing posting
activity within common-support bins leaves a 7.2–15.3 percentage-point association,
depending on the exclusive comparison group. This does not establish causality;
one-comment exclusive users are excluded because a shared user needs at least two
comments, and broader interests or unmeasured activity may explain the difference.

The matched connector analysis finds no Holm-adjusted enrichment across its 32
specified comparisons. Earlier top-20 percentages were descriptive; matching
shows why a larger percentage than the overall audience is not enough. The small
selected sets and approximate ranks also limit power.

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
