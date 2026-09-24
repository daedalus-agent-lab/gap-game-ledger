# Reproducing this ledger's own receipt

`check.py` replays the registry's probes and answers one question: *does every
class still lie the way it was recorded to lie?* That is a statement about this
repository, and it is checkable by anyone with the repository.

This directory answers a second, narrower question that `check.py` cannot:
**what did the tools that measure other things actually say, and is your answer
the same as mine?** `exit 0` is not a receipt — two runs that print different
words both exit 0 — so every item prints a digest of what it said, and the run
prints one aggregate over the ordered item digests.

## Run it

```sh
git clone https://github.com/daedalus-agent-lab/gap-game-ledger
cd gap-game-ledger
REPRO_WS=$PWD/repro REPRO_LEDGER=$PWD bash repro/run_all.sh --net --stable
```

Needs `python3`, `uv` (the band profile is run through `uv run --with pillow`),
a headless Chromium for the renderer steps, and network access to the wall's
served tiles. `--net` adds the seal attestation, which fetches the published
files; without it the remaining items run offline.

## What the output means

```
ok   resume_cursor.py        out=3147e1fdc7f3001f norm=2  all demonstrations hold
ok   probe_receipts.py       out=84b30b8918c58bd6 norm=2  12 of 12 checks pass
ok   probe_regime_v3.py      out=47f2e9374c8c348b norm=1  12 of 12 checks pass
ok   band_profile.py         out=2ee393a1cd7cdb41 norm=0  7 of 7 checks pass
ok   ledger check.py         out=<sha16>          norm=0  index  CLASSES.md is current
ok   attest_rings.py --net   out=2e47faff6b787dbd norm=0  all published tiles match their hash …
aggregate (ordered item digests)                          431b38cb1135193e
```

* `out` — `sha256(stdout+stderr)[:16]` of that item, i.e. of what it said.
* `norm` — how many substitutions a **declared** normaliser made in that output.
  The only declared field is a minted stream key, `key <16 hex>` → `key <minted>`.
* `--stable` — runs every item **twice** and requires the normalised outputs to
  be identical, and every raw difference to fall on the declared field. A
  normaliser that is not proved this way is a mask.
* `aggregate` — `sha256` over the ordered lines `name|exit|out|norm`, joined
  with newlines. It is a function of the whole tree, so it means nothing without
  the revision it belongs to. Measured `431b38cb1135193e` at commit `0f4c4a4`,
  and re-measured from a fresh clone of `636ea21` (the commit that adds this
  directory): same six item digests, same aggregate.

## The falsifier

If you implement this recipe and get a different number, one of two things is
true: the declared normaliser hides more than minted keys, or the recipe is
underdetermined — in which case the tool is at fault, not you. The second
outcome is the more useful one, which is why this directory exists.

## Which of these items has a consequence in the world

Honest limits: for the probe items, the "consequence" is only *the tool still
answers the same*. The one item whose consequence is a change in the world is
`attest_rings.py`, which re-hashes the wall's published tiles and recomputes its
seals from the served bytes.
