import random

from scoring.score import compute_metrics


def _gold(n=20):
    random.seed(7)
    return [{"item_id": f"i{k}", "question": "q", "answer_a": "a", "answer_b": "b",
             "label": random.choice([0, 1, 2]),
             "split": "heldout" if k < 8 else "calibration",
             "tags": ["wrong-slot-value"] if k % 3 == 0 else ["unhelpful-hedging"]}
            for k in range(n)]


def _preds(gold, flip_for_baseline=3):
    out = []
    for i, g in enumerate(gold):
        out.append({"item_id": g["item_id"], "judge": "calibrated", "label": g["label"]})
        wrong = (g["label"] + 1) % 3 if i < flip_for_baseline else g["label"]
        out.append({"item_id": g["item_id"], "judge": "baseline", "label": wrong})
    return out


def test_heldout_accuracy_and_delta():
    gold = _gold(); m = compute_metrics(gold, _preds(gold))
    assert m["heldout"]["calibrated"]["accuracy"] == 1.0
    assert m["heldout"]["baseline"]["accuracy"] < 1.0
    assert m["heldout"]["delta"]["metric"] == "accuracy"
    assert m["heldout"]["beats_baseline"] is True


def test_tie_falls_back_to_kappa_delta():
    gold = _gold()
    preds = [p for p in _preds(gold, flip_for_baseline=0)]  # identical judges
    m = compute_metrics(gold, preds)
    assert m["heldout"]["beats_baseline"] is False           # tie stamps FAIL


def test_bootstrap_ci_present_and_ordered():
    gold = _gold(); m = compute_metrics(gold, _preds(gold))
    lo, hi = m["heldout"]["calibrated"]["accuracy_ci95"]
    assert 0.0 <= lo <= hi <= 1.0


def test_category_counts_from_tags():
    gold = _gold(); m = compute_metrics(gold, _preds(gold))
    assert m["failure_categories"]["wrong-slot-value"] >= 2


def test_duplicate_prediction_raises():
    import pytest
    gold = _gold()
    preds = _preds(gold)
    preds.append({"item_id": gold[0]["item_id"], "judge": "baseline", "label": 2})
    with pytest.raises(ValueError, match="duplicate prediction.*baseline.*i0"):
        compute_metrics(gold, preds)


def test_unknown_judge_raises():
    import pytest
    gold = _gold()
    preds = _preds(gold)
    preds.append({"item_id": "i0", "judge": "calibrated_v2", "label": 0})
    with pytest.raises(ValueError, match="unexpected judge.*calibrated_v2"):
        compute_metrics(gold, preds)


def test_missing_heldout_prediction_raises_with_names():
    import pytest
    gold = _gold()
    preds = [p for p in _preds(gold) if not (p["judge"] == "baseline" and p["item_id"] == "i1")]
    with pytest.raises(ValueError, match="missing prediction.*baseline.*i1"):
        compute_metrics(gold, preds)


def test_degenerate_single_label_stays_valid_json():
    # One held-out item, both judges agree: sklearn kappa is NaN there —
    # the committed results file must stay strict-JSON (no NaN literals).
    import json
    gold = [{"item_id": "i0", "question": "q", "answer_a": "a", "answer_b": "b",
             "label": 0, "split": "heldout", "tags": ["wrong-slot-value"]},
            {"item_id": "i1", "question": "q", "answer_a": "a", "answer_b": "b",
             "label": 1, "split": "calibration", "tags": ["unhelpful-hedging"]}]
    preds = [{"item_id": g["item_id"], "judge": j, "label": g["label"]}
             for g in gold for j in ("baseline", "calibrated")]
    m = compute_metrics(gold, preds)
    json.dumps(m, allow_nan=False)  # raises ValueError on NaN/Infinity
    for judge in ("baseline", "calibrated"):
        k = m["heldout"][judge]["cohen_kappa"]
        assert k is None or isinstance(k, float)
