# Pre-registration — held-out evaluation (committed before any labeling)

> **Correction note (2026-08-11).** The timing claims in this file overstate what the
> git record supports: the file's first commit is 2026-08-04 (`3c42c77`), and the
> project log records 45 of 60 first-pass gradings already done on 2026-08-03. What the
> record does support: the held-out split assignment was committed before calibration
> existed, and this analysis plan was committed before the judge runs (2026-08-06).
> The original text below is unchanged.

Committed 2026-08-04, before labeling session 1. Governs the real run; the
FROZEN acceptance checklist's strict-greater rule is the PASS bar —
significance is honesty framing, never the bar.

- **Held-out size:** n = max(15, ceil(0.25 × final_gold_count)) — never below
  the frozen floor (≥10 items AND ≥25%) at any gold-set size. If the labeling
  timebox yields fewer than 40 gold items, the n=15 target yields to
  n = max(10, ceil(0.25 × final_gold_count)) and the shortfall is disclosed
  in the results (the frozen floor still binds; the timebox never expands).
- **Split:** drawn ONCE before calibration starts; assignment committed
  (`split` field in `data/gold_set.jsonl`); held-out items never read during
  calibration.
- **Primary metric:** exact agreement (accuracy) with the annotator's held-out
  labels. PASS = calibrated judge strictly greater than the zero-shot baseline
  on the same split; a tie stamps FAIL. Cohen's kappa reported alongside.
- **Statistics reported:** paired-delta bootstrap 95% CI (shared resample
  indices) plus exact McNemar discordant-pair counts and p-value. Power note,
  computed: at n=15, if every discordant pair favors one judge, at least 6
  discordant pairs are required for p < 0.05 (2 × 0.5^6 = 0.03125). With few
  discordant pairs no significant result is possible — that outcome ships with
  plain words.
- **Baseline sanity band (pre-registered):** zero-shot baseline held-out
  accuracy expected within [0.30, 0.80]. Outside the band → investigate task
  triviality/degeneracy and disclose before headlining any delta.
- **Losing or insignificant results ship anyway** with the numbers stated
  plainly — this pre-registration removes the option of quiet re-runs.
