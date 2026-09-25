# Audit of the byte column's guard — `probes/ladder_rungs.py`

Adversarial audit of one claim:

> every row's byte count is now published together with the one condition that can make it
> incomparable with another row's byte count, and a row taken under a condition the record does
> not carry would fail the run.

**Verdict: REFUTED in three independent places.** The guard is real and it does fire on a
content-coded answer, but (1) content coding is not the only condition that moves the count,
(2) the published `content_encoding` column is never read back — no run fails when a record
carries a wrong, empty or missing one, and (3) the control does not reach the run's guard, so a
tree that stops calling it stays green. The supporting measurement in `probes/wire_instrument.py`
reproduces here (4/4), and its wording is refuted for one transfer coding.

Everything below was run on loopback listeners started by the scripts under `.audit/`. No
existing file was modified; no network but `127.0.0.1`; nothing committed.

Baseline, re-run:

```
$ python3 probes/wire_instrument.py
ok  encoding size_download        29                                 the content-coded length
ok   transfer content-length       1024 reported  1024 B served
ok   transfer chunked              1024 reported  6149 B served
8/8 request lines as recorded ; 4/4 checks hold        (rc=0)
```

The probe's own two measured facts stand: chunked framing is folded in, gzip is not.

---

## Attack 1 — a condition OTHER than content coding moves `%{size_download}` with `content-encoding` empty

Script: `.audit/conditions.py` (drives the run's own `ladder_rungs.one()` and
`ladder_rungs.byte_column_refusal` against listeners written here).

```
$ python3 .audit/conditions.py
1 plain content-length status=200 size= 1024 ctype='application/json'     cenc=''       guard=PASSES
2 gzip + header (CRLF) status=200 size=   29 ctype='application/json'     cenc='gzip'   guard=FIRES
                       2 gzip + header (CRLF): answered with content-encoding 'gzip'; 29 B is a content-coded length ...
3 gzip, LF-only headers EXC ValueError: invalid literal for int() with base 10: ''
4 gzip, empty CE value status=200 size=   29 ctype='application/json'     cenc=''       guard=PASSES
5 truncated body (100/1024) status=200 size=  100 ctype='application/json'     cenc=''       guard=PASSES
6 lying content-length 0 status=200 size=    0 ctype='application/json'     cenc=''       guard=PASSES
7 206 partial + Range row status=200 size=  100 ctype='application/octet-stream' cenc=''       guard=PASSES
8 chunked full (6149 B) status=200 size= 1024 ctype='application/json'     cenc=''       guard=PASSES
9 chunked truncated    status=200 size=  500 ctype='application/json'     cenc=''       guard=PASSES
10 no length, close-framed status=200 size= 1024 ctype='application/json'     cenc=''       guard=PASSES
11 gzip in a trailer   status=200 size=    0 ctype='application/json'     cenc=''       guard=PASSES
```

Guard fired: only on rows 2 (and it is *not* fired on 4, 5, 6, 7, 9, 11).

Cross-check with raw curl on a second script, `.audit/wording.py`:

```
$ python3 .audit/wording.py
W1 TE:gzip (transfer coding)   status=200 size=29  cenc=''  body_bytes=29  curl_rc=0
W6 CL:4096, body 1024, closed  status=200 size=1024 cenc='' body_bytes=1024 curl_rc=18
```

Verdicts:
- **truncated / aborted transfer** — `size=100` for a 1024-byte entity, `content-encoding` empty,
  guard passes. The record has no field that says the body was cut short; a reader of the JSON
  sees `100` beside `1024` in the same column. **Hole.** (W6 is the same hole with a lying
  `content-length`: `curl` exits 18, the row records 1024 for a 4096-byte entity, guard passes.)
- **partial content / `Range`** — `size=100`, status 206, no encoding, guard passes. `status` is
  in `got` but the guard never looks at it and `got` is not a condition field. **Hole.**
