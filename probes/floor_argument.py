#!/usr/bin/env python3
"""The floor is published as a formula over a name the payload defines three times.

`election_rules.floor` reads `max(5, ceil(0.30 * N))`. `N` is not one number in the
payload it is published in. One read of `GET /v1/politics` carries:

  registration.active_count          73   live, no snapshot field
  initiatives.term.electorate_size   70   snapshotted 19 s after election:1 closed
  election:1.electorate_size         67   frozen at that election's opening

Two of those sites publish a floor beside them, and both say 21. This probe applies
the published formula to each N and reports which published floor each N reproduces,
which N reproduces none, and -- the part a reader cannot see by eye -- which pairs of
N the formula cannot separate, so that a floor number cannot settle the dispute the
two governance pages have.

Usage:
  python3 probes/floor_argument.py                    # read the fixture, print the table
  python3 probes/floor_argument.py --check            # exit 0 or 1 on the fixture claims
  python3 probes/floor_argument.py --selftest         # the formula and the separator
  python3 probes/floor_argument.py --predict 74       # floor(74) and floor(75)

Boundary, stated because it is what the numbers do not carry: a floor reproduces the
formula for an N; it does not say at which instant the board read that N. The only
published pair spanning an election window is (67, 70), and it names two different
objects, so this probe does not claim that the electorate grew during election day.
"""
from __future__ import annotations

import io
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "politics_n_20260925T2355Z.json"

QUORUM = 10


def floor_from(n: int) -> int:
    """The published rule, evaluated. Read from election_rules.floor, not restated
    from prose: max(5, ceil(0.30 * N))."""
    return max(5, math.ceil(0.30 * n))


def load(path: Path = FIXTURE) -> dict:
    return json.loads(Path(path).read_text())


def rows(doc: dict) -> list[dict]:
    out = []
    for c in doc["claims"]:
        n = c["n"]
        out.append(
            {
                "site": c["site"],
                "route": c["route"],
                "n": n,
                "frozen_at": c.get("frozen_at"),
                "published": c.get("floor_beside_it"),
                "computed": None if n is None else floor_from(n),
            }
        )
    return out


def agreeing(rs: list[dict]) -> list[dict]:
    return [r for r in rs if r["published"] is not None and r["computed"] == r["published"]]


def diverging(rs: list[dict]) -> list[dict]:
    return [r for r in rs if r["published"] is not None and r["computed"] != r["published"]]


def indistinguishable_pairs(rs: list[dict]) -> list[tuple[int, int]]:
    ns = sorted({r["n"] for r in rs if r["n"] is not None})
    return [(a, b) for i, a in enumerate(ns) for b in ns[i + 1 :] if floor_from(a) == floor_from(b)]


def report(doc: dict, out=sys.stdout) -> None:
    rs = rows(doc)
    out.write("formula (platform): %s\n" % doc["formula"]["text"])
    out.write("quorum_min %d  tally %s\n" % (doc["formula"]["quorum_min"], doc["formula"]["tally_version"]))
    out.write("%-36s %-40s %5s %8s %5s\n" % ("site", "route", "N", "floor", "pub."))
    for r in rs:
        out.write(
            "%-36s %-40s %5s %8s %5s\n"
            % (
                r["site"],
                r["route"],
                "-" if r["n"] is None else r["n"],
                "-" if r["computed"] is None else r["computed"],
                "-" if r["published"] is None else r["published"],
            )
        )
    out.write("\n")
    for r in agreeing(rs):
        out.write("reproduced: %s N=%d -> %d equals the published %d\n" % (r["site"], r["n"], r["computed"], r["published"]))
    for r in diverging(rs):
        out.write("CONTRADICTED: %s N=%d -> %d, published %d\n" % (r["site"], r["n"], r["computed"], r["published"]))
    live = [r for r in rs if r.get("published") is None and r["n"] is not None]
    for r in live:
        out.write("no floor beside it: %s N=%d -> %d (would change a term-level floor: %s)\n" % (r["site"], r["n"], r["computed"], floor_from(r["n"]) != 21))
    pairs = indistinguishable_pairs(rs)
    for a, b in pairs:
        out.write("not separated by the formula: N=%d and N=%d both give %d\n" % (a, b, floor_from(a)))
    sep = [p for p in [(a, b) for a, b in ((67, 70), (70, 73), (73, 74))] if floor_from(a) != floor_from(b)]
    for a, b in sep:
        out.write("separated by the formula: N=%d -> %d, N=%d -> %d\n" % (a, floor_from(a), b, floor_from(b)))


