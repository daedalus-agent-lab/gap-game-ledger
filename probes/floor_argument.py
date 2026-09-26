#!/usr/bin/env python3
"""The floor is published as a formula over a name the payload defines three times.

`election_rules.floor` reads `max(5, ceil(0.30 * N))`. `N` is not one number in the
payload it is published in. One read of `GET /v1/politics` carries three numbers that
could each be read as the N of that rule:

  registration.active_count          73   live, no snapshot field, no floor beside it
  initiatives.term.electorate_size   70   snapshotted 19 s after election:1 closed
  election:1.electorate_size         67   frozen at that election's opening

Two of the three stand beside a published floor, and both floors say 21. This probe
parses the published formula string itself -- not a restatement of it in Python --
applies it to each N, and reports which published floor each N reproduces, which N
reproduces none, and which pairs of N the formula cannot separate, so that a floor
number cannot settle the question two governance pages leave open.

The two instants, named because the numbers belong to them: election:1's 67 is frozen
at that election's opening (1790121600), and the term's 70 is created at 1790208019,
19 s after election:1 closed (1790208000). The rival this probe cannot exclude is not
staleness -- it is that the term snapshot recomputes under its own liveness rule, and
no published number says which rule that is. So the probe reports that 67 -> 70 is
consistent with growth between the opening and the close, and does not claim it: the
two numbers stand at two different instants and name two different objects.

The staircase, with the range it was measured over, because the prose was wrong once:
over N = 17..400 the floor stands still for up to 4 consecutive values of N; over
N = 10..16 it stands still for 7, and that stretch is the `max(5, ...)` clamp, not the
0.30 ratio. So a floor that did not move is not evidence that N did not move, and the
published floor cannot be used as an indicator that a late elector was admitted.

Usage:
  python3 probes/floor_argument.py                    # read the fixture, print the table
  python3 probes/floor_argument.py --check            # exit 0 or 1 on the fixture's claims
  python3 probes/floor_argument.py --selftest         # the formula, the separator, wrong fixtures
  python3 probes/floor_argument.py --predict 74       # floor(74) and floor(75)
  python3 probes/floor_argument.py --staircase 10 400 # the flat stretches over a range
"""
from __future__ import annotations

import io
import json
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "politics_n_20260925T2315Z.json"

# The rule as the platform publishes it, and the numbers standing beside it.
# The second rule the same payload publishes BESIDE the same N: the signature count an
# initiative needs. Taken from the guide the board names as canonical, not restated here
# by ear -- https://getpostingboard.dev/politics.md, table "Thresholds and limits".
SIGNATURE_FORMULA = "max(3, ceil(0.20 * N))"
SIGNATURE_SOURCE = "https://getpostingboard.dev/politics.md"
EXPECTED_FORMULA = "max(5, ceil(0.30 * N))"
QUORUM = 10
TALLY = "irv-2"
ELECTION1_CLOSES_AT = 1790208000
ELECTION1_FROZEN_AT = 1790121600
TERM_SNAPSHOT_AT = 1790208019
SNAPSHOT_LAG = 19

# (site, route, n, snapshot_field, snapshot_at, floor beside it, other fields recorded)
PLAN = [
    ("registration.active_count", "GET /v1/politics", 73, None, None, None, {}),
    (
        "initiatives.term.electorate_size",
        "GET /v1/politics",
        70,
        "created_at",
        None,  # the instant of this row is read by the lag rule below, not twice
        21,
        {"threshold_beside_it": 14},
    ),
    (
        "election:1.electorate_size",
        "GET /v1/politics",
        67,
        "frozen_at",
        ELECTION1_FROZEN_AT,
        21,
        {"votes_cast": 37},
    ),
    (
        "election:1.electorate_size",
        "GET /v1/politics/elections/election:1",
        67,
        "frozen_at",
        ELECTION1_FROZEN_AT,
        21,
        {"sealed": True},
    ),
    (
        "election:2.electorate_size",
        "GET /v1/politics/elections/election:2",
        None,
        "snapshot_status",
        None,
        None,
        {"snapshot_status": "pending", "opens_at": 1790726400, "closes_at": 1790812800},
    ),
    (
        "initiatives:term:0.electorate_size",
        "GET /v1/politics/initiatives",
        32,
        None,
        None,
        10,
        {"threshold_beside_it": 7, "term_id": 0, "kind": "recall"},
    ),
]
EXPECTED_ROUTES = {
    "GET /v1/politics",
    "GET /v1/politics/elections/election:1",
    "GET /v1/politics/elections/election:2",
    "GET /v1/politics/initiatives",
}

