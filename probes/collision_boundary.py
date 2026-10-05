"""The boundary of the duplicate check, pinned in the tree rather than in prose.

WHAT THIS IS. `check.class_collisions` compares class fragments by a fingerprint:
bound names are erased, free names are kept. So it refuses a second NAME for one
logic and never a second SPELLING of it -- two classes over one logic, the second a
behaviour-preserving rewrite of the first, are accepted. Equivalence of programs is
not decidable, so no change to that function closes it; the cheap substitute (agree
on a fixed input set) was built, run over this ledger and withdrawn
(`probes/behavioural_twin.py`, 4 candidates, all artifacts of its own pool, and 134
of 242 class fragments take no arguments at all).

WHY A PROBE. The paragraph above used to live only in the docstring of
`class_collisions`, where nothing read it: a reader of this repo could take "the
gate refuses a duplicate" to mean "the gate refuses a duplicate however it is
written", and the sentence would have to be re-measured by hand every time someone
doubted it. The four cases below are the same four that were measured by hand on
2026-10-05 (`_work/i4/collision_probe.py`, receipt v1671, digest e0f749319ce0a2ad);
here they are asked of the REAL functions, with the answer each is required to give
written down before the call, so a future change that starts refusing a rewrite, or
stops refusing a rename, or starts accepting a repeat that is the class probe again,
fails this file instead of passing quietly.

WHAT IT DOES NOT CLAIM. That the accepted rewrite is fine. It is a hole with a
stated shape: a defect laundered by a rewrite that changes nothing reads as two
classes. The probe pins the hole so that its size is known and its edges are tested.

Two functions are asked, and they answer different questions:
  `class_collisions`  -- is one logic wearing two class names (cases A, B)
  `evaluate`          -- does a repeat claim a second sighting (cases C, D)

Nothing in the ledger tree is written: the synthetic classes live in
`fragments.NAMESPACES`, which is the dict object `check.py` imported, and the probe
exits non-zero if any case answers differently from what is written beside it.

usage: python3 probes/collision_boundary.py          # exit 0 iff every case matches
       python3 probes/collision_boundary.py --json   # the same, one JSON object
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.environ.get("LEDGER", os.path.dirname(HERE))
sys.path.insert(0, LEDGER)

import check  # noqa: E402
import fragments  # noqa: E402


def f_loop(nums, window):
    total = 0
    for v in nums[:window]:
        total = total + v
    return total


def f_rewrite(nums, window):
    """Same answer as f_loop for every input, written the other way."""
    part = nums[:window]
    return sum(part)


def g_loop(xs, wnd):
    """f_loop with every bound name changed and nothing else."""
    acc = 0
    for item in xs[:wnd]:
        acc = acc + item
    return acc


fragments.NAMESPACES["synth-boundary-a"] = {"f_loop": f_loop}
fragments.NAMESPACES["synth-boundary-b"] = {"f_rewrite": f_rewrite}
fragments.NAMESPACES["synth-boundary-c"] = {"g_loop": g_loop}

CLASS_ENTRY = {"class": "synth-boundary-a", "lang": "python",
               "probe": "f_loop([1,2,3,4], 2)", "observed": "3", "expected": "10"}


def two_classes(namespace_a, namespace_b):
    return {"entries": [
        {"class": namespace_a, "probe": "f_loop(nums, window)"},
        {"class": namespace_b, "probe": "f_rewrite(nums, window)"},
    ]}


def case_a():
    """Two classes, one shape of lie, the second a behaviour-preserving rewrite."""
    n, problems, shared = check.class_collisions(
        {"entries": [
            {"class": "synth-boundary-a", "probe": "f_loop(nums, window)"},
            {"class": "synth-boundary-b", "probe": "f_rewrite(nums, window)"},
        ]})
    return {"primaries": n, "problems": problems, "shared": shared,
            "accepted_as_two_classes": not problems}


def case_b():
    """The same pair, the second differing only in bound names."""
    n, problems, shared = check.class_collisions(
        {"entries": [
            {"class": "synth-boundary-a", "probe": "f_loop(nums, window)"},
            {"class": "synth-boundary-c", "probe": "g_loop(xs, wnd)"},
        ]})
    return {"primaries": n, "problems": problems, "shared": shared,
            "refused": bool(problems)}


def case_c():
    """A repeat that is the class fragment again, with a reworded promise."""
    entry = dict(CLASS_ENTRY)
    entry["repeats"] = [{
        "id": "r-same", "fn": "f_loop", "promise": "returns the windowed sum",
        "fact": "the sum is not the promised value",
        "probe": "f_loop([1,2,3,4], 2)", "expected": "10", "observed": "3"}]
    status, why = check.evaluate(entry)
    return {"status": status, "why": why,
            "refused_as_the_class_probe": status != "ok",
            "names_same_measurement": "not a second sighting" in (why or "")}


def case_d():
    """A repeat on the same fragment with a DIFFERENT measurement: legitimate."""
    entry = dict(CLASS_ENTRY)
    entry["repeats"] = [{
        "id": "r-diff", "fn": "f_loop", "promise": "the window is not truncated",
        "fact": "a one-element window is taken, not the promised value",
        "probe": "f_loop([9,9,9], 1)", "expected": "99", "observed": "9"}]
    status, why = check.evaluate(entry)
    return {"status": status, "why": why, "accepted": status == "ok"}


# The answer each case is required to give, written before the calls.
EXPECT = {
    "A a behaviour-preserving rewrite is ACCEPTED as a second class":
        lambda r: r["primaries"] == 2 and r["accepted_as_two_classes"],
    "B the same pair renamed is REFUSED":
        lambda r: bool(r["problems"]),
    "C a repeat that is the class probe again is REFUSED":
        lambda r: r["refused_as_the_class_probe"] and r["names_same_measurement"],
    "D a repeat with a different measurement is ACCEPTED":
        lambda r: r["accepted"],
}


def main() -> int:
    results = {
        "A a behaviour-preserving rewrite is ACCEPTED as a second class": case_a(),
        "B the same pair renamed is REFUSED": case_b(),
        "C a repeat that is the class probe again is REFUSED": case_c(),
        "D a repeat with a different measurement is ACCEPTED": case_d(),
    }
    bad = []
    for label, got in results.items():
        ok = EXPECT[label](got)
        print(f"{'ok  ' if ok else 'FAIL'} {label}")
        if not ok:
            bad.append(label)
        print(f"       {json.dumps(got, sort_keys=True)[:300]}")
    summary = {
        "cases": len(results),
        "matched": len(results) - len(bad),
        "unexpected": bad,
        "boundary": ("the fingerprint refuses a second NAME for one logic and never "
                     "a second SPELLING of it; a repeat is gated in evaluate, not here"),
        "ledger": LEDGER,
        "head": os.popen(f"git -C {LEDGER} rev-parse HEAD").read().strip(),
    }
    if "--json" in sys.argv:
        print(json.dumps(summary, sort_keys=True))
    else:
        print(f"cases {summary['cases']}  matched {summary['matched']}  "
              f"unexpected {len(bad)}  head {summary['head'][:12]}")
        print(f"BOUNDARY {summary['boundary']}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
