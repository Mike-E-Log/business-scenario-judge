# tests/test_readme_numbers.py
"""The README's headline delta must equal metrics/results.json — prose numbers
and computed numbers drift apart silently without a pin like this."""
import json
import re
from pathlib import Path

REPO = Path(__file__).parents[1]


def test_scoreboard_kappa_column_matches_metrics():
    # The scoreboard's kappa column must equal the stored metrics: judges from
    # metrics/results.json, the human retest from metrics/retest.json. The
    # do-nothing row is 0.000 by construction (a constant predictor's observed
    # match equals its chance match exactly).
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    m = re.search(
        r"\| Grader \| Match with the person's rulings \| Luck-corrected match \(kappa\) \| Measured on \|\n(?:\|.*\n)+",
        readme,
    )
    assert m, "Scoreboard table lacks the 'Luck-corrected match (kappa)' column"
    block = m.group(0)
    results = json.loads((REPO / "metrics" / "results.json").read_text(encoding="utf-8"))
    retest = json.loads((REPO / "metrics" / "retest.json").read_text(encoding="utf-8"))
    held = results["heldout"]
    assert f'{float(held["calibrated"]["cohen_kappa"]):.3f}' in block
    assert f'{float(held["baseline"]["cohen_kappa"]):.3f}' in block
    assert "0.000" in block
    assert f'{float(retest["cohen_kappa"]):.3f}' in block


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
