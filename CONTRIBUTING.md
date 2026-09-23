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
  "id": "v1083-round_half_up",
  "promise": "rounds .5 cases up, away from zero for positives",
  "fact": "Python's round() ties to even",
  "probe": "round_half_up(2.5)",
  "expected": "3",
  "observed": "2"
}
```

An object repeat is replayed by `check.py` exactly like the class probe: the probe
must reproduce `observed` and `observed` must differ from `expected`, and a missing
field is a miss. The point is that a stranger can then audit the repeat count instead
of taking it on trust — `check.py` prints how many repeats are replayable and how many
are still label-only. Replacing one label with an object is a complete contribution.

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
