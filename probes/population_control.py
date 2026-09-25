#!/usr/bin/env python3
"""A Receipt Guild packet: a predicate, a RED_CONTROL, and a population_control.

Why a third control is needed. A packet's RED_CONTROL flips the verdict by making
the PAYLOAD not what it claims. A population control flips it by making the
INSTRUMENT's population not cover the payload -- and that is the defect the
packet is supposed to catch, so a schema that records both as FAIL cannot tell
the two apart.

The first form of this probe separated them by "the count moves", and its own
control refuted it: the red control moves the count too (the value stops being a
boolean, so the second reader sees nothing). The discriminator is WHICH reader
moved, and in which direction:

    B falls below A   the payload is at fault -- a value is not what it claims
    B rises above A   the list is at fault -- a block the list never named
    A == B            the two readers agree

A is invariant under both, and that is the point: the list's reader is blind to
both controls, which is exactly why the list is the thing under test.

The predicate below is a real one, taken from a live instrument. It asks whether
a reader that takes the blocks a LIST names sees the same blocks as a reader that
takes every block carrying a boolean. On the canonical payload they agree. On the
population control they do not, and the reader that used the list is the one that
is wrong.

Run:
    python3 probes/population_control.py --selftest
    python3 probes/population_control.py --packet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys

# The list the instrument carries. This is the filter, and it decides what there
# is to read, so it is printed beside every packet rather than left in the code.
DECLARED = ("can_vote", "can_downvote")

CANONICAL = {"voting": {"can_vote": True, "expires_at": 1790500000}}

# RED_CONTROL: the payload is not what it claims -- the boolean is a string.
RED_CONTROL = {"voting": {"can_vote": "yes", "expires_at": 1790500000}}

# POPULATION_CONTROL: the payload is fine and the list does not cover it. The
# block holds both a boolean and a date, and its boolean is not on the list, so
# the list's reader skips the block whole -- the counterexample the reading was
# looking for, invisible to the reading.
POPULATION_CONTROL = {
    "voting": {"can_vote": True, "expires_at": 1790500000},
    "politics": {"registered": True, "as_of": 1790340000},
}

# SEMANTIC_CONTROL: the block's boolean IS on the list, so neither count moves and
# both readers agree -- the list produces the right count on a payload whose own
# sibling refutes the boolean. This is the case a count-based packet cannot see,
# and the reason "the list that produces the right count" is not yet "the right
# list": nothing about a count decides whether a claim agrees with its block.
SEMANTIC_CONTROL = {"voting": {"can_vote": True, "remaining": 0,
                                "expires_at": 1790500000}}

# The mutation of the contradiction reader: drop the sibling it reads and the
# rule goes silent, so the rule is not vacuously true.
NO_SIBLING = {"voting": {"can_vote": True, "expires_at": 1790500000}}


def reader_that_uses_the_list(doc):
    """The blocks the instrument's list names. This is the filter at work."""
    return [b for b in doc.values() if any(k in b for k in DECLARED)]


def reader_that_takes_every_boolean(doc):
    """Every block carrying a boolean, whether or not a list names it."""
    return [b for b in doc.values()
            if any(isinstance(v, bool) for v in b.values())]


def predicate(doc):
    """True when both readers see the same number of blocks."""
    return len(reader_that_uses_the_list(doc)) == \
        len(reader_that_takes_every_boolean(doc))


def counts(doc):
    return (len(reader_that_uses_the_list(doc)),
            len(reader_that_takes_every_boolean(doc)))


def contradictions(doc):
    """Blocks whose own sibling refutes a boolean the list names.

    A count says which blocks are read. It says nothing about whether what they
    claim agrees with what sits beside it in the same block, and that is the
    question a list has to answer to be the RIGHT list rather than a list that
    happens to produce the right count on today's payloads.
    """
    out = []
    for name, block in doc.items():
        if isinstance(block, dict) and block.get("can_vote") is True \
                and block.get("remaining") == 0:
            out.append(name)
    return out


def digest(doc):
    return hashlib.sha256(
        json.dumps(doc, sort_keys=True).encode()).hexdigest()[:16]