TOKEN = re.compile(r"\s*(\d+\.?\d*|[A-Za-z_][A-Za-z_0-9]*|[(),*/+-])")


def parse_formula(text: str):
    """Read the published string into a tree. A string is a rule only when something
    evaluates it: printing `formula.text` beside a check that computes a Python copy of
    the same rule leaves the string free to say anything."""
    toks = TOKEN.findall(text)
    if "".join(toks) != re.sub(r"\s+", "", text):
        raise ValueError("formula carries characters this parser does not read: %r" % text)
    pos = [0]

    def peek():
        return toks[pos[0]] if pos[0] < len(toks) else None

    def eat(t=None):
        tok = peek()
        if tok is None or (t is not None and tok != t):
            raise ValueError("expected %r, found %r" % (t, tok))
        pos[0] += 1
        return tok

    def expr():
        node = term()
        while peek() in ("+", "-"):
            op = eat()
            node = (op, node, term())
        return node

    def term():
        node = factor()
        while peek() in ("*", "/"):
            op = eat()
            node = (op, node, factor())
        return node

    def factor():
        tok = peek()
        if tok is not None and re.fullmatch(r"\d+\.?\d*", tok):
            eat()
            return float(tok)
        if tok == "N":
            eat()
            return "N"
        if tok == "(":
            eat("(")
            node = expr()
            eat(")")
            return node
        if tok is not None and re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*", tok):
            name = eat()
            eat("(")
            args = [expr()]
            while peek() == ",":
                eat(",")
                args.append(expr())
            eat(")")
            return (name,) + tuple(args)
        raise ValueError("unread token %r in %r" % (tok, text))

    node = expr()
    if peek() is not None:
        raise ValueError("trailing %r in %r" % (peek(), text))
    return node


def eval_formula(node, n):
    if node == "N":
        return n
    if isinstance(node, float):
        return node
    op = node[0]
    if op == "max":
        return max(eval_formula(a, n) for a in node[1:])
    if op == "min":
        return min(eval_formula(a, n) for a in node[1:])
    if op == "ceil":
        return math.ceil(eval_formula(node[1], n))
    if op == "floor":
        return math.floor(eval_formula(node[1], n))
    a, b = eval_formula(node[1], n), eval_formula(node[2], n)
    if op == "+":
        return a + b
    if op == "-":
        return a - b
    if op == "*":
        return a * b
    if op == "/":
        return a / b
    raise ValueError("no operator named %r" % op)


def floor_from(n: int, text: str = EXPECTED_FORMULA) -> int:
    """The published rule, evaluated from the published string."""
    return int(eval_formula(parse_formula(text), n))


def load(path: Path = FIXTURE) -> dict:
    return json.loads(Path(path).read_text())


def formula_of(doc: dict) -> str:
    return (doc.get("formula") or {}).get("text") or ""


def rows(doc: dict) -> list[dict]:
    text = formula_of(doc)
    out = []
    for c in doc["claims"]:
        n = c["n"]
        try:
            computed = None if n is None else floor_from(n, text)
        except ValueError:
            computed = None
        out.append(
            {
                "site": c["site"],
                "route": c["route"],
                "n": n,
                "frozen_at": c.get("frozen_at"),
                "published": c.get("floor_beside_it"),
                "computed": computed,
            }
        )
    return out


def agreeing(rs: list[dict]) -> list[dict]:
    return [r for r in rs if r["published"] is not None and r["computed"] == r["published"]]


def diverging(rs: list[dict]) -> list[dict]:
    return [r for r in rs if r["published"] is not None and r["computed"] != r["published"]]


def indistinguishable_pairs(rs: list[dict]) -> list[tuple[int, int]]:
    ns = sorted({r["n"] for r in rs if r["n"] is not None})
    out = []
    for i, a in enumerate(ns):
        for b in ns[i + 1 :]:
            fa, fb = _computed(rs, a), _computed(rs, b)
            if fa is not None and fa == fb:
                out.append((a, b))
    return out


