#!/usr/bin/env python3
"""Is every probe in `probes/` either run by the standing suite or named as excluded?

A reader of the reply to the write-once critique asked the question this file
answers: "not wired into `check.py`". The answer is that `check.py` is not the
suite -- `repro/run_all.sh` is -- and that until this file existed, nothing said
which probes the suite ran. A probe that no run reaches is a promissory note, and
"the suite runs the probes" was a sentence about the directory, not about the
runner.

WHAT THIS FILE READS, and the four corrections that reading needed:

  THE UNIVERSE IS WHAT A READER COULD MISTAKE FOR A PROBE, not what ends in `.py`.
    The first version took `PROBES.glob("*.py")` and printed "probes in the
    directory 33" while seven shell probes sat beside them, outside the claim and
    named by nobody. A program named `*.sh`, or any file marked executable, is a
    candidate now; a file whose suffix is a data suffix or whose name carries a
    timestamp is reported as data; anything else is reported as a kind this file
    does not know, which is a failure and not a silence.

  A WIRED PROBE IS ATTRIBUTED TO THE RUN THAT REACHES IT. Nine of the runner's
    invocations sit inside `if [ "$NET" = 1 ]`, so a plain `bash repro/run_all.sh`
    runs none of them -- and the count printed inside that same run said "29
    wired". The count now splits: on every run, and only under `--net`, with the
    gated names printed. A coverage number that does not say which run it covers
    is the defect it was written to catch.

  A NAME IS WIRED WHERE A COMMAND LINE RUNS THE INTERPRETER ON IT, not where the
    file is mentioned. The first version of `wired()` took any occurrence of
    `probes/<name>.py` in the runner's text, and a runner whose only mention of a
    probe was a comment counted that probe as run -- measured on a fixture holding
    `# probes/silent.py moved under the --net gate`: `wired=['one.py',
    'silent.py'], unanswered=[]`. The rule is `python3 ... probes/<name>.py` on one
    line, and THE LINE IS CUT AT ITS `#` FIRST, because that rule was one level
    short: a disabled command still holds the interpreter and the name on one line,
    and a live line can carry a trailing note about a different probe.

  AND THE NAME THE EXCLUSION LIST CARRIES IS THE NAME THAT IS CHECKED. The first
    version intersected the list with the files present (`set(excluded) & present`)
    before looking for names with no file behind them, so an excluded probe could
    be deleted -- or mistyped -- and the item stayed green and silent. Every name
    in either list is compared with the directory, present or not.

Two ways for a probe to be answered for, and no third:

  WIRED     `repro/run_all.sh` invokes it, so a change that breaks it goes red.
            A live-reading probe may be an item when the runner's own gate says
            the claim is conditioned on `--net`, and when what it does under that
            gate is compare a live reading against something kept in this tree.
  EXCLUDED  this file names it and says why in one line. The reason is READ, not
            printed: it must not be empty, it must not state a reading (a numeral
            in a reason is a number nothing re-measures), and it must not claim
            the network for a file whose own bytes never mention one. Probes
            excluded today only report the wall's answer, compare it against
            nothing kept here, or are hand transcripts with no verdict at all.

Anything else is reported and this probe exits 1.

    0  every probe is answered for
    1  a probe nobody answers for, a name with no file behind it, a probe named
       twice, or an exclusion whose reason fails the three rules above
    2  this file cannot judge: no runner, or a runner whose text invokes no probe
       in this directory (a runner that loops over the directory cannot be read by
       this rule, and a green here would be a sentence)

    python3 probe_coverage.py --selftest   # the detector, on fixtures
    python3 probe_coverage.py --check      # the live directory, the live runner
"""
import argparse
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROBES = Path(__file__).resolve().parent
RUNNER = ROOT / "repro" / "run_all.sh"

PROBE_SUFFIXES = {".py", ".sh"}
DATA_SUFFIXES = {".json", ".txt", ".bin", ".log", ".md"}
STAMPED = re.compile(r"_\d{8}T\d{4}Z")

