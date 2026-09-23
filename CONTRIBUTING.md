# Adding a class

A class is a *shape of lie*, not a fragment and not a credit.

## The cheapest contribution

Open an issue titled `class: <kebab-name>` with:

```text
promise : <the docstring's extra claim, quoted>
fact    : <one sentence about what the code does instead>
probe   : <one Python expression>
expected: <the promised value>
observed: <the actual value>
```

That is enough. Do not attach authorship. If the class is already in `catches.json`, say so in the issue and it goes in `repeats` instead of a new entry.

## Repeats carry their own bytes

A `repeats` entry is either a legacy **label** (a string: it records *that* a shape
arrived again, not what arrived) or an **object** with the same five fields as a
class plus an `id`:

```json
{
  "id": "v1083-round_half_up-ish",
  "promise": "rounded to the nearest integer",
  "fact": "int(x + 0.5) is not the nearest integer below zero",
  "fn": "round_int_plus_half",
  "probe": "round_int_plus_half(-1.6)",
  "expected": "-2",
  "observed": "-1"
}
```

An object repeat is replayed by `check.py` exactly like the class probe: the probe
must reproduce `observed` and `observed` must differ from `expected`, a missing
field is a miss, and a probe that raises is compared by the exception's class name.
`fn` names the fragment in the class namespace that the repeat
replays, the probe must actually call it, and that fragment must not fingerprint
like the fragment the class's own probe calls. The fingerprint is the function's
logic with every name it chose thrown away, so a second name for the class's own
bytes is refused: that is the class probe again, not a second sighting. The point
is that a stranger can audit the repeat count instead of taking it on trust —
`check.py` prints how many repeats it replays and how many are still label-only.

A repeat you can recover but that turns out indistinguishable from the class
fragment goes in `retired`, with the reason:

```json
"retired": [{"id": "rotate-left-any-k", "kind": "class-fragment",
             "why": "fingerprints identically to the class fragment rotate"}]
```

Retired repeats are not counted as instances; they say a claimed sighting was
checked and had nothing of its own in it. A retirement carries a `kind`:
`class-fragment` (the bytes were the class's own, under a second name) or
`not-a-fragment` (the receipt named a run of the ledger, not a shape at all).
`check.py` prints the two counts separately, because they mean different things —
one is a class sighting that was already counted, the other was never a sighting.

**Address the instance, or say you cannot.** A class or a repeat may carry `address`:
the public message id the fragment was posted in. `check.py` counts them and prints
`instances with a public address N/M (the rest are remembered, not shown)`, so the
gap between what a stranger can find and what only this seat remembers is on every
run. Add one whenever a fragment arrives with a public message behind it.

**A class is a shape, so it is checked as one.** Every class must hold a shape no
other class holds: `check.py` fingerprints the fragment each class's own probe calls
and prints `DUPE` with a non-zero exit if two class names cover one logic — or if a
repeat replays another class's logic. That is the `already-known class reported as new`
refusal made mechanical. Measured on the whole ledger: 76 of 76 executable classes
hold distinct logic.

A label is a question, not an instance. `v1083` and friends name verification receipts
that this repository does not publish, so a stranger cannot recover the promise behind
one. That is a reason to answer it locally, not to leave it standing: `recover_labels.py`
loads the labels whose source files are still on hand, replays each probe, and asks the
same fingerprint question `check.py` asks. Every label comes out as one of four things —
`OBJECT` (a second sighting with bytes of its own: it becomes a repeat), `CLASS` (the
class fragment again: it is retired with that reason), `MOVE` (the fragment is another
class's own bytes, so the label was filed under the wrong class) or `RUN` (the receipt
named a ledger run, not a fragment). `--write` applies the verdicts; provenance goes to
`label_recovery.json` in the repository so the mapping is public even though the receipts
are not. Measured 2026-09-23: 23 labels in, 10 objects, 13 retirements, 0 labels left.

Repeat fragments live in `fragments.py` under a `repeat fragments` heading, one
function per materialised repeat, and are registered in the namespace of the class
they repeat. Name them for the bytes, not for an author: a repeat is a second sighting
of a shape, and the ledger does not hand out credit.

`python3 selftest.py` proves the gate is live: it breaks copies of the ledger on
purpose and asserts `check.py` catches each mutation.

## The executable contribution

A pull request that:

1. Adds a **minimal reproduction** to `fragments.py` (not the author's original bytes) and registers it in `NAMESPACES` under the class name.
2. Adds the matching object to `catches.json`.
3. Leaves `python3 check.py` exiting 0.

An entry whose probe cannot be re-run belongs behind `"executable": false` with the reason, not left unverified. JavaScript is currently the only such case (`default-string-sort`).

## What will be refused

- A credit claim ("I found this first").
- A fragment whose class is already in the ledger, posted as if new.
- An entry whose `observed == expected` (that is not a divergence).
- An entry whose probe does not reproduce `observed` on this tree.

## Lookup before you post

```bash
python3 check.py --lookup "remaining elements from the longer sequence"
```

A miss means the class *may* be new. A hit means it is not.
