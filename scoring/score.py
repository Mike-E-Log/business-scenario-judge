"""Recompute all reported metrics from committed files. No model calls, ever."""
import argparse
import json
import math
import random
import sys
from collections import Counter
from pathlib import Path

from scipy.stats import binomtest
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


def _paired_delta_ci95(yt, yp_base, yp_cal):
    """Shared resample indices per iteration — never differencing per-judge CIs."""
    rng = random.Random(SEED); n = len(yt); deltas = []
    for _ in range(N_BOOT):
        idx = [rng.randrange(n) for _ in range(n)]
        acc_b = sum(yt[i] == yp_base[i] for i in idx) / n
        acc_c = sum(yt[i] == yp_cal[i] for i in idx) / n
        deltas.append(acc_c - acc_b)
    deltas.sort()
    return [deltas[int(0.025 * N_BOOT)], deltas[int(0.975 * N_BOOT)]]


def _mcnemar_exact(yt, yp_base, yp_cal):
    """Exact McNemar via the two-sided binomial on discordant pairs. Deterministic, seedless."""
    b = sum(t == pb and t != pc for t, pb, pc in zip(yt, yp_base, yp_cal))
    c = sum(t != pb and t == pc for t, pb, pc in zip(yt, yp_base, yp_cal))
    p = 1.0 if b + c == 0 else float(binomtest(min(b, c), b + c, 0.5).pvalue)
    return {"discordant_baseline_only_correct": b,
            "discordant_calibrated_only_correct": c,
            "mcnemar_exact_p": p}


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
    yt = [g["label"] for g in held]
    yp_b = [by_judge["baseline"][g["item_id"]] for g in held]
    yp_c = [by_judge["calibrated"][g["item_id"]] for g in held]
    delta_ci = _paired_delta_ci95(yt, yp_b, yp_c)
    out["heldout"]["delta"] = {
        "metric": "accuracy",                      # headline never switches (no silent fallback)
        "baseline": b["accuracy"], "calibrated": c["accuracy"],
        "delta": c["accuracy"] - b["accuracy"],
        "delta_ci95": delta_ci,
        "straddles_zero": delta_ci[0] <= 0.0 <= delta_ci[1],
        **_mcnemar_exact(yt, yp_b, yp_c),
    }
    out["heldout"]["beats_baseline"] = c["accuracy"] > b["accuracy"]   # tie = FAIL (checklist B)
    calib_labels = [g["label"] for g in gold if g["split"] == "calibration"]
    if calib_labels:
        cnts = Counter(calib_labels)
        top = max(cnts.values())
        maj = min(lbl for lbl, n_ in cnts.items() if n_ == top)   # deterministic tie-break
        maj_acc = sum(t == maj for t in yt) / len(yt)
    else:
        maj, maj_acc = None, None
    out["heldout"]["majority_label_baseline"] = {"label": maj, "accuracy": maj_acc}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", required=True); ap.add_argument("--pred", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--check", action="store_true",
                    help="recompute and compare against --out; never overwrites")
    a = ap.parse_args()
    gold = [json.loads(x) for x in Path(a.gold).read_text(encoding="utf-8").splitlines() if x]
    preds = [json.loads(x) for x in Path(a.pred).read_text(encoding="utf-8").splitlines() if x]
    result = compute_metrics(gold, preds)
    if a.check:
        committed = json.loads(Path(a.out).read_text(encoding="utf-8"))
        if committed != result:
            print("MISMATCH: committed metrics do not equal recomputation", file=sys.stderr)
            sys.exit(1)
        print("OK: committed metrics match recomputation")
        return
    Path(a.out).write_text(json.dumps(result, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
