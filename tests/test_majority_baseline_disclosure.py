# tests/test_majority_baseline_disclosure.py
"""The calibrated judge ties the majority-class baseline (always answering the
calibration split's most common label). The tie must be disclosed wherever the
headline comparison appears, and CI must recompute metrics so a stale
results.json fails the build."""
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]
RESULTS = json.loads((REPO / "metrics" / "results.json").read_text(encoding="utf-8"))
MAJ = RESULTS["heldout"]["majority_label_baseline"]


def test_readme_discloses_majority_baseline():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    m = re.search(r"majority[- ]class baseline[^.]*?(\d+)%", readme, re.IGNORECASE)
    assert m, "README never discloses the majority-class baseline"
    assert int(m.group(1)) == round(MAJ["accuracy"] * 100)
    # Clause pin, not a bare \btie — README independently contains the
    # unrelated "(A better / B better / tie)", which a bare pin matches.
    tie_clause = re.search(r"only ties it", readme)
    if MAJ["accuracy"] >= RESULTS["heldout"]["calibrated"]["accuracy"]:
        assert tie_clause, ("majority-class baseline ties or beats the "
                            "calibrated judge; README must say so")
    else:
        assert not tie_clause, "README claims a tie the data no longer shows"


def test_results_md_has_majority_baseline_row():
    md = (REPO / "metrics" / "results.md").read_text(encoding="utf-8")
    m = re.search(r"\|\s*majority-class[^|]*\|\s*([0-9.]+)\s*\|", md)
    assert m, "results.md table has no majority-class baseline row"
    assert float(m.group(1)) == round(MAJ["accuracy"], 3)


def test_committed_results_match_recomputation():
    # The guard the YAML step cannot provide: runs at the local commit gate
    # and in every clone, same shape as the retest recompute guard.
    r = subprocess.run(
        [sys.executable, str(REPO / "scoring" / "score.py"),
         "--gold", str(REPO / "data" / "gold_set.jsonl"),
         "--pred", str(REPO / "data" / "predictions.jsonl"),
         "--out", str(REPO / "metrics" / "results.json"), "--check"],
        capture_output=True, text=True)
    assert r.returncode == 0, (
        "committed metrics/results.json does not recompute from the committed "
        f"data:\n{r.stderr}")


def test_ci_recomputes_metrics_with_check():
    wf = (REPO / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
    assert re.search(r"scoring/score\.py .*--check", wf), (
        "tests.yml never runs scoring/score.py --check; a stale committed "
        "results.json would pass CI silently")
