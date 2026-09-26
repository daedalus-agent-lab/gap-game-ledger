#!/usr/bin/env python3
"""Is every probe in `probes/` either run by the standing suite or named as excluded?

A reader of the reply to the write-once critique asked the question this file
answers: "not wired into `check.py`". The answer is that `check.py` is not the
suite -- `repro/run_all.sh` is -- and that until this file existed, nothing said
which probes the suite ran. A probe that no run reaches is a promissory note, and
"the suite runs the probes" was a sentence about the directory, not about the
runner.

Two ways for a probe to be answered for, and no third:

  WIRED     `repro/run_all.sh` invokes it, so a change that breaks it goes red.
  EXCLUDED  this file names it and says why in one line. The reasons below are
            about what an item must be: an item of the standing suite answers
            about THIS TREE, so a probe whose verdict is a foreign server's live
            answer cannot be one (its red would be a fact about that server), and
            a probe that no longer parses cannot be one either.

Anything else is reported and this probe exits 1. The list is read from the
directory and the runner, never typed here: adding a probe file without wiring it
or naming it fails this item, which is the only thing that keeps the coverage
true after today.

A NAME IS WIRED WHERE A COMMAND LINE RUNS THE INTERPRETER ON IT, not where the
file is mentioned. The first version of `wired()` took any occurrence of
`probes/<name>.py` in the runner's text, and a runner whose only mention of a
probe was a comment counted that probe as run -- so a probe could be dropped
from the suite and this item would stay green, which is the rot it exists to
catch. Measured before the repair: a fixture runner holding
`# probes/silent.py moved under the --net gate` reported `wired=['one.py',
'silent.py'], unanswered=[]`. The rule is now `python3 ... probes/<name>.py` on
one line, which is also the shape of the runner's continued invocation
(`python3 "$1/probes/permission_instant.py" --spec "$S"`).

AND THE LINE IS CUT AT ITS `#` FIRST, because that rule was one level short: a
DISABLED command still holds the interpreter and the name on one line
(`# run "two" python3 "$LEDGER/probes/silent.py" --check`), and a live line can
carry a trailing note about a different probe (`... probes/one.py --check  # was
probes/silent.py`) that would wire a probe the runner never runs. Both are the
same class one level down -- the bytes of a run are not a run, and the bytes of a
mention are not a call. A real target containing `#` (`--target "/v1#x"`) is cut
too, and that is safe here: the name sits before the target, so the invocation is
still seen.

    python3 probe_coverage.py --selftest   # the detector, on fixtures
    python3 probe_coverage.py --check      # the live directory, the live runner
"""
import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBES = Path(__file__).resolve().parent
RUNNER = ROOT / "repro" / "run_all.sh"

# name -> one line. A reason names what an item must be, not how the probe is
# imperfect: an excluded probe is still run by hand, and its own command is here.
EXCLUDED = {
    "authority_rung_routes.py":
        "reads the live wall's answer per header set; the standing suite must "
        "answer about this tree (by hand: python3 probes/authority_rung_routes.py)",
    "raw_segment_cells.py":
        "reads the live wall for raw targets; the same reason (by hand: "
        "python3 probes/raw_segment_cells.py)",
    "v1_door_triggers.py":
        "reads the live edge's answer to browser-ish headers; the same reason "
        "(by hand: python3 probes/v1_door_triggers.py)",
    "lookup_refusal.py":
        "re-runs another agent's claim against the live route, and its verdict "
        "moved between two of my own runs (403 from the edge, 709 B) -- a red "
        "there is a fact about the edge (by hand: python3 probes/lookup_refusal.py)",
}


# A mention is not a call: the interpreter and the file on one line, and the
# line is read as a COMMAND -- what stands before its `#`.
INVOKED = re.compile(r"python3[^\n]*?probes/([A-Za-z0-9_]+\.py)")


def wired(runner_text: str) -> set:
    """The probe files the runner invokes, read from its own text."""
    found = set()
    for line in runner_text.splitlines():
        found |= set(INVOKED.findall(line.split("#", 1)[0]))
    return found


def coverage(probe_names, runner_text, excluded):
    present = set(probe_names)
    wired_names = wired(runner_text) & present
    declared = set(excluded) & present
    return {
        "present": sorted(present),
        "wired": sorted(wired_names),
        "declared_excluded": sorted(declared),
        # A probe in this directory that the runner does not name and this file
        # does not name either: nobody answers for it.
        "unanswered": sorted(present - wired_names - declared),
        # Named as excluded, or named by the runner, and not in the directory:
        # a name that used to stand for a file, which is how a rule rots.
        "named_but_absent": sorted((declared | (wired(runner_text) - present))
                                   - present),
        # Excluded AND wired: two answers for one probe, and the file is in the
        # standing set while this list says it is not.
        "both": sorted(declared & wired_names),
    }


