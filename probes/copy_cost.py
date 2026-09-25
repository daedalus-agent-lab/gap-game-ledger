#!/usr/bin/env python3
"""What one case copies, and what the copy rule leaves behind.

`verify_claims.py` gives every case its own tree by copying this repository. The
copy rule decides what a case carries, and it is the rule that went wrong once:
it named three directories -- `verify`, `__pycache__`, `.git` -- written when
those were the large ones, and a package cache that arrived later was not on the
list. Every case then carried 130.0 MB of which 127.7 MB was uv's cache, 32 times
per run, and no exit code said a word about it.

The rule is now "the record is what git tracks", which cannot go stale the way a
list of names does. This probe measures both, from the same source the runner
uses -- it imports `ignore_for_the_record` from `verify_claims.py` instead of
restating it, so a probe and the runner cannot drift apart.

    python3 probes/copy_cost.py            # what a copy carries now
    python3 probes/copy_cost.py --check    # exit 1 on a budget breach or any rule error
    python3 probes/copy_cost.py --verbose  # the largest things a copy carries

`--check` reads two things and refuses on either. The budget is a number I chose:
a case must carry the record, not the tooling, and the record is a few megabytes
while a cache is three orders of magnitude larger, so a line between them catches
a cache without tripping on ordinary growth. The second reading is the property
itself, and needs no number from me: **every file a copy carries is tracked, and
every file it leaves out is not**, name by name over the whole tree. The first
version of this probe printed only the budget and called that a check.

WHAT THIS DOES NOT DO: it measures bytes and file counts and it compares the rule
with git's index; it does not show that a case NEEDS the files it carries. A copy
can be small, exact and still the wrong copy; that is what the cases test.
"""
import argparse
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE.parent

# A case must carry the record, not the tools that read it. The record is a few
# megabytes of source and JSON; a cache is three orders of magnitude larger. The
# budget sits between the two so that ordinary growth of the ledger never trips
# it and a single cache always does.
BUDGET_BYTES = 24 * 1024 * 1024

OLD_RULE = ("verify", "__pycache__", ".git")


def load_runner():
    """Import verify_claims so the probe and the runner share one copy rule."""
    spec = importlib.util.spec_from_file_location("verify_claims", LEDGER / "verify_claims.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def measure(root: Path, ignore) -> tuple[int, int, list[tuple[int, str]]]:
    """Bytes and files a copytree with this rule would write, and the largest top-levels.

    `ignore` follows `shutil.copytree`'s convention: it is asked with a directory
    and its entry names and RETURNS the names to leave out. The first version of
    this function assigned that answer straight to `dirnames`, which descends into
    exactly the directories the rule excludes -- so it measured a copy of the
    caches and reported the record. A probe of a rule has to use the rule the way
    the runner uses it.
    """
    total = 0
    files = 0
    per_top: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        drop = set(ignore(dirpath, dirnames))
        dirnames[:] = [d for d in dirnames if d not in drop]
        dropped_files = set(ignore(dirpath, filenames))
        for f in filenames:
            if f in dropped_files:
                continue
            p = Path(dirpath) / f
            try:
                size = p.stat().st_size
            except OSError:
                continue
            total += size
            files += 1
            rel = p.relative_to(root)
            top = rel.parts[0] if len(rel.parts) < 3 else "/".join(rel.parts[:2])
            per_top[top] = per_top.get(top, 0) + size
    largest = sorted(per_top.items(), key=lambda kv: -kv[1])
    return total, files, largest


def rule_errors(root: Path, ignore, tracked: set[str] | None) -> list[tuple[str, bool, bool]]:
    """Where the rule disagrees with the trackedness of what it was asked about.

    A budget is a number I chose; `rel not in tracked` is the property the rule is
    supposed to have, and it can be read directly. Every name the rule is asked
    about under `root` is compared with the one answer the record defines: a file
    git does not track must be left out, and a file git tracks must be carried.

    Returns (relative path, should be left out, was left out) for each disagreement.

    A directory is carried when anything under it is tracked, so the comparison
    uses the directory prefixes of the tracked paths as well as the paths
    themselves.
    """
    if tracked is None:
        return []
    prefixes = set()
    for t in tracked:
        parts = t.split("/")
        for i in range(1, len(parts)):
            prefixes.add("/".join(parts[:i]))
    wrong = []
    for dirpath, dirnames, filenames in os.walk(root):
        for names in (dirnames, filenames):
            left_out = set(ignore(dirpath, names))
            for name in names:
                rel = (Path(dirpath) / name).relative_to(root).as_posix()
                below = rel in tracked or rel in prefixes
                should = not below
                was = name in left_out
                if should != was:
                    wrong.append((rel, should, was))
        drop = set(ignore(dirpath, dirnames))
        dirnames[:] = [d for d in dirnames if d not in drop]
    return wrong


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    runner = load_runner()
    cases = len(runner.CASES)

    rule = runner.ignore_for_the_record(LEDGER)
    tracked = runner.tracked_files(LEDGER)
    now_bytes, now_files, largest = measure(LEDGER, rule)
    wrong = rule_errors(LEDGER, rule, tracked)
    old_rule = runner.FALLBACK_IGNORE[:3]
    old_bytes, old_files, _ = measure(
        LEDGER, lambda _d, names, keep=old_rule: [n for n in names if n in keep])

    print(f"cases declared by the runner: {cases}")
    print(f"per case, rule now in use:  {now_bytes:>12,} B  {now_files:>6} files")
    print(f"per case, the rule it replaced: {old_bytes:>8,} B  {old_files:>6} files")
    print(f"one full run:  {now_bytes * cases / 1e9:.2f} GB now, "
          f"{old_bytes * cases / 1e9:.2f} GB before")
    if largest:
        print(f"largest thing a copy carries: {largest[0][1] / 1e6:.1f} MB  {largest[0][0]}")
    if args.verbose:
        for name, size in largest[:10]:
            print(f"    {size / 1e6:9.3f} MB  {name}")

    ok = now_bytes <= BUDGET_BYTES
    print(f"budget {BUDGET_BYTES:,} B per case: {'held' if ok else 'EXCEEDED'} "
          f"({now_bytes:,} B)")
    if old_bytes > BUDGET_BYTES:
        print(f"the rule it replaced would have failed this budget by "
              f"{old_bytes / BUDGET_BYTES:.1f}x")
    # The stronger reading, and the one that needs no number from me: every file a
    # copy carries is tracked, and every file it leaves out is untracked.
    if tracked is None:
        print("the copy root is not the top of a checkout: git cannot say what the record is")
    else:
        print(f"every file a copy carries is tracked, and every one it leaves out is not: "
              f"{'yes' if not wrong else f'NO, {len(wrong)} disagree'}"
              f"  (over {len(tracked)} tracked paths)")
        for rel, should, was in wrong[:5]:
            print(f"    {rel}: should {'be left out' if should else 'be carried'}, "
                  f"was {'left out' if was else 'carried'}")
    if args.check and (not ok or wrong):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
