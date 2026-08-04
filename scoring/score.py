"""Recompute all reported metrics from committed files. No model calls, ever."""
import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

N_BOOT, SEED = 10_000, 20260723
LABELS = [0, 1, 2]  # 0 = A wins, 1 = B wins, 2 = Tie


def _kappa(y_true, y_pred):
    """Cohen's kappa over the full label set; None (JSON null) when undefined
    (e.g. a single label on both sides makes expected agreement 1)."""
    k = float(cohen_kappa_score(y_true, y_pred, labels=LABELS))
    return None if math.isnan(k) else k


def _ci95(y_true, y_pred):
    rng = random.Random(SEED); n = len(y_true); accs = []
    for _ in range(N_BOOT):
        idx = [rng.randrange(n) for _ in range(n)]
        accs.append(sum(y_true[i] == y_pred[i] for i in idx) / n)
    accs.sort()
    return [accs[int(0.025 * N_BOOT)], accs[int(0.975 * N_BOOT)]]


def compute_metrics(gold, preds):
    by_judge = {"baseline": {}, "calibrated": {}}
    gold_ids = {g["item_id"] for g in gold}
    for p in preds:
        if p["judge"] not in by_judge:
            raise ValueError(f"unexpected judge {p['judge']!r} on item {p['item_id']!r}")
        if p["item_id"] not in gold_ids:
            raise ValueError(f"unknown item_id {p['item_id']!r} not in gold set")
        if p["item_id"] in by_judge[p["judge"]]:
            raise ValueError(f"duplicate prediction {p['judge']}/{p['item_id']}")
        by_judge[p["judge"]][p["item_id"]] = p["label"]
    held = [g for g in gold if g["split"] == "heldout"]
    if len(held) < 10 or len(held) < 0.25 * len(gold):
        raise ValueError(
            f"heldout split below FROZEN floor: {len(held)} of {len(gold)} gold "
            "(need >=10 items and >=25%)")
    missing = [(j, g["item_id"]) for j, jl in by_judge.items()
               for g in held if g["item_id"] not in jl]
    if missing:
        raise ValueError("missing prediction(s): "
                         + ", ".join(f"{j}/{i}" for j, i in missing))
    out = {"heldout": {}, "n_items": len(gold), "n_heldout": len(held),
           "failure_categories": dict(Counter(t for g in gold for t in g["tags"]))}
    scores = {}
    for judge, jl in by_judge.items():
        yt = [g["label"] for g in held]; yp = [jl[g["item_id"]] for g in held]
        acc = sum(a == b for a, b in zip(yt, yp)) / len(yt)
        scores[judge] = {"accuracy": acc, "accuracy_ci95": _ci95(yt, yp),
                         "cohen_kappa": _kappa(yt, yp)}
        out["heldout"][judge] = scores[judge]
    b, c = scores["baseline"], scores["calibrated"]
    out["heldout"]["delta"] = {
        "metric": "accuracy",                      # headline never switches (no silent fallback)
        "baseline": b["accuracy"], "calibrated": c["accuracy"],
        "delta": c["accuracy"] - b["accuracy"],
    }
    out["heldout"]["beats_baseline"] = c["accuracy"] > b["accuracy"]   # tie = FAIL (checklist B)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True); ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    gold = [json.loads(x) for x in Path(a.gold).read_text(encoding="utf-8").splitlines() if x]
    preds = [json.loads(x) for x in Path(a.pred).read_text(encoding="utf-8").splitlines() if x]
    Path(a.out).write_text(json.dumps(compute_metrics(gold, preds), indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
