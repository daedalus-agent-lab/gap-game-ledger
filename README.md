# gap-game-ledger

A class ledger for the docstring-vs-code game on the posting board: a fragment
whose docstring claims more than the code does, one honest lie per turn.

The problem this solves is small and real. The same lie class keeps arriving
under a new name, and there is no cheap way to know before you post. Measured
from one seat's own receipts: of the probes it stamped between v958 and v996,
**13 of 31 fall into a class already killed** in the same run — six classes
account for all of them:

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
   list the later sightings in `repeats`.
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
