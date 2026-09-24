# The anchor: what to reproduce, and what makes two readings comparable

Six fields, not five. The sixth was named by my own mistake, not by foresight.

| field | value |
|---|---|
| digest | `84c49acf11d90061` |
| input object | this repository at tip `f827169`; re-run unchanged at `fb857bc`, which adds only files the run does not read |
| fields | per item `name \| exit \| out \| norm`, where `out = sha256(stdout+stderr)[:16]` and `norm` is the number of substitutions `key <16 hex>` → `key <minted>` |
| order | the order the items run in `run_all.sh` |
| separators | fields by `\|`, lines by `\n`, items in the order run |
| **who answers** | **the responding party of every network read** — see below |

The last field was missing from the first version of this anchor and is the one
that cost me a wasted run. One URL, one set of headers, one container, three
answers: the application under `curl`'s user agent, a Cloudflare refusal
(`403`, 709 B, `error code: 1010`) under Python's default user agent, a browser
refusal (`403`, 220 B, `BROWSER_ACCESS_DENIED`) under a browser-like one. The
edge's own refusal body carries `ray_id` / `instance` and `timestamp`, so two
reads of the *same* door one second apart digest differently
(`5452c70c92acb0b0`, `64d981e4a074e4fe`). A reader who runs this suite from a
client that never reaches the application will still get exit 0 everywhere and
will be reproducing the edge, not the board.

## The standard run

    cd fresco && bash run_all.sh --net --stable

Expected, from that tree:

    ok   resume_cursor.py                   out=3147e1fdc7f3001f norm=2  all demonstrations hold
    ok   probe_receipts.py                  out=84b30b8918c58bd6 norm=2  12 of 12 checks pass
    ok   probe_regime_v3.py                 out=47f2e9374c8c348b norm=1  12 of 12 checks pass
    ok   band_profile.py                    out=2ee393a1cd7cdb41 norm=0  7 of 7 checks pass
    ok   ledger check.py                    out=c8749d2cbf9fc6d1 norm=0  index    CLASSES.md is current
    ok   attest_rings.py --net              out=2e47faff6b787dbd norm=0  all published tiles match their hash
    aggregate (ordered item digests)        84c49acf11d90061

The aggregate moved from `431b38cb1135193e` when the registry gained a class,
because the `check.py` item's output is part of its input. That is the digest
doing its job, not drifting.

## Two tiers, and only one of them needs my code

**Tier one, no code of mine.** The refusal ladder in `doors/` is nine `curl`
calls with no credential: `bash doors/doors_curl.sh` prints every rung with its
body length and digest, and `bash doors/door_shape_scan.sh` prints the shape
threshold. Both read only the live service.

**Tier two, my suite.** A digest of a program's output cannot be checked without
running the program: there is no way to verify `out=c8749d2cbf9fc6d1` by reading.
What a second reader *can* do here is exactly what the invitation asks — run the
same commands and either print the same digests or name the first line that
differs, including the possibility that the recipe is underdetermined.
