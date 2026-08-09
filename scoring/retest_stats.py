"""Recompute the blind-retest self-agreement statistics from committed data.

Reads data/retest.jsonl (one row per retest scenario: both rulings and the
recall-probe answer) and the committed draw (data/retest_items.json), refuses
to score any row set that is not exactly the committed draw, and recomputes
every retest number the README and metrics/results.md publish: raw agreement,
a Wilson 95% interval on that raw proportion, unweighted Cohen's kappa, and
the recall-restricted agreement (only reported at or above the pre-registered
floor of 5 scenarios).

No model calls, no randomness — the numbers recompute from the files alone.

    python scoring/retest_stats.py --retest data/retest.jsonl --items data/retest_items.json --out metrics/retest.json
    python scoring/retest_stats.py --retest data/retest.jsonl --items data/retest_items.json --out metrics/retest.json --check

--check never overwrites: it recomputes and compares against the committed
metrics. Exit codes: 0 ok, 1 mismatch (draw or --check), 2 configuration error.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score

RECALL_FLOOR = 5


def compute(rows: list[dict]) -> dict:
    first = [r["first_label"] for r in rows]
    second = [r["retest_label"] for r in rows]
    n = len(rows)
    agree_n = sum(a == b for a, b in zip(first, second))
    ci = binomtest(agree_n, n).proportion_ci(confidence_level=0.95, method="wilson")
    kappa = float(cohen_kappa_score(first, second, weights=None))
    recall_rows = [r for r in rows if r["recall"] in ("no", "unsure")]
    recall_restricted: dict = {"n": len(recall_rows), "agreement": None}
    if len(recall_rows) >= RECALL_FLOOR:
        recall_restricted["agreement"] = (
            sum(r["first_label"] == r["retest_label"] for r in recall_rows)
            / len(recall_rows))
    return {"n": n, "agreement": agree_n / n,
            "wilson_ci95": [float(ci.low), float(ci.high)],
            "cohen_kappa": None if math.isnan(kappa) else kappa,
            "recall_restricted": recall_restricted}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--retest", required=True)
    ap.add_argument("--items", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    rows = [json.loads(line)
            for line in Path(a.retest).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    if not rows:
        print("CONFIG ERROR: no retest rows", file=sys.stderr)
        return 2
    draw = json.loads(Path(a.items).read_text(encoding="utf-8"))
    if sorted(r["item_id"] for r in rows) != sorted(draw["items"]):
        print("MISMATCH: retest rows do not match the committed draw — "
              "refusing to score a different item set", file=sys.stderr)
        return 1
    m = compute(rows)
    out = Path(a.out)
    if a.check:
        committed = json.loads(out.read_text(encoding="utf-8"))
        if committed != m:
            print(f"MISMATCH: committed {a.out} != recomputation", file=sys.stderr)
            return 1
        print("OK: committed retest metrics match recomputation")
        return 0
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
