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


def with_tree(mutate, extra_module=""):
    """Copy the ledger, apply `mutate(catches)`, return check.py's exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp)
        for name in FILES:
            shutil.copy(HERE / name, tree / name)
        if extra_module:
            with (tree / "fragments.py").open("a", encoding="utf-8") as fh:
                fh.write(extra_module)
        catches = json.loads((tree / "catches.json").read_text(encoding="utf-8"))
        mutate(catches)
        (tree / "catches.json").write_text(
            json.dumps(catches, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return run(tree)


TWIN = '''

def clamp_twin(val, low, high):
    """A second name for the class clamp, with the same logic."""
    return min(max(val, low), high)


NAMESPACES["clamp-no-range-validation"]["clamp_twin"] = clamp_twin
'''

SECOND_CLASS = '''

NAMESPACES["clamp-second-name"] = {"clamp_twin": clamp_twin}
'''


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

    def same_as_class(catches):
        """Point a repeat at the class fragment itself: same bytes, no sighting."""
        import re

        for entry in catches["entries"]:
            for rep in entry.get("repeats") or []:
                if not isinstance(rep, dict) or not rep.get("fn"):
                    continue
                name = re.findall(r"[A-Za-z_]\w*", entry["probe"])[0]
                rep["fn"] = name
                rep["probe"] = entry["probe"]
                rep["expected"] = "5"
                rep["observed"] = entry["observed"]
                return

    cases.append(("a repeat points at the class fragment", with_tree(same_as_class), 1))

    def same_logic_other_name(catches):
        """A repeat whose fragment differs in name but not in logic.

        The twin is appended to the copied fragments.py, so the class gets a
        second name for its own bytes; the gate must refuse it.
        """
        for entry in catches["entries"]:
            if entry["class"] != "clamp-no-range-validation":
                continue
            for rep in entry.get("repeats") or []:
                if isinstance(rep, dict):
                    rep["fn"] = "clamp_twin"
                    rep["probe"] = "clamp_twin(5, 10, 0)"
                    rep["expected"] = "5"
                    rep["observed"] = "0"
                    return

    cases.append(
        (
            "a repeat whose fragment is the class logic",
            with_tree(same_logic_other_name, extra_module=TWIN),
            1,
        )
    )

    def flip_class_probe(catches):
        catches["entries"][0]["observed"] = "999"

    cases.append(("a class probe's observed value is wrong", with_tree(flip_class_probe), 1))

    def second_class_same_logic(catches):
        """Two class names for one shape: the ledger counts the same lie twice."""
        catches["entries"].append(
            {
                "class": "clamp-second-name",
                "promise": "clamped to the inclusive range",
                "fact": "no range validation",
                "probe": "clamp_twin(5, 10, 0)",
                "expected": "5",
                "observed": "0",
                "lang": "python",
            }
        )

    cases.append(
        (
            "a class is another class under a new name",
            with_tree(second_class_same_logic, extra_module=TWIN + SECOND_CLASS),
            1,
        )
    )

    def unquoted_address(catches):
        """An address with no line from the message is a direction, not evidence."""
        for entry in catches["entries"]:
            if entry.get("address"):
                del entry["address_quote"]
                return

    cases.append(("an address with no line from the message", with_tree(unquoted_address), 1))

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
