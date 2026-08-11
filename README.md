# business-scenario-judge

An AI judge taught to match one person's recorded rulings on business-style
customer-service scenarios. The taught judge (called "calibrated") is compared
against an untaught one (the "zero-shot baseline") on a held-out set of
scenarios that the teaching step never reads.

On the held-out scenarios the calibrated judge scored higher than the baseline, 53% against 40%, but the 95% uncertainty ranges overlap. This run does not establish a real difference.

A blunter yardstick: the majority-class baseline (a fake judge that always answers "A better", the most common ruling in the calibration half) also scores 53%, so the calibrated judge only ties it (`majority_label_baseline` in `metrics/results.json`).

## Check the numbers yourself (no API key needed)

```
pip install -r requirements.txt
python scoring/score.py --gold data/gold_set.jsonl --pred data/predictions.jsonl --out metrics/results.json
python scoring/retest_stats.py --retest data/retest.jsonl --items data/retest_items.json --out metrics/retest.json
```

Every judge answer is committed in `data/predictions.jsonl`, so everything
recomputes with no AI calls at all.

## What this is, exactly

A **constructed** demonstration, not a deployed system.

- **Scenarios** are real public data: MultiWOZ 2.2, MIT licence, Copyright (c)
  2019 Paweł Budzianowski. Each is the opening turns of a real service
  dialogue, ending on the customer's request.
- **Both candidate replies are AI-written.** One comes from `claude-sonnet-5`
  asked to answer well; the other from `claude-haiku-4-5-20251001` asked to
  answer plausibly while slipping in one realistic service flaw. Which reply
  appears first is a coin flip fixed in advance, so position carries no
  information.
- **No real client work and no real customer data.** Nothing here records how
  any deployed system behaved.

## Built with my own eval software

The gold set was made in **Eval Studio**, a local grading workbench I built
for this project: blind side-by-side grading with reason tags, a blind
re-grading pass that measures my own consistency, and a teaching layer that
explains each phase in place.

![The grading surface: six-phase board on top, the current phase's teaching in place, one real matchup below](docs/screenshots/eval-studio-grading.png)
*The grading surface, captured mid-run on a fresh instance. The six-phase
board tracks where the run is, and model names are hidden so a ruling cannot
lean on them.*

![The blind retest's results screen: 80% agreement, 55–93% interval, kappa 0.526](docs/screenshots/eval-studio-retest-results.png)
*This project's actual retest result: 80% self-agreement (12 of 15 matched),
55–93% Wilson interval, κ 0.526. The same one-person ceiling this README
states in prose.*

![A phase page: dated debugging history, cause-then-fix](docs/screenshots/eval-studio-phase-page.png)
*Each phase page records what ran and what went wrong: dated, cause-then-fix,
including the two live API failures fixed test-first during the judge runs.*

![The Learn hub: six phases with live status for completed ones](docs/screenshots/eval-studio-learn-hub.png)
*The six phases as they actually ran. A number appears only once its phase
has genuinely produced it.*

## Why measure a judge at all

Human rulings are the expensive part of evaluation: one published estimate
puts expert labels at $8 per sample ([Eugene Yan's survey of LLM
evaluators](https://eugeneyan.com/writing/llm-evaluators/), citing the
Shepherd paper), while an AI judge costs a small fraction of that. The cheap
judge is a defensible substitute only after its agreement with human judgment
is measured: OpenAI's guidance says to "validate agreement against your human
labels before optimizing for cost or latency" ([evaluation best
practices](https://developers.openai.com/api/docs/guides/evaluation-best-practices)),
and the MT-Bench study found strong AI judges reach over 80% agreement with
human preferences, the level humans reach with each other
([Zheng et al. 2023](https://arxiv.org/abs/2306.05685)). This repository
practices that measurement step, with uncertainty stated honestly at a small
sample size. It claims no cost saving of its own.

## What the numbers can and cannot support

- **Every ruling comes from one person.** That one judgment is the gold
  standard here, so every number inherits their consistency and their blind
  spots.
- **Ruling twice as a self-test: 80% over 15 scenarios ruled twice (95% Wilson range 55%–93% on the raw share; chance-corrected agreement, Cohen's κ, 0.526, given no strength label because such labels are not stable at n=15)**, with
  the two passes 2–4 days apart, a range because individual rulings carry no
  timestamps. The retest showed none of the first pass. After each retest
  ruling, one question asked whether the annotator remembered the earlier
  ruling; each answer was recorded once, at the first ruling of each scenario,
  and the question itself can influence later rulings. That side effect is
  disclosed here, not designed away.
  Counting only the 15 scenarios whose answer was no or unsure, agreement was
  80% (the restriction is not selective here: every answer was no). The 15
  retest scenarios are the fixed seeded draw committed in
  `data/retest_items.json` before the retest ran; agreement means an exact
  match on the three-way verdict (A better / B better / tie). A self-report
  cannot rule memory out, so 80% stays an upper bound on this one person's
  consistency.
- **The held-out set was fixed before any teaching existed**, 15 scenarios
  held out of 60, and the calibrated prompt is built only from the other 45.
- **Known biases are not controlled.** An AI judging AI text can favor text
  that resembles its own, and judges are sensitive to answer order. Order is
  randomised here, which handles position but not self-preference.
- The comparison is one run on 15 held-out scenarios. Read the 95% intervals
  in `metrics/results.md` before treating any gap as real.

## Layout

- `data/gold_set.jsonl`: scenarios, the annotator's ruling, split, and reason tags
- `data/predictions.jsonl`: every prediction from both judges
- `data/retest_items.json`: the fixed seeded draw of 15 scenarios ruled twice
- `data/retest.jsonl`: both rulings and the recall-probe answer for each retest scenario
- `scoring/retest_stats.py`, `metrics/retest.json`: the retest recompute and its committed output
- `judge/baseline_prompt.txt`, `judge/calibrated_prompt.txt`: the exact prompts (the calibrated prompt embeds the annotator's verbatim written notes for its example rulings)
- `metrics/results.json`, `metrics/results.md`: the recomputed numbers
- `scoring/score.py`: the recompute-only scorer
