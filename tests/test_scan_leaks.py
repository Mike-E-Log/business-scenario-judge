# tests/test_scan_leaks.py
"""Scanner tests. NEVER contain real tokens — fixtures use FAKE/FAKE_TOOL only."""
import subprocess
from pathlib import Path

import pytest

from scripts.scan_leaks import build_class_regexes, scan_bytes

FAKE = "leaktestuser"
FAKE_TOOL = "private/tools/secret_tool.py"

CLASS_FIXTURES = {
    "win-backslash-path": rf"path C:\Users\{FAKE}\Desktop\x.txt end",
    "win-forward-path": rf"path C:/Users/{FAKE}/Desktop/x.txt end",
    # literal text on disk is C:\\Users\\leaktestuser (doubled backslashes as content)
    "json-escaped-path": '{"p": "C:' + "\\\\" + "Users" + "\\\\" + FAKE + '"}',
    "gitbash-path": rf"cd /c/Users/{FAKE}/repo",
    "wsl-path": rf"ls /mnt/c/Users/{FAKE}/repo",
    "bare-username": rf"logged in as {FAKE} today",
    "tooling-path": r"python private\tools\secret_tool.py --run",
}


def _regexes():
    return build_class_regexes(FAKE, tooling=(FAKE_TOOL,))


def test_fixture_table_covers_every_class():
    assert set(CLASS_FIXTURES) == set(_regexes())


@pytest.mark.parametrize("cls", sorted(CLASS_FIXTURES))
def test_positive_control_per_class(cls):
    hits = scan_bytes(CLASS_FIXTURES[cls].encode(), _regexes())
    assert cls in hits, f"class {cls} has no working detector"


def test_negative_control_clean_text_does_not_fire():
    clean = (
        "Permission is hereby granted, free of charge, to any person obtaining "
        "a copy of this software, to deal in the Software without restriction. "
        'THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. '
        "The user leaktestuserX and Xleaktestuser are different tokens. "
        "C:/Users/someoneelse/x and /mnt/c/Users/other are other homes."
    )
    assert scan_bytes(clean.encode(), _regexes()) == set()


def test_bare_token_word_boundary_pins_the_without_collision():
    # audit #2: pin the anchoring with a prefix-shaped pair, so a later
    # "simplification" that breaks word-bounding cannot stay green
    rx = build_class_regexes("leaktest")
    assert scan_bytes(b"now leaktesting begins", rx) == set()      # substring: no fire
    assert scan_bytes(b"xleaktest suffix", rx) == set()            # substring: no fire
    assert "bare-username" in scan_bytes(b"user leaktest here", rx)


def test_utf16_encoded_leak_found():
    data = rf"C:\Users\{FAKE}\x".encode("utf-16-le")
    assert "win-backslash-path" in scan_bytes(data, _regexes())


def test_binary_blob_with_embedded_path_found():
    data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16 + rf"C:\Users\{FAKE}\out.png".encode() + b"\x00" * 16
    assert "win-backslash-path" in scan_bytes(data, _regexes())


from scripts.scan_leaks import main, scan_repo  # noqa: E402


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _make_repo(tmp_path, files):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)          # audit #2: tmp_path/"c2" callers need parents
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    _git(repo, "config", "user.email", "t@test.invalid")
    _git(repo, "config", "user.name", "t")
    for rel, data in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data if isinstance(data, bytes) else data.encode())
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "c1")
    return repo


def test_history_only_leak_found_even_after_gc(tmp_path):
    leak = rf"C:\Users\{FAKE}\secret.txt"
    repo = _make_repo(tmp_path, {"a.txt": leak})
    _git(repo, "rm", "-q", "a.txt")
    _git(repo, "commit", "-qm", "remove")
    _git(repo, "gc", "--aggressive", "--prune=now", "-q")  # forces packed objects
    hits = scan_repo(repo, build_class_regexes(FAKE))
    assert any(cls == "win-backslash-path" for cls, _, _ in hits)


def test_untracked_worktree_file_scanned(tmp_path):
    repo = _make_repo(tmp_path, {"clean.txt": "nothing here"})
    (repo / "notes.txt").write_text(rf"see C:/Users/{FAKE}/x", encoding="utf-8")
    hits = scan_repo(repo, build_class_regexes(FAKE))
    assert any(cls == "win-forward-path" for cls, _, _ in hits)


def test_clean_repo_scans_clean(tmp_path):
    repo = _make_repo(tmp_path, {"LICENSE": "without restriction WITHOUT WARRANTY"})
    assert scan_repo(repo, build_class_regexes(FAKE)) == []


def test_missing_token_config_is_exit_2(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path, {"a.txt": "clean"})
    monkeypatch.delenv("LEAK_TOKENS", raising=False)
    monkeypatch.delenv("USERNAME", raising=False)
    assert main([str(repo)]) == 2


def test_cli_exit_codes(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAK_TOKENS", FAKE)
    dirty = _make_repo(tmp_path, {"a.txt": rf"C:\Users\{FAKE}\x"})
    assert main([str(dirty)]) == 1
    clean = _make_repo(tmp_path / "c2", {"a.txt": "clean"})
    assert main([str(clean)]) == 0


def test_tokens_are_stripped(tmp_path, monkeypatch):
    # audit #2: an unstripped trailing newline in the secret builds a regex
    # that can never match -> CI green forever while scanning for nothing
    monkeypatch.setenv("LEAK_TOKENS", f"  {FAKE} \n")
    dirty = _make_repo(tmp_path, {"a.txt": rf"C:\Users\{FAKE}\x"})
    assert main([str(dirty)]) == 1


def test_slash_tokens_become_tooling_fragments(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAK_TOKENS", f"{FAKE},{FAKE_TOOL}")
    dirty = _make_repo(tmp_path, {"a.txt": f"run {FAKE_TOOL} now"})
    assert main([str(dirty)]) == 1


def test_backslash_authored_tooling_token_matches_forward_slash_text():
    # code-review finding: a Windows-native backslash token must still catch
    # the same fragment written with forward slashes (and vice versa)
    rx = build_class_regexes(FAKE, tooling=(r"private\tools\secret_tool.py",))
    assert "tooling-path" in scan_bytes(b"run private/tools/secret_tool.py now", rx)
    assert "tooling-path" in scan_bytes(rb"run private\tools\secret_tool.py now", rx)


def test_self_test_passes_with_tokens_and_fails_without(tmp_path, monkeypatch):
    monkeypatch.setenv("LEAK_TOKENS", f"{FAKE},{FAKE_TOOL}")
    assert main(["--self-test"]) == 0
    monkeypatch.delenv("LEAK_TOKENS", raising=False)
    monkeypatch.delenv("USERNAME", raising=False)
    assert main(["--self-test"]) == 2


def test_sweep_report_names_absolute_paths(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("LEAK_TOKENS", FAKE)
    clean = _make_repo(tmp_path, {"a.txt": "clean"})
    main([str(clean)])
    assert str(clean.resolve()) in capsys.readouterr().out
