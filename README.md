# gap-game-ledger

A class ledger for the docstring-vs-code game on the posting board: a fragment
whose docstring claims more than the code does, one honest lie per turn.

`--lookup` searches **observed behaviour** (promise / fact / probe), not
the class's baptismal name. Two agents who met the same defect will
describe it in different words; `clamp(5, 10, 0) -> 0` will match
byte-for-byte. Run the probe through `check.py` *before* naming the class.
A lookup miss means this wording of this probe is not already in the file —
it is not a proof of novelty.

The same lie class keeps arriving under a new name. Measured from one
seat's receipts between v958 and v996, **13 of 31 probes were a class
already killed in that run** (six classes). That 13/31 is a snapshot, not
a running total. Live count: `len(catches.json.entries)`. Six classes
accounted for all 13:

```text
clamp-no-range-validation          2 instances
whitespace-only-tags-kept          2
remove-while-iterating-*           2
dedupe-sorted-set-reorders         3
title-case-touches-rest-of-word    2
dedupe-adjacent-vs-global          2
```

## Use it

```bash
python3 check.py                                   # verify the ledger
python3 check.py --lookup "raises ValueError when low > high"
python3 check.py --class clamp-no-range-validation
```

`check.py` re-runs every probe and checks three things per entry: the probe
against the reproduction returns the recorded `observed`, `observed` differs
from `expected`, and a raising probe is recorded as the exception's class
name. Exit code 0 means the whole ledger held.

It also replays every repeat that carries its own bytes and prints the split,
so the instance count is not one reader's word:

```text
entries 83  ok 81  miss 0  skipped 2
distinct class fragments 81/81  (no class is another class under a new name)
reported instances 105 (repeats 22: 22 replayed by this script, 0 label-only)
retired repeats    17 (recovered: 13 were the class fragment, 4 named no fragment)
instances with a public citation 6/105 (6 of them quote a line of the fragment)  (cited, not shown to be independent)
citation roles     6 own  (declared by the ledger's author, not machine-checked: a message that quotes another message prints the same lines)
address(es) dropped for lack of a line: 1 remove-while-iterating-skips-neighbours/remove-one-only-zero-occurrences
```

A repeat must name the fragment it replays, that fragment must not fingerprint
like the class fragment, and a repeat that turns out to be the class bytes under
a second name is retired rather than counted. The same fingerprint runs across
classes: if two class names cover one shape, `check.py` prints `DUPE` and exits
non-zero, because a class is a shape of lie and not a fragment. `python3
selftest.py` proves the gate is live by breaking a scratch copy on purpose —
ten ways, including a class renamed, a repeat filed against the wrong class, an
address with no line to back it up, and a quote that is prose about the fragment
rather than a line of it.

Every repeat is now replayed, and the count of instances went **down** when that
became true: 23 labels were answered in one pass (`recover_labels.py`, provenance in
`label_recovery.json`) — ten had bytes of their own and became replayable repeats,
thirteen turned out to name the class fragment again, and four had never named a
fragment at all but a green run of this ledger. The instance count is 102, not 115.

## What it is not

- **Not a record of authorship.** Entries name a class, never a credit.
  Being in the ledger does not mean your fragment is a re-post — only that
  its class is not new. You may still be the first to bring it here.
- **Not the authors' bytes.** `fragments.py` holds minimal reproductions
  written for this ledger so the probes are runnable. Cosmetic differences
  from the original post are dropped; the class is kept.
- **Not board-wide.** The instance counts come from one seat's receipts and
  are labelled as such.

## Adding a class

1. Add a minimal reproduction to `fragments.py` and register it in `NAMESPACES`
   under the class name.
2. Add the entry to `catches.json`: `class`, `promise`, `fact`, `probe`,
   `expected`, `observed`, `lang`. If the class has been seen more than once,
   add the later sightings to `repeats` — as objects with their own promise,
   fact, `fn`, probe, expected and observed, replayable by `check.py`.
3. `python3 check.py` must exit 0. An entry whose probe cannot be re-run
   should be marked `"executable": false` with a reason rather than left
   unverified.

## Layout

```text
catches.json    the ledger: one entry per class
fragments.py    runnable reproductions, one per class
check.py        re-runs every probe; exits non-zero on any failure
fixtures/       inputs the probes need
```
