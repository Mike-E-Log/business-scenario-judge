# tests/test_check_mode.py
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).parents[1]


def _run(args):
    return subprocess.run([sys.executable, str(REPO / "scoring" / "score.py"), *map(str, args)],
                          capture_output=True, text=True)


def _write_fixture(tmp_path):
    gold = ([{"item_id": f"h{k}", "question": "q", "answer_a": "a", "answer_b": "b",
              "label": 0, "split": "heldout", "tags": ["wrong-slot-value"]} for k in range(10)]
            + [{"item_id": f"c{k}", "question": "q", "answer_a": "a", "answer_b": "b",
                "label": 1, "split": "calibration", "tags": ["unhelpful-hedging"]} for k in range(4)])
    preds = [{"item_id": g["item_id"], "judge": j, "label": g["label"]}
             for g in gold for j in ("baseline", "calibrated")]
    gp, pp = tmp_path / "gold.jsonl", tmp_path / "pred.jsonl"
    gp.write_text("\n".join(json.dumps(g) for g in gold), encoding="utf-8")
    pp.write_text("\n".join(json.dumps(p) for p in preds), encoding="utf-8")
    return gp, pp


def test_check_matches_after_normal_write(tmp_path):
    gp, pp = _write_fixture(tmp_path)
    out = tmp_path / "results.json"
    assert _run(["--gold", gp, "--pred", pp, "--out", out]).returncode == 0
    r = _run(["--gold", gp, "--pred", pp, "--out", out, "--check"])
    assert r.returncode == 0 and "OK" in r.stdout


def test_check_detects_mismatch_and_never_overwrites(tmp_path):
    gp, pp = _write_fixture(tmp_path)
    out = tmp_path / "results.json"
    _run(["--gold", gp, "--pred", pp, "--out", out])
    tampered = out.read_text(encoding="utf-8").replace("1.0", "0.9", 1)
    out.write_text(tampered, encoding="utf-8")
    r = _run(["--gold", gp, "--pred", pp, "--out", out, "--check"])
    assert r.returncode == 1
    assert out.read_text(encoding="utf-8") == tampered   # untouched
