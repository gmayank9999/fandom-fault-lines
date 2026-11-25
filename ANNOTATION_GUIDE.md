# Independent annotation protocol

After both study analyses finish, run `python tools/prepare_annotation.py` to
prepare two independently shuffled, blinded sheets in `data/gold/study/` (default
eight comments per community-period-mention stratum, up to 256 per rater). Labels
are blank. Sampling probabilities are recorded separately. The helper refuses to
overwrite existing sheets, protecting any subsequent human annotation work.

The inherited 300 examples in `data/gold/gold_labels.csv` were labelled by Claude.
They are **AI-generated development labels**, not human ground truth. They were
length-restricted and drawn during partial collection. Agreement scores support
model exploration only; they are not independent human-validated accuracy.

1. Draw a new sample stratified by community, period and mention category. Record
   stratum populations and inclusion probabilities. Separate development and
   held-out evaluation examples. Include different text lengths, or explicitly
   restrict the population your sample represents.
2. Ask two humans to independently label a manageable pilot, such as 50–100
   examples each. Hide model predictions, AI labels and each other's labels.
3. Label overall tone: positive / neutral-or-mixed / negative / uncertain.
   Separately label stance toward the specified rival: favourable / hostile /
   neutral-or-mixed / not-mentioned / uncertain. Criticism of one's own franchise
   does not automatically imply hostility toward the rival.
4. Address quotations, sarcasm, plot descriptions and ambiguous names in the
   codebook. Use uncertain when missing context prevents a responsible judgement.
5. Freeze the codebook after the pilot. Evaluate untouched held-out examples.
   Preserve independent labels before reconciliation. Report label counts,
   uncertain/missing rates, raw agreement, Cohen's kappa and confusion matrices.
6. Report model macro-F1 and per-class precision/recall on human labels. Population
   stance rates require stratum weights and appropriate uncertainty. Do not
   extrapolate the old development sample to every comment.

For a quick development check only, label `gold_to_label.csv` independently and
save `gold_id,sentiment` to `data/gold/gold_labels_human.csv`, using positive,
negative or neutral. `python -m src.gold_set evaluate` compares those with the AI
labels. This is not a replacement for a fresh held-out evaluation set.

Keep text-bearing annotation files local. A student's Git author identity does
not change the provenance of an AI-generated annotation.
