# Mentor discussion: what we asked, checked and learned

## Opening: the question, not a predetermined outcome

“We asked whether rival Reddit communities form separate audiences or overlapping
ones. We examined content, reply structure and audience boundaries together, first
in Marvel/DC and then in PS5/Xbox. We treated rivalry as a reason to compare the
communities, not as proof that their users are hostile.”

The original main question has three parts. The temporal and sampling analyses
strengthen those parts; they do not replace them with unrelated questions.

| Original research question | Evidence delivered | What remains outside the evidence |
|---|---|---|
| RQ1: topics and sentiment concerning own/rival franchises | Pooled topics, explicit mentions, original/adapted VADER, clustered comparisons and paired-author sensitivities | Validated rival-directed attitudes; independent human annotation is still needed |
| RQ2: internal organisation and connector users | Directed weighted reply graphs; centralities; communities; graph null comparison; thread-starter sensitivity; activity-matched connector tests; independent raw-edge audit | Causal influence, diffusion, ideological factions, or precise stable individual rankings |
| RQ3: audience overlap and boundaries | Directional/Jaccard overlap, six-community comparisons, activity thresholds, participation persistence and prior-participation reply mixing | Fan allegiance, reading/exposure without commenting, or generalization to all fandoms |

## Act 1: first check whether the measurement is trustworthy

“The pilot used a small sampled corpus and its report lagged behind the newer
data. We audited collection, preprocessing and network construction before
interpreting the apparent boundaries.”

Explain the graph on a tiny example: A replies to B twice and B replies to A once.
There are two directed edges, A→B with weight 2 and B→A with weight 1. The
undirected projection used for Louvain has one edge of weight 3. Accounts with
unresolved parents remain nodes; unresolved replies are counted separately.
Self-replies are excluded and counted. Same-subscription or same-thread presence
does not by itself create an edge.

Show `edge_audit.csv` from the network review. Its independent reconstruction
compares every saved edge and weight with a raw-record parent-author join.
Gephi's import checks are a second check on exported graph fidelity. Neither
check proves that the source archive contains all Reddit comments.

## Act 2: expand the case and expose observation sensitivity

“We expanded to two rival pairs, two comparison audiences, two adjacent 28-day
windows and 1,168,638 archive comments across six communities. NLP and detailed
reply-network analysis focus on the four rivalry communities.”

Show the sampling/duration figure. In September Marvel/DC, mean Jaccard overlap
using a random 10% of comments is 3.16%, versus 6.78% for the full collected
window. This demonstrates a sampling sensitivity, not an exact reconstruction
of the original sampling scheme.

## Act 3: audiences overlap, but overlap is not a stable membership label

Show directional overlap alongside Jaccard. Across 56 days, Marvel/DC shares
8,807 commenters: 12.84% of Marvel commenters and 22.07% of DC commenters.
PS5/Xbox shares 4,978: 10.70% and 11.23%, respectively. Marvel/DC has the largest
Jaccard overlap among the 15 selected community pairs in both windows.

Then show the transition matrix. Only 17.9% of pooled superhero shared users and
19.0% of pooled console shared users appear in both communities in each window.
About 36% of the *first-window* shared cohort is shared again in the second.
These statements have different denominators and are both useful.

“We therefore distinguish pooled overlap from persistent overlap. Shared users
are not one uniform, permanent audience.”

## Act 4: explain the network before calling someone influential

Show the all-reply versus comment-only component comparison. September Xbox's
largest weak component falls from 98.6% to 53.3% after removing replies to posts.
Thread starters explain much of the apparent connectivity.

Show the observed-versus-matched connector chart. Some unadjusted top-20 sets
contain a larger shared-user proportion than the whole audience, but none of
32 activity/degree-matched enrichment comparisons survives Holm correction.
This is not evidence of equivalence: the selected sets are small, bins are coarse,
and betweenness is approximate. It prevents overstating the unadjusted result.

Use the combined second-window graphs to distinguish shared membership from
actual reply interactions. Their colors represent first-window participation,
not opinions. A reply between prior Marvel-only and prior DC-only participants
occurs in a thread in one subreddit; it is not a reply physically crossing
subreddits. Read exact mixing counts from the generated report.

The all-reply combined networks have prior-participation assortativity around
0.35 for both pairs, while the individual subreddit coefficients range from
about 0.001 to 0.040. The same contrast remains in comment-only graphs. This
illustrates an aggregation effect: separation between discussion spaces can
make the combined graph look segregated even when within-space mixing is near
its endpoint-marginal expectation. It is not a test of ideological homophily.
Only about 46–48% of all-reply events have both endpoints observed in the prior
window, so the assortativity result is conditional on that subset.

In the second window, there are 7,428 superhero and 3,438 console reply events
between prior A-only and prior B-only participants, in either direction. These
are reply events, not distinct people. They demonstrate some direct interaction
between prior participation groups; they do not demonstrate agreement or diffusion.

## Act 5: examine content without equating negativity with hostility

“Explicit rival mentions are asymmetric. DC mentions Marvel more often than the
reverse, and Xbox mentions PlayStation more often than the reverse, under our
specified dictionaries. Automated sentiment does not show a consistent pattern
of rival-mentioning comments scoring more negatively.”

Show paired-author results and acknowledge the eligible population changes.
These compare an author's two category means, giving authors equal weight. They
reduce author-composition differences but do not solve sarcasm, topic selection,
thread dependence or target-specific stance. Topics are exploratory; roughly a
third of usable comments lack sufficient topical vocabulary for assignment.

## Act 6: a temporal association worth following up

Initially shared users are more likely to appear somewhere in the pair during
the next window. Standardizing first-window posting activity on common support
leaves differences of 7.2–15.3 percentage points relative to the exclusive groups.
This is an association, not evidence that cross-participation causes retention.
One-comment exclusive users have no shared-user counterparts and are excluded
from the adjusted target.

## Closing claim

“In these two rivalry cases, participation boundaries are permeable and change
over time. Measurement effort changes the overlap we detect. Reply structure is
strongly shaped by thread mechanics, and apparent connector prominence needs
activity-adjusted comparison. Our automated content evidence does not establish
generalized rival-directed hostility.”

The study is valuable because it distinguishes explanations that a single
overlap percentage or a Gephi picture would conflate. It is a bounded exploratory
case study, not a causal account of rivalry or a conclusive echo-chamber test.

## Scope decisions and the next strongest evidence

There is no universal duration or subreddit count that makes a study “enough.”
The current design supports its bounded comparisons. It does not establish
seasonal stability, behaviour around different release cycles or generality
beyond these cases. Adjacent windows are not independent replications.

For stronger attitude claims, complete independent human annotation first, then
evaluate on an untouched set if the pilot is used for tuning. For broader temporal
claims, specify separated periods or event-aligned windows before collecting
them and publish all outcomes. For broader domain claims, add a third rivalry
with an explicit selection rationale; do not choose it because its results look
dramatic. More data cannot fix an invalid measure of hostility.

Until a mentor rubric is available, no guarantee of a grade or of complete
coverage of course-specific requirements is justified. Demonstrate the Gephi
files yourself and be able to explain direction, weights, filters, missing data,
sampling and the distinction between centrality and influence.

## Methodological anchors

The categorical mixing coefficient follows the endpoint-marginal definition
described in [NetworkX's assortativity reference](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.assortativity.attribute_assortativity_coefficient.html).
We apply it to observed prior participation, not ideology. The distinction
between our measurements and a full echo-chamber claim is motivated by the
interaction-homophily and diffusion dimensions in
[Cinelli et al.](https://doi.org/10.1073/pnas.2023301118).