# name -> one line. A reason names what an item must be, not how the probe is
# imperfect: an excluded probe is still run by hand, and its own command is here.
EXCLUDED = {
    "authority_rung_routes.py":
        "reports the live wall's answer per header set and compares it against "
        "nothing kept in this tree, so a red there would be a fact about the wall "
        "(by hand: python3 probes/authority_rung_routes.py)",
    "raw_segment_cells.py":
        "reports the live wall's answers for raw targets and compares them against "
        "nothing kept here (by hand: python3 probes/raw_segment_cells.py)",
    "v1_door_triggers.py":
        "reports the live edge's answer to browser-ish headers and compares it "
        "against nothing kept here (by hand: python3 probes/v1_door_triggers.py)",
    "lookup_refusal.py":
        "re-runs another agent's claim against the live route, and its verdict "
        "moved between two runs of my own on the same bytes, so a red there is a "
        "fact about the edge (by hand: python3 probes/lookup_refusal.py)",
    "door_cells_hermione.sh":
        "a hand transcript against the live board: it prints what the wall said "
        "and decides nothing (by hand: bash probes/door_cells_hermione.sh)",
    "door_cells_hermione_b.sh":
        "a hand transcript against the live board, the same shape (by hand: bash "
        "probes/door_cells_hermione_b.sh)",
    "lookup_alphabet.sh":
        "a hand transcript against the live board, the same shape (by hand: bash "
        "probes/lookup_alphabet.sh)",
    "lookup_boundary.sh":
        "a hand transcript against the live board, the same shape (by hand: bash "
        "probes/lookup_boundary.sh)",
    "lookup_refusal.sh":
        "a hand transcript of another agent's claim, run against the live board "
        "(by hand: bash probes/lookup_refusal.sh)",
    "lookup_variants.sh":
        "a hand transcript against the live board, the same shape (by hand: bash "
        "probes/lookup_variants.sh)",
}

# A mention is not a call: the interpreter and the file on one line, and the line
# is read as a COMMAND -- what stands before its `#`.
# The interpreter, then the file on the same line: `python3` for a python probe,
# `bash` for the shell program among them.
INVOKED = re.compile(r"(?:python3|bash)[^\n]*?probes/([A-Za-z0-9_.-]+\.(?:py|sh))")
# The runner's network gate, and the `fi` at column 0 that closes it.
GATE = re.compile(r'^\s*if\s+\[\s*"\$NET"\s*=\s*1\s*\]\s*;\s*then\s*$')

# The words a reason uses to say "this reads a foreign server", and the words a
# probe's own bytes must show before that reason is allowed to say so.
NET_WORDS = ("http://", "https://", "curl", "urllib", "socket", "requests",
             "live board", "live wall", "live edge", "live route")
NET_MARKERS = ("http", "curl", "urllib", "socket", "requests")
# A standalone numeral: digits not glued to letters (`v1_door_triggers.py` and
# `python3` are names, `403` and `709` are readings).
NUMERAL = re.compile(r"(?<![A-Za-z0-9_])\d+(?![A-Za-z0-9_])")
# A probe named inside an exclusion reason: the citation a reader reproduces by hand.
# A probe named inside an exclusion reason: the citation a reader reproduces by hand.
# The name must carry an extension, so a trailing full stop or a path with a directory
# prefix yields no citation rather than a name that is not in the directory.
NAME_IN_REASON = re.compile(r"probes/([A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+)")


def runner_calls(runner_text: str) -> dict:
    """name -> [(line number, only under --net?), ...], read from the runner."""
    calls = {}
    gated = False
    for number, line in enumerate(runner_text.splitlines(), 1):
        if GATE.match(line):
            gated = True
            continue
        if gated and line.startswith("fi"):
            gated = False
            continue
        for name in INVOKED.findall(line.split("#", 1)[0]):
            calls.setdefault(name, []).append((number, gated))
    return {name: sorted(hits) for name, hits in calls.items()}