def _computed(rs: list[dict], n: int):
    for r in rs:
        if r["n"] == n and r["computed"] is not None:
            return r["computed"]
    return None


def report(doc: dict, out=sys.stdout) -> None:
    rs = rows(doc)
    out.write("formula (platform): %s\n" % formula_of(doc))
    out.write(
        "quorum_min %s  tally %s\n"
        % ((doc.get("formula") or {}).get("quorum_min"), (doc.get("formula") or {}).get("tally_version"))
    )
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
    for r in [r for r in rs if r["published"] is None and r["n"] is not None]:
        out.write(
            "no floor beside it: %s N=%d -> %d (would change a term-level floor: %s)\n"
            % (r["site"], r["n"], r["computed"], floor_from(r["n"], formula_of(doc)) != 21)
        )
    for a, b in indistinguishable_pairs(rs):
        out.write("not separated by the formula: N=%d and N=%d both give %d\n" % (a, b, _computed(rs, a)))
    for c in doc.get("claims") or []:
        sig = c.get("threshold_beside_it")
        if sig is None or c.get("n") is None:
            continue
        n = c["n"]
        out.write(
            "one N, two published thresholds: N=%d carries floor %d (%s) and signature count "
            "%d (%s, %s) -- so a count that stands beside one of them is not evidence about "
            "the other, and the row says which rules were read on this N\n"
            % (n, floor_from(n), EXPECTED_FORMULA, sig, SIGNATURE_FORMULA, SIGNATURE_SOURCE)
        )


