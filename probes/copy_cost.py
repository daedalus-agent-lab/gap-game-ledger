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
    python3 probes/copy_cost.py --check    # exit 1 if a copy exceeds the budget
    python3 probes/copy_cost.py --verbose  # the largest things a copy carries

WHAT THIS DOES NOT DO: it measures bytes and file counts, not whether a case
needs a file. A copy can be small and still wrong; that is what the cases
themselves test.
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    runner = load_runner()
    cases = len(runner.CASES)

    now_bytes, now_files, largest = measure(LEDGER, runner.ignore_for_the_record(LEDGER))
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
    if args.check and not ok:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
