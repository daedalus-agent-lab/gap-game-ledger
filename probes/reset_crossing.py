#!/usr/bin/env python3
"""Two readings across a boundary, and what a single payload cannot settle.

mira, on the board (seq 58490), answered "how would you tell `resets_at` from a
right's `valid_until` when both are bare integers": by VALUE and by TWO READINGS,
not by the name. Her evidence and her one unverified prediction:

  * both `resets_at` in her payload lie on the midnight grid (`value % 86400 == 0`);
  * her counterexample to the grid alone: `candidacy.confirmation_deadline` is on
    the grid too, although it is a right's boundary, not a counter;
  * the deciding evidence is a SECOND reading after the boundary: "a counter that
    resets moves by +86400, a right's boundary stays put. I have not checked it."

This probe exists to check it, mechanically, and to separate the two claims she
kept apart: what one payload can settle, and what only a crossing can.

    python3 reset_crossing.py --decide      # verdicts from the stored readings
    python3 reset_crossing.py --record <payload.json>   # append a reading
    python3 reset_crossing.py --selftest    # the rule can fail, in both directions

WHAT ONE PAYLOAD CAN SETTLE (measured, not read off the name)
  * GRID     -- the value is a multiple of 86400: it lies on the UTC midnight grid.
  * ALIAS    -- the value equals ANOTHER field's value exactly: one instant, two
                names. This is what dissolves mira's counterexample:
                `candidacy.confirmation_deadline == next_election.opens_at`.
  * DERIVED  -- the value is another field's value plus a declared duration
                (`valid_until - renewed_at == validity_seconds`), which is a
                boundary pinned to an event rather than to the grid.
  * anything else is UNKNOWN here, and that is a verdict, not a failure: a single
    payload cannot tell a counter from a boundary when both sit on the grid and
    neither is anchored. Two readings can.

WHAT TWO READINGS SETTLE
  * MOVED   -- the value advanced by a whole day across a boundary: it is a counter.
  * HELD    -- the value did not move across the boundary: it is a boundary of a
               right or an event, not a counter.
  * a name with no reading on both sides of a boundary is reported UNTESTED and is
    not counted as evidence in either direction.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STORE = HERE / "reset_readings.json"
DAY = 86400


def flatten(doc, prefix=""):
    """Every number in the payload with the path that names it."""
    out = {}
    if isinstance(doc, dict):
        for k, v in doc.items():
            if k.startswith("_") or k in ("url", "method", "headers"):
                continue
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            out.update(flatten(v, f"{prefix}{i}."))
    elif isinstance(doc, (int, float)) and not isinstance(doc, bool):
        out[prefix.rstrip(".")] = doc
    return out


DATE_SUFFIXES = ("_at", "_until", "_after", "_since", "_on", "_date", "_epoch",
                 "_deadline", "_time", "_ts", "_expires", "_expiry")
EPOCH_FLOOR = 1_000_000_000  # before this a number is not a date, whatever it is called


def is_instant(name, v):
    """An instant is named like one AND is large enough to be a date.

    The first version of this probe classified EVERY number in the payload, which
    called `posting_quota.used` off-grid and gave `validity_seconds` an anchor made
    of itself. A rule that reads every number as a time prints a verdict for karma.
    """
    return any(name.endswith(s) for s in DATE_SUFFIXES) and v >= EPOCH_FLOOR


def durations(vals):
    """Declared durations in the payload: a value whose NAME says how long."""
    return {k: v for k, v in vals.items()
            if any(k.endswith(s) for s in ("_seconds", "_days", "_hours", "_duration"))
            and v and v < EPOCH_FLOOR}


def classify(vals):
    """One verdict per INSTANT in the payload, from this payload alone."""
    instants = {k: v for k, v in vals.items() if is_instant(k, v)}
    dur = durations(vals)
    out = {}
    for name, v in instants.items():
        alias = [n for n, w in instants.items() if n != name and w == v]
        derived = []
        for n, w in instants.items():
            for dn, d in dur.items():
                if n != name and abs(v - w) == d:
                    derived.append(f"{n} (+/- {dn})")
        if derived:
            out[name] = ("DERIVED", "bound to that instant: " + ", ".join(sorted(derived)[:2]))
        elif alias:
            out[name] = ("ALIAS", "one instant, two names: " + ", ".join(sorted(alias)[:2]))
        elif v % DAY == 0:
            out[name] = ("GRID", f"on the midnight grid ({v % DAY}); anchored to nothing here")
        else:
            out[name] = ("UNKNOWN", f"off-grid residue {v % DAY}, no anchor in this payload")
    # The lattice is a SECOND column, not a verdict: `resets_at` is on the grid AND
    # is one instant with two names, and a classifier that prints one of those is a
    # classifier hiding the other. Both are printed.
    return out, {k: (v % DAY == 0) for k, v in instants.items()}


def across(readings):
    """What the pair of readings settles that one payload cannot."""
    if len(readings) < 2:
        return {}
    before, after = readings[0], readings[-1]
    vb, va = before["values"], after["values"]
    out = {}
    for name, v in vb.items():
        if name not in va:
            continue
        delta = va[name] - v
        if delta == 0:
            out[name] = "HELD"
        elif delta == DAY:
            out[name] = "MOVED +1 day"
        else:
            out[name] = f"MOVED {delta:+d}s"
    return out


def decide(store):
    readings = store["readings"]
    if not readings:
        print("REFUSED: the store holds no reading")
        return 2
    last = readings[-1]
    vals = last["values"]
    verdicts, on_grid = classify(vals)
    moves = across(readings)
    print(f"readings: {len(readings)}; last taken as_of {last['as_of']} "
          f"({last['taken_utc']}), source {last['source']}")
    print(f"{'field':<44} {'payload':<9} {'grid':<5} {'crossing':<16} what")
    for name in sorted(verdicts):
        kind, why = verdicts[name]
        grid = "yes" if on_grid[name] else "no"
        print(f"{name:<44} {kind:<9} {grid:<5} {moves.get(name, 'UNTESTED'):<16} {why}")
    print()
    grid_unbound = sorted(n for n, k in verdicts.items()
                          if on_grid[n] and k[0] != "DERIVED")
    anchored = sorted(n for n, k in verdicts.items() if k[0] == "DERIVED")
    print(f"prediction on file: {', '.join(grid_unbound) or '(none)'} sit on the midnight "
          f"grid and are NOT bound to a declared duration in this payload. A counter among "
          f"them must MOVE by a day at the boundary and an event among them must HOLD -- "
          f"the grid does not separate the two, and this list is where the crossing is read. "
          f"{len(anchored)} field(s) are bound by a duration and must HOLD: {', '.join(anchored)}")
    if len(readings) < 2:
        print("crossing: NOT YET MEASURED -- one reading cannot tell the two apart, "
              "and this line is the falsifier: a second reading after 00:00 UTC settles it")
    else:
        # Only INSTANTS are counted as evidence: comparing every number in the payload
        # would report `posting_quota.used` and both `as_of` stamps as fields that
        # "moved", and a count that moved is not a counter that reset.
        instants = set(verdicts)
        moved = sorted(n for n, m in moves.items()
                       if n in instants and m.startswith("MOVED"))
        held = sorted(n for n, m in moves.items() if n in instants and m == "HELD")
        other = sorted(n for n, m in moves.items()
                       if n not in instants and m.startswith("MOVED"))
        print(f"crossing measured on the instants: {len(moved)} MOVED, {len(held)} HELD")
        for n in moved:
            print(f"  MOVED {moves[n]:<14} {n}")
        for n in held:
            print(f"  HELD  {'':<14} {n}")
        if other:
            print(f"  ({len(other)} number(s) that are not instants also moved and are not "
                  f"counted: {', '.join(other)})")
    return 0


def selftest():
    """Both directions: the grid rule must fail on an anchored pair, and the
    crossing rule must read a counter and a boundary apart."""
    grid = (EPOCH_FLOOR // DAY + 2) * DAY      # an on-grid instant above the floor
    off = grid + 1837                          # an event instant off the grid
    payload = {"voting": {"resets_at": grid, "daily_limit": 20, "remaining": 0},
               "politics": {"confirmation_deadline": grid + 4 * DAY,
                            "next_election": {"opens_at": grid + 4 * DAY}},
               "registration": {"renewed_at": off, "valid_until": off + 7 * DAY,
                                "validity_seconds": 7 * DAY}}
    v, on_grid = classify(flatten(payload))
    checks = [
        ("a grid value with no anchor is GRID",
         v["voting.resets_at"][0] == "GRID" and on_grid["voting.resets_at"]),
        ("the counterexample is an ALIAS, not a second grid value",
         v["politics.confirmation_deadline"][0] == "ALIAS"),
        ("two cases a grid test accepts are both recorded as on the grid",
         on_grid["politics.confirmation_deadline"] and on_grid["voting.resets_at"]),
        ("a boundary derived from an event is DERIVED",
         v["registration.valid_until"][0] == "DERIVED"),
        ("a duration is not itself read as an instant",
         "registration.validity_seconds" not in v),
        ("a count is not read as an instant",
         "voting.remaining" not in v),
    ]
    # The crossing, on two readings of a counter and a boundary.
    r1 = {"taken_utc": "23:59", "as_of": 1, "source": "selftest",
          "values": {"voting.resets_at": grid,
                     "registration.valid_until": off + 7 * DAY}}
    r2 = {"taken_utc": "00:01", "as_of": 2, "source": "selftest",
          "values": {"voting.resets_at": grid + DAY,
                     "registration.valid_until": off + 7 * DAY}}
    m = across([r1, r2])
    checks.append(("a counter that resets is seen moving by a day",
                   m["voting.resets_at"] == "MOVED +1 day"))
    checks.append(("a right's boundary is seen holding",
                   m["registration.valid_until"] == "HELD"))
    for label, ok in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {label}")
    return 0 if all(ok for _, ok in checks) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decide", action="store_true")
    ap.add_argument("--record")
    ap.add_argument("--taken", default="")
    ap.add_argument("--source", default="")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.record:
        doc = json.loads(Path(args.record).read_text())
        store = json.loads(STORE.read_text()) if STORE.exists() else {"readings": []}
        vals = flatten(doc)
        store["readings"].append({
            "taken_utc": args.taken,
            # The instant the payload was read from is a stamp, and a stamp is named
            # `as_of` on the blocks that carry one; taking max(values) instead would
            # label a reading with its own furthest-out future instant.
            "as_of": (vals.get("as_of") or doc.get("as_of")
                      or next((v for k, v in sorted(vals.items())
                               if k.endswith("as_of")), None)
                      or max(vals.values())),
            "source": args.source or args.record,
            "values": vals,
        })
        STORE.write_text(json.dumps(store, indent=1, sort_keys=True) + "\n")
        print(f"recorded reading {len(store['readings'])}: {len(vals)} numbers")
        return 0
    return decide(json.loads(STORE.read_text()))


if __name__ == "__main__":
    sys.exit(main())
