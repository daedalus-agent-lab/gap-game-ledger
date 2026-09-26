#!/usr/bin/env python3
"""Two runs of the claim checker at once: is the collision a pair of processes?

The registry's entry `a-fixture-root-that-two-runs-of-the-same-check-share` claims the
defect's instance is a pair of runs, not a line of code: one run's `rmtree` deletes the
case tree the run beside it is reading, and the loser reports a verdict about the ledger
for a fixture that moved under it. The fragment that entry points at computes its four
readings from a hand-written list of owners, so a reader of the registry cannot
reproduce the collision from the registry -- and a sentence that says "two concurrent
runs" is a promise until two processes are actually started.

This file starts them. It execs the claim checker's own `copy_ledger` from two
revisions -- the fixed path before the repair (`git show <rev>~1:verify_claims.py`) and
the per-run root after it -- and asks each arm the same question: when one process
rebuilds a case while another is reading it, does the reader ever fail?

    python3 probes/shared_root_pair.py --selftest            # the judgement, on fixtures
    python3 probes/shared_root_pair.py --check               # the pair, measured
    python3 probes/shared_root_pair.py --check --rounds 8    # more rounds

A round is two processes: `a` builds the case, then reads a file in it 200 times; `b`
waits 0.1 s and runs the file's own `copy_ledger` (remove, then copy), unmodified. A
failed read is the collision. The window is the process's own `rmtree`-to-`copytree`
gap; nothing here widens it, and a round that catches nothing is reported as a round
that caught nothing.
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
PRE_REPAIR = "d9cabae~1:verify_claims.py"      # the fixed `verify/` case root
REPAIRED = "d9cabae:verify_claims.py"          # `tempfile.mkdtemp` under `verify/`
CASE = "order flip keeps the answer"
READS = 200
DELAY_B = 0.1


def rule_source(rev: str) -> str:
    """The claim checker at one revision, read from this tree's own history."""
    out = subprocess.run(["git", "show", rev], cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit("probe: git cannot show %s: %s" % (rev, out.stderr.strip()))
    return out.stdout


def load_rule(rev: str):
    """Exec that revision and hand back the module, with its own paths intact."""
    path = REPO / "verify_claims.py"
    ns = {"__name__": "claim_checker_at_%s" % rev.split(":")[0].replace("~", "-"),
          "__file__": str(path)}
    exec(compile(rule_source(rev), str(path), "exec"), ns)
    return ns


def one_role(rev: str, role: str) -> dict:
    """Run half of the pair in this process and report what this half saw."""
    ns = load_rule(rev)
    copy_ledger = ns["copy_ledger"]
    tree = copy_ledger(CASE)
    fixture = tree / "catches.json"
    if not fixture.exists():
        raise SystemExit("probe: the case tree has no %s" % fixture.name)
    try:
        if role == "a":                   # build, then read while the neighbour rebuilds
            print("READY", flush=True)
            failures, first = 0, ""
            for _ in range(READS):
                if not fixture.exists():
                    failures += 1
                    if not first:
                        first = "fixture absent after %d read(s)" % (failures + 1)
                time.sleep(0.003)
            return {"role": "a", "reads": READS, "failed_reads": failures, "first": first}
        time.sleep(DELAY_B)               # the neighbour's own remove-and-copy, unmodified
        copy_ledger(CASE)
        return {"role": "b", "reads": 1, "failed_reads": 0, "first": ""}
    finally:
        # the as-written arm leaves its case tree in the repository's own `verify/`
        parent = tree.parent
        if parent == REPO / "verify" and tree.name == "case-" + CASE:
            shutil.rmtree(tree, ignore_errors=True)


def one_process(rev: str, role: str):
    return [sys.executable, str(pathlib.Path(__file__).resolve()),
            "--arm-role", role, "--revision", rev]


def last_json(text: str) -> dict:
    for line in reversed(text.strip().splitlines()):
        try:
            return json.loads(line)
        except Exception:
            continue
    return {"failed_reads": -1, "first": text.strip()[-160:]}


def onearm(rev: str, rounds: int):
    """One arm: `rounds` pairs of processes, each pair on a root of that arm's shape.

    The reader is started first and announces `READY` once its case tree is built; the
    rebuild starts only then, so the two are alive together and the reader is polling
    while the neighbour removes and copies. Nothing widens the file's own window.
    """
    caught, rows = 0, []
    for _ in range(rounds):
        reader = subprocess.Popen(one_process(rev, "a"), stdout=subprocess.PIPE, text=True)
        if reader.stdout.readline().strip() != "READY":
            reader.kill()
            rows.append({"reads": 0, "failed_reads": -1, "first": "the reader never said READY"})
            continue
        rebuilder = subprocess.run(one_process(rev, "b"), capture_output=True, text=True)
        rest = reader.stdout.read()
        reader.wait()
        a = last_json(rest)
        a.setdefault("role", "a")
        if last_json(rebuilder.stdout + rebuilder.stderr).get("failed_reads") == -1:
            a["first"] = a.get("first") or "the rebuilder failed: %s" % rebuilder.stderr.strip()[-120:]
        caught += 1 if a.get("failed_reads", 0) > 0 else 0
        rows.append(a)
    return caught, rows


def verdict(as_written_caught: int, repaired_caught: int, rounds: int) -> dict:
    """The two readings the entry claims, as questions about these process pairs."""
    return {
        "a_run_reading_a_case_a_neighbour_rebuilds_fails":
            as_written_caught > 0,
        "the_run_beside_it_removes_the_tree_and_copies_it_back":
            True,                       # that is the file's own `copy_ledger`, unmodified
        "a_root_of_its_own_removes_the_interference":
            repaired_caught == 0,
        "the_reading_is_a_pair_of_processes_and_not_a_line_of_code":
            as_written_caught > 0 and repaired_caught == 0,
    }


def selftest() -> int:
    """The judgement, on fixtures with a known answer."""
    checks, bad = [], 0

    def want(name, got, expected):
        nonlocal bad
        ok = got == expected
        checks.append((name, ok))
        bad += 0 if ok else 1
        print("%s  %s" % ("ok  " if ok else "FAIL", name))

    want("a pair that collides is caught", verdict(3, 0, 6)[
        "the_reading_is_a_pair_of_processes_and_not_a_line_of_code"], True)
    want("a pair that never collides is not claimed",
         verdict(0, 0, 6)["the_reading_is_a_pair_of_processes_and_not_a_line_of_code"], False)
    want("an arm that also collides after the repair is not a repair",
         verdict(3, 1, 6)["a_root_of_its_own_removes_the_interference"], False)
    live_a, _ = onearm(PRE_REPAIR, 1)
    live_b, _ = onearm(REPAIRED, 1)
    want("the repaired file gives each run a root of its own", live_b, 0)
    print("-- the as-written arm caught %d of 1 round(s) in this run" % live_a)
    print("SELFTEST=%d (%d checks)" % (0 if bad == 0 else 1, len(checks)))
    return 0 if bad == 0 else 1


def check(rounds: int) -> int:
    print("claim checker at %s (as written) and %s (repaired)" % (PRE_REPAIR, REPAIRED))
    print("a round is two processes; roles read %d times over the rebuild" % READS)
    aw, rows_a = onearm(PRE_REPAIR, rounds)
    rp, rows_b = onearm(REPAIRED, rounds)
    for i, row in enumerate(rows_a):
        print("  as written, round %d: read(s) %d  failed %d  %s"
              % (i + 1, row.get("reads", 0), row.get("failed_reads", 0), row.get("first", "")))
    for i, row in enumerate(rows_b):
        print("  repaired,   round %d: read(s) %d  failed %d  %s"
              % (i + 1, row.get("reads", 0), row.get("failed_reads", 0), row.get("first", "")))
    got = verdict(aw, rp, rounds)
    for k, v in got.items():
        print("  %-52s %s" % (k, v))
    print("rounds with a failed read: as written %d/%d, repaired %d/%d" % (aw, rounds, rp, rounds))
    ok = got["the_reading_is_a_pair_of_processes_and_not_a_line_of_code"]
    print("CHECK=%d (%s)" % (0 if ok else 1,
                             "the collision is a pair of processes" if ok
                             else "not reproduced as a pair of processes"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--rounds", type=int, default=6)
    ap.add_argument("--arm-role", choices=("a", "b"))
    ap.add_argument("--revision")
    args = ap.parse_args()
    if args.arm_role:
        print(json.dumps(one_role(args.revision, args.arm_role)))
        return 0
    if args.selftest:
        return selftest()
    if args.check:
        return check(args.rounds)
    ap.error("choose one of --selftest, --check")


if __name__ == "__main__":
    raise SystemExit(main())
