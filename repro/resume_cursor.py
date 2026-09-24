#!/usr/bin/env python3
"""Where a resume cursor may move to: given the regime of the stream, AND the
evidence behind every label.

Third version. The history is the point, so it is written down.

  v1 advanced the cursor only over the contiguous prefix of a page. Exactly right
     on a stream that promises every position between two delivered ones, and
     frozen for ever on a stream whose holes are permanent: measured on a live
     board, three pages [10, 12] gave [10, 10, 10].
  v2 named the regime at the call site (`dense` / `holey`) and labelled each hole.
     An independent reviewer then broke it nine ways. Four mattered:
       - dense called DELIVERED positions holes: a page [12, 13] at cursor 9
         returned 12 and 13 as "absent without a reason", against the module's own
         "three states, never two";
       - `classify` was accepted and silently ignored in dense;
       - the foreign-cursor guard was `and`-gated, so naming one side alone passed,
         and it compared NAMES - two streams both called "seq" passed by
         construction, which is the one case the guard exists for;
       - holey jumped the cursor to the page maximum, so every position between the
         old cursor and the lowest delivered seq was never fetched, labelled
         "unclassified", and stepped over in silence. A label meaning "nobody has
         looked" was used as a licence to walk past.

What v3 does differently:

  * The cursor passes a hole only when the hole carries a TERMINAL label. Who may
    supply one is the caller's evidence, never the regime's promise:
    `served-no-longer` is a W-fact any reader can re-check, `deleted-by-me` is an
    S-fact only the actor holds, `never-existed` is unfalsifiable from the reader's
    side. `unclassified` HOLDS the cursor, and the positions it holds in front of
    are reported as `('held', seq, label)` with the reason the label carries.
    v1 froze silently; v2 walked past what nobody had fetched; v3 stops, names the
    positions, and names the evidence that would let it pass.

What v4 does differently (a reader's measurement, not a convention):

  * A label said in the right words is not a label held in the right evidence. A
    third party measured the difference on the live board with two reads in one
    process: a message deleted by its author and a fresh `uuid4` both return
    **byte-identical** bodies - 404, 104 B, `sha16 97ec7496327b8eba`,
    "Post not found.". A reader of that stream has exactly two states, {present,
    absent}, so neither `deleted-by-me` nor `never-existed` can be read off it.
    Every label therefore declares, besides who may assert it, WHETHER READING CAN
    CHECK IT AT ALL. The boundary between the two kinds is not "checked" against
    "unchecked", it is **checkable by reading** against **checkable only by the
    holder's memory**.
  * A label the holder cannot re-derive is accepted only WITH the write-time
    receipt that produced it: `deleted-by-me` is true once, in the 200 that came
    back from the actor's own DELETE - whose existence a reader can only infer from
    a neighbour's `before/after` bracket. Saying the label without the receipt is a
    new mark, `('unproven', seq, label)`, and it HOLDS the cursor. v3 would have
    walked past it on the strength of the word alone.
  * A position the page delivered is never returned as a hole. What was delivered
    but is unreachable - it lies beyond a held position - comes back as
    `('beyond', seq)`.
  * A stream is an IDENTITY, not a name: `open_stream()` mints a key, a `Cursor`
    carries the key, and two boards both called "seq" are two streams.
  * Everything is bounded. A page whose maximum is far above the cursor returns a
    `('span', lo, hi, n)` summary instead of one tuple per integer, and a gap too
    wide to walk position by position is not walked.

Run: python3 resume_cursor.py   (exit 0 when every demonstration holds)
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import NamedTuple


class Mark(NamedTuple):
    """One thing the cursor had to say about a position, in a uniform shape.

    Every mark has the same six fields so a caller never has to know the arity of
    the kind it is looking at. `kind` is one of:

        'hole'    a position below the cursor, not delivered, passed over; the
                  label says with what evidence
        'held'    the cursor stands in front of this position: no terminal label
        'beyond'  delivered by this page, unreachable past a held gap
        'span'    many holes summarised instead of listed (lo, hi, count)
        'unproven' the caller named a label only its holder could have written and
                  did not send the write-time receipt; the cursor stands here
    """
    kind: str
    seq: int | None = None
    label: str | None = None
    lo: int | None = None
    hi: int | None = None
    count: int | None = None

@dataclass(frozen=True)
class Label:
    """A claim about a hole: who may assert it, how it can be checked, over what window."""
    holder: str
    checkable: str          # 'reading' | 'holder-memory' | 'none'
    window: str
    needs_receipt: bool = False


# Every label declares three things: who may assert it, whether reading can check
# it, and the window in which it was true. `unclassified` is deliberately absent
# from the terminal set - a hole nobody has accounted for is not a licence.
LABELS = {
    "served-no-longer": Label(
        holder="any reader",
        checkable="reading",
        window="any time after the page that served it: re-check the stream (W-fact)",
        needs_receipt=False),
    "never-existed": Label(
        holder="the stream's owner, from memory",
        checkable="holder-memory",
        window=("always, and never with a receipt: nothing happened, so there is no "
                "response to show. A reading cannot tell it from a deletion"),
        needs_receipt=False),
    "deleted-by-me": Label(
        holder="the actor only",
        checkable="holder-memory",
        window=("once, in the response to the actor's own DELETE; a third reader can "
                "recover it only from a neighbour's before/after bracket"),
        needs_receipt=True),
    "unclassified": Label(
        holder="nobody yet",
        checkable="none",
        window="until someone looks",
        needs_receipt=False),
}
TERMINAL_LABELS = tuple(l for l, spec in LABELS.items()
                        if spec.checkable == "reading"
                        or (spec.checkable == "holder-memory" and (spec.needs_receipt
                            or l == "never-existed")))
WHO_CAN_CHECK = {l: spec.holder + " - " + spec.window.replace("\n", " ")
                 for l, spec in LABELS.items()}
HOLE_LABELS = tuple(LABELS)
REGIMES = ("dense", "holey")
MAX_HOLES = 4096        # per-integer tuples listed before a span summary
SCAN_CAP = 10 ** 6      # widest gap this module will walk position by position


class ForeignCursor(ValueError):
    """A cursor offered to a stream it did not come from."""


class GapTooWide(RuntimeError):
    """A gap wider than SCAN_CAP: not walked, reported as a span."""


@dataclass(frozen=True)
class Stream:
    """A stream's identity: a name for humans, a minted key for the machine.

    The name is not the identity. Two streams may share a name and the guard must
    still tell them apart, so the key is minted, never derived from the name.
    """
    name: str
    key: str = field(default_factory=lambda: secrets.token_hex(8))

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Cursor:
    """A position in one stream, together with the identity of that stream."""
    stream: Stream
    value: int


def open_stream(name: str, key: str | None = None) -> Stream:
    """Mint the identity of a stream. Call once per stream, not once per call.

    `key` is a test fixture, not a production path: a demonstration that prints a
    minted key prints a different key every run, so its own output cannot be
    compared with yesterday's and a behaviour change cannot be told from a fresh
    nonce. A demo passes fixed keys; production mints, because a key derived from
    the name would defeat the guard it exists for.
    """
    return Stream(name=name) if key is None else Stream(name=name, key=key)


def max_seen(items: list[dict]):
    """The largest delivered seq, or None for an empty page. Does not raise."""
    return max((i["seq"] for i in items), default=None)


def _holes(lo: int, hi: int, seen: set, cap: int = MAX_HOLES):
    """Non-delivered positions in [lo, hi]: up to `cap` of them, and the exact count.

    Returns (listed, count, first, last). Bounded on a page whose gap is huge.
    """
    listed, n, first, last = [], 0, None, None
    if hi < lo:
        return listed, 0, None, None
    if hi - lo + 1 > cap * 64:
        # too wide to walk: report the span and nothing else
        return [], hi - lo + 1, lo, hi
    for s in range(lo, hi + 1):
        if s in seen:
            continue
        n += 1
        first = s if first is None else first
        last = s
        if len(listed) < cap:
            listed.append(s)
    return listed, n, first, last


def _first_non_steppable(lo: int, hi: int, seen: set, steppable):
    """The first non-delivered position in [lo, hi] that may not be stepped over."""
    if hi < lo:
        return None
    if hi - lo + 1 > SCAN_CAP:
        raise GapTooWide(f"{hi - lo + 1} positions > SCAN_CAP {SCAN_CAP}")
    for s in range(lo, hi + 1):
        if s in seen:
            continue
        if not steppable(s):
            return s
    return None


def advance(items: list[dict], resume_from, *, regime: str, classify=None,
            stream: Stream | None = None, receipts: dict | None = None,
            asserted_by: str | None = None) -> tuple:
    """Where the cursor may move to, and what stood in its way.

    `resume_from` is a `Cursor` (a value plus its stream's identity) or a bare int
    (an unnamed cursor, which nothing can be checked against - the call then says
    so in its return value). `receipts` maps a seq to the write-time evidence that
    produced a holder-memory label; a `deleted-by-me` without one does not pass.
    Returns (cursor, marks); the cursor is a `Cursor` when a stream was named.
    `marks` holds, in order:

        ('hole', seq, label)    a position below the cursor, not delivered, passed
                                or held; the label says with what evidence
        ('span', lo, hi, n)     n > MAX_HOLES holes summarised instead of listed
        ('held', seq, label)    the cursor stands in front of this: no terminal label
        ('unproven', seq, label) the label is holder-memory and no receipt came with it
        ('beyond', seq)         delivered by this page, unreachable past a held gap
    """
    if regime not in REGIMES:
        raise ValueError(f"regime must be one of {REGIMES}, got {regime!r}")
    if isinstance(resume_from, Cursor):
        if stream is not None and resume_from.stream.key != stream.key:
            raise ForeignCursor(
                f"cursor from {resume_from.stream.name!r} (key {resume_from.stream.key}) "
                f"offered to {stream.name!r} (key {stream.key})")
        stream = stream or resume_from.stream
        at = resume_from.value
    else:
        at = int(resume_from)      # unnamed: there is no identity to check

    seen = {i["seq"] for i in items}
    delivered = sorted(seen)
    ahead = [s for s in delivered if s > at]
    receipts = receipts or {}
    def label(s: int) -> str:
        return (classify(s) if classify else None) or "unclassified"

    def account(s: int) -> tuple[str, str]:
        """What the cursor can say about a non-delivered position, and on what evidence.

        One place, so the label is asked for once and the same answer decides both
        whether the cursor may move and what the mark says. Asking twice is how a
        classifier that is not a function gets two different answers for one
        position.
        """
        lab = label(s)
        spec = LABELS.get(lab)
        if spec is None or spec.checkable == "none":
            return "held", lab
        if spec.checkable == "holder-memory":
            # the words come from a party that reading cannot check, so the call has
            # to say who is asserting them, and for a write-time fact what it wrote
            if not asserted_by:
                return "unproven", lab
            if spec.needs_receipt and not receipts.get(s):
                return "unproven", lab
        return "pass", lab

    def steppable(s: int) -> bool:
        # dense: a gap is a failure of the walk, never a licence to step over.
        return regime == "holey" and account(s)[0] == "pass"

    if not delivered:
        return (Cursor(stream, at) if stream else at), []

    marks: list = []
    frontier = at
    blocked_before = None
    if ahead:
        for s in ahead:
            try:
                bad = _first_non_steppable(frontier + 1, s - 1, seen, steppable)
            except GapTooWide:
                lo, hi = frontier + 1, s - 1
                marks.append(Mark("span", lo=lo, hi=hi, count=hi - lo + 1))
                blocked_before = s
                break
            if bad is not None:
                blocked_before = s
                break
            frontier = s

    listed, n, first, last = _holes(at + 1, frontier, seen)
    for s in listed:
        marks.append(Mark("hole", seq=s, label=label(s)))
    if n > len(listed):
        marks.append(Mark("span", lo=first, hi=last, count=n))

    if blocked_before is not None:
        held_lo, held_hi = frontier + 1, blocked_before - 1
        listed, n, first, last = _holes(held_lo, held_hi, seen)
        for s in listed:
            kind, lab = account(s)
            marks.append(Mark("held" if kind == "pass" else kind, seq=s, label=lab))
        if n > len(listed):
            marks.append(Mark("span", lo=first, hi=last, count=n))
        for s in delivered:
            if s > frontier:
                marks.append(Mark("beyond", seq=s))

    return (Cursor(stream, frontier) if stream else frontier), marks


def trace(pages: list[list[dict]], start, **kw) -> list:
    """One (cursor, marks) pair per page: the labels are not dropped.

    A caller that walks pages end to end is exactly the caller that has to act on
    the marks, so this entry point returns them instead of discarding them.
    """
    out, cursor = [], start
    for page in pages:
        cursor, marks = advance(page, cursor, **kw)
        out.append((cursor, marks))
    return out



def demo() -> None:
    def page(*seqs):
        return [{"seq": s} for s in seqs]

    def kinds(marks):
        return sorted({m.kind for m in marks})

    print("a delivered position is not a hole")
    assert advance(page(9, 10, 11), 9, regime="dense") == (11, [])
    out = advance(page(12, 13), 9, regime="dense")
    print(f"  page [12,13] at 9      -> cursor {out[0]}, {kinds(out[1])}")
    assert out[0] == 9 and [m for m in out[1] if m.kind == "held"] == [
        Mark("held", 10, "unclassified"), Mark("held", 11, "unclassified")]
    assert [m.seq for m in out[1] if m.kind == "beyond"] == [12, 13]

    print("dense on a projected page: the stream is dense, the page is a projection")
    projection = page(1, 2, 4, 6, 8, 10)
    t = trace([projection] * 3, 0, regime="dense")
    print(f"  three pages [1,2,4,6,8,10] at 0 -> cursor {t[0][0]}, held at "
          f"{[m.seq for m in t[0][1] if m.kind == 'held']}")
    assert t[0][0] == 2 and t[2][0] == 2, "no page is walked past its own gap"

    print("holey: the cursor passes a hole only when the hole carries a terminal label")
    out = advance(page(10, 12), 9, regime="holey")
    print(f"  no classifier          -> cursor {out[0]}, {out[1]}")
    assert out[0] == 10 and out[1] == [Mark("held", 11, "unclassified"), Mark("beyond", 12)]
    out = advance(page(10, 12), 9, regime="holey", classify=lambda s: "served-no-longer")
    print(f"  classifier: W-fact     -> cursor {out[0]}, {out[1]}")
    assert out[0] == 12 and out[1] == [Mark("hole", 11, "served-no-longer")]

    print("a label said in the right words is not a label held in the right evidence")
    for l, spec in LABELS.items():
        print(f"  {l:18s} holder={spec.holder:30s} checkable={spec.checkable:14s} "
              f"receipt={'required' if spec.needs_receipt else 'not needed'}")
    out = advance(page(10, 12), 9, regime="holey",
                  classify=lambda s: "deleted-by-me")
    print(f"  'deleted-by-me', nobody declared    -> cursor {out[0]}, {out[1]}")
    assert out[0] == 10 and out[1] == [Mark("unproven", 11, "deleted-by-me"),
                                       Mark("beyond", 12)]
    out = advance(page(10, 12), 9, regime="holey", classify=lambda s: "deleted-by-me",
                  asserted_by="me")
    print(f"  holder declared, no receipt         -> cursor {out[0]}, {out[1]}")
    assert out[0] == 10 and out[1][0].kind == "unproven"
    out = advance(page(10, 12), 9, regime="holey", classify=lambda s: "deleted-by-me",
                  asserted_by="me", receipts={11: ("DELETE", 200, 74)})
    print(f"  holder and write-time receipt       -> cursor {out[0]}, {out[1]}")
    assert out[0] == 12 and out[1] == [Mark("hole", 11, "deleted-by-me")]
    out = advance(page(10, 12), 9, regime="holey",
                  classify=lambda s: "served-no-longer")
    print(f"  'served-no-longer' needs only a reader -> cursor {out[0]}")
    assert out[0] == 12
    out = advance(page(10, 12), 9, regime="holey", classify=lambda s: "never-existed")
    print(f"  'never-existed', nobody declared    -> cursor {out[0]}, held on the owner's word")
    assert out[0] == 10 and out[1][0].kind == "unproven"
    out = advance(page(10, 12), 9, regime="holey",
                  classify=lambda s: "never-existed", asserted_by="the stream's owner")
    print(f"  the owner declares it               -> cursor {out[0]} (no receipt exists "
          f"for a non-event)")
    assert out[0] == 12

    print("why 5..19 may not be walked past: nobody fetched them")
    out = advance(page(4, 20), 3, regime="holey")
    print(f"  page [4,20] at 3       -> cursor {out[0]}, {len(out[1])} marks, "
          f"kinds {kinds(out[1])}, first {out[1][0]}")
    assert out[0] == 4 and out[1][0] == Mark("held", 5, "unclassified")

    print("a stream is an identity, not a name")
    # Fixed keys: this demo is a receipt, and a receipt that prints a fresh nonce
    # every run cannot be checked against yesterday's. Minting stays the default
    # above; here the two keys only have to be different from each other.
    a, b = open_stream("seq", key="00" * 8), open_stream("seq", key="11" * 8)
    for kw, note in (({"stream": b}, "two streams both named 'seq'"),
                     ({"stream": open_stream("inbox_seq", key="22" * 8)},
                       "a cursor from another stream")):
        try:
            advance(page(10, 11), Cursor(a, 9), regime="holey", **kw)
        except ForeignCursor as exc:
            print(f"  {note} -> {str(exc)[:64]}...")
        else:
            raise AssertionError(f"{note}: accepted")

    print("classification is never silently dropped")
    seen_by_classifier = []
    advance(page(10, 12), 9, regime="dense",
            classify=lambda s: (seen_by_classifier.append(s), "served-no-longer")[1])
    print(f"  dense labels its held positions with the caller's classify: {seen_by_classifier}")
    assert seen_by_classifier == [11], seen_by_classifier

    print("everything stays bounded")
    cursor, marks = advance(page(10 ** 9), 0, regime="holey")
    spans = [m for m in marks if m.kind == "span"]
    print(f"  page [1e9] at 0        -> cursor {cursor}, {len(marks)} marks, span {spans[0][1:]}")
    assert cursor == 0 and spans and spans[0].count == 10 ** 9 - 1

    print("empty page, stale page, cursor on a hole, max_seen([])")
    assert advance(page(), 9, regime="holey") == (9, [])
    assert advance(page(5, 6), 9, regime="holey") == (9, [])
    assert advance(page(10, 12), 11, regime="holey") == (12, [])
    assert max_seen([]) is None and max_seen(page(3, 7)) == 7
    print("  all four agree with the contract")

    print("trace keeps the labels: a caller walking pages must see them")
    t = trace([page(10, 12), page(13)], 9, regime="holey",
              classify=lambda s: "served-no-longer")
    print(f"  cursor per page {[c for c, _ in t]}, marks of page 1 {t[0][1]}")
    assert t[0][1] == [Mark("hole", 11, "served-no-longer")]
    print("all demonstrations hold")

if __name__ == "__main__":
    demo()
