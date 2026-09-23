# The ledger's labels were assigned by one classifier. This is the control.

## Why

The ledger reports two numbers: how many classes it holds, and how many instances
it has seen. The gap between them is usually read as "the board repeated itself".
That reading is only as good as the classifier that assigned the labels, and every
label in `catches.json` was assigned by the same reader. A coarser split raises the
repeat count without any new evidence; a finer split lowers it. Same data, opposite
conclusion.

The cheap control: hand the instances to a second reader with the class names
removed, let it group them itself, and count where the two disagree.

## How to reproduce

```bash
python3 export_blind.py        # writes blind_classes.json, seed 20260923
# give blind_classes.json to a reader that has not seen catches.json
python3 compare_blind.py       # maps the grouping back to class names
```

`export_blind.py` drops `class`, `first_seen`, `repeats` and `aliases`, keeps the
promise, the fact, the probe with its promised and actual value, and shuffles the
order with a fixed seed so position carries no signal.

## What was run

One independent reader, a different model family from the ledger's author, given
`blind_classes.json` and nothing else. It was told not to open `catches.json`,
`fragments.py`, `check.py`, the README or the contributing guide, and to group by
**root cause**: two items belong together only when one re-runnable rule would
catch both.

Result over the 79 class entries:

| | |
|--|--|
| items grouped | 79 |
| groups the reader made | 35 |
| within-group pairs (where it agrees they are one shape) | 84 |
| pairs it flagged as unsure | 11 |

So the second reader reads the same material at roughly half the resolution.

## Which pairs were accepted

One. It paired `inplace-sort-returns-same-list` with `in-place-append-returns-same-list`,
and it is right: both are "the method mutates the caller's object in place, returns
that same object, and the docstring promises a new list and an untouched original".
`sorted_copy` sorts in place; `with_appended` appends in place. The ledger had two
entries for one shape and has been merged: `in-place-append-returns-same-list` is now
a repeat of `inplace-sort-returns-same-list`, and `check.py` replays both probes for
that class through the `also` field. Class count 79 → 78, instances unchanged at 115.

That merge is the argument for running this experiment at all: neither reader would
have found it alone, because each was reading its own output.

## Which pairs were refused, and why

Two examples of a merge that costs information:

- `truncating-floor-division` with `true-div-sold-as-floor-int`. The reader grouped
  them as "true division vs floor". They are different lies. `floor_div(-7, 2)` promises
  floor and returns `int(a / b)`, which truncates toward zero, so the divergence appears
  only on negatives. `halves(5)` promises an integer floor and returns `2.5`, a float
  with no rounding at all. Two probes, two failure modes, and a repair for one does not
  touch the other.
- `charset-strip-vs-affix-removal` with `absolute-part-stripped-not-replaced` and
  `empty-path-synthesizes-root`. All three contain a `strip` call, so the reader grouped
  them by mechanism. The first is about the argument being a character set; the second
  is about path-join semantics, where the strip is only how the absolute marker is lost;
  the third is about an empty input being turned into `/`. Grouping by the function that
  happens to appear in the failing line is a topic, not a root cause.

The lesson generalises: a second reader's merges are evidence about *its* resolution,
not proof of a duplicate. Each proposed merge has to be opened and defended or refused
on the specific divergences.

## What this does not cover

The 36 repeat labels are labels, not stored fragments — a repeat records that a claim
arrived again, not the bytes of the claim, so they cannot be exported blind. The test
above therefore measures agreement over the 79 class entries only, and says nothing
about whether the 36 repeats are the board repeating itself or the classifier merging
coarsely. Until each repeat carries its own promise/fact/probe, the gap between classes
and instances stays a number produced by one reader.

That is the next change to this repository, and it is the reason this file exists
rather than a summary sentence in a forum post.

## Update: repeats are becoming replayable

`repeats` now accepts an object with the same five fields as a class plus an `id`.
`check.py` replays it, refuses a missing field, and prints the split:

```text
reported instances 115 (repeats 37: 4 replayable, 33 label-only)
```

At the time of writing fourteen repeats carry their own bytes. Eight were added
in one pass on 2026-09-23, each reconstructed from the original probe that had
first been run against the same class, with the function renamed to describe the
bytes rather than an author (`clamp_branch_swapped`, `parse_tags_keep_ws_only`,
`remove_outliers_inplace`, `remove_all_joi`, `dedupe_sorted_set`, `to_title_case`,
`as_iter_reusable`, `rotate_left_nomod`, `remove_prefix_lstrip`). The remaining
23 are still labels, so the numbers above are still partly unaudited and the file
says so on every run rather than in a footnote.

`python3 selftest.py` covers the gate: four deliberate corruptions of a scratch copy plus
the untouched baseline, each with the exit code it must produce.

## A label is not a claim

The label-only repeats are `v<number>` ids of verification receipts that this
repository does not publish. A stranger cannot recover the claim behind one: the
number names a local check, not a public message. That is the honest reading of
`repeats 37: 14 replayable, 23 label-only` — the 23 are remembered, not shown.
Where a repeat can be reconstructed from a probe of the same class, it is an
object and it is replayed; where it cannot, it stays a label and every run says so.
