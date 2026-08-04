# scripts/scan_leaks.py
"""Leak scanner: fails when configured identity tokens appear anywhere in a repo.

Tokens come from the environment (LEAK_TOKENS comma-separated, else USERNAME) —
NEVER from committed literals or command-line literals. A LEAK_TOKENS entry
containing a slash is a tooling-path fragment; the rest are usernames.
Exit codes: 0 clean / self-test OK, 1 hits found / self-test failed,
2 configuration error.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}


def build_class_regexes(username: str, tooling: tuple[str, ...] = ()) -> dict[str, re.Pattern]:
    u = re.escape(username)
    pats = {
        "win-backslash-path": rf"C:\\Users\\{u}",
        "win-forward-path": rf"C:/Users/{u}",
        "json-escaped-path": rf"C:\\\\Users\\\\{u}",
        "gitbash-path": rf"/c/Users/{u}",
        "wsl-path": rf"/mnt/c/Users/{u}",
        # word-bounded so "without" never matches a username like a home-dir name;
        # its per-class positive control proves anchoring didn't disable it
        "bare-username": rf"(?<![A-Za-z0-9_]){u}(?![A-Za-z0-9_])",
    }
    if tooling:  # never a committed literal — arrives via LEAK_TOKENS
        # normalize to forward slashes first so a backslash-authored token
        # still matches forward-slash occurrences (and vice versa)
        pats["tooling-path"] = "|".join(
            re.escape(t.replace("\\", "/")).replace("/", r"[\\/]+") for t in tooling)
    return {name: re.compile(p, re.IGNORECASE) for name, p in pats.items()}


def scan_bytes(data: bytes, regexes: dict[str, re.Pattern]) -> set[str]:
    hits: set[str] = set()
    for text in (data.decode("utf-8", "ignore"), data.decode("utf-16-le", "ignore")):
        for name, rx in regexes.items():
            if rx.search(text):
                hits.add(name)
    return hits


def _iter_history_blobs(repo: Path):
    out = subprocess.run(["git", "-C", str(repo), "rev-list", "--objects", "--all"],
                         capture_output=True, text=True, check=True)
    seen = set()
    for line in out.stdout.splitlines():
        sha, _, path = line.partition(" ")
        if sha in seen:
            continue
        seen.add(sha)
        typ = subprocess.run(["git", "-C", str(repo), "cat-file", "-t", sha],
                             capture_output=True, text=True).stdout.strip()
        if typ != "blob":
            continue
        data = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", sha],
                              capture_output=True).stdout
        yield sha, path, data


def _iter_worktree_files(repo: Path):
    for p in repo.rglob("*"):
        if p.is_file() and not (SKIP_DIRS & set(p.parts)):
            yield p


def scan_repo(repo: Path, regexes: dict[str, re.Pattern], history: bool = True) -> list[tuple[str, str, str]]:
    hits: list[tuple[str, str, str]] = []
    if history and (repo / ".git").exists():
        for sha, path, data in _iter_history_blobs(repo):
            for cls in sorted(scan_bytes(data, regexes)):
                hits.append((cls, f"blob:{sha[:12]}", path))
    for f in _iter_worktree_files(repo):
        for cls in sorted(scan_bytes(f.read_bytes(), regexes)):
            hits.append((cls, f"file:{f.relative_to(repo)}", str(f.relative_to(repo))))
    return hits


def _class_samples(username: str, tooling: tuple[str, ...]) -> dict[str, str]:
    """One synthetic sample per class, built from the CONFIGURED tokens."""
    samples = {
        "win-backslash-path": "C:\\Users\\" + username + "\\control",
        "win-forward-path": f"C:/Users/{username}/control",
        "json-escaped-path": "C:" + "\\\\" + "Users" + "\\\\" + username,
        "gitbash-path": f"/c/Users/{username}/control",
        "wsl-path": f"/mnt/c/Users/{username}/control",
        "bare-username": f" {username} ",
    }
    if tooling:
        samples["tooling-path"] = tooling[0]
    return samples


def self_test(usernames: list[str], tooling: tuple[str, ...]) -> bool:
    """Every class must fire on a sample built from the real config —
    an absence guard needs a positive control."""
    for u in usernames:
        regexes = build_class_regexes(u, tooling)
        for cls, text in _class_samples(u, tooling).items():
            if cls not in scan_bytes(text.encode(), regexes):
                print(f"SELF-TEST FAIL: class {cls} did not fire for a configured token",
                      file=sys.stderr)
                return False
    print(f"SELF-TEST OK: all classes fired for {len(usernames)} username token(s)")
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="*")
    ap.add_argument("--no-history", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    tokens = [t.strip() for t in os.environ.get("LEAK_TOKENS", "").split(",") if t.strip()]
    if not tokens and os.environ.get("USERNAME", "").strip():
        tokens = [os.environ["USERNAME"].strip()]
    if not tokens:
        print("CONFIG ERROR: no tokens (set LEAK_TOKENS or USERNAME)", file=sys.stderr)
        return 2  # loud, never a vacuous pass
    usernames = [t for t in tokens if "/" not in t and "\\" not in t]
    tooling = tuple(t for t in tokens if "/" in t or "\\" in t)
    if not usernames:
        print("CONFIG ERROR: no username token configured", file=sys.stderr)
        return 2
    if a.self_test:
        return 0 if self_test(usernames, tooling) else 1
    if not a.repos:
        print("CONFIG ERROR: no repo paths given", file=sys.stderr)
        return 2
    total = 0
    for r in a.repos:
        repo = Path(r)
        if not repo.exists():
            print(f"CONFIG ERROR: missing repo path {repo}", file=sys.stderr)
            return 2
        for u in usernames:
            for cls, loc, path in scan_repo(repo, build_class_regexes(u, tooling),
                                            history=not a.no_history):
                print(f"HIT {cls} {repo.name} {loc} {path}")
                total += 1
        print(f"SCANNED {repo.resolve()}")   # sweep evidence must name absolute paths
    print(f"{'FAIL' if total else 'CLEAN'}: {total} hit(s) across {len(a.repos)} repo(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