- **lying `content-length: 0`** — `size=0`, guard passes. **Hole** (same family).
- **`Transfer-Encoding: gzip`** (W1) — `size=29` for the same 1024-byte entity, `content-encoding`
  empty, guard passes. **Hole, and a refutation of the wording** (see attack 4).
- `gzip` announced with an empty value (row 4) — curl does not decode, `size=29`, guard reads `''`
  and passes. Weak (an unnamed coding is a broken answer), noted, not counted.
- row 3 (LF-only header block) — not a silent pass but a crash: the head is split on `\r\n\r\n`,
  the split fails, the meta line is unparsable and `one()` raises `ValueError`, taking the whole
  run down. Fragility of the parser, not a hole in the guard.
- rows 8 and 10 confirm the probe: chunked framing and close-framing do not move the count.

## Attack 2 — is the guard reachable for every row, and does `--check` compare the published column?

Reading `probes/ladder_rungs.py:398-459`: the loop calls `one()` and then
`if cencoding: bad.append(byte_column_refusal(...))` for every cell of `CELLS`, before the row is
appended to `rows`. There is no path that records a row without that call, and the record schema
does carry the field for all cells:

```
$ python3 -c "import json; d=json.load(open('probes/ladder_rungs.json'))['cells']; print(len(d), sum('content_encoding' in c for c in d))"
59 59
```

What `--check` *reads back*, however, is only the record's `sent` (`ladder_rungs.py:401-402`,
`422-423`). The record's `content_encoding`, `content_type` and `got` are never read: the
"cells as recorded" mark compares the LIVE answer against the hard-coded `CELLS` constants
(`got == (status, size, digest)`, line 415-417).

Script: `.audit/harness2.py` (loads a copy of the probe, points `BASE` at a loopback listener,
runs the real `main()`).

```
$ python3 .audit/harness2.py
=== A. unmutated, --check, answer gzipped (guard live) ===            EXIT=1  MOVED <guard refusal>
=== B. unmutated, DEFAULT mode (no --check), answer gzipped ===       EXIT=0  MOVED <guard refusal>
        rec: {'cell': 'audit-row', 'got': [200, 29, 'e25ebcac0a0e0f55'], 'content_encoding': 'gzip', ...}
=== G. record pre-seeded content_encoding='', --check, gzip answer === EXIT=1  MOVED <guard refusal>
=== F1. RECORD says content_encoding='gzip', live answer plain, --check ===
        EXIT=0 | 1/1 cells as recorded
        rec: {'got': [200, 29, 'e25ebcac0a0e0f55'], 'content_encoding': 'gzip', ...}
=== F2. same, but record's content_encoding field DELETED ===         EXIT=0 | 1/1 cells as recorded
=== F3. same, but record's `sent` tampered ===                        EXIT=1  MOVED sent ... != ...
```

Verdicts:
- **B — the refusal does not stop the run by default.** Without `--check` the guard's refusal is
  printed and the offending row is written into the published table, exit 0. "would fail the run"
  is true only of the `--check` invocation (which the repro harness does use —
  `repro/run_all.sh:185` — so this is a caveat, not a silent failure), but any plain run
  regenerates `ladder_rungs.json` with the refused row in it.
- **F1/F2 — the published column is write-only.** A record that says `content_encoding: "gzip"`
  with a 29-byte count passes `--check` as "1/1 cells as recorded" against a live plain 1024-byte
  answer; deleting the field entirely still passes. Only `sent` tampering is caught (F3). This is
  the registry class the project already names: *a field written and never read is a sentence*.
  **Hole.**
- G shows the guard reads the live wire, not the record — correct behaviour, but it also means the
  guard can never detect a record whose column disagrees with what was measured.

## Attack 3 — the control

```
$ python3 .audit/harness2.py
=== D. control can fail: predicate stubbed to return None ===
control() EXIT = 1 | ['MOVED the guard refuses an encoded row', 'MOVED  the guard refuses an encoded row: no refusal']
```

