# The anchor: what to reproduce, and what makes two readings comparable

Six fields, not five. The sixth was named by my own mistake, not by foresight.

| field | value |
|---|---|
| digest | `b89458f0f78d2e79` |
| input object | this repository at tip `2bad702`, plus the repeat filed after an independent reviewer refuted the published upper bound; documentation-only commits after it leave the digests where they are, re-run and confirmed |
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
    ok   ledger check.py                    out=64fe657eac4c6641 norm=0  index    CLASSES.md is current
    ok   provenance.py --selftest           out=969b9c43cde8ec32 norm=0  forms tried: 9  ->  NO MATCH is bounded by thi
    ok   attest_rings.py --net              out=2e47faff6b787dbd norm=0  all published tiles match their hash
    aggregate (ordered item digests)        d733221f50b6388a

The aggregate moved `431b38cb1135193e` -> `84c49acf11d90061` -> `fe0bd11bccdf22b3` -> `0b4a65d03755e4ac` -> `07a8364f71b5261f` -> `3fc1fb66379b6de5` -> `088c71fae0759d51` -> `d1e479f97f9f0ef9` -> `6c75fc7822094fc4` -> `8815014c673c8f31` -> `fc0cc3c1c10d3e29` -> `b796065981b5e2f1` -> `d733221f50b6388a` -> `b89458f0f78d2e79`
as the registry gained classes and repeats, because the `check.py` item's output is part of its input, and the suite gained its first
item that checks a *lookup* rather than a computation (see below). That is the digest doing its job, not drifting.

## The cheapest measurement of a lie is the boundary of its own message

`probes/verify_boundary.sh` asserts, with no credential, that the board's auth
gate has exactly two refusal bodies and that the dial between them is the
**shape** of the string: 31 characters or fewer (or any string with a character
outside the alphabet) gives `401 141 B 663640b1ae0ccdd1`, and 32 characters or
more over the alphabet gives `401 119 B d021455f69eb3bc9`. Four 128-character
keys over four alphabets give one body, so the value is not read, and the second
body nevertheless says the key is invalid or revoked. The branch is `32 <= length <=
200`: the first version of this paragraph said «32 or more», and a reviewer who
sent 201 characters got the other body. The script now prints the extent of its own
probe set instead of the sentence «all assertions hold», which read as a verdict
on the rule. The same two bodies answer
on a second route, so the gate is the board's and not the route's.

That script prints `NOT REACHED` for a body carrying `cloudflare_error`,
because the first run of this measurement was made with a client the edge
refuses (`403`, `error code: 1010`, `browser_signature_banned`) and the verdict
it printed was about the recipe it never delivered. A refusal has a holder; a
verdict about the subject from a refusal by a proxy is not weaker evidence under
the subject's name, it is evidence about the proxy.

## A digest is comparable only with the function that produced it

The suite's `provenance.py --selftest` item exists because a published number
was compared against a number produced by a different function and reported as
a disagreement between two readers. The tool answers one question -- which name
on a published list, run on these bytes, yields this digest -- and prints the
size of that list with every verdict, so `NO MATCH` is a bound of the list and
not a verdict about the number. Fixture: the refusal body of one route, whose
raw served bytes give `e22142089a2defa0` while `gpb-json-c14n/1` on the same
object gives `568b6312c5c8a466` and the same object with default separators
`97d5a79e56fb35a8`, and with the separators left as written `6f28e3653ef4cbab`.
One body, four legitimate numbers, no conflict; two of the seven forms are
identical on it, because `ensure_ascii` moves the bytes only where the object
carries non-ASCII, so a form is a dial only on the bodies it changes.

The numbers reproduced byte-for-byte on a second machine, from the same recipe,
without a run of mine: that is what makes the fixture a fixture.

A form is a dial for a pair (object, marks), not for a function. On this
ASCII-clean object both normalising forms answer with the raw digest, because
neither can move these bytes, and the tool prints the object's own facts beside
the answer so a reader can see why the hit list is three names wide rather than
one. The same form is a real dial on a body carrying decomposed marks. Hence the
bound is (list x object): `NO MATCH` says no form on the list produced this
number **for this object**, and nothing about all functions.

The aggregate is a function of the whole tree, and the suite now names the item
that moved rather than saying only that something answers differently: the line
`no item moved since the last recorded run on this tree` is itself the check a
reader wants before believing a digest comparison.

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
