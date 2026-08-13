# tests/test_readme_honesty_disclosures.py
"""The README's honesty disclosures and citation chain are load-bearing prose
with no numeric pin — a prose pass can drop them while every other test stays
green (audit finding 2026-08-11). This pin makes the README's own claim true:
the tests fail if the honesty text drifts."""
from pathlib import Path

REPO = Path(__file__).parents[1]

DISCLOSURES = [
    # "A demonstration built for..." replaced "constructed" and the
    # no-real-client-data line was removed, both on operator order 2026-08-13
    "A demonstration built for this measurement",
    "Every ruling comes from one person",           # one-person ceiling
    "Known biases are not controlled",               # self-preference caveat
    "the same model that wrote reply one",           # judge = reply-one author
    "upper bound on this one person's consistency",
    "eugeneyan.com/writing/llm-evaluators",         # $8 estimate source
    "citing the Shepherd paper",                    # $8 sub-attribution
    "developers.openai.com/api/docs/guides/evaluation-best-practices",
    "before optimizing for cost or latency",        # OpenAI quote, verbatim scope
    "arxiv.org/abs/2306.05685",                     # MT-Bench
    "MultiWOZ 2.2",
    "PREREGISTRATION.md",                           # pre-run plan + its correction note
    "one changed ruling ends the tie",              # tie fragility (audit 2026-08-13)
    "26 of 59",                                     # planted-flaw axis check (wording
    # pin only: the number's source data is deliberately not in this repo,
    # and the sentence must keep saying so)
    "cannot be rechecked from the files here",
]


def _missing(text: str):
    return [d for d in DISCLOSURES if d not in text]


def test_readme_keeps_every_honesty_disclosure_and_citation():
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    missing = _missing(readme)
    assert not missing, (
        f"a prose pass dropped {missing} — the README claims the tests catch "
        "exactly this drift"
    )


def test_missing_checker_fires():
    # positive control: an absence guard that cannot fail guards nothing
    assert _missing("empty readme") == DISCLOSURES


def test_readme_has_no_em_dashes():
    # publication voice register (operator-ratified): zero em-dashes in README;
    # metrics/results.md keeps its two table N/A cells and is not covered here
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert readme.count("—") == 0
