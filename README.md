# business-scenario-judge (STUB — under construction)

A constructed demo on public data (MultiWOZ, MIT): an LLM judge calibrated to
one annotator's recorded rulings on business-style customer-service scenarios,
compared against a zero-shot baseline on a held-out split. Never a real client
deployment. All labels come from a single annotator (STUB disclosure — final
text lands at export).

## Reproduce the metrics (no API key needed)

```
python scoring/score.py --gold data/gold_set.jsonl --pred data/predictions.jsonl --out metrics/results.json --check
```

STUB delta: accuracy 0.50 → 0.75 (placeholder numbers; replaced by the real
held-out run before ship).
