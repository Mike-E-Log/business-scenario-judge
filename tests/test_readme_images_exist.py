# tests/test_readme_images_exist.py
"""Every image the README embeds must exist on disk — a deleted screenshot
with a surviving embed ships a broken image to a public recruiter-facing
page while every other test stays green (audit finding 2026-08-13)."""
import re
from pathlib import Path

REPO = Path(__file__).parents[1]


def _dangling(readme: str):
    paths = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme)
    return [p for p in paths if not p.startswith("http") and not (REPO / p).exists()]


def test_every_readme_image_exists_on_disk():
    dangling = _dangling((REPO / "README.md").read_text(encoding="utf-8"))
    assert not dangling, f"README embeds missing files: {dangling}"


def test_dangling_checker_fires():
    # positive control (house rule 2026-08-04)
    assert _dangling("![x](docs/screenshots/does-not-exist.png)")