def check(doc: dict, out=sys.stdout) -> int:
    bad = 0

    def fail(msg):
        nonlocal bad
        bad += 1
        out.write("FAIL %s\n" % msg)

    def ok(msg):
        out.write("ok   %s\n" % msg)

    # 1. the formula string is the published one and this run parses it
    text = formula_of(doc)
    tree = None
    if text != EXPECTED_FORMULA:
        fail("the formula text is %r, not the published %r" % (text, EXPECTED_FORMULA))
    try:
        tree = parse_formula(text)
        ok("the formula string parses: %s" % text)
    except ValueError as exc:
        fail("the formula text does not parse: %s" % exc)

    # 2. the numbers beside the formula
    for field, want in (("quorum_min", QUORUM), ("tally_version", TALLY)):
        got = (doc.get("formula") or {}).get(field)
        if got != want:
            fail("formula.%s is %r, the read recorded %r" % (field, got, want))
        else:
            ok("formula.%s is %r" % (field, want))

    # 3. the rows are exactly the plan
    got_rows = [(c.get("site"), c.get("route")) for c in doc.get("claims") or []]
    want_rows = [(s, r) for s, r, *_ in PLAN]
    if got_rows != want_rows:
        fail("the fixture's rows are %r, the read recorded %r" % (got_rows, want_rows))
    else:
        ok("the fixture carries exactly the %d rows this probe read" % len(want_rows))
    by_key = {(c.get("site"), c.get("route")): c for c in doc.get("claims") or []}

    # 4. every field of every planned row
    for site, route, n, snap_field, snap_at, floor, extra in PLAN:
        c = by_key.get((site, route))
        if c is None:
            continue  # already reported by the row plan
        label = "%s@%s" % (site, route)
        if c.get("n") != n:
            fail("%s carries N=%r, the read recorded %r" % (label, c.get("n"), n))
        else:
            ok("%s carries N=%r" % (label, n))
        if c.get("snapshot_field") != snap_field:
            fail("%s names snapshot field %r, the read recorded %r" % (label, c.get("snapshot_field"), snap_field))
        else:
            ok("%s names snapshot field %r" % (label, snap_field))
        if snap_at is not None and c.get("frozen_at") != snap_at:
            fail("%s carries snapshot instant %r, the read recorded %r" % (label, c.get("frozen_at"), snap_at))
        elif snap_at is not None:
            ok("%s carries snapshot instant %r" % (label, snap_at))
        if c.get("floor_beside_it") != floor:
            fail("%s publishes floor %r, the read recorded %r" % (label, c.get("floor_beside_it"), floor))
        elif floor is not None:
            ok("%s publishes floor %r" % (label, floor))
        for key, want in extra.items():
            if c.get(key) != want:
                fail("%s carries %s=%r, the read recorded %r" % (label, key, c.get(key), want))
            else:
                ok("%s carries %s=%r" % (label, key, want))
        if n is not None and floor is not None and tree is not None:
            computed = int(eval_formula(tree, n))
            if computed != floor:
                fail("%s: the published formula gives %d for N=%d, the payload publishes %s" % (label, computed, n, floor))
            else:
                ok("%s: the published formula gives %d for N=%d" % (label, computed, n))
        # The same row carries a SECOND threshold, and one N carrying two thresholds is
        # what says which class the N belongs to: if the signature count beside it is the
        # signature formula's answer, this N is the one the initiative rules are read on.
        sig = c.get("threshold_beside_it")
        if sig is not None and n is not None:
            want_sig = int(eval_formula(parse_formula(SIGNATURE_FORMULA), n))
            if want_sig != sig:
                fail(
                    "%s: the signature formula %r gives %d for N=%d, the payload publishes %s"
                    % (label, SIGNATURE_FORMULA, want_sig, n, sig)
                )
            else:
                ok("%s: the signature count %d beside N=%d is the signature formula's answer" % (label, sig, n))

    # 5. the lag between the close and the term snapshot
    term = by_key.get(("initiatives.term.electorate_size", "GET /v1/politics"))
    if term is not None and term.get("frozen_at") is not None:
        lag = term["frozen_at"] - ELECTION1_CLOSES_AT
        if lag != SNAPSHOT_LAG:
            fail("the term snapshot stands %d s after election:1 closed, the read recorded %d" % (lag, SNAPSHOT_LAG))
        else:
            ok("the term snapshot stands %d s after election:1 closed" % lag)

    # 6. the live count is contradicted by the floors published elsewhere
    published = {r["published"] for r in rows(doc) if r["published"] is not None}
    lives = [c for c in doc.get("claims") or [] if c.get("n") is not None and c.get("floor_beside_it") is None]
    if not lives:
        fail("no row stands beside no floor, so nothing is contradicted")
    for c in lives:
        computed = floor_from(c["n"], text) if tree is not None else None
        if computed in published:
            fail(
                "the live count %s N=%s gives %s, which is also a published floor, so it is not the contradicted one"
                % (c["site"], c["n"], computed)
            )
        else:
            ok("the live count %s N=%s gives %s, which no published floor carries" % (c["site"], c["n"], computed))

    # 7. at least one pair the formula cannot separate
    pairs = indistinguishable_pairs(rows(doc))
    if not pairs:
        fail("the fixture carries no pair of N the formula cannot separate, so it cannot show why a floor number settles nothing")
    else:
        ok("the fixture carries a pair the formula cannot separate: %s" % (pairs,))

    # 8. provenance: the routes, and each instant standing after the events it reports
    prov = doc.get("_provenance") or {}
    reads = prov.get("reads") or []
    routes = [r.get("route") for r in reads]
    if sorted(routes) != sorted(EXPECTED_ROUTES):
        fail("the provenance names routes %r, the read recorded %r" % (routes, sorted(EXPECTED_ROUTES)))
    else:
        ok("the provenance names the %d routes this probe read" % len(routes))
    for r in reads:
        a = r.get("as_of")
        if not isinstance(a, int) or a <= ELECTION1_CLOSES_AT:
            fail("a read claims as_of %r, which is not after the last instant it reports (%d)" % (a, ELECTION1_CLOSES_AT))
        else:
            ok("the read at %d stands after the last instant it reports" % a)
        if str(a) not in (prov.get("what") or ""):
            fail("the provenance prose does not carry the as_of %s it lists beside it" % a)
        else:
            ok("the provenance prose carries the as_of %s" % a)

    out.write("floor_argument: %d failed\n" % bad)
    return 1 if bad else 0


def longest_flat(lo: int, hi: int, text: str = EXPECTED_FORMULA) -> int:
    best = run = 1
    for n in range(lo + 1, hi + 1):
        run = run + 1 if floor_from(n, text) == floor_from(n - 1, text) else 1
        best = max(best, run)
    return best


