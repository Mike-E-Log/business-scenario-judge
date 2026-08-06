# tests/test_readme_numbers.py
"""The README's headline delta must equal metrics/results.json — prose numbers
and computed numbers drift apart silently without a pin like this."""
import json
import re
from pathlib import Path

REPO = Path(__file__).parents[1]


def test_readme_headline_equals_results_json():
    # The generated headline (export_flagship.headline) states whole
    # percentages, calibrated first: "..., 53% against 40%, ...".
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    m = re.search(r"(\d+)%\s+against\s+(\d+)%", readme)
    assert m, "README carries no '<calibrated>% against <baseline>%' headline"
    results = json.loads((REPO / "metrics" / "results.json").read_text(encoding="utf-8"))
    held = results["heldout"]
    assert int(m.group(1)) == round(held["calibrated"]["accuracy"] * 100)
    assert int(m.group(2)) == round(held["baseline"]["accuracy"] * 100)
