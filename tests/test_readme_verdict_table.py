# tests/test_readme_verdict_table.py
"""The README's per-chat verdict table must equal a recompute from the
committed data files (gold_set + predictions) - a hand-drifted row would
fabricate a ruling on a page whose brand is that prose cannot drift."""
import json
import re
from pathlib import Path

REPO = Path(__file__).parents[1]
NAME = {0: "A", 1: "B", 2: "Tie"}


def _expected_rows():
    gold, pred = {}, {}
    for line in (REPO / "data" / "gold_set.jsonl").read_text(encoding="utf-8").splitlines():
        g = json.loads(line)
        gold[g["item_id"]] = g
    for line in (REPO / "data" / "predictions.jsonl").read_text(encoding="utf-8").splitlines():
        p = json.loads(line)
        pred.setdefault(p["item_id"], {})[p["judge"]] = p["label"]
    return [
        f"| `{i}` | {NAME[gold[i]['label']]} | {NAME[pred[i]['calibrated']]} "
        f"| {NAME[pred[i]['baseline']]} | A |"
        for i in sorted(i for i, g in gold.items() if g["split"] == "heldout")
    ]


def _readme_rows(text: str):
    return [l.strip() for l in text.splitlines() if l.strip().startswith("| `mwz_")]


def test_readme_verdict_table_matches_data():
    rows = _readme_rows((REPO / "README.md").read_text(encoding="utf-8"))
    assert rows == _expected_rows(), "per-chat verdict table drifted from the data files"


def test_verdict_table_checker_fires():
    # positive control (house rule 2026-08-04)
    assert _readme_rows("| `mwz_FAKE0000` | tie | tie | tie | A better |") != _expected_rows()