def staircase(lo: int, hi: int, out=sys.stdout) -> int:
    """The floor is a staircase, not a gauge. Over the range N = 17..400 it stands still
    for up to 4 consecutive values of N and moves on a single one; over N = 10..16 it
    stands still for 7, and that stretch is the `max(5, ...)` clamp rather than the 0.30
    ratio. So a floor that did not move does not say that N did not move."""
    if lo > hi:
        out.write("the range is reversed: %d..%d. The floor is read over an increasing N; "
                  "nothing was measured.\n" % (lo, hi))
        return 2
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
    clamped = [r for r in runs if r[2] == 5]
    for a, b, v in clamped:
        out.write("that stretch is the max(5, ...) clamp, not the 0.30 ratio: N=%d..%d -> %d\n" % (a, b, v))
    if lo <= 17 <= hi:
        out.write("above the clamp (N=17..%d) the longest flat stretch is %d\n" % (hi, longest_flat(17, hi)))
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


def _mutations(doc: dict) -> list[tuple[str, dict]]:
    """Wrong fixtures the check must refuse. Each one changes exactly one thing a reader
    would otherwise take on the fixture's word."""
    out = []

    def clone(name, fn):
        d = json.loads(json.dumps(doc))
        fn(d)
        out.append((name, d))

    def row(d, site, route):
        for c in d["claims"]:
            if c["site"] == site and c["route"] == route:
                return c
        raise KeyError((site, route))

    clone("the election's N changed to the term's", lambda d: row(d, "election:1.electorate_size", "GET /v1/politics").update(n=70))
    clone(
        "the term's N changed to the election's",
        lambda d: row(d, "initiatives.term.electorate_size", "GET /v1/politics").update(n=67, frozen_at=1790121600),
    )
    clone("the live count set to a number a published floor covers", lambda d: row(d, "registration.active_count", "GET /v1/politics").update(n=70))
    clone("the live row deleted", lambda d: d.update(claims=[c for c in d["claims"] if c["n"] != 73]))
    clone("the pending election's row deleted", lambda d: d.update(claims=[c for c in d["claims"] if not c["site"].startswith("election:2")]))
    clone("every snapshot instant zeroed", lambda d: [c.update(frozen_at=0) for c in d["claims"]])
    clone("the term snapshot lag changed", lambda d: row(d, "initiatives.term.electorate_size", "GET /v1/politics").update(frozen_at=1234567890))
    clone("the formula text changed", lambda d: d["formula"].update(text="ceil(1.00 * N)"))
    clone("the tally version changed", lambda d: d["formula"].update(tally_version="irv-99"))
    clone("a site invented", lambda d: d["claims"].append({"site": "invented.site", "route": "GET /v1/politics", "n": 100, "floor_beside_it": 30}))
    clone("a route invented", lambda d: d["_provenance"]["reads"][0].update(route="GET /nowhere", as_of=1))
    clone("the provenance prose drops an instant it lists", lambda d: d["_provenance"].update(what="the numbers standing for N, read once"))
    clone("the published floor changed", lambda d: row(d, "election:1.electorate_size", "GET /v1/politics").update(floor_beside_it=23))
    clone(
        "the signature count replaced by the floor's answer",
        lambda d: row(d, "initiatives.term.electorate_size", "GET /v1/politics").update(threshold_beside_it=21),
    )
    return out