def classify(files) -> dict:
    """(name, executable?) pairs -> candidates, data, and kinds not known here."""
    candidates, data, unknown = [], [], []
    for name, is_executable in files:
        suffix = Path(name).suffix
        if suffix in PROBE_SUFFIXES or is_executable:
            candidates.append(name)
        elif suffix in DATA_SUFFIXES or STAMPED.search(name):
            data.append(name)
        else:
            unknown.append(name)
    return {"candidates": sorted(candidates), "data": sorted(data),
            "unknown": sorted(unknown)}


def coverage(candidate_names, runner_text: str, excluded: dict) -> dict:
    present = set(candidate_names)
    calls = runner_calls(runner_text)
    named = set(calls)
    wired = named & present
    every_run = sorted(n for n in wired if not all(g for _, g in calls[n]))
    only_net = sorted(n for n in wired if all(g for _, g in calls[n]))
    declared = sorted(set(excluded) & present)
    answered = wired | set(declared)
    return {
        "present": sorted(present),
        "wired_on_every_run": every_run,
        "only_under_net": only_net,
        "declared_excluded": declared,
        # A candidate this directory holds that neither the runner nor this list
        # names: nobody answers for it.
        "unanswered": sorted(present - answered),
        # A name either list carries with no file behind it -- how a rule rots.
        # Both lists are compared with the directory in full, not intersected.
        "named_but_absent": sorted((named | set(excluded)) - present),
        "both": sorted(wired & set(excluded)),
    }


def present_in_directory() -> set:
    """The names a reason's citation may point at: the FILES this directory holds.

    Files, not the probes among them. The refusal says "not a file in this directory",
    and a reason may cite the rows a probe wrote, which are here and are not probes.
    """
    return {p.name for p in PROBES.iterdir() if p.is_file()}


def judgeable(c: dict) -> bool:
    """The runner's text invokes at least one probe in this directory."""
    return bool(c["wired_on_every_run"] or c["only_under_net"])


def reason_problems(excluded: dict, present_names, read_text) -> list:
    """The exclusion reasons, read: present, unattributed, and about the right file."""
    bad = []
    for name in sorted(excluded):
        reason = excluded[name]
        if not reason.strip():
            bad.append("the exclusion of %s carries no reason" % name)
            continue
        numerals = NUMERAL.findall(reason)
        if numerals:
            bad.append("the reason for %s states a reading (%s) that nothing "
                       "re-measures" % (name, ", ".join(numerals)))
        cited = NAME_IN_REASON.findall(reason)
        missing = sorted({c for c in cited if c not in present_names})
        if missing:
            bad.append("the reason for %s names %s, which is not a file in this "
                       "directory" % (name, ", ".join(missing)))
        if name in present_names and any(w in reason for w in NET_WORDS):
            text = read_text(name)
            if not any(m in text for m in NET_MARKERS):
                bad.append("the reason for %s says it reads the network, and its "
                           "own bytes never mention one" % name)
    return bad


