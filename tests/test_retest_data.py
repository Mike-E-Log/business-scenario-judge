"""The blind-retest numbers published in README.md and metrics/results.md must
recompute from data committed in THIS repo (honesty item F): the fixed draw
(data/retest_items.json), both rounds of rulings plus the recall-probe answers
(data/retest.jsonl), and a recompute-only script (scoring/retest_stats.py)
whose committed output is metrics/retest.json."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RETEST_CMD = ("python scoring/retest_stats.py --retest data/retest.jsonl "
              "--items data/retest_items.json --out metrics/retest.json")


def _jsonl(p: Path):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _run_stats(retest: Path, items: Path, out: Path, *extra: str):
    return subprocess.run(
        [sys.executable, str(ROOT / "scoring" / "retest_stats.py"),
         "--retest", str(retest), "--items", str(items), "--out", str(out), *extra],
        capture_output=True, text=True)


def test_retest_draw_committed_and_consistent():
    draw_path = ROOT / "data" / "retest_items.json"
    rows_path = ROOT / "data" / "retest.jsonl"
    assert draw_path.exists(), "retest draw file not committed"
    assert rows_path.exists(), "retest rulings file not committed"
    draw = json.loads(draw_path.read_text(encoding="utf-8"))
    items = draw["items"]
    assert len(items) == 15 and len(set(items)) == 15
    gold = {r["item_id"] for r in _jsonl(ROOT / "data" / "gold_set.jsonl")}
    assert set(items) <= gold
    rows = _jsonl(rows_path)
    assert sorted(r["item_id"] for r in rows) == sorted(items)


def test_first_pass_labels_match_gold_set():
    rows_path = ROOT / "data" / "retest.jsonl"
    assert rows_path.exists(), "retest rulings file not committed"
    gold = {r["item_id"]: r["label"] for r in _jsonl(ROOT / "data" / "gold_set.jsonl")}
    for r in _jsonl(rows_path):
        assert r["first_label"] == gold[r["item_id"]]
        assert r["retest_label"] in (0, 1, 2)
        assert r["recall"] in ("yes", "no", "unsure")


def test_committed_retest_metrics_match_recomputation(tmp_path):
    script = ROOT / "scoring" / "retest_stats.py"
    committed_path = ROOT / "metrics" / "retest.json"
    assert script.exists(), "recompute script not committed"
    assert committed_path.exists(), "committed retest metrics not present"
    out = tmp_path / "retest.json"
    r = _run_stats(ROOT / "data" / "retest.jsonl", ROOT / "data" / "retest_items.json", out)
    assert r.returncode == 0, r.stderr
    recomputed = json.loads(out.read_text(encoding="utf-8"))
    committed = json.loads(committed_path.read_text(encoding="utf-8"))
    assert recomputed == committed
    # the published run: 12 of 15 matched, every probe answer "no"
    assert committed["n"] == 15
    assert committed["agreement"] == 0.8
    assert committed["recall_restricted"]["n"] == 15


def test_refuses_rows_outside_the_committed_draw(tmp_path):
    """A trimmed (or padded) rulings file must never yield a clean, different
    number against the committed draw — mismatch exits 1 with a message."""
    rows = _jsonl(ROOT / "data" / "retest.jsonl")
    trimmed = tmp_path / "trimmed.jsonl"
    trimmed.write_text("\n".join(json.dumps(r) for r in rows[:10]) + "\n",
                       encoding="utf-8")
    r = _run_stats(trimmed, ROOT / "data" / "retest_items.json", tmp_path / "out.json")
    assert r.returncode == 1
    assert "draw" in r.stderr.lower()
    assert not (tmp_path / "out.json").exists()


def test_published_prose_quotes_the_committed_numbers():
    committed_path = ROOT / "metrics" / "retest.json"
    assert committed_path.exists(), "committed retest metrics not present"
    m = json.loads(committed_path.read_text(encoding="utf-8"))
    # full clause, not a bare percentage — README independently contains an
    # unrelated "over 80% agreement" (MT-Bench), which a bare pin matches
    clause = f"{m['agreement']:.0%} over {m['n']} scenarios ruled twice"
    interval = f"{m['wilson_ci95'][0]:.0%}–{m['wilson_ci95'][1]:.0%}"
    kap = f"{m['cohen_kappa']:.3f}"
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    results = (ROOT / "metrics" / "results.md").read_text(encoding="utf-8")
    for text in (readme, results):
        assert clause in text
        assert kap in text
        assert interval in text
        assert "scoring/retest_stats.py" in text
        assert "--items data/retest_items.json" in text
    # the prose may only claim what the committed recall column records
    assert "did not eliminate recall" not in readme
    assert "reported remembering" not in readme
    assert "not selective here" in readme
    # the pointer must name the path that exists in this repo — and no other
    assert "`data/retest_items.json`" in readme
    assert "retest_items.json" not in readme.replace("data/retest_items.json", "")
    # hand-added README sections survive (a wholesale re-export would drop them)
    assert "docs/screenshots/eval-studio-grading.png" in readme
