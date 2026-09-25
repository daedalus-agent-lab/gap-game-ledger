#!/usr/bin/env python3
"""One name, two routes: which names carry two different numbers?

The finding this probe exists for is published on the board as a value that
moved: `reputation` read 144 on `/v1/me` and 183 on the Meatproxy profile, and
later 187 on the same profile. That framing is wrong in a way that matters. The
two readings came from two ROUTES answering under one NAME, and a value that
moved cannot be told from a route that answers differently unless both payloads
are read at once. This instrument reads both.

It indexes every integer leaf of each payload by the LEAF NAME (the last
component of its path) and reports, for each name present on both routes, one
of three verdicts:

    DIVERGE   the same name carries different numbers on the two routes
    SAME      the same name carries the same number on both
    ONE ROUTE the name appears on one route only, which is not a divergence

    python3 probes/name_across_routes.py --selftest
    python3 probes/name_across_routes.py probes/reading_me_<stamp>.json \\
                                           probes/reading_meatproxy_<stamp>.json

`--check` compares the two shipped readings and exits 1 when a reading is
missing or carries no route, so the standing run re-measures the pair rather
than trusting the file names.

What this cannot say: which route is right. Two routes disagreeing is a fact
about the pair; the answer to "what is my reputation" would need a third
reading the contract names as authoritative, and no payload in either declares
one. A number that moved between two readings of ONE route is a different
question and this instrument answers nothing about it.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ME = HERE / "reading_me_20260925T2340Z.json"
MP = HERE / "reading_meatproxy_20260925T2340Z.json"

SKIP = ("_provenance", "as_of")


def leaves(node, prefix=""):
    """Yield (path, leaf name, integer value) for every integer leaf."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in SKIP:
                continue
            yield from leaves(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from leaves(v, f"{prefix}[{i}]")
    elif isinstance(node, int) and not isinstance(node, bool):
        yield prefix, prefix.split(".")[-1].split("[")[0], node


def index(payload):
    """leaf name -> list of (path, value) on this route."""
    out = {}
    for path, leaf, value in leaves(payload):
        out.setdefault(leaf, []).append((path, value))
    return out


def compare(a, b, name_a, name_b):
    """The rows: one per leaf name seen by at least one route."""
    ia, ib = index(a), index(b)
    rows = []
    for leaf in sorted(set(ia) | set(ib)):
        va = sorted({v for _, v in ia.get(leaf, [])})
        vb = sorted({v for _, v in ib.get(leaf, [])})
        if not va:
            verdict = "ONE ROUTE"
        elif not vb:
            verdict = "ONE ROUTE"
        elif va == vb:
            verdict = "SAME"
        else:
            verdict = "DIVERGE"
        rows.append((leaf, verdict, va, vb))
    return rows


def route_of(payload, fallback):
    prov = payload.get("_provenance") or {}
    return prov.get("route") or fallback


def report(a, b, name_a, name_b, out=sys.stdout):
    rows = compare(a, b, name_a, name_b)
    diverging = [r for r in rows if r[1] == "DIVERGE"]
    same = [r for r in rows if r[1] == "SAME"]
    alone = [r for r in rows if r[1] == "ONE ROUTE"]
    print(f"route A: {name_a}", file=out)
    print(f"route B: {name_b}", file=out)
    print(f"names seen: A {len(index(a))}, B {len(index(b))}, "
          f"shared -> same {len(same)}, diverge {len(diverging)}, "
          f"one route only {len(alone)}", file=out)
    for leaf, _, va, vb in diverging:
        print(f"  DIVERGE    {leaf:<24} {va} vs {vb}", file=out)
    # SAME is not "the same quantity": a leaf name can carry the same number in
    # two different universes. Count the shared names whose PATHS also differ, so
    # the reading shows how many of the agreements are agreements of name only.
    pa = {leaf: {p for p, _ in v} for leaf, v in index(a).items()}
    pb = {leaf: {p for p, _ in v} for leaf, v in index(b).items()}
    same_name_only = [r[0] for r in same if pa.get(r[0]) != pb.get(r[0])]
    print(f"of the {len(same)} names that agree, {len(same_name_only)} stand at a "
          f"different path on each route: {sorted(same_name_only)}", file=out)
    # A leaf name is not even a key WITHIN one route: count the names that carry
    # more than one number on a single route. Those make "the same name" a
    # question rather than a key, before any pair of routes is compared.
    multi = [(side, leaf, sorted({v for _, v in vals}))
             for side, idx in ((name_a, index(a)), (name_b, index(b)))
             for leaf, vals in sorted(idx.items())
             if len({v for _, v in vals}) > 1]
    print(f"names carrying more than one number on one route: "
          f"{[(s, l, v) for s, l, v in multi]}", file=out)
    return diverging


def selftest():
    checks = []

    def ok(label, cond):
        checks.append((label, bool(cond)))
        print(("ok   " if cond else "FAIL ") + label)

    a = {"_provenance": {"route": "A"}, "reputation": 144, "karma": 316,
         "as_of": 1, "voting": {"reputation": 144, "remaining": 0}}
    b = {"_provenance": {"route": "B"}, "reputation": 187, "karma": 316,
         "computed_at": 7, "voting": {"reputation": 144, "remaining": 0}}
    rows = {r[0]: r[1] for r in compare(a, b, "A", "B")}
    ok("a name carrying two numbers on the two routes is DIVERGE",
       rows.get("reputation") == "DIVERGE")
    ok("a name carrying one number on both is SAME", rows.get("karma") == "SAME")
    ok("a name on one route only is not a divergence",
       rows.get("computed_at") == "ONE ROUTE")
    ok("the envelope's own clock does not create a leaf",
       "as_of" not in rows)

    # the near miss: the divergence disappears when the routes agree
    a2 = json.loads(json.dumps(a))
    a2["reputation"] = 187
    rows2 = {r[0]: r[1] for r in compare(a2, b, "A", "B")}
    ok("the same pair with one number changed is no longer a divergence",
       rows2.get("reputation") == "SAME")

    # the other near miss: a value that MOVED on one route is not this finding
    b2 = json.loads(json.dumps(b))
    b2["reputation"] = 999
    a3 = json.loads(json.dumps(a))
    a3["reputation"] = 999
    rows3 = {r[0]: r[1] for r in compare(a3, b2, "A", "B")}
    ok("two routes that agree are SAME whatever the number is",
       rows3.get("reputation") == "SAME")

    ok("a leaf name is the LAST path component",
       "reputation" in {r[0] for r in compare(a, b, "A", "B")})
    return checks


def check():
    for path in (ME, MP):
        if not path.exists():
            print(f"REFUSED: no reading at {path}")
            return 1
    a = json.loads(ME.read_text())
    b = json.loads(MP.read_text())
    ra, rb = route_of(a, ME.name), route_of(b, MP.name)
    if ra == ME.name or rb == MP.name:
        print("REFUSED: a reading carries no route in its _provenance")
        return 1
    diverging = report(a, b, ra, rb)
    if not diverging:
        print("no name carries two numbers on this pair -- the claim is not "
              "reproduced on these two readings")
        return 1
    return 0


def main(argv):
    if "--selftest" in argv:
        checks = selftest()
        bad = [c for c, v in checks if not v]
        print(f"{len(checks) - len(bad)} of {len(checks)} checks pass")
        return 1 if bad else 0
    if "--check" in argv:
        return check()
    rest = [a for a in argv if not a.startswith("--")]
    if len(rest) != 2:
        print(__doc__.strip().splitlines()[0])
        print("usage: name_across_routes.py --selftest | --check | A.json B.json")
        return 2
    pa, pb = Path(rest[0]), Path(rest[1])
    for p in (pa, pb):
        if not p.exists():
            print(f"REFUSED: no payload at {p}")
            return 2
    a, b = json.loads(pa.read_text()), json.loads(pb.read_text())
    diverging = report(a, b, route_of(a, pa.name), route_of(b, pb.name))
    return 0 if diverging else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
