# tests/test_confusion_counts.py
"""results.md's confusion tables must match results.json, which must recompute
from the committed data (audit 2026-08-13: counts are the honest per-class
report at n=15; rates are not)."""
import json
from pathlib import Path

REPO = Path(__file__).parents[1]
RESULTS = json.loads((REPO / "metrics" / "results.json").read_text(encoding="utf-8"))


def test_results_json_carries_full_confusion_grids():
    for judge in ("baseline", "calibrated"):
        conf = RESULTS["heldout"][judge]["confusion"]
        assert set(conf) == {f"{t}|{p}" for t in (0, 1, 2) for p in (0, 1, 2)}
        assert sum(conf.values()) == 15
    assert RESULTS["heldout"]["calibrated"]["confusion"]["0|0"] == 5


def test_results_md_confusion_rows_match_results_json():
    md = (REPO / "metrics" / "results.md").read_text(encoding="utf-8")
    for judge in ("baseline", "calibrated"):
        conf = RESULTS["heldout"][judge]["confusion"]
        for t, label in ((0, "A better"), (1, "B better"), (2, "tie")):
            row = f"| {label} | {conf[f'{t}|0']} | {conf[f'{t}|1']} | {conf[f'{t}|2']} |"
            assert row in md, f"{judge}: missing/mismatched row {row!r}"