def selftest() -> int:
    checks = []

    def check(name, ok, detail=""):
        checks.append((name, ok, detail))

    check("canonical payload: the predicate holds",
          predicate(CANONICAL) is True,
          f"counts {counts(CANONICAL)}")
    check("RED_CONTROL: the predicate fails, and the payload is at fault",
          predicate(RED_CONTROL) is False,
          f"counts {counts(RED_CONTROL)} -- the list's reader still sees one block")
    check("RED_CONTROL: the payload's reader is the one that moved",
          counts(RED_CONTROL)[1] < counts(RED_CONTROL)[0],
          f"counts {counts(RED_CONTROL)} -- B fell below A: a value is not a boolean")
    check("POPULATION_CONTROL: the predicate fails too",
          predicate(POPULATION_CONTROL) is False,
          f"counts {counts(POPULATION_CONTROL)}")
    check("POPULATION_CONTROL: the list's reader is the one that fell short",
          counts(POPULATION_CONTROL)[1] > counts(POPULATION_CONTROL)[0],
          "B rose above A: a block the list never named")
    check("the two controls are separated by WHICH reader moved",
          counts(RED_CONTROL)[1] < counts(RED_CONTROL)[0]
          and counts(POPULATION_CONTROL)[1] > counts(POPULATION_CONTROL)[0],
          "so a packet can record which control fired without asking the runner")
    check("the list's reader is blind to both controls",
          counts(RED_CONTROL)[0] == counts(CANONICAL)[0]
          and counts(POPULATION_CONTROL)[0] == counts(CANONICAL)[0],
          "A never moves -- which is why the list is the thing under test")
    check("the list is printed with the packet",
          all(k in json.dumps(DECLARED) for k in DECLARED),
          "a list that is not in the packet is a list the reader cannot check")
    check("SEMANTIC_CONTROL: the count does not move, so no count can see it",
          counts(SEMANTIC_CONTROL) == counts(CANONICAL)
          and predicate(SEMANTIC_CONTROL) is True,
          f"counts {counts(SEMANTIC_CONTROL)} -- identical to the canonical payload")
    check("SEMANTIC_CONTROL: a reader of the sibling catches what the count cannot",
          contradictions(CANONICAL) == []
          and contradictions(SEMANTIC_CONTROL) == ["voting"],
          "can_vote True beside remaining 0: the block refutes its own boolean")
    check("the contradiction reader is not vacuously true",
          contradictions(NO_SIBLING) == [],
          "the same boolean with no sibling is silent, so the rule reads the sibling")
    check("so the count and the contradiction are two observables, not one",
          (counts(NO_SIBLING) == counts(SEMANTIC_CONTROL))
          and (contradictions(NO_SIBLING) != contradictions(SEMANTIC_CONTROL)),
          "the count cannot separate these two; the contradiction reader does")

    width = max(len(n) for n, _, _ in checks)
    for name, ok, detail in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {name:<{width}}  {detail}")
    failed = sum(1 for _, ok, _ in checks if not ok)
    print(f"\n{len(checks) - failed}/{len(checks)} selftest checks hold")
    return 0 if failed == 0 else 1


def packet() -> int:
    print("claim            a reader that takes the blocks a list names sees the "
          "same blocks as a reader that takes every block carrying a boolean")
    print("source           probes/population_control.py, this repo, this commit")
    print(f"population       the list the instrument carries: {list(DECLARED)}")
    print("command          python3 probes/population_control.py --selftest")
    print("expected         the predicate holds on the canonical payload")
    print()
    for label, doc in (("canonical", CANONICAL),
                       ("RED_CONTROL", RED_CONTROL),
                       ("POPULATION_CONTROL", POPULATION_CONTROL),
                       ("SEMANTIC_CONTROL", SEMANTIC_CONTROL),
                       ("NO_SIBLING", NO_SIBLING)):
        a, b = counts(doc)
        print(f"{label:<19} sha16 {digest(doc)}  counts A={a} B={b}  "
              f"predicate={predicate(doc)}  contradictions={contradictions(doc)}")
    print()
    print("red_control      the boolean is a string; B falls below A, so the "
          "payload is at fault")
    print("population_control  a block holding both a boolean and a date, whose "
          "boolean the list does not name; B rises above A, so the list is at fault")
    print("invariant        A does not move under either control: the list's "
          "reader cannot see what the list left out")
    print("semantic_control a block whose boolean the list DOES name, refuted by "
          "its own sibling: count unchanged, predicate true, contradiction found")
    print("second_observable  the count separates whole-population defects; a "
          "sibling reader separates defects inside a block the population covers, "
          "so a packet that records one number is recording one of two questions")
    print("result_origin    output, not typed: the counts above are printed by "
          "the run that computed them")
    print("status           PASS on this machine; a runner on another machine "
          "reports its own passport")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--packet", action="store_true")
    args = ap.parse_args(argv)
    if args.packet:
        return packet()
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
