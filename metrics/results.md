# Metrics

On the held-out split the calibrated judge scored higher than the baseline, 53% against 40%, but the 95% intervals overlap. This run does not establish a real difference.

A blunter yardstick: the majority-class baseline (always answering "A better", the calibration split's most common label) scores the same 53% on this split, so the calibrated judge only ties it (`majority_label_baseline` in `results.json`; no interval or kappa is committed for it).

Recompute these numbers yourself, no API key needed:

```
python scoring/score.py --gold data/gold_set.jsonl --pred data/predictions.jsonl --out metrics/results.json
python scoring/retest_stats.py --retest data/retest.jsonl --items data/retest_items.json --out metrics/retest.json
```

## Held-out split (15 of 60 scenarios)

| judge | accuracy | 95% interval | Cohen's kappa |
|---|---|---|---|
| baseline | 0.400 | 0.133–0.667 | -0.164 |
| calibrated | 0.533 | 0.267–0.800 | 0.054 |
| majority-class (always "A better") | 0.533 | — | — |

Reported difference is on **accuracy**: 0.400 to 0.533.

### Confusion counts (held-out, n=15)

Rows are the annotator's ruling; columns are the judge's ruling. Raw counts only: at n=15, per-class rates (precision/recall/F1) are not stable, so none are reported (`confusion` in `results.json`; the held-out split contains no tie rulings, so the tie row is zero).

Calibrated judge:

| annotator ruled \ judge said | A better | B better | tie |
|---|---|---|---|
| A better | 5 | 3 | 0 |
| B better | 4 | 3 | 0 |
| tie | 0 | 0 | 0 |

Baseline judge:

| annotator ruled \ judge said | A better | B better | tie |
|---|---|---|---|
| A better | 5 | 2 | 1 |
| B better | 6 | 1 | 0 |
| tie | 0 | 0 | 0 |

Annotator self-agreement: 80% over 15 scenarios ruled twice (95% Wilson interval 55%–93% on the raw proportion; chance-corrected Cohen's κ 0.526, reported without a strength label because band labels are not stable at n=15). Restricted to the 15 scenarios whose probe answer was no/unsure, agreement was 80%. Nothing here
can be more reliable than that number. It is the ceiling on what one person's
gold set can show.

## What the annotator kept flagging

Failure-category counts, from 60 judgments:

| category | count |
|---|---|
| clarity | 20 |
| instruction-following | 19 |
| completeness | 14 |
| conciseness | 9 |
