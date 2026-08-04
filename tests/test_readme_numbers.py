# tests/test_readme_numbers.py
"""The README's headline delta must equal metrics/results.json — the
prose-vs-computed drift this pins already happened once (see the 2026-08-04 audit)."""
import json
import re
from pathlib import Path

REPO = Path(__file__).parents[1]


def test_readme_headline_equals_results_json():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    m = re.search(r"accuracy\s+(\d+\.\d+)\s*(?:→|->)\s*(\d+\.\d+)", readme)
    assert m, "README carries no 'accuracy X -> Y' headline"
    results = json.loads((REPO / "metrics" / "results.json").read_text(encoding="utf-8"))
    held = results["heldout"]
    assert float(m.group(1)) == held["baseline"]["accuracy"]
    assert float(m.group(2)) == held["calibrated"]["accuracy"]
