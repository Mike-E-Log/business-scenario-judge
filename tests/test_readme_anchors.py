# tests/test_readme_anchors.py
"""Every intra-README link must resolve to a real heading — the 2026-08-13
audit demonstrated a dead Contents link ships green today."""
import re
from pathlib import Path

REPO = Path(__file__).parents[1]


def _slug(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"[\s]+", "-", s)


def test_every_internal_link_resolves_to_a_heading():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    headings = {_slug(m) for m in re.findall(r"^#{1,6}\s+(.+)$", readme, re.M)}
    links = re.findall(r"\]\(#([^)]+)\)", readme)
    assert links, "README carries no internal links at all"
    dead = [l for l in links if l not in headings]
    assert not dead, f"dead internal links: {dead}"


def test_experiment_sections_exist_and_are_adjacent():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    i1 = readme.find("## Experiment 1: the judge calibration")
    i2 = readme.find("## Experiment 2: the self-check (grading twice)")
    assert 0 < i1 < i2, "experiment sections missing or misordered"
    between = readme[i1:i2]
    assert between.count("\n## ") == 0, "another top section sits between the two experiments"