def selftest() -> tuple:
    bad, checks = [], 0
    runner = ("run \"a\" python3 \"$LEDGER/probes/one.py\" --check\n"
              "if [ \"$NET\" = 1 ]; then\n"
              "  run \"b\" python3 \"$LEDGER/probes/two.py\" --check\n"
              "fi\n"
              "run \"c\" python3 \"$LEDGER/probes/three.py\" --check\n")
    names = ["one.py", "two.py", "three.py", "four.py"]
    checks += 1
    c = coverage(names, runner, {})
    if c["wired_on_every_run"] != ["one.py", "three.py"]:
        bad.append("the detector did not read the ungated invocations: %r"
                   % (c["wired_on_every_run"],))
    checks += 1
    if c["only_under_net"] != ["two.py"]:
        bad.append("an invocation inside the --net gate was not attributed to the "
                   "gated run: %r" % (c["only_under_net"],))
    checks += 1
    checks += 1
    c = coverage(names, runner, {"four.py": "reason"})
    if c["declared_excluded"] != ["four.py"]:
        bad.append("the detector did not read the exclusion list: %r"
                   % (c["declared_excluded"],))
    checks += 1
    if c["unanswered"]:
        bad.append("a fully answered fixture still reported an unanswered probe: %r"
                   % (c["unanswered"],))
    checks += 1
    if coverage(names, runner, {})["unanswered"] != ["four.py"]:
        bad.append("a probe that is neither wired nor named was not reported: %r"
                   % (coverage(names, runner, {})["unanswered"],))
    checks += 1
    # The other rot: an excluded name whose file is gone. The name must be
    # reported, and it must be THIS name -- the first version intersected the
    # list with the files present and answered the question with 'two.py'.
    c = coverage(["one.py"], runner, {"gone.py": "reason"})
    if "gone.py" not in c["named_but_absent"]:
        bad.append("an excluded name with no file beside it was not reported: %r"
                   % (c["named_but_absent"],))
    checks += 1
    if c["declared_excluded"]:
        bad.append("a name with no file behind it was counted among the exclusions: %r"
                   % (c["declared_excluded"],))
    checks += 1
    # And a name the runner invokes whose file is gone is reported too.
    c = coverage(["one.py"], runner, {})
    if "two.py" not in c["named_but_absent"]:
        bad.append("a wired name with no file beside it was not reported: %r"
                   % (c["named_but_absent"],))
    checks += 1
    checks += 1
    c = coverage(names, runner, {"one.py": "reason"})
    if c["both"] != ["one.py"]:
        bad.append("a probe named both wired and excluded was not reported")
    checks += 1
    # A mention is not a call.
    talker = ("# probes/four.py was moved under the --net gate\n"
              'run "a" python3 "$LEDGER/probes/one.py" --check\n')
    if "four.py" in runner_calls(talker):
        bad.append("a comment that mentions a probe was read as running it: %r"
                   % (sorted(runner_calls(talker)),))
    checks += 1
    if coverage(names, talker, {})["unanswered"] != ["four.py", "three.py", "two.py"]:
        bad.append("a probe only mentioned in a comment was not reported as "
                   "unanswered: %r" % (coverage(names, talker, {})["unanswered"],))
    checks += 1
    cont = ('run "spec" bash -c \'S="$1/../spec/x.json"\n'
            '  python3 "$1/probes/two.py" --spec "$S"\' _ "$LEDGER"\n')
    if set(runner_calls(cont)) != {"two.py"}:
        bad.append("a continued invocation was not read as a call: %r"
                   % (sorted(runner_calls(cont)),))
    checks += 1
    disabled = ('# run "two" python3 "$LEDGER/probes/four.py" --check\n'
                'run "one" python3 "$LEDGER/probes/one.py" --check  '
                '# was probes/two.py\n')
    if set(runner_calls(disabled)) != {"one.py"}:
        bad.append("a disabled or trailing-comment mention was read as a run: %r"
                   % (sorted(runner_calls(disabled)),))
    checks += 1
    # A runner whose text invokes nothing here cannot be judged, and a green
    # would be a sentence: the caller must be able to tell.
    empty = "bash -c 'for p in probes/*.py; do python3 \"$p\"; done'\n"
    if judgeable(coverage(names, empty, {})):
        bad.append("a runner that invokes no probe by name was called judgeable")
    checks += 1
    if not judgeable(coverage(names, runner, {"four.py": "reason"})):
        bad.append("a runner that invokes probes was called unjudgeable")
    checks += 1
    # The universe: a shell program is a candidate, a saved reading is not, and a
    # kind this file does not know is a failure rather than a silence.
    kinds = classify([("a.py", False), ("b.sh", False), ("c.json", False),
                      ("d_20260926T0154Z.junk", False), ("e", True), ("f.csv", False)])
    if kinds["candidates"] != ["a.py", "b.sh", "e"]:
        bad.append("the universe of candidates is wrong: %r" % (kinds["candidates"],))
    checks += 1
    if kinds["data"] != ["c.json", "d_20260926T0154Z.junk"]:
        bad.append("a saved reading was not read as data: %r" % (kinds["data"],))
    checks += 1
    if kinds["unknown"] != ["f.csv"]:
        bad.append("a file of an unknown kind was not reported: %r"
                   % (kinds["unknown"],))
    checks += 1
    # The reasons are read, not printed.
    read = lambda name: {"live_wall.py": "curl https://example.invalid/v1\n",
                         "offline.py": "print('nothing here')\n"}.get(name, "")
    checks += 1
    if not reason_problems({"x.py": ""}, {"x.py"}, read):
        bad.append("an exclusion with no reason was accepted")
    checks += 1
    if not reason_problems({"x.py": "ran it 403 times"}, {"x.py"}, read):
        bad.append("a reason stating a reading was accepted")
    checks += 1
    if not reason_problems({"offline.py": "reads the live wall"},
                           {"offline.py"}, read):
        bad.append("a reason claiming the network for an offline probe was accepted")
    checks += 1
    if reason_problems({"live_wall.py": "reads the live wall, and compares it "
                                       "against nothing kept here"},
                       {"live_wall.py"}, read):
        bad.append("a reason whose probe really does read the network was refused")
    checks += 1
    if reason_problems({"absent.py": "reads the live wall"}, set(), read):
        bad.append("a reason was refused for a probe whose bytes cannot be read")
    checks += 1
    # A reason that cites a probe must cite one this directory holds: the citation is
    # how a reader reproduces the exclusion by hand, and a stale name is a dead end.
    if not reason_problems({"x.py": "ran it by hand: bash probes/gone.py"},
                           {"x.py"}, read):
        bad.append("a reason naming a probe that is not here was accepted")
    checks += 1
    if reason_problems({"x.py": "ran it by hand: python3 probes/here.py"},
                       {"x.py", "here.py"}, read):
        bad.append("a reason naming a probe that is here was refused")
    checks += 1
    # A full stop after the name and a path with a directory prefix are not citations of
    # a probe: neither may be read as one and refused.
    if reason_problems({"x.py": "ran it by hand: python3 probes/here.py."},
                       {"x.py", "here.py"}, read):
        bad.append("a citation followed by a full stop was refused")
    checks += 1
    if reason_problems({"x.py": "kept beside probes/sub/here.py"},
                       {"x.py", "here.py"}, read):
        bad.append("a citation with a directory prefix was refused")
    checks += 1
    # The refusal says "not a file in this directory", so the set it is judged against
    # must be the files in the directory -- not only the probes among them. A reason may
    # cite a data file it left beside the probe, and a message about FILES that refuses a
    # file would be false in its own words.
    if reason_problems({"x.py": "the rows it wrote are in probes/rows.json"},
                       {"x.py", "rows.json"}, read):
        bad.append("a citation of a data file this directory holds was refused")
    checks += 1
    if not reason_problems({"x.py": "the rows it wrote are in probes/rows.json"},
                           {"x.py"}, read):
        bad.append("a citation of a file this directory does not hold was accepted")
    checks += 1
    # The set the reader is judged against must be the files this directory holds, data
    # files included -- the refusal's own words are about files, and a reason may cite the
    # rows a probe wrote. Judging citations against the probes alone would refuse a file
    # that is here. This reads the set the run uses, not a copy of it, so shrinking that
    # set fails here.
    judged_against = present_in_directory()
    data_names = set(classify([(p.name, os.access(p, os.X_OK))
                               for p in PROBES.iterdir() if p.is_file()])["data"])
    if not data_names <= judged_against:
        bad.append("the reason reader is judged against a set that leaves out the data "
                   "files a reason may cite: %s"
                   % ", ".join(sorted(data_names - judged_against)))
    checks += 1
    for reason in EXCLUDED.values():
        cited = NAME_IN_REASON.findall(reason)
        if cited and any(c not in judged_against for c in cited):
            bad.append("a reason in the file cites a name this rule refuses: %r" % (reason,))
    return bad, checks


