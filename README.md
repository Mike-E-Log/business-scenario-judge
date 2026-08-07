# business-scenario-judge

An LLM judge calibrated to one annotator's recorded rulings on business-style
customer-service scenarios, compared against a zero-shot baseline on a held-out
split that no calibration code ever reads.

On the held-out split the calibrated judge scored higher than the baseline, 53% against 40%, but the 95% intervals overlap — this run does not establish a real difference.

## Reproduce the metrics (no API key needed)

```
pip install -r requirements.txt
python scoring/score.py --gold data/gold_set.jsonl --pred data/predictions.jsonl --out metrics/results.json
```

Every judge prediction is committed in `data/predictions.jsonl`, so the numbers
recompute with no model calls at all.

## What this is, exactly

This is a **constructed** demonstration, not a deployment.

- **Scenarios** are real public data: MultiWOZ 2.2, MIT licence, Copyright (c)
  2019 Paweł Budzianowski. Each one is the opening turns of a genuine
  task-oriented dialogue, ending on a customer's request.
- **Both candidate replies are generated.** One comes from
  `claude-sonnet-5` asked to answer well; the other from
  `claude-haiku-4-5-20251001` asked to answer plausibly while including a
  single realistic service flaw. Which one appears first is a coin flip fixed
  in advance, so position carries no information.
- **No real client work, and no real customer data, is involved here.** Nothing
  in this repository records how any deployed system behaved.

## Built with my own eval software

The gold set here was produced in **Eval Studio**, a local evaluation
workbench I built for this project: blind pairwise grading with reason tags,
a blind retest that measures my own consistency, and a teaching layer that
explains each phase of the protocol in place.

![The grading surface: six-phase board on top, the current phase's teaching in place, one real matchup below](docs/screenshots/eval-studio-grading.png)
*The grading surface, captured mid-run on a fresh instance. The six-phase
board tracks where the run is, and model attribution is stripped so a ruling
cannot pattern-match its way out of judging.*

![The blind retest's results screen: 80% agreement, 55–93% interval, kappa 0.526](docs/screenshots/eval-studio-retest-results.png)
*This project's actual retest result: 80% self-agreement (12 of 15 matched),
55–93% Wilson interval, κ 0.526 — the same single-annotator ceiling this
README discloses in prose.*

![A phase page: dated debugging history, cause-then-fix](docs/screenshots/eval-studio-phase-page.png)
*Each phase page records what ran and what went wrong — dated,
cause-then-fix, including the two live API failures fixed test-first during
the judge runs.*

![The Learn hub: six phases with live status for completed ones](docs/screenshots/eval-studio-learn-hub.png)
*The six phases as they actually ran. Results stay payload-gated: a number
appears only once its phase has genuinely produced it.*

## Why validate a judge at all

Human labels are the expensive part of evaluation — one published estimate
puts expert annotation at $8 per sample ([Eugene Yan's survey of LLM
evaluators](https://eugeneyan.com/writing/llm-evaluators/), citing the
Shepherd paper) — while an LLM judge costs a small fraction of that per
verdict. The cheap judge is only a defensible substitute if its agreement
with human judgment is measured first: OpenAI's evaluation guidance says to
"validate agreement against your human labels before optimizing for cost or
latency" ([evaluation best
practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)),
and the MT-Bench study reported strong LLM judges reaching over 80%
agreement with human preferences — the level humans reach with each other
([Zheng et al. 2023](https://arxiv.org/abs/2306.05685)). That measurement —
judge against human rulings, with intervals honest about a small n — is
what this repository practices. It claims no cost saving of its own; it
demonstrates the validation step that makes replacing expensive labels with
a cheap judge defensible.

## What the numbers can and cannot support

- **All labels come from a single annotator.** One person's judgment is the
  gold standard here, so every number inherits their consistency and their
  blind spots.
- **Self-agreement on a blind retest: 80% over 15 scenarios ruled twice (95% Wilson interval 55%–93% on the raw proportion; chance-corrected Cohen's κ 0.526, reported without a strength label — band labels are not stable at n=15)**, and
  the two passes were 2–4 days apart — a range, because individual labels carry no timestamps. The retest showed none of the first pass.
  After each retest ruling a one-question probe asked whether the annotator
  remembered the earlier ruling; answers were recorded once, at the first
  ruling of each scenario, and the probe itself can influence later rulings —
  that reactivity is disclosed here, not designed away.
  Restricted to the 15 scenarios whose probe answer was no/unsure, agreement was 80%. The 15 retest scenarios are the fixed seeded
  draw committed in `retest_items.json` before the retest ran; agreement is
  exact match on the three-way verdict (A better / B better / tie). A gap of
  a few days did not eliminate recall; the self-agreement figure is
  an upper bound on this annotator's consistency.
- **The split was fixed before calibration existed** — 15 held-out
  of 60 — and the calibrated prompt is built only from the
  calibration side.
- **Known biases not controlled for.** An LLM judging LLM output can show
  self-preference toward text resembling its own, and judges are known to be
  sensitive to answer position. Order is randomised, which addresses position
  but not self-preference.
- The comparison is one run on 15 held-out scenarios. Read the
  confidence intervals in `metrics/results.md` before treating any gap as real.

## Layout

- `data/gold_set.jsonl` — scenarios, the annotator's ruling, split, and reason tags
- `data/predictions.jsonl` — every prediction from both judges
- `judge/baseline_prompt.txt`, `judge/calibrated_prompt.txt` — the exact prompts  (the calibrated prompt embeds the annotator's verbatim written notes for its example rulings)

- `metrics/results.json`, `metrics/results.md` — the recomputed numbers
- `scoring/score.py` — the recompute-only scorer
