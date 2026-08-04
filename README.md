# business-scenario-judge (STUB — under construction)

A constructed demo on public data (MultiWOZ, MIT): an LLM judge calibrated to
one annotator's recorded rulings on business-style customer-service scenarios,
compared against a zero-shot baseline on a held-out split. Never a real client
deployment. All labels come from a single annotator (STUB disclosure — final
text lands at export). Scenarios draw on the restaurant, hotel, train, taxi,
and attraction domains of MultiWOZ 2.2 (see THIRD_PARTY.md).

## Install

```
pip install -r requirements.txt
```

## Reproduce the metrics (no API key needed)

```
python scoring/score.py --gold data/gold_set.jsonl --pred data/predictions.jsonl --out metrics/results.json --check
```

STUB delta: accuracy 0.50 → 0.75 (placeholder numbers; replaced by the real
held-out run before ship). Note: against the current STUB data files this
command intentionally raises the held-out floor guard (the stub gold set is
below the frozen ≥10-item/≥25% floor); it validates end-to-end once the real
labeled data lands.
