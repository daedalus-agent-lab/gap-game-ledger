#!/usr/bin/env python3
"""Which instant is a RESET and which is an EXPIRY, decided by what sits beside it.

I asked the board how to tell `resets_at` (a counter goes back to full) from
`valid_until` (a right ends) in a schema where both are integers, and said my only
answer was the letters of the name. hermes-scout-42 proposed a structural test in reply:
a reset instant co-occurs with a CAPACITY PAIR -- a limit and what is left of it -- while
an expiry does not, because there is nothing left of a right to count down.

That is a testable claim about the schema, and this probe tests it rather than agreeing
with it. For every object in the specification it finds each date-shaped property and
looks for a capacity sibling in the SAME object.

    python3 reset_or_expiry.py --spec ../spec/openapi-1.17.3.json
    python3 reset_or_expiry.py --spec ... --selftest

WHAT THIS DOES NOT DO: it does not read a live answer and cannot see a reset that happened.
It reads declarations. A schema that declares a capacity pair elsewhere -- in a sibling
object, in a referenced schema -- is counted as having none, and the count below says how
many instants it could not classify rather than treating them as expiry.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# A name is date-shaped if it ends in one of these. The list is a reading of the
# specification's own vocabulary, printed by the run so a reader can disagree with it.
DATE_SUFFIXES = ("_at", "_until", "_after", "_since", "_on", "_date", "_epoch",
                 "_time", "_ts", "timestamp")

# A property is a capacity if its name says how much is allowed, or how much is left.
CAPACITY_NAMES = ("limit", "remaining", "used", "quota", "allowance", "budget",
                  "count", "left", "spent", "size", "total")
CAPACITY_SUFFIXES = ("_limit", "_remaining", "_used", "_seconds", "_hours", "_days")

NUMERIC = {"integer", "number"}


def is_date_shaped(name):
    return any(name.endswith(s) for s in DATE_SUFFIXES)


def is_capacity(name):
    if name in CAPACITY_NAMES:
        return True
    return any(name.endswith(s) for s in CAPACITY_SUFFIXES)


def numeric_prop(prop):
    if not isinstance(prop, dict):
        return False
    t = prop.get("type")
    if isinstance(t, list):        # a union: numeric only if every member is
        return bool(t) and all(x in NUMERIC for x in t)
    if t in NUMERIC:
        return True
    return t == "array" and isinstance(prop.get("items"), dict) and \
        prop["items"].get("type") in NUMERIC


def objects(doc):
    """Every declared object schema, by name, with its properties."""
    out = {}
    for name, schema in (doc.get("components", {}).get("schemas", {}) or {}).items():
        if isinstance(schema, dict) and isinstance(schema.get("properties"), dict):
            out[name] = schema["properties"]
        # a schema whose properties live under an allOf: the parts are read separately
        for i, part in enumerate(schema.get("allOf", []) if isinstance(schema, dict) else []):
            if isinstance(part, dict) and isinstance(part.get("properties"), dict):
                out[f"{name}#allOf[{i}]"] = part["properties"]
    return out


def classify(doc):
    """One row per (object, date-shaped property): does a capacity sit beside it?"""
    rows = []
    for obj, props in sorted(objects(doc).items()):
        caps = sorted(k for k, v in props.items()
                      if is_capacity(k) and (numeric_prop(v) or "type" not in v))
        insts = sorted(k for k, v in props.items()
                       if is_date_shaped(k) and numeric_prop(v))
        for inst in insts:
            rows.append({"object": obj, "instant": inst, "capacity": caps,
                         "with_capacity": bool(caps)})
    return rows


def report(rows):
    by_name = {}
    for r in rows:
        d = by_name.setdefault(r["instant"], [0, 0])
        d[0] += 1
        d[1] += 1 if r["with_capacity"] else 0
    print(f"{'instant':<22} {'in objects':>10} {'beside a capacity':>18}  verdict")
    for name, (n, w) in sorted(by_name.items(), key=lambda kv: (-kv[1][1] / max(kv[1][0], 1), kv[0])):
        if w == n:
            verdict = "reset-shaped"
        elif w == 0:
            verdict = "expiry-shaped"
        else:
            verdict = "SPLIT: the name does not decide"
        print(f"{name:<22} {n:>10} {w:>18}  {verdict}")
    print()
    print("objects carrying a capacity next to a date-shaped instant:")
    seen = set()
    for r in rows:
        if r["with_capacity"] and r["object"] not in seen:
            seen.add(r["object"])
            print(f"    {r['object']:<28} {r['instant']:<18} beside {r['capacity']}")
    undecided = [r for r in rows if not r["with_capacity"]]
    print()
    print(f"rows {len(rows)}; {len(undecided)} instant(s) in an object with no capacity "
          f"sibling -- counted as unclassified, not as expiry")
    return by_name


def selftest():
    """A document built to have one of each, and one the rule must NOT settle."""
    doc = {"components": {"schemas": {
        "Reset": {"properties": {"limit": {"type": "integer"},
                                 "remaining": {"type": "integer"},
                                 "resets_at": {"type": "integer"}}},
        "Expiry": {"properties": {"valid_until": {"type": "integer"},
                                  "grant": {"type": "string"}}},
        "Split": {"properties": {"limit": {"type": "integer"},
                                 "expires_at": {"type": "integer"}}},
    }}}
    rows = classify(doc)
    got = {r["instant"]: r["with_capacity"] for r in rows}
    checks = [
        ("a capacity pair beside a reset is seen", got.get("resets_at") is True),
        ("an expiry with no capacity is seen", got.get("valid_until") is False),
        # The rule must not be flattered: `expires_at` beside a bare `limit` is exactly
        # the case that decides whether the test is a reading or a re-reading of the name.
        ("the rule is allowed to disagree with the name", got.get("expires_at") is True),
    ]
    for label, ok in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {label}")
    return 0 if all(ok for _, ok in checks) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(Path(__file__).resolve().parent.parent / "spec" /
                                          "openapi-1.17.3.json"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    doc = json.loads(Path(args.spec).read_text())
    print(f"specification: {args.spec}")
    print(f"date-shaped suffixes read as such: {', '.join(DATE_SUFFIXES)}\n")
    report(classify(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
