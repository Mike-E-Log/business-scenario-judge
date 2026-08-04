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


def _paired_gold(n_held=10, n_cal=4):
    return ([{"item_id": f"h{k}", "question": "q", "answer_a": "a", "answer_b": "b",
              "label": 0, "split": "heldout", "tags": ["wrong-slot-value"]} for k in range(n_held)]
            + [{"item_id": f"c{k}", "question": "q", "answer_a": "a", "answer_b": "b",
                "label": 1, "split": "calibration", "tags": ["unhelpful-hedging"]} for k in range(n_cal)])


def test_paired_delta_ci_is_zero_when_judges_identical_but_half_right():
    # Both judges correct on the SAME 5 of 10 held-out items -> every resample's
    # delta is exactly 0. Differencing two per-judge CIs (the wrong implementation)
    # yields a wide interval here — this fixture discriminates.
    gold = _paired_gold()
    preds = []
    for i, g in enumerate([g for g in gold if g["split"] == "heldout"]):
        lab = g["label"] if i < 5 else (g["label"] + 1) % 3
        preds.append({"item_id": g["item_id"], "judge": "baseline", "label": lab})
        preds.append({"item_id": g["item_id"], "judge": "calibrated", "label": lab})
    m = compute_metrics(gold, preds)
    assert m["heldout"]["delta"]["delta_ci95"] == [0.0, 0.0]
    assert m["heldout"]["delta"]["straddles_zero"] is True


def test_paired_delta_ci_known_answer_all_right_vs_all_wrong():
    # Calibrated right on all 10, baseline wrong on all 10 -> delta 1.0 in every
    # resample -> CI exactly [1.0, 1.0]; McNemar b=0, c=10 -> p = 2 * 0.5**10.
    gold = _paired_gold()
    preds = []
    for g in [g for g in gold if g["split"] == "heldout"]:
        preds.append({"item_id": g["item_id"], "judge": "baseline", "label": (g["label"] + 1) % 3})
        preds.append({"item_id": g["item_id"], "judge": "calibrated", "label": g["label"]})
    m = compute_metrics(gold, preds)
    d = m["heldout"]["delta"]
    assert d["delta_ci95"] == [1.0, 1.0]
    assert d["straddles_zero"] is False
    assert d["discordant_baseline_only_correct"] == 0
    assert d["discordant_calibrated_only_correct"] == 10
    assert abs(d["mcnemar_exact_p"] - 2 * 0.5**10) < 1e-12


def test_mcnemar_p_is_one_with_no_discordant_pairs():
    gold = _gold()
    m = compute_metrics(gold, _preds(gold, flip_for_baseline=0))
    d = m["heldout"]["delta"]
    assert d["discordant_baseline_only_correct"] == 0
    assert d["discordant_calibrated_only_correct"] == 0
    assert d["mcnemar_exact_p"] == 1.0


def test_majority_label_baseline_reported():
    gold = _paired_gold()          # calibration labels all 1 -> majority label 1
    preds = [{"item_id": g["item_id"], "judge": j, "label": g["label"]}
             for g in gold if g["split"] == "heldout" for j in ("baseline", "calibrated")]
    m = compute_metrics(gold, preds)
    mlb = m["heldout"]["majority_label_baseline"]
    assert mlb["label"] == 1
    assert mlb["accuracy"] == 0.0  # heldout labels are all 0
