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
