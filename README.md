# business-scenario-judge

## Can you trust an AI to grade another AI? This repo checks.

**An AI judge is only a trustworthy stand-in for a human after you measure how well it matches that human. This repo is that measurement, done honestly: every number recomputes from committed data, tests fail if the key numbers or honesty statements drift, and the unflattering result ships anyway. On the 15 test chats, a blind judge that gives the same answer every time scores 53%, and the taught judge also scores 53%: a tie.**

## The problem

- **Hand-checking is costly.** One published estimate: about $8 for each AI answer an expert grades ([Eugene Yan's survey of LLM evaluators](https://eugeneyan.com/writing/llm-evaluators/), citing the Shepherd paper).
- **So companies ask a second AI to do the grading.** That opens a new question: is the AI grader any good?
- **The standard first step is to measure it.** [OpenAI's guidance](https://developers.openai.com/api/docs/guides/evaluation-best-practices) says to "validate agreement against your human labels before optimizing for cost or latency". The MT-Bench study ([Zheng et al. 2023](https://arxiv.org/abs/2306.05685)) found strong AI judges reach over 80% agreement with human preferences, the level humans reach with each other.
- **This repo practices that first step**, and claims no cost saving of its own.

## What happened here

1. One person read real customer-service chats and picked between two AI answers, 60 times.
2. An AI judge was taught (the "calibrated" judge) using 45 of those picks.
3. The judge was tested on the other 15 chats, which were held out of the teaching step. Each chat's split is committed in `data/gold_set.jsonl`. The pre-run plan, with a dated correction note on its own timing claims, is in [PREREGISTRATION.md](PREREGISTRATION.md).

## The honest result

- **The score:** the taught judge matched the person 53% against 40% for the untaught judge (the "zero-shot baseline").
- **Why that is not a win yet:** the 95% uncertainty ranges overlap, so this run does not establish a real difference.
- **The blunter yardstick:** the majority-class baseline (a fake judge that ignores the chat and always answers "A better", the most common ruling in the teaching half) also scores 53%, so the taught judge only ties it (`majority_label_baseline` in `metrics/results.json`).
- **Printed, not hidden:** the tie is disclosed here and pinned by a test, so it cannot quietly disappear.

## Check the numbers yourself (a few minutes, no AI account needed)

```
pip install -r requirements.txt
python scoring/score.py --gold data/gold_set.jsonl --pred data/predictions.jsonl --out metrics/results.json
python scoring/retest_stats.py --retest data/retest.jsonl --items data/retest_items.json --out metrics/retest.json
```

Every judge answer is committed in `data/predictions.jsonl`, so everything recomputes with no AI calls at all.

## What this is, exactly

A **constructed** demonstration, not a deployed system.

- **The chats are real public data**: MultiWOZ 2.2, MIT licence, Copyright (c) 2019 Paweł Budzianowski. Each is the opening turns of a real service dialogue, ending on the customer's request.
- **Both candidate replies are AI-written.** One comes from `claude-sonnet-5` asked to answer well; the other from `claude-haiku-4-5-20251001` asked to answer plausibly while slipping in one realistic service flaw. Which reply appears first is a coin flip fixed in advance, so position carries no information.
- **No real client work and no real customer data.** Nothing here records how any deployed system behaved.

## Built with Eval Studio

The picks were made in **Eval Studio**, a local grading workbench I built for this project: blind side-by-side grading with reason tags, a blind re-grading pass that measures my own consistency, and a teaching layer that explains each phase in place.

![The grading surface: six-phase board on top, the current phase's teaching in place, one real matchup below](docs/screenshots/eval-studio-grading.png)
*The grading screen, captured mid-run on a fresh instance. Model names are hidden so a pick cannot lean on them.*

![The blind retest's results screen: 80% agreement, 55–93% interval, kappa 0.526](docs/screenshots/eval-studio-retest-results.png)
*The real self-check result: 80% match (12 of 15), with the same one-person ceiling this README states in words.*

![A phase page: dated debugging history, cause-then-fix](docs/screenshots/eval-studio-phase-page.png)
*Each phase page records what ran and what broke: dated, cause then fix, including the two live API failures fixed test-first during the judge runs.*

![The Learn hub: six phases with live status for completed ones](docs/screenshots/eval-studio-learn-hub.png)
*The six phases as they really ran. A number appears only once its phase has genuinely produced it.*

## What the numbers can and cannot support

- **Every ruling comes from one person.** That one judgment is the gold standard here, so every number inherits their consistency and their blind spots.
- **The self-check: 80% over 15 scenarios ruled twice** (12 of 15 matched).
  - The same 15 chats were ruled a second time, 2–4 days later (a range because individual rulings carry no timestamps). The retest showed none of the first pass.
  - The 95% Wilson range on that share is 55%–93%. Chance-corrected agreement (Cohen's κ) is 0.526, given no strength label because such labels are not stable at n=15.
  - After each retest ruling, one question asked whether the annotator remembered the earlier ruling; answers were recorded once, at each scenario's first ruling, and the question itself can influence later rulings, a side effect disclosed here, not designed away.
  - Counting only the 15 scenarios whose answer was no or unsure, agreement was 80% (the restriction is not selective here: every answer was no).
  - The 15 retest scenarios are the fixed seeded draw committed in `data/retest_items.json` before the retest ran. Agreement means an exact match on the three-way verdict (A better / B better / tie).
  - A self-report cannot rule memory out, so 80% stays an upper bound on this one person's consistency.
- **Known biases are not controlled.** An AI judging AI text can favor text that resembles its own, and judges are sensitive to answer order. Order is randomised here, which handles position but not self-preference.
- The comparison is one run on 15 held-out scenarios. Read the 95% intervals in `metrics/results.md` before treating any gap as real.

## Layout

- `data/gold_set.jsonl`: scenarios, the person's ruling, split, and reason tags
- `data/predictions.jsonl`: every prediction from both judges
- `data/retest_items.json`: the fixed seeded draw of 15 scenarios ruled twice
- `data/retest.jsonl`: both rulings and the recall-probe answer for each retest scenario
- `scoring/retest_stats.py`, `metrics/retest.json`: the retest recompute and its committed output
- `judge/baseline_prompt.txt`, `judge/calibrated_prompt.txt`: the exact prompts (the calibrated prompt embeds the annotator's verbatim written notes for its example rulings)
- `metrics/results.json`, `metrics/results.md`: the recomputed numbers
- `scoring/score.py`: the recompute-only scorer