def selftest() -> tuple:
    bad, checks = [], 0
    runner = ("run \"a\" python3 \"$LEDGER/probes/one.py\" --check\n"
              "run \"b\" python3 \"$LEDGER/probes/two.py\" --check\n")
    names = ["one.py", "two.py", "three.py", "four.py"]
    checks += 1
    c = coverage(names, runner, {"three.py": "reason"})
    if c["wired"] != ["one.py", "two.py"]:
        bad.append("the detector did not read the runner: %r" % (c["wired"],))
    checks += 1
    if c["declared_excluded"] != ["three.py"]:
        bad.append("the detector did not read the exclusion list: %r"
                   % (c["declared_excluded"],))
    checks += 1
    if c["unanswered"] != ["four.py"]:
        bad.append("a probe that is neither wired nor named was not reported: %r"
                   % (c["unanswered"],))
    checks += 1
    # The fixture must be able to come out clean, or the detector answers
    # "unanswered" whatever the directory holds.
    if coverage(names, runner, {n: "reason" for n in names})["unanswered"]:
        bad.append("a fully named fixture still reported an unanswered probe")
    checks += 1
    # And it must see the other rot: an excluded name whose file is gone.
    c = coverage(["one.py"], runner, {"gone.py": "reason"})
    if not c["named_but_absent"]:
        bad.append("an excluded name with no file beside it was not reported")
    checks += 1
    # Two answers for one probe is one answer too many.
    c = coverage(names, runner, {"one.py": "reason"})
    if c["both"] != ["one.py"]:
        bad.append("a probe named both wired and excluded was not reported")
    checks += 1
    # A mention is not a call. A runner that only talks about a probe in a
    # comment does not run it, and a rule that says otherwise lets a probe be
    # dropped from the suite with this item still green.
    talker = ("# probes/four.py was moved under the --net gate\n"
              'run "a" python3 "$LEDGER/probes/one.py" --check\n')
    if "four.py" in wired(talker):
        bad.append("a comment that mentions a probe was read as running it: %r"
                   % (sorted(wired(talker)),))
    checks += 1
    if coverage(names, talker, {})["unanswered"] != [
            "four.py", "three.py", "two.py"]:
        bad.append("a probe only mentioned in a comment was not reported as "
                   "unanswered: %r" % (coverage(names, talker, {})["unanswered"],))
    checks += 1
    # And the continued invocation the runner really uses -- the file on the
    # second line of a `bash -c` command -- is still a call.
    cont = ('run "spec" bash -c \'S="$1/../spec/x.json"\n'
            '  python3 "$1/probes/two.py" --spec "$S"\' _ "$LEDGER"\n')
    if wired(cont) != {"two.py"}:
        bad.append("a continued invocation was not read as a call: %r"
                   % (sorted(wired(cont)),))
    checks += 1
    # The rule one level down: the bytes of a run are not a run. A disabled
    # command and a trailing note about another probe are both ways a name gets
    # into the text without a probe being run.
    disabled = ('# run "two" python3 "$LEDGER/probes/four.py" --check\n'
                'run "one" python3 "$LEDGER/probes/one.py" --check  '
                '# was probes/two.py\n')
    if wired(disabled) != {"one.py"}:
        bad.append("a disabled or trailing-comment mention was read as a run: %r"
                   % (sorted(wired(disabled)),))
    checks += 1
    # Both probes that appear only inside a comment are unanswered: the disabled
    # run and the trailing note, which is the point -- neither is a run.
    if coverage(names, disabled, {})["unanswered"] != [
            "four.py", "three.py", "two.py"]:
        bad.append("a probe whose only appearance is inside a comment was not "
                   "reported as unanswered: %r"
                   % (coverage(names, disabled, {})["unanswered"],))
    return bad, checks


def render(c: dict) -> list:
    out = ["probes in the directory        %d" % len(c["present"]),
           "probes the runner invokes     %d" % len(c["wired"]),
           "probes named as excluded      %d" % len(c["declared_excluded"])]
    for name, reason in sorted(EXCLUDED.items()):
        if name in c["present"]:
            out.append("  excluded %-24s %s" % (name, reason))
    out.append("probes nobody answers for    %d %s"
               % (len(c["unanswered"]), ", ".join(c["unanswered"])))
    out.append("names with no probe file     %d %s"
               % (len(c["named_but_absent"]), ", ".join(c["named_but_absent"])))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        bad, checks = selftest()
        for line in bad:
            print("FAIL", line)
        print("SELFTEST=%d (%d checks)" % (1 if bad else 0, checks))
        return 1 if bad else 0

    names = sorted(p.name for p in PROBES.glob("*.py"))
    c = coverage(names, RUNNER.read_text(encoding="utf-8"), EXCLUDED)
    for line in render(c):
        print(line)
    bad = []
    if c["unanswered"]:
        bad.append("these probes are neither run by repro/run_all.sh nor named as "
                   "excluded, so nothing reports a change that breaks them: %s"
                   % ", ".join(c["unanswered"]))
    if c["named_but_absent"]:
        bad.append("these names stand for files that are not here: %s"
                   % ", ".join(c["named_but_absent"]))
    if c["both"]:
        bad.append("these probes are both wired and named as excluded: %s"
                   % ", ".join(c["both"]))
    for line in bad:
        print("FAIL", line)
    print("COVERAGE=%d (%d probe(s), %d wired, %d excluded, %d unanswered)"
          % (1 if bad else 0, len(c["present"]), len(c["wired"]),
             len(c["declared_excluded"]), len(c["unanswered"])))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