def check(doc: dict, out=sys.stdout) -> int:
    bad = 0
    rs = rows(doc)
    for r in rs:
        if r["published"] is None:
            continue
        if r["computed"] != r["published"]:
            out.write("FAIL %s: formula gives %s, payload publishes %s\n" % (r["site"], r["computed"], r["published"]))
            bad += 1
        else:
            out.write("ok   %s: N=%d reproduces the published floor %d\n" % (r["site"], r["n"], r["published"]))
    live = [r for r in rs if r.get("published") is None and r["n"] is not None]
    for r in live:
        if floor_from(r["n"]) in {x["published"] for x in rs if x["published"] is not None}:
            out.write("FAIL %s: the live count N=%d gives %d, which is also a published floor, so it is not the contradicted one\n" % (r["site"], r["n"], floor_from(r["n"])))
            bad += 1
        else:
            out.write("ok   %s: live count N=%d gives %d, which no published floor carries\n" % (r["site"], r["n"], floor_from(r["n"])))
    if not indistinguishable_pairs(rs):
        out.write("FAIL the fixture carries no pair of N the formula cannot separate, so it cannot show why a floor number settles nothing\n")
        bad += 1
    else:
        out.write("ok   the fixture carries a pair the formula cannot separate: %s\n" % (indistinguishable_pairs(rs),))
    q = doc["formula"]["quorum_min"]
    if q != QUORUM:
        out.write("FAIL quorum_min %d is not the %d this probe asserts\n" % (q, QUORUM))
        bad += 1
    out.write("floor_argument: %d failed\n" % bad)
    return 1 if bad else 0


def _longest_flat(lo: int, hi: int) -> int:
    best = run = 1
    for n in range(lo + 1, hi + 1):
        run = run + 1 if floor_from(n) == floor_from(n - 1) else 1
        best = max(best, run)
    return best


def selftest(out=sys.stdout) -> int:
    checks = []
    for n, want in [(10, 5), (16, 5), (17, 6), (67, 21), (70, 21), (73, 22), (74, 23)]:
        got = floor_from(n)
        checks.append(("floor(%d) == %d" % (n, want), got == want))
    checks.append(("two different N give one floor, so a floor cannot separate them", floor_from(67) == floor_from(70)))
    checks.append(("one step of N can move the floor, so a live count can be contradicted", floor_from(70) != floor_from(73)))
    doc = load()
    rs = rows(doc)
    checks.append(("fixture: the term floor reproduces its own N", any(r["computed"] == 21 and r["n"] == 70 and r["published"] == 21 for r in rs)))
    checks.append(("fixture: the election floor reproduces its own N", any(r["computed"] == 21 and r["n"] == 67 and r["published"] == 21 for r in rs)))
    checks.append(("fixture: the live count is not the N behind either floor", not any(r["n"] == 73 and r["computed"] == r["published"] for r in rs if r["published"] is not None)))
    checks.append(("fixture: the next election publishes no N yet", any(r["n"] is None and r["site"].startswith("election:2") for r in rs)))
    # the staircase: a floor that did not move is not evidence that N did not move
    checks.append(("three consecutive N can share one floor", len({floor_from(x) for x in (74, 75, 76)}) == 1))
    checks.append(("one step of N can move the floor", floor_from(73) != floor_from(74)))
    checks.append(("the longest flat stretch from 64 to 83 is 4 values of N", _longest_flat(64, 83) == 4))
    # a payload that carries the same N twice with two different floors must not pass
    broken = dict(doc)
    broken["claims"] = [dict(c) for c in doc["claims"]]
    for c in broken["claims"]:
        if c.get("floor_beside_it") is not None and c["n"] == 67:
            c["floor_beside_it"] = 23
    buf = io.StringIO()
    rc = check(broken, buf)
    checks.append(("a floor the formula does not give fails the check", rc == 1 and "FAIL" in buf.getvalue()))
    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        out.write("%s %s\n" % ("ok  " if ok else "FAIL", name))
    out.write("selftest: %d of %d checks pass\n" % (len(checks) - len(failed), len(checks)))
    return 1 if failed else 0


def staircase(lo: int, hi: int, out=sys.stdout) -> int:
    """The floor is a staircase, not a gauge: it stands still for 3 or 4 consecutive
    values of N and moves on a single one. So a floor that did not move does not say
    that N did not move, and the published floor cannot be used as an indicator that a
    late elector was admitted."""
    runs = []
    start = lo
    prev = floor_from(lo)
    for n in range(lo + 1, hi + 1):
        cur = floor_from(n)
        if cur != prev:
            runs.append((start, n - 1, prev))
            start, prev = n, cur
    runs.append((start, hi, prev))
    out.write("N in [%d, %d]: the floor takes %d value(s)\n" % (lo, hi, len({r[2] for r in runs})))
    for a, b, v in runs:
        out.write("  N=%d..%d (%d value(s) of N) -> floor %d\n" % (a, b, b - a + 1, v))
    longest = max(b - a + 1 for a, b, _ in runs)
    out.write("longest flat stretch: %d consecutive values of N share one floor\n" % longest)
    return 0


def predict(n: int, out=sys.stdout) -> int:
    out.write("if N at the opening is %d: floor %d\n" % (n, floor_from(n)))
    out.write("if one late elector is then admitted: N=%d, floor %d\n" % (n + 1, floor_from(n + 1)))
    out.write("the floor moves: %s\n" % (floor_from(n) != floor_from(n + 1)))
    out.write("headroom before the next step: ")
    k = n
    while floor_from(k + 1) == floor_from(n):
        k += 1
    out.write("N up to %d gives %d (%d elector(s))\n" % (k, floor_from(n), k - n))
    return 0


def main(argv: list[str]) -> int:
    if "--selftest" in argv:
        return selftest()
    if "--check" in argv:
        return check(load())
    if "--predict" in argv:
        i = argv.index("--predict")
        return predict(int(argv[i + 1]))
    if "--staircase" in argv:
        i = argv.index("--staircase")
        return staircase(int(argv[i + 1]), int(argv[i + 2]))
    report(load())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
