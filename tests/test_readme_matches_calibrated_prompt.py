# tests/test_readme_matches_calibrated_prompt.py
"""The README's exemplar-count claim must equal what judge/calibrated_prompt.txt
actually embeds — audit finding 2026-08-13: the prose said the prompt carries
45 rulings; the committed file carries 12 worked examples (plus tag tallies
over all 45). No other test reads the prompt files, so this drift was
invisible to the suite."""
import re
from pathlib import Path

REPO = Path(__file__).parents[1]


def test_readme_exemplar_count_matches_the_committed_prompt():
    prompt = (REPO / "judge" / "calibrated_prompt.txt").read_text(encoding="utf-8")
    n = len(re.findall(r"^Example \d+$", prompt, re.M))
    assert n > 0, "prompt file carries no numbered examples at all"
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    claims = [int(c) for c in re.findall(r"carries (\d+) of", readme)]
    assert claims, "README no longer states how many rulings the prompt carries"
    assert all(c == n for c in claims), (
        f"README claims the prompt carries {claims} worked examples; "
        f"judge/calibrated_prompt.txt contains {n}")
