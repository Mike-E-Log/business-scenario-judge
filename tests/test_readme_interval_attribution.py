# tests/test_readme_interval_attribution.py
"""The repo reports 95% ranges from TWO methods: Wilson (the human self-check,
scoring/retest_stats.py:38) and seeded bootstrap (the judges,
scoring/score.py:24-30). No other test states which prose sentence claims
which method, so a rewrite could mis-attribute one and ship green.
House rule 2026-08-04: checkers ship with a fires-on-fake control."""
import re
from pathlib import Path

REPO = Path(__file__).parents[1]
README = REPO / "README.md"

WINDOW = 400


def _wilson_violations(text):
    issues = []
    hits = [m.start() for m in re.finditer(r"(?i)wilson", text)]
    if not hits:
        issues.append("no Wilson mention at all")
    exp2 = text.find("## Experiment 2")
    for i in hits:
        window = text[max(0, i - WINDOW): i + WINDOW]
        if "55%–93%" not in window:
            issues.append(f"Wilson at {i} not anchored to 55%-93%")
        if "27%" in window or "13%" in window:
            issues.append(f"Wilson at {i} near a judge (bootstrap) range")
        if exp2 != -1 and i >= exp2:
            issues.append(f"Wilson at {i} inside Experiment 2")
    low = text.lower()
    boots = [m.start() for m in re.finditer("bootstrap", low)]
    if not boots:
        issues.append("no bootstrap mention at all")
    elif not any("27%" in text[max(0, b - WINDOW): b + WINDOW] for b in boots):
        issues.append("no bootstrap mention near the judges' 27% range")
    return issues


def test_wilson_and_bootstrap_are_not_conflated():
    assert _wilson_violations(README.read_text(encoding="utf-8")) == []


def test_checker_fires():
    good = README.read_text(encoding="utf-8")
    assert _wilson_violations(good) == []
    bad = good.replace("a bootstrap 95% range", "a Wilson 95% range", 1)
    assert _wilson_violations(bad), "checker failed to fire on a planted misattribution"
