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

**The `before` column must not be a property of the machine that ran it.** The first
version of this report printed, as its headline, the two rules measured on whatever
tree it happened to be standing in. On the author's tree the old rule carried
130,008,502 B per case and the new one 1,254,875 B -- a 100x improvement. On a clean
clone of the same commit a second machine measured the old rule at 1,254,770 B: the
same as the new one, to the byte. The 130 MB was not a property of either rule; it was
the owner's untracked `.uvcache`, present in his tree and absent from the clone. A
reader reproducing the report got `1,254,770 -> 1,254,770` and could not tell "the
repair was unnecessary" from "the repair is already done". The probe therefore now
BUILDS the difference it reports: it makes a tiny git checkout, plants an untracked
cache-shaped directory of a declared size in it, and measures both rules there. That
reading is reproducible from a clone because the probe manufactures its subject.

WHAT THIS DOES NOT DO: it measures bytes and file counts and it compares the rule
with git's index; it does not show that a case NEEDS the files it carries. A copy
can be small, exact and still the wrong copy; that is what the cases test.
"""
import argparse
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE.parent

# A case must carry the record, not the tools that read it. The record is a few
# megabytes of source and JSON; a cache is three orders of magnitude larger. The
# budget sits between the two so that ordinary growth of the ledger never trips
# it and a single cache always does.
BUDGET_BYTES = 24 * 1024 * 1024

OLD_RULE = ("verify", "__pycache__", ".git")

# The planted cache, declared here and not read off any tree. Small enough to build in
# milliseconds, large enough that the two rules cannot agree about it by accident.
PLANTED_DIR = ".uvcache"
PLANTED_FILES = 8
PLANTED_BYTES = 4 * 1024 * 1024


def tree_state(root: Path) -> str:
    """Which commit this reading was taken on, and how far the worktree has moved.

    A copy carries the CONTENT of the worktree, not the index: a tracked file modified
    and not committed changes the byte count of the copy while the commit id stands
    still. Two readings of the same commit differing by 105 bytes were exactly that.
    """
    def git(*args: str) -> str:
        try:
            out = subprocess.run(["git", *args], cwd=root, capture_output=True,
                                 text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return ""
        return out.stdout.strip() if out.returncode == 0 else ""

    head = git("rev-parse", "--short", "HEAD") or "not a checkout"
    dirty = [ln for ln in git("status", "--porcelain").splitlines() if ln.strip()]
    return f"{head}, {len(dirty)} path(s) moved in the worktree"


def plant_fixture(root: Path) -> Path:
    """A tiny checkout that carries an untracked cache -- the difference, manufactured.

    Built here rather than found in the working tree, so that the comparison between
    the two rules reproduces from a clean clone. The fixture lives in the system
    temporary directory on purpose: it is a git repository of its own, and a second
    checkout inside the ledger root would appear in every other probe's file walk.
    """
    (root / "record").mkdir(parents=True)
    (root / "record" / "a.py").write_text("a = 1\n", encoding="utf-8")
    (root / "record" / "b.json").write_text('{"b": 2}\n', encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "add", "--", "record"], cwd=root, check=True, capture_output=True)
    cache = root / PLANTED_DIR
    cache.mkdir()
    per_file = PLANTED_BYTES // PLANTED_FILES
    for i in range(PLANTED_FILES):
        (cache / f"blob{i}").write_bytes(b"\0" * per_file)
    return root


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
    print(f"this reading was taken on: {tree_state(LEDGER)}")
    print(f"on this tree, rule now in use:  {now_bytes:>12,} B  {now_files:>6} files")
    print(f"on this tree, the rule it replaced: {old_bytes:>8,} B  {old_files:>6} files")
    print(f"    (both numbers above move with this worktree, not with the commit: a copy "
          f"carries the content it finds)")
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
    # The reproducible comparison: the same two rules on a fixture the probe builds.
    planted_ok = None
    with tempfile.TemporaryDirectory(prefix="copy-cost-fixture-") as td:
        fx = plant_fixture(Path(td))
        fx_rule = runner.ignore_for_the_record(fx)
        fx_tracked = runner.tracked_files(fx)
        fx_now_b, fx_now_f, _ = measure(fx, fx_rule)
        fx_old_b, fx_old_f, _ = measure(
            fx, lambda _d, names, keep=old_rule: [n for n in names if n in keep])
        difference = fx_old_b - fx_now_b
        planted_ok = (difference == PLANTED_BYTES
                      and fx_tracked is not None and len(fx_tracked) == 2
                      and fx_now_f == 2
                      and fx_old_f == 2 + PLANTED_FILES)
        print(f"fixture built by this probe, {PLANTED_BYTES:,} B in {PLANTED_FILES} "
              f"files under {PLANTED_DIR}/ (untracked, cache-shaped):")
        print(f"    rule now in use:       {fx_now_b:>12,} B  {fx_now_f:>6} files")
        print(f"    the rule it replaced:  {fx_old_b:>12,} B  {fx_old_f:>6} files")
        print(f"    the two rules differ by exactly the planted cache: "
              f"{'yes' if planted_ok else 'NO'}  ({difference:,} B, planted {PLANTED_BYTES:,} B)")

    if args.check and (not ok or wrong or not planted_ok):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