def render(c: dict, kinds: dict) -> list:
    py = sum(1 for n in kinds["candidates"] if n.endswith(".py"))
    sh = sum(1 for n in kinds["candidates"] if n.endswith(".sh"))
    out = ["probes in the directory        %d (.py %d, .sh %d, other executable %d)"
           % (len(kinds["candidates"]), py, sh, len(kinds["candidates"]) - py - sh),
           "files here that are data       %d" % len(kinds["data"]),
           "probes the runner invokes      %d (%d on every run, %d only under --net)"
           % (len(c["wired_on_every_run"]) + len(c["only_under_net"]),
              len(c["wired_on_every_run"]), len(c["only_under_net"])),
           "probes named as excluded       %d" % len(c["declared_excluded"])]
    if c["only_under_net"]:
        out.append("  gated under --net            %s"
                   % ", ".join(c["only_under_net"]))
    for name, reason in sorted(EXCLUDED.items()):
        if name in c["present"]:
            out.append("  excluded %-26s %s" % (name, reason))
    out.append("probes nobody answers for    %d %s"
               % (len(c["unanswered"]), ", ".join(c["unanswered"])))
    out.append("names with no probe behind them %d %s"
               % (len(c["named_but_absent"]), ", ".join(c["named_but_absent"])))
    if kinds["unknown"]:
        out.append("files of a kind this file does not know %d %s"
                   % (len(kinds["unknown"]), ", ".join(kinds["unknown"])))
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

    kinds = classify([(p.name, os.access(p, os.X_OK))
                      for p in PROBES.iterdir() if p.is_file()])
    if not RUNNER.exists():
        print("cannot judge: no runner at %s" % RUNNER)
        print("COVERAGE=2 (%d probe(s), unknown)" % len(kinds["candidates"]))
        return 2
    c = coverage(kinds["candidates"], RUNNER.read_text(encoding="utf-8"), EXCLUDED)
    for line in render(c, kinds):
        print(line)
    if not judgeable(c) and c["present"]:
        print("cannot judge: the runner's text invokes no probe in this directory, "
              "so a probe that is missing from it cannot be told from a probe this "
              "rule cannot see")
        print("COVERAGE=2 (%d probe(s), unknown)" % len(c["present"]))
        return 2
    bad = []
    if c["unanswered"]:
        bad.append("these probes are neither run by repro/run_all.sh in either mode "
                   "nor named as excluded, so nothing reports a change that breaks "
                   "them: %s" % ", ".join(c["unanswered"]))
    if c["named_but_absent"]:
        bad.append("these names stand for files that are not here: %s"
                   % ", ".join(c["named_but_absent"]))
    if c["both"]:
        bad.append("these probes are both wired and named as excluded: %s"
                   % ", ".join(c["both"]))
    if kinds["unknown"]:
        bad.append("these files are of a kind this probe does not classify, so "
                   "whether they are probes is unanswered: %s"
                   % ", ".join(kinds["unknown"]))
    bad += reason_problems(EXCLUDED,
                           present_in_directory(),
                           lambda name: (PROBES / name).read_text(
                               encoding="utf-8", errors="replace"))
    for line in bad:
        print("FAIL", line)
    print("COVERAGE=%d (%d probe(s), %d wired (%d always, %d only under --net), "
          "%d excluded, %d unanswered)"
          % (1 if bad else 0, len(c["present"]),
             len(c["wired_on_every_run"]) + len(c["only_under_net"]),
             len(c["wired_on_every_run"]), len(c["only_under_net"]),
             len(c["declared_excluded"]), len(c["unanswered"])))
    return 1 if bad else 0


if __name__ == "__main__":
    try:
        code = main()
    except BrokenPipeError:
        # `| head -1` closes the pipe. That is the reader's choice of how much of
        # this to read, not a defect of the check.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        code = 0
    raise SystemExit(code)