So the control *can* fail — the first half of the ask is met: break
`byte_column_refusal` (make it return `None` always) and `control()` reports `1/4`, exit 1.

Disproving it: remove the guard *call* from `main()` and leave the predicate untouched
(`.audit/mut_no_guard.py`, the two guard lines replaced by `pass`):

```
=== C. guard call REMOVED from main, --check (control still green) ===
EXIT=0
   | 1/1 cells as recorded
   | ok  the client read the answer's content-encoding
   | ok  the byte column is the wire, not the object
   | ok  the guard refuses an encoded row
   | ok  the guard passes a plain row
   | 4/4 checks hold
```

The control calls `one()` and `byte_column_refusal` itself; it never calls the run's loop. A tree
whose `main()` has stopped consulting the guard answers 4/4 and exits 0 on a gzipped cell. Same
result for any mutation that keeps the predicate but drops or narrows its use
(`if cencoding and who == "edge"`, `byte_column_refusal(label, size, "")`). **Hole in the control's
reach**: it proves the predicate works, not that the run uses it.

## Attack 4 — is "the entity after transfer decoding and before content decoding" exactly right?

- `--compressed` on a gzip answer: `size=29`, 1024 body bytes delivered → the number is before
  content decoding. **Confirmed** (W3).
- chunked + gzip: `size=29` → **confirmed** (W5).
- **`Transfer-Encoding: gzip` (no content-encoding): `size=29` for a 1024-byte entity, and curl
  delivers the 29 coded bytes (`body_bytes=29`).** Transfer coding gzip is *not* folded in, so the
  number here sits **before** transfer decoding: the universal wording is wrong, and the sentence
  "`transfer-encoding` cannot move the number" (wire_instrument.py, docstring) is true of chunked
  only. **Refuted.**
- A truncated body: the number is what arrived, not the entity's length. **Refuted** for that case.
- The guard's own docstring (`byte_column_refusal`, ladder_rungs.py:196) still justifies itself
  with "a count of the WIRE … a 1024-byte object served gzipped is reported as 29" — the exact
  reading `wire_instrument.py` was written to refute ("the first answer given for it was wrong: it
  is NOT a count of the wire"). The predicate's stated reason contradicts its own measurement.
- Not tested: HTTP/2. The ladder asks `https://…` with no `--http2`, so curl speaks HTTP/1.1 and
  h2 framing is out of scope; no offline h2 server was available to me.

---

## Surviving holes

1. **The guard is blind to every non-content condition that moves the count.** A short or aborted
   read (100 of 1024, curl rc 18), a 206/`Range` partial, a lying `content-length`, and
   `Transfer-Encoding: gzip` all report a count with `content-encoding` empty and pass
   `byte_column_refusal`. The record carries no field for transfer completeness, range or transfer
   coding, so such a row is published as if comparable.
2. **The `content_encoding` column is never read back.** `--check` compares the live answer against
   the in-code `CELLS` constants and reads only `sent` from the record; a record with a wrong,
   empty or deleted `content_encoding` passes as "cells as recorded" (F1, F2). A field that is
   written and never read cannot make a row fail.
3. **The guard does not fail the run in the default invocation.** The refusal is printed and the
   offending row is written into `ladder_rungs.json`; exit 0 (B). Only `--check` exits 1.
4. **The control does not reach the run's guard.** With the guard call removed from `main()`, the
   control is 4/4 green and `--check` exits 0 on a content-coded cell (C).
5. **The wording overstates the measured point of the count.** "After transfer decoding" is false
   for `Transfer-Encoding: gzip`; "the entity" is false for a truncated transfer. The guard's own
   docstring still describes the count as "a count of the WIRE", the reading the probe refuted.

Claims that still rest on trust (not run here): the behaviour of the wall at
`https://getpostingboard.dev` itself — this audit touched loopback only, so what the real wall
answers, and whether any of its answers come back with a transfer coding, a range or a short read,
is unverified here.
