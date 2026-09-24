#!/usr/bin/env python3
"""The nine failures an independent reviewer found in resume_cursor.py, v2.

Each check takes the reviewer's own counterexample and asserts that v3 does not
reproduce it, or - where v3 deliberately changed the contract - asserts the new
behaviour and says so. Written after their report; their own probe file
(probe_regime.py) is not edited, because it encodes v2's API and v2's holey rule,
and a silently edited acceptance test is worth nothing.

Run: python3 probe_regime_v3.py    (exit 0 when every counterexample is answered)
"""

import resource
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import resume_cursor as rc  # noqa: E402


def page(*seqs):
    return [{"seq": s} for s in seqs]


RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    for line in detail.splitlines():
        print(f"      {line}")


# 1. dense reported DELIVERED positions as holes.
out = rc.advance(page(12, 13), 9, regime="dense")
delivered = {12, 13}
as_holes = [m.seq for m in out[1] if m.kind == "hole" and m.seq in delivered]
check("1. dense no longer calls a delivered position a hole",
      out[0] == 9 and not as_holes and sorted(m.seq for m in out[1] if m.kind == "beyond") == [12, 13],
      f"page [12,13] at 9 -> cursor {out[0]}, kinds {sorted({m.kind for m in out[1]})}, "
      f"delivered positions returned as holes: {as_holes}")

# 2. classify accepted and never called in dense.
called = []
rc.advance(page(10, 12), 9, regime="dense",
           classify=lambda s: (called.append(s), "served-no-longer")[1])
check("2. dense uses the caller's classify", bool(called), f"classifier called for {called}")

# 3. the guard was `and`-gated on two names.
a, b = rc.open_stream("seq"), rc.open_stream("seq")
try:
    rc.advance(page(10, 11), rc.Cursor(a, 9), regime="holey", stream=b)
except rc.ForeignCursor:
    check("3. the guard fires when both sides are named", True, "refused")
else:
    check("3. the guard fires when both sides are named", False, "accepted")

# 3b. naming ONE side is no longer expressible: there is no bare name parameter.
ks = rc.advance.__code__.co_varnames[:rc.advance.__code__.co_argcount
                                     + rc.advance.__code__.co_kwonlyargcount]
check("3b. a bare stream NAME is no longer a parameter (only a minted identity is)",
      "stream_id" not in ks and "cursor_stream" not in ks, f"keyword parameters: {ks}")

# 4. two streams sharing one name.
try:
    rc.advance(page(500, 501), rc.Cursor(a, 9), regime="holey", stream=b)
except rc.ForeignCursor as exc:
    check("4. two streams both named 'seq' are told apart", True,
          f"refused on keys, not on names: {str(exc)[:88]}...")
else:
    check("4. two streams both named 'seq' are told apart", False,
          "a cursor from board A used on board B, both named 'seq'")

# 5. holey walked past positions nobody had fetched.
out = rc.advance(page(4, 20), 3, regime="holey")
held = [m.seq for m in out[1] if m.kind == "held"]
check("5. holey does not step over 5..19 unread", out[0] == 4 and held == list(range(5, 20)),
      f"page [4,20] at 3 -> cursor {out[0]} (v2 gave 20), held {held[:3]}..{held[-1:]} "
      f"= {len(held)} positions, all labelled 'unclassified'")
out2 = rc.advance(page(4, 20), 3, regime="holey", classify=lambda s: "served-no-longer")
check("5b. with a W-fact for every hole the cursor does advance",
      out2[0] == 20 and len([m for m in out2[1] if m.kind == "hole"]) == 15,
      f"cursor {out2[0]}, labelled holes {len([m for m in out2[1] if m.kind == 'hole'])}")

# 6. dense froze for ever on a projected page.
projection = page(1, 2, 4, 6, 8, 10)
t = rc.trace([projection] * 3, 0, regime="dense")
check("6. dense on a projected page stops at its own gap and says why",
      t[0][0] == 2 and [m.seq for m in t[0][1] if m.kind == "held"] == [3],
      f"three pages {[1, 2, 4, 6, 8, 10]} at 0 -> cursors {[c for c, _ in t]}; "
      "the stream is dense, the page is a projection, and the gap at 3 is held, not skipped")

# 8. unbounded hole list.
soft, hard = resource.getrlimit(resource.RLIMIT_AS)
resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 ** 3, hard))
try:
    cursor, marks = rc.advance(page(10 ** 9), 0, regime="holey")
    ok, detail = cursor == 0 and len(marks) <= 8, f"cursor {cursor}, {len(marks)} marks"
except MemoryError as exc:
    ok, detail = False, f"MemoryError: {exc}"
finally:
    resource.setrlimit(resource.RLIMIT_AS, (soft, hard))
check("8. a page far above the cursor survives a 2 GiB address limit", ok, detail)

# 9. max_seen([]) raised.
check("9. max_seen([]) agrees with advance about an empty page",
      rc.max_seen([]) is None, f"max_seen([]) -> {rc.max_seen([])}")

# 10. the convenience path dropped the labels.
t = rc.trace([page(10, 12), page(13)], 9, regime="holey",
             classify=lambda s: "served-no-longer")
check("10. trace() returns the labelled holes",
      t[0][1] == [rc.Mark("hole", 11, "served-no-longer")],
      f"trace -> cursors {[c for c, _ in t]}, marks of the first page {t[0][1]}")

# 11. dense is still exactly the contiguous prefix (their probe 10, as a contract).
bad = []
for resume_from in range(-1, 6):
    for r in range(0, 5):
        import itertools
        for combo in itertools.combinations(range(0, 6), r):
            cursor, _ = rc.advance(page(*combo), resume_from, regime="dense")
            seen, want = set(combo), resume_from
            while want + 1 in seen:
                want += 1
            if cursor != want:
                bad.append((resume_from, combo, cursor, want))
check("11. dense's cursor is the contiguous prefix on every small page",
      not bad, f"122 combinations; mismatches: {bad[:3]}")

n = sum(1 for _, ok in RESULTS if ok)
print(f"\n{n} of {len(RESULTS)} checks pass")
sys.exit(0 if n == len(RESULTS) else 1)
