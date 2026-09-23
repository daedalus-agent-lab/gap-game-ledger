#!/usr/bin/env python3
"""Prove the ledger's gate is live: a green run must mean something.

check.py exits 0 when every probe reproduces its recorded observation and
differs from its recorded expectation. A gate that never fails is decoration,
so this script copies the ledger to a scratch directory, breaks it on purpose
one way at a time, and asserts check.py notices each time.

    python3 selftest.py

Exit 0 means every mutation was caught and the untouched copy still passed.
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ("check.py", "fragments.py", "holds.py", "catches.json")


def run(tree: Path) -> int:
    return subprocess.run(
        [sys.executable, "check.py"], cwd=tree, capture_output=True
    ).returncode


def with_tree(mutate):
    """Copy the ledger, apply `mutate(catches)`, return check.py's exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp)
        for name in FILES:
            shutil.copy(HERE / name, tree / name)
        catches = json.loads((tree / "catches.json").read_text(encoding="utf-8"))
        mutate(catches)
        (tree / "catches.json").write_text(
            json.dumps(catches, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return run(tree)


def first_object_repeat(catches):
    for entry in catches["entries"]:
        for rep in entry.get("repeats") or []:
            if isinstance(rep, dict):
                return entry, rep
    raise AssertionError("no object-form repeat in the ledger to test with")


def main() -> int:
    cases = []

    cases.append(("untouched copy passes", with_tree(lambda c: None), 0))

    def flip_observed(catches):
        _, rep = first_object_repeat(catches)
        rep["observed"] = "999"

    cases.append(("a repeat's observed value is wrong", with_tree(flip_observed), 1))

    def same_as_expected(catches):
        _, rep = first_object_repeat(catches)
        rep["observed"] = rep["expected"]

    cases.append(("a repeat's expected == observed", with_tree(same_as_expected), 1))

    def drop_field(catches):
        _, rep = first_object_repeat(catches)
        del rep["promise"]

    cases.append(("a repeat is missing a field", with_tree(drop_field), 1))

    def flip_class_probe(catches):
        catches["entries"][0]["observed"] = "999"

    cases.append(("a class probe's observed value is wrong", with_tree(flip_class_probe), 1))

    bad = 0
    for name, code, want in cases:
        ok = code == want
        bad += 0 if ok else 1
        print(f"{'ok  ' if ok else 'FAIL'} {name:<42} exit {code} (want {want})")
    print()
    print(f"cases {len(cases)}  failed {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
