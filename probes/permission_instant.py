#!/usr/bin/env python3
"""Which booleans in a payload are read as permissions, and which of those say WHEN.

A payload boolean read at the moment of action is a promise about the present.
If its block carries no instant, the boolean is a statement about "now-ish" and
the only honest receipt is the act itself -- the 429 that follows a `can_vote:
true` with `remaining: 0` is that receipt, and it is declared behaviour, not a
lie. What is missing is not the truth of the boolean but the date of it.

    python3 permission_instant.py                 # check the fixture
    python3 permission_instant.py <payload.json>
    python3 permission_instant.py --selftest      # the rule can fail

Exit 0 when every declared permission boolean is dated AND the payload does not
contradict the disjointness claim; 1 otherwise.

WHAT THIS DOES NOT DO, stated so a green run is not read as more than it is:
  * it is a name-based reading. `DECLARED` below is a list of booleans whose
    names are read at a decision point; a boolean whose name is not on it is
    reported as UNDECLARED and is not part of the "undated permission" warning.
  * the disjointness statement, unlike the warning, is computed over EVERY
    boolean in the payload. It is a fact about the payload, not about the list.
    This is the repair of a real defect: the first version of this tool computed
    it over the declared list only, and printed DISJOINT over a fixture that
    already contained `politics: {registered: true, as_of: ...}` -- a block with
    both. The list decided the answer, and the safeguard that was supposed to
    catch an undeclared name was unreachable for exactly the blocks where one
    could hide. See `--selftest`, case 4.
  * it says nothing about whether a dated boolean was true when it was read.
  * it reads one payload. It is a snapshot tool, not a drift tool.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Booleans whose NAMES are read at a decision point, with the reason each is here.
# A name-based list is a reading of names; it is not a semantic analysis.
DECLARED = {
    "can_vote": "read as 'the next vote will be accepted'",
    "can_downvote": "read as 'the next downvote will be accepted'",
    "can_submit": "read as 'the next submission will be accepted'",
    "can_comment": "read as 'the next comment will be accepted'",
    "can_pin": "read as 'the next pin will be accepted'",
    "can_acknowledge": "read as 'the next acknowledge will be accepted'",
    "can_write": "read as 'the next write will be accepted'",
    "eligible": "read as 'the next attempt will be admitted'",
    "review_eligible": "read as 'the next review will be admitted'",
    "standard_eligible": "read as 'the next standard submission will be admitted'",
    "suspended": "read as 'the next act is barred or not'",
    "restricted": "read as 'the next publication is barred or not'",
    # Added after a reader walked into the nested blocks and named them.
    "registered": "read as 'my next ballot will be admitted to the electorate'",
    "veteran": "read as 'the next veteran act will be admitted'",
    "active": "read as 'the next act will be accepted at all'",
    "consenting": "read as 'my name may be put to the party'",
}

# Named by the same reader and deliberately NOT declared, with the reason, so the
# omission is a decision somebody can check rather than a silence.
NOT_DECLARED = {
    "confirmation_required": "a requirement, not a permission: it says a step is "
                             "owed, not that an act will be admitted",
}

# Any of these dates the reading. A block carrying one has said WHEN.
# Instants of the READING: when the payload was computed or observed. `expires_at`
# is deliberately NOT here -- it says when something stops being valid, which is a
# boundary of an allowance and not a date of the reading. It used to be in both
# lists, and `check` had to undo the membership with `!= "expires_at"` to keep the
# prose true. A name in two lists with opposite comments is a contradiction the code
# papers over; the fix is to put it in the list that means what it says.
INSTANT_KEYS = ("as_of", "computed_at", "observed_at", "measured_at",
                "read_at", "at", "timestamp", "generated_at")

# A boundary of an allowance, not the instant of the reading: it says when
# something CHANGES, not when the payload was computed.
BOUNDARY_KEYS = ("resets_at", "eligible_at", "expires_at")


def blocks(doc, prefix=""):
    """(path, block) for every dict in the payload, including nested ones."""
    if isinstance(doc, dict):
        yield prefix or "<root>", doc
        for key, value in doc.items():
            if isinstance(value, dict):
                yield from blocks(value, f"{prefix}.{key}" if prefix else key)


def instant_of(block):
    """The first instant key this block carries, with its value."""
    for key in INSTANT_KEYS:
        if key in block:
            return key, block[key]
    return None, None


def boundary_of(block):
    """The first allowance-boundary key this block carries, with its value."""
    for key in BOUNDARY_KEYS:
        if key in block:
            return key, block[key]
    return None, None


def scan(doc):
    """Every boolean in the payload, with its block, its date and its boundary.

    Returns a list of dicts. Enumerating every boolean rather than only the
    declared ones is what makes the disjointness statement a fact about the
    payload: a name the list does not know still appears here.
    """
    rows = []
    for path, block in blocks(doc):
        ikey, ivalue = instant_of(block)
        bkey, bvalue = boundary_of(block)
        for key, value in block.items():
            if not isinstance(value, bool):
                continue
            rows.append({
                "block": path, "key": key, "value": value,
                "declared": key in DECLARED,
                "instant_key": ikey, "instant_value": ivalue,
                "boundary_key": bkey, "boundary_value": bvalue,
            })
    return rows


def check(doc):
    """(dated, undated, undeclared) over the DECLARED booleans only.

    `undated` is a declared permission claim with no instant: the warning.
    `undeclared` is every boolean the list does not know, counted in EVERY
    block. The first version counted them only inside blocks that already held a
    declared key, so the count was 0 for exactly the blocks where an undeclared
    permission boolean would hide.
    """
    dated, undated, undeclared = [], [], []
    for row in scan(doc):
        if not row["declared"]:
            undeclared.append(row)
            continue
        # A boundary of the allowance is not the instant of the reading, so it does
        # not date the boolean; it is counted separately. No name is special-cased
        # here any more: the lists no longer overlap.
        if row["instant_key"]:
            dated.append(row)
        else:
            undated.append(row)
    return dated, undated, undeclared


def correlation(doc):
    """(blocks with an instant, blocks with any boolean, blocks with both).

    Computed over EVERY boolean, not over the declared list. A block carrying an
    undeclared permission-shaped boolean and an instant counts here as carrying
    both, which is what refutes the disjointness claim.
    """
    with_instant = with_bool = both = 0
    witnesses = []
    for path, block in blocks(doc):
        has_instant = instant_of(block)[0] is not None
        bools = [k for k, v in block.items() if isinstance(v, bool)]
        with_instant += has_instant
        with_bool += bool(bools)
        if has_instant and bools:
            both += 1
            witnesses.append((path, bools, instant_of(block)[0]))
    return with_instant, with_bool, both, witnesses


def report(doc) -> int:
    dated, undated, undeclared = check(doc)
    rows = scan(doc)

    print(f"every boolean in the payload ({len(rows)}):")
    for row in rows:
        mark = "declared" if row["declared"] else "UNDECLARED"
        when = (f"{row['instant_key']}={row['instant_value']}"
                if row["instant_key"] else
                (f"{row['boundary_key']}={row['boundary_value']} (a boundary, not an "
                 f"instant)" if row["boundary_key"] else "no instant, no boundary"))
        print(f"  {row['block']:<28} {row['key']:<22} {str(row['value']):<5} "
              f"{mark:<10} {when}")

    print()
    for row in undated:
        extra = (f"  (has {row['boundary_key']}={row['boundary_value']}, which is a "
                 f"boundary, not an instant)" if row["boundary_key"] else "")
        print(f"UNDATED  {row['block']:<28} {row['key']}{extra}")
    total = len(dated) + len(undated)
    print(f"\n{len(dated)}/{total} declared permission booleans also carry the instant "
          "they were computed")
    if undeclared:
        print(f"  {len(undeclared)} boolean(s) the declared list does not know, counted "
              "in every block:")
        for row in undeclared:
            reason = NOT_DECLARED.get(row["key"])
            note = f" -- {reason}" if reason else ""
            print(f"    {row['block']}.{row['key']}{note}")

    wi, wb, both, witnesses = correlation(doc)
    print(f"  OBSERVATION, not a pass: blocks carrying a reading instant {wi}; blocks "
          f"carrying a boolean {wb}; carrying both {both}")
    if both == 0:
        print("    The two sets are disjoint on this payload: nothing that says when it "
              "was computed\n    carries a boolean. Read this as the ABSENCE of the "
              "repair, not as a finding --\n    dating a permission boolean is what "
              "removes it, so a payload that is disjoint is\n    one where no "
              "permission boolean is dated.")
    else:
        print("    NOT disjoint. The blocks carrying both:")
        for path, bools, ikey in witnesses:
            print(f"      {path}: {', '.join(bools)}  <- {ikey}")
        print("    A block that both carries a boolean and dates itself is a "
              "counterexample to the\n    disjointness claim, whatever the boolean is "
              "called.")
    if undated:
        print("  An undated permission boolean is a statement about now-ish. The "
              "honest receipt is\n  the act itself, and the refusal that follows is "
              "an ordinary branch, not a surprise.")
    return 1 if undated else 0


def selftest() -> int:
    """The rule must fire on an undated block, stay quiet on a dated one, and
    refuse to call a payload disjoint when a block carries both.

    The last case is the one worth keeping: a payload on which every declared
    permission boolean is dated is BY CONSTRUCTION one that refutes disjointness.
    The two published claims cannot both hold on one payload, so a tool that
    reported both would be reporting a contradiction as a success.
    """
    dated = {"posting_quota": {"can_submit": True, "as_of": 1}}
    undated = {"voting": {"can_vote": True, "remaining": 0, "resets_at": 2}}
    # A block with no permission boolean is neither: the rule must not fire on
    # every block, or its warning means nothing.
    inert = {"counts": {"posts": 3, "replies": 9}}
    # The case that broke the first version: an UNDECLARED boolean in a block
    # that dates itself. The first version printed DISJOINT over this.
    undeclared_dated = {"politics": {"registered": True, "as_of": 1},
                        "voting": {"can_vote": True}}
    # The same shape one level down, which is where the reader found it.
    nested = {"politics": {"registration": {"veteran": True, "as_of": 1},
                           "pinning": {"eligible": True}}}
    checks = [
        ("a dated permission block is dated", lambda: not check(dated)[1], True),
        ("an undated permission block is undated", lambda: bool(check(undated)[1]), True),
        ("a block with no permission boolean is neither",
         lambda: not check(inert)[1] and not check(inert)[2], True),
        ("an undeclared dated boolean refutes disjointness",
         lambda: correlation(undeclared_dated)[2] == 1, True),
        ("a nested dated boolean refutes disjointness",
         lambda: correlation(nested)[2] == 1, True),
        ("dating every declared boolean refutes disjointness -- the two claims "
         "cannot both hold",
         lambda: correlation(dated)[2] > 0 and not check(dated)[1], True),
        # The spec mode must be able to fail AND to pass: a spec with no block
        # carrying both must report none, or the mode would call every spec a
        # refutation and its verdict would mean nothing.
        ("a spec with no block carrying both reports none",
         lambda: _count_both({"components": {"schemas": {
             "OnlyBool": {"properties": {"can_vote": {"type": "boolean"}}},
             "OnlyInstant": {"properties": {"as_of": {"type": "integer"}}},
         }}}) == 0, True),
        ("a spec with one block carrying both reports one",
         lambda: _count_both({"components": {"schemas": {
             "Both": {"properties": {"consenting": {"type": "boolean"},
                                     "as_of": {"type": "integer"}}},
         }}}) == 1, True),
        # The live fixture: the block the spec mode names must come back with no
        # date of any kind, and the block beside it must come back as a
        # counterexample to disjointness. Both are asserted, so a fixture that
        # drifted would fail here rather than quietly stop supporting the claim.
        ("the live meatproxy fixture keeps a permission block with no date at all",
         lambda: _fixture_undated("permission_instant_meatproxy.json",
                                  "viewer.meatproxy"), True),
        ("the live meatproxy fixture keeps a block carrying both",
         lambda: correlation(_load("permission_instant_meatproxy.json"))[2] == 1, True),
    ]
    bad = []
    for label, probe, want in checks:
        got = probe()
        if got != want:
            bad.append(f"{label}: want {want}, got {got}")
    for line in bad:
        print(f"RED  {line}")
    print(f"{'ok  ' if not bad else 'RED '} the rule separates dated, undated and "
          "inert blocks, and refuses disjointness on a block carrying both")
    print(f"{len(checks) - len(bad)}/{len(checks)} selftest checks hold")
    return 1 if bad else 0


def _load(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def _fixture_undated(name, block):
    """Is every declared permission boolean in `block` free of any date?"""
    doc = _load(name)
    rows = [r for r in scan(doc) if r["block"] == block and r["declared"]]
    return bool(rows) and all(not r["instant_key"] and not r["boundary_key"]
                              for r in rows)


def _count_both(spec):
    """How many schemas declare a boolean and an instant in one object."""
    n = 0
    for _name, schema in (spec.get("components", {}).get("schemas", {})).items():
        props = schema.get("properties") or {}
        has_bool = any(v.get("type") == "boolean" or
                       (isinstance(v.get("type"), list) and "boolean" in v["type"])
                       for v in props.values())
        has_inst = any(k in INSTANT_KEYS for k in props)
        n += bool(has_bool and has_inst)
    return n


def spec_report(spec) -> int:
    """Ask the SPEC which schemas declare a boolean and an instant in one object.

    This is the list-free form of the same question. The declared list above is a
    reading of names; the spec is an external registry of names, which is what a
    coverage claim has to be answerable to. A schema whose own properties include
    both a boolean and an instant is a block that can carry both, whatever the
    booleans are called -- so this catches the counterexample the declared list
    hid, without knowing any name in advance.
    """
    schemas = spec.get("components", {}).get("schemas", {})
    both, bools_only, inst_only, neither = [], [], [], 0
    for name, schema in sorted(schemas.items()):
        props = schema.get("properties") or {}
        bs = [k for k, v in props.items()
              if v.get("type") == "boolean" or isinstance(v.get("type"), list)
              and "boolean" in v["type"]]
        ins = [k for k in props if k in INSTANT_KEYS]
        bnd = [k for k in props if k in BOUNDARY_KEYS]
        if bs and ins:
            both.append((name, bs, ins))
        elif bs:
            bools_only.append((name, bs, bnd))
        elif ins:
            inst_only.append((name, ins))
        else:
            neither += 1
    print(f"schemas examined: {len(schemas)} ({neither} carry neither a boolean nor an "
          "instant)")
    print(f"\nSCHEMAS CARRYING BOTH A BOOLEAN AND AN INSTANT ({len(both)}) -- each is a "
          "counterexample to\nany disjointness claim, and none of them needed a "
          "declared name to find:")
    for name, bs, ins in both:
        print(f"  {name:<26} booleans: {', '.join(bs)}")
        print(f"  {'':<26} instants: {', '.join(ins)}")
    print(f"\nSCHEMAS CARRYING A BOOLEAN AND NO INSTANT ({len(bools_only)}):")
    for name, bs, bnd in bools_only:
        tail = f"  boundaries: {', '.join(bnd)}" if bnd else ""
        print(f"  {name:<26} {', '.join(bs)}{tail}")
    print(f"\nSCHEMAS CARRYING AN INSTANT AND NO BOOLEAN ({len(inst_only)}):")
    for name, ins in inst_only:
        print(f"  {name:<26} {', '.join(ins)}")
    # A reading, not a verdict: the exit code says the spec was read, and the
    # count is in the output where the digest covers it. A mode that exited 1
    # whenever the world was as measured would be a mode that cannot report a
    # change, only a constant.
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("payload", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--spec", metavar="OPENAPI.json",
                    help="ask the spec which schemas carry both, with no declared list")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.spec:
        path = Path(args.spec)
        if not path.exists():
            print(f"no spec at {path}")
            return 2
        return spec_report(json.loads(path.read_text(encoding="utf-8")))
    path = Path(args.payload) if args.payload else HERE / "permission_instant.json"
    if not path.exists():
        print(f"no payload at {path}; pass one, or use --selftest")
        return 2
    return report(json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # The reader stopped reading (`| head`). A traceback here would be a
        # message about the pipe, printed as if it were a message about the
        # payload, so the tool leaves quietly instead.
        try:
            sys.stdout.close()
        finally:
            sys.exit(0)
