import random

from scoring.score import compute_metrics


def _gold(n=20):
    random.seed(7)
    return [{"item_id": f"i{k}", "question": "q", "answer_a": "a", "answer_b": "b",
             "label": random.choice([0, 1, 2]),
             "split": "heldout" if k < 10 else "calibration",   # 10/20 = 50%: clears both floors
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


def test_tie_keeps_accuracy_headline():
    gold = _gold()
    preds = [p for p in _preds(gold, flip_for_baseline=0)]  # identical judges
    m = compute_metrics(gold, preds)
    assert m["heldout"]["beats_baseline"] is False            # tie stamps FAIL (FROZEN B)
    assert m["heldout"]["delta"]["metric"] == "accuracy"      # headline never switches
    assert m["heldout"]["delta"]["delta"] == 0.0


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
    # Single-label heldout, both judges agree: sklearn kappa is NaN there —
    # the committed results file must stay strict-JSON (no NaN literals).
    # (Fixture sized 10/14 = 71% heldout to clear the FROZEN floor guards.)
    import json
    gold = ([{"item_id": f"h{k}", "question": "q", "answer_a": "a", "answer_b": "b",
              "label": 0, "split": "heldout", "tags": ["wrong-slot-value"]} for k in range(10)]
            + [{"item_id": f"c{k}", "question": "q", "answer_a": "a", "answer_b": "b",
                "label": 1, "split": "calibration", "tags": ["unhelpful-hedging"]} for k in range(4)])
    preds = [{"item_id": g["item_id"], "judge": j, "label": g["label"]}
             for g in gold for j in ("baseline", "calibrated")]
    m = compute_metrics(gold, preds)
    json.dumps(m, allow_nan=False)  # raises ValueError on NaN/Infinity
    for judge in ("baseline", "calibrated"):
        k = m["heldout"][judge]["cohen_kappa"]
        assert k is None or isinstance(k, float)


def test_heldout_below_10_items_raises():
    import pytest
    gold = _gold(40)                       # helper marks k<10 heldout -> 10 items
    for g in gold[9:10]:
        g["split"] = "calibration"         # now 9 heldout of 40
    preds = _preds(gold)
    with pytest.raises(ValueError, match="FROZEN floor"):
        compute_metrics(gold, preds)


def test_heldout_below_25_percent_raises():
    import pytest
    gold = _gold(60)                       # 10 heldout of 60 = 16.7% < 25%
    preds = _preds(gold)
    with pytest.raises(ValueError, match="FROZEN floor"):
        compute_metrics(gold, preds)


def test_unknown_item_id_raises():
    import pytest
    gold = _gold()
    preds = _preds(gold)
    preds.append({"item_id": "ghost-item", "judge": "baseline", "label": 0})
    with pytest.raises(ValueError, match="unknown item_id.*ghost-item"):
        compute_metrics(gold, preds)