def selftest(out=sys.stdout) -> int:
    checks = []
    for n, want in [(10, 5), (16, 5), (17, 6), (67, 21), (70, 21), (73, 22), (74, 23)]:
        checks.append(("floor(%d) == %d" % (n, want), floor_from(n) == want))
    checks.append(("the published string parses to the rule the platform prints", eval_formula(parse_formula(EXPECTED_FORMULA), 73) == 22))
    checks.append(("a string carrying a different rule evaluates differently", floor_from(70, "ceil(1.00 * N)") == 70))
    checks.append(("the signature formula answers 14 for N=70", int(eval_formula(parse_formula(SIGNATURE_FORMULA), 70)) == 14))
    checks.append(("the signature formula answers 7 for N=32", int(eval_formula(parse_formula(SIGNATURE_FORMULA), 32)) == 7))
    checks.append(("the two published rules disagree on one N", floor_from(70) != int(eval_formula(parse_formula(SIGNATURE_FORMULA), 70))))
    checks.append(("a string the parser cannot read is refused", _refuses(lambda: parse_formula("max(5, ceil(0.30 * N)"))))
    checks.append(("two different N give one floor, so a floor cannot separate them", floor_from(67) == floor_from(70)))
    checks.append(("one step of N can move the floor, so a live count can be contradicted", floor_from(70) != floor_from(73)))

    # the CLI: a form the parser does not read is an error, not a default
    code, said = _refuses_an_argument(["--fixture", "politics_mutant.json"])
    checks.append(("an argument the parser does not read is refused, not ignored",
                   code == 2 and "not a form this probe reads" in said))
    code, said = _refuses_an_argument(["--staircase", "10"])
    checks.append(("a form missing an operand is refused rather than read as the default",
                   code == 2 and "not a form this probe reads" in said))

    doc = load()
    rs = rows(doc)
    checks.append(("fixture: the term floor reproduces its own N", any(r["computed"] == 21 and r["n"] == 70 and r["published"] == 21 for r in rs)))
    checks.append(("fixture: the election floor reproduces its own N", any(r["computed"] == 21 and r["n"] == 67 and r["published"] == 21 for r in rs)))
    live = [r for r in rs if r["published"] is None and r["n"] is not None]
    published = {r["published"] for r in rs if r["published"] is not None}
    checks.append(("fixture: a live row is present at all", len(live) == 1 and live[0]["n"] == 73))
    checks.append(
        (
            "fixture: the live count is not the N behind either floor",
            bool(live) and all(r["computed"] not in published for r in live) and live[0]["computed"] is not None,
        )
    )
    checks.append(("fixture: the next election publishes no N yet", any(r["n"] is None and r["site"].startswith("election:2") for r in rs)))
    checks.append(("the check accepts the fixture as shipped", check(doc, io.StringIO()) == 0))

    # the staircase: a floor that did not move is not evidence that N did not move
    checks.append(("three consecutive N can share one floor", len({floor_from(x) for x in (74, 75, 76)}) == 1))
    checks.append(("one step of N can move the floor", floor_from(73) != floor_from(74)))
    checks.append(("above the clamp the longest flat stretch to 400 is 4", longest_flat(17, 400) == 4))
    checks.append(("below the clamp, N=10..16 share one floor of 5", [floor_from(x) for x in (10, 16)] == [5, 5]))

    # wrong fixtures: a check that reads only the row its filter lets through is no check
    mutations = _mutations(doc)
    missed = []
    for name, broken in mutations:
        buf = io.StringIO()
        if check(broken, buf) == 0:
            missed.append(name)
    checks.append(("every wrong fixture is refused (%d of %d)" % (len(mutations) - len(missed), len(mutations)), not missed))
    # and the fixture itself still passes, so the mutations are not passing for a trivial reason
    checks.append(("the untouched fixture is still accepted after those refusals", check(doc, io.StringIO()) == 0))

    failed = [name for name, ok in checks if not ok]
    for name, ok in checks:
        out.write("%s %s\n" % ("ok  " if ok else "FAIL", name))
    for name in missed:
        out.write("     accepted a wrong fixture: %s\n" % name)
    out.write("selftest: %d of %d checks pass\n" % (len(checks) - len(failed), len(checks)))
    return 1 if failed else 0


def _refuses_an_argument(argv: list[str]) -> tuple[int, str]:
    """Run the CLI on one argv and keep what it said, so the refusal is a reading."""
    err, real = io.StringIO(), sys.stderr
    sys.stderr = err
    try:
        return main(argv), err.getvalue()
    finally:
        sys.stderr = real


def _refuses(fn) -> bool:
    try:
        fn()
    except ValueError:
        return True
    return False


def main(argv: list[str]) -> int:
    """Every argument is either read or refused.

    A flag this parser does not know is a flag whose effect nothing measured:
    `--fixture mutant.json` was passed to this probe and silently ignored, so the
    run printed the shipped fixture's rows and exited 0 -- which reads exactly
    like a run that used the mutant. The form is spelled out on refusal, and an
    unread form is an error rather than a default.
    """
    if not argv:
        report(load())
        return 0
    if argv == ["--selftest"]:
        return selftest()
    if argv == ["--check"]:
        return check(load())
    if len(argv) == 2 and argv[0] == "--predict":
        return predict(int(argv[1]))
    if len(argv) == 3 and argv[0] == "--staircase":
        return staircase(int(argv[1]), int(argv[2]))
    sys.stderr.write(
        "refused: %r is not a form this probe reads. Forms: (no argument) | "
        "--selftest | --check | --predict N | --staircase LO HI\n" % (argv,))
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
