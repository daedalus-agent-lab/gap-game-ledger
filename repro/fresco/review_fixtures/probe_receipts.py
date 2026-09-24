#!/usr/bin/env python3
"""Probes for the receipt gate in resume_cursor.py v4.

The claim under test is a measurement a third party made on the live board: a
message deleted by its author and a fresh uuid4 return byte-identical bodies, so
a reader of that stream has two states, {present, absent}, and neither
`deleted-by-me` nor `never-existed` can be read off it. A label that only its
holder can re-derive therefore has to travel with the write-time receipt that
produced it, or it is a word.

Run: python3 fresco/review_fixtures/probe_receipts.py     (exit 0 when all hold)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import resume_cursor as rc


def page(*seqs):
    return [{"seq": s} for s in seqs]


CHECKS = []


def check(name):
    def wrap(fn):
        CHECKS.append((name, fn))
        return fn
    return wrap


@check("a holder-memory label with nobody to assert it holds the cursor and is named")
def _():
    out = rc.advance(page(10, 12), 9, regime="holey",
                     classify=lambda s: "deleted-by-me")
    assert out[0] == 10, out
    assert out[1][0] == rc.Mark("unproven", 11, "deleted-by-me"), out[1]
    assert out[1][1] == rc.Mark("beyond", 12), out[1]


@check("a declared holder without the write-time receipt still holds")
def _():
    out = rc.advance(page(10, 12), 9, regime="holey",
                     classify=lambda s: "deleted-by-me", asserted_by="me")
    assert out[0] == 10 and out[1][0].kind == "unproven", out


@check("the same label with holder and receipt lets the cursor pass")
def _():
    out = rc.advance(page(10, 12), 9, regime="holey",
                     classify=lambda s: "deleted-by-me",
                     asserted_by="me", receipts={11: ("DELETE", 200, 74)})
    assert out[0] == 12 and out[1] == [rc.Mark("hole", 11, "deleted-by-me")], out


@check("a receipt for another position is not a receipt for this one")
def _():
    out = rc.advance(page(10, 12), 9, regime="holey",
                     classify=lambda s: "deleted-by-me", asserted_by="me",
                     receipts={99: "x"})
    assert out[0] == 10, out


@check("a label reading can check needs no holder and no receipt")
def _():
    out = rc.advance(page(10, 12), 9, regime="holey",
                     classify=lambda s: "served-no-longer")
    assert out[0] == 12, out


@check("a non-event has no receipt to show, so only its owner may assert it")
def _():
    out = rc.advance(page(10, 12), 9, regime="holey", classify=lambda s: "never-existed")
    assert out[0] == 10 and out[1][0].kind == "unproven", out
    out = rc.advance(page(10, 12), 9, regime="holey",
                     classify=lambda s: "never-existed", asserted_by="owner")
    assert out[0] == 12 and out[1] == [rc.Mark("hole", 11, "never-existed")], out


@check("every label declares a holder, a way to check it, and a window")
def _():
    for lab, spec in rc.LABELS.items():
        assert spec.holder and spec.checkable and spec.window, lab
        assert spec.checkable in ("reading", "holder-memory", "none"), (lab, spec)
        assert "\n" not in spec.window, lab
    assert rc.LABELS["deleted-by-me"].needs_receipt is True
    assert rc.LABELS["served-no-longer"].needs_receipt is False
    assert rc.LABELS["served-no-longer"].checkable == "reading"
    assert rc.LABELS["never-existed"].checkable == "holder-memory", \
        "no reading can tell a non-event from a deletion"
    assert rc.LABELS["deleted-by-me"].checkable == "holder-memory"
    assert rc.LABELS["unclassified"].checkable == "none", "unclassified is not a licence"


@check("the receipt gate is asked of holes, never of delivered positions")
def _():
    seen = []
    rc.advance(page(10, 11, 12), 9, regime="holey",
               classify=lambda s: (seen.append(s), "deleted-by-me")[1])
    assert seen == [], seen
    assert rc.advance(page(10, 11, 12), 9, regime="holey")[0] == 12


@check("a classifier is asked once per position in dense, so a non-function cannot lie")
def _():
    seen = []
    rc.advance(page(10, 12), 9, regime="dense",
               classify=lambda s: (seen.append(s), "deleted-by-me")[1])
    assert seen == [11], seen


@check("dense never steps over a gap, whatever the label promises")
def _():
    out = rc.advance(page(10, 12), 9, regime="dense", classify=lambda s: "served-no-longer",
                     receipts={11: ("DELETE", 200, 74)})
    # the cursor walks over what the page delivered (10) and stops in front of the
    # gap; a W-fact label and a write-time receipt change nothing in dense
    assert out[0] == 10 and out[1] == [rc.Mark("held", 11, "served-no-longer"),
                                       rc.Mark("beyond", 12)], out


@check("a stale page moves nothing, and an empty page says so with no marks")
def _():
    assert rc.advance(page(5, 6), 9, regime="holey") == (9, [])
    assert rc.advance(page(), 9, regime="holey") == (9, [])


@check("the module's own demonstration still runs")
def _():
    rc.demo()


def main() -> int:
    bad = []
    for name, fn in CHECKS:
        try:
            fn()
            print(f"ok   {name}")
        except AssertionError as exc:
            bad.append((name, exc))
            print(f"FAIL {name}: {exc}")
    print(f"\n{len(CHECKS) - len(bad)} of {len(CHECKS)} checks pass")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
