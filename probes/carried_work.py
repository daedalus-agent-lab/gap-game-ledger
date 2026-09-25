#!/usr/bin/env python3
"""What exists on the tree, and what the record carries.

The copy rule is "the record is what git tracks". That rule is right about what it
carries and blind in one direction that costs an autonomous agent real work: a probe
written, run by hand, and never added to the index is on disk and in no case. The rule
does not drop it -- it never took it -- and no run says anything about it, because a
file the index does not mention is not a missing file, it is a file nobody asked about.

    python3 carried_work.py            # list what the record does not carry
    python3 carried_work.py --check    # exit 1 when there is any
    python3 carried_work.py --selftest # build a tree that has one, and require the exit

WHAT THIS IS NOT: it is not a claim that a file must be tracked. The suite's own record
of its last run is deliberately untracked and ignored, and ignored files are not listed
here. It says only that a file which is neither carried nor declared as output is work
nothing will tell you about.

WHAT THIS DOES NOT DO: it reads `git ls-files --others --exclude-standard`, so it inherits
whatever the tree's ignore rules hide -- a file made invisible by an over-broad ignore
pattern is invisible here too. And it cannot tell a forgotten probe from a scratch file
someone meant to leave: the two look the same, and the fix is a decision, not a reading.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def uncarried(tree):
    """Paths on disk that the index does not mention and the ignore rules do not hide."""
    out = git(["ls-files", "--others", "--exclude-standard"], tree)
    if out.returncode != 0:
        return None, out.stderr.strip() or "git ls-files failed"
    rows = [line for line in out.stdout.splitlines() if line.strip()]
    return sorted(rows), None


def selftest():
    """A tree that HAS work outside the record, and one that has not."""
    scratch = Path(tempfile.mkdtemp(prefix="carried-work-"))
    try:
        git(["init", "-q", "."], scratch)
        (scratch / "carried.txt").write_text("in the index\n")
        git(["add", "carried.txt"], scratch)
        (scratch / "written_but_not_added.py").write_text("# a probe nobody added\n")

        found, err = uncarried(scratch)
        assert err is None, err
        ok = found == ["written_but_not_added.py"]
        print(f"{'ok  ' if ok else 'FAIL'} a file on disk and not in the index is named: {found}")

        git(["add", "-A"], scratch)
        found2, err = uncarried(scratch)
        ok2 = found2 == []
        print(f"{'ok  ' if ok2 else 'FAIL'} once it is carried, nothing is named: {found2}")

        # The reading must not be satisfied by an empty tree: a repository with no files
        # at all also reports nothing, and that is not the same state.
        empty = Path(tempfile.mkdtemp(prefix="carried-work-empty-"))
        try:
            git(["init", "-q", "."], empty)
            found3, _ = uncarried(empty)
            ok3 = found3 == []
            tracked = git(["ls-files"], empty).stdout.split()
            print(f"{'ok  ' if ok3 and not tracked else 'FAIL'} an empty repository is a "
                  f"different state from a carried tree ({len(tracked)} tracked files)")
        finally:
            shutil.rmtree(empty, ignore_errors=True)
        return 0 if (ok and ok2 and ok3) else 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--tree", default=str(ROOT))
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    tree = Path(args.tree)
    rows, err = uncarried(tree)
    if err:
        print(f"REFUSED: {err}")
        return 2
    tracked = len(git(["ls-files"], tree).stdout.splitlines())
    print(f"the record carries {tracked} file(s) under {tree}")
    print(f"on disk and in no case    {len(rows)}")
    for row in rows[:50]:
        print(f"    uncarried  {row}")
    if args.check and rows:
        print("REFUSED: work exists on this tree that no case will read, and nothing else "
              "in the run mentions it")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
