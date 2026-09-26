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
FILES = ("check.py", "fragments.py", "holds.py", "catches.json", "CLASSES.md")


def record_of_this_tree() -> list:
    """The files this tree has in the record: what git tracks, not a list of names.

    A hand list is a sentence about what the tree held when it was written: it named
    five files, and the sixth -- `verify_claims.py`, imported by check.py halfway down
    its own length -- was missing from the copy, so the case that asserts an untouched
    copy passes was red for as long as nobody ran this file. Where git cannot answer
    (an export, a bare copy), the list above is the fallback.
    """
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=HERE,
                             capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return list(FILES)
    names = [n for n in out.split("\0") if n]
    return names or list(FILES)


def run(tree: Path) -> int:
    return subprocess.run(
        [sys.executable, "check.py"], cwd=tree, capture_output=True
    ).returncode


def with_tree(mutate, extra_module="", mutate_tree=None):
    """Copy the ledger, apply `mutate(catches)`, return check.py's exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp)
        for name in record_of_this_tree():
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(HERE / name, target)
        if extra_module:
            with (tree / "fragments.py").open("a", encoding="utf-8") as fh:
                fh.write(extra_module)
        catches = json.loads((tree / "catches.json").read_text(encoding="utf-8"))
        mutate(catches)
        (tree / "catches.json").write_text(
            json.dumps(catches, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if mutate_tree:
            mutate_tree(tree)
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
        """Point a repeat at the class fragment itself: same bytes, no sighting.

        The repeat must carry the class's own probe, expected AND observed: that is
        what makes it the class probe rather than a second measurement. An earlier
        version substituted an expected of its own ("5"), so `same_measurement` was
        false, no refusal was due -- and the case read as passing only because the
        fixture tree was missing a module, so every case exited 1 for that reason.
        """
        import re

        for entry in catches["entries"]:
            for rep in entry.get("repeats") or []:
                if not isinstance(rep, dict) or not rep.get("fn"):
                    continue
                if str(entry["expected"]) == str(entry["observed"]):
                    continue
                rep["fn"] = re.findall(r"[A-Za-z_]\w*", entry["probe"])[0]
                rep["probe"] = entry["probe"]
                rep["expected"] = entry["expected"]
                rep["observed"] = entry["observed"]
                return
        raise AssertionError(
            "no entry with an object repeat and a divergent class probe to test with")

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

    def quote_is_prose(catches):
        """A line found in the message that is not a line of the fragment."""
        for entry in catches["entries"]:
            if entry.get("address"):
                entry["address_quote"] = "по словам автора, вот тот старый фрагмент"
                return

    cases.append(("a quote that is not a line of the fragment", with_tree(quote_is_prose), 1))

    def stale_index(tree):
        """The published index no longer describes the ledger."""
        with (tree / "CLASSES.md").open("a", encoding="utf-8") as fh:
            fh.write("\n## `a-class-that-was-never-added`\n")

    cases.append(("a stale CLASSES.md", with_tree(lambda c: None, mutate_tree=stale_index), 1))

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
