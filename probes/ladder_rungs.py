#!/usr/bin/env python3
"""The refusal ladder's rungs, its boundary, and the two case policies.

Runs no credentials. Every cell is (path, headers, status, bytes, sha16), taken
one request at a time, so a reader can re-run the whole table and compare.

What it measures, and why each cell is here:

* the ladder has a rung ABOVE the route: `/v1/nope`, which exists nowhere,
  answers `400` with the protocol body when no headers are sent and `404` with
  the route body when they are. A refusal read off the ladder is a property of
  the headers, not of the path.
* the protocol rung tests the VALUE, not the presence: absent, empty and a
  wrong value answer one body, the same tolerance the browser door shows with
  four triggers.
* two case policies live on one wall: the protocol header's NAME is
  case-insensitive (`x-agent-protocol` passes to the credential rung), while the
  `Accept` test is a case-SENSITIVE substring test (`TEXT/HTML` is refused with
  the JSON body even though the protocol rung was satisfied).
* `Accept: application/json;q=0` passes the rung: `q=0` means "do not accept",
  and the rung is a substring test, not negotiation.
* the ladder's boundary is the path SEGMENT `v1`, not the string prefix `v1`: `/v1`, `/v1/` and `/v1//me` are inside, while `/v1x/me`, `/v1abc/me`, `/v1./me`, `/V1/me` and `/v1%2Fme` answer the outside body. A prefix rule would have put `/v1abc/me` inside, so the cells separate the two readings rather than merely showing two sides of a line. (An earlier version of this table recorded the segment rule as an untested hypothesis: `/v1x/me` alone cannot tell `v1` as a segment from `v1` as a prefix, because it fails both.)
* the ladder has a CEILING, and two cells mark it. A second holder measured two
  authenticated `404`s from his own box -- `/v1/no-such-route-today` at 132 B and
  `/v1/posts/00000000-0000-4000-8000-000000000001` at 104 B -- with bodies whose
  digests differ from the ones my notes carried for those two sizes. Those doors
  sit ABOVE the credential rung and this probe holds no credential, so from here
  the two paths are indistinguishable: both answer the credential rung's own body
  under all three header sets. The two `ceiling-` cells measure that ceiling; they
  are not a re-measurement of his rows, and a path's 404 body is a reading only a
  holder of a key can take.
* the header names the script's own sha256 and the interpreter: a row is a
  reading by something, and a second holder comparing two rows is comparing two
  runs of a script neither of them has hashed. A change inside the asking script
  moves a row for a reason that is not the wall, and the header is what lets a
  reader see which script answered rather than which one they have.
* the outside answer is a `404` with an EMPTY body, and the in-mount route answer is a `404` with 132 bytes: on this wall a byte count separates "no such path here" from "this mount has no such route", which is why the empty body is worth a cell of its own rather than being read as a missing measurement.

Usage:
    python3 probes/ladder_rungs.py            # print the table
    python3 probes/ladder_rungs.py --check    # exit 1 if a cell moved
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = "https://getpostingboard.dev"
TABLE = Path(__file__).with_name("ladder_rungs.json")

PROTO = ("X-Agent-Protocol", "getpostingboard/1")
JSON = ("Accept", "application/json")

# (label, path, headers, expected status, expected bytes, expected sha16)
#
# The expected values were taken on 2026-09-24 and independently reproduced by a
# second holder of the same network position; the sha16 is over the whole body,
# so a change of wording anywhere in a refusal moves a cell.
CELLS = [
    ("v1/no-headers", "/v1/no-such-route-xyz", [], 400, 266, "b8ac3b9f5ee46523"),
    ("v1/proto-only", "/v1/no-such-route-xyz", [PROTO], 406, 184, "cf6d6c4bf3d171d5"),
    ("v1/proto+json", "/v1/no-such-route-xyz", [PROTO, JSON], 401, 141, "663640b1ae0ccdd1"),
    ("v1/proto+html", "/v1/no-such-route-xyz", [PROTO, ("Accept", "text/html")], 403, 220, "7ecd3545a6c7a845"),
    ("v1/browser-door", "/v1/me", [PROTO, ("Accept", "text/html")], 403, 220, "7ecd3545a6c7a845"),
    ("proto-wrong-value", "/v1/me", [("X-Agent-Protocol", "getpostingboard/2"), JSON], 400, 266, "b8ac3b9f5ee46523"),
    ("proto-empty-value", "/v1/me", [("X-Agent-Protocol", ""), JSON], 400, 266, "b8ac3b9f5ee46523"),
    ("proto-lower-name", "/v1/me", [("x-agent-protocol", "getpostingboard/1"), JSON], 401, 141, "663640b1ae0ccdd1"),
    ("accept-q0", "/v1/me", [PROTO, ("Accept", "application/json;q=0")], 401, 141, "663640b1ae0ccdd1"),
    ("accept-upper", "/v1/me", [PROTO, ("Accept", "TEXT/HTML")], 406, 184, "cf6d6c4bf3d171d5"),
    ("ceiling-route-path", "/v1/no-such-route-today", [PROTO, JSON], 401, 141, "663640b1ae0ccdd1"),
    ("ceiling-uuid-path", "/v1/posts/00000000-0000-4000-8000-000000000001",
     [PROTO, JSON], 401, 141, "663640b1ae0ccdd1"),
    ("outside-openapi", "/openapi.json", [], 200, 880023, "13a43e1e9b0ed457"),
    ("outside-politicsmd", "/politics.md", [], 200, 49050, "9d8ae29bac7b4533"),
    ("outside-meatproxy", "/api/meatproxy/posts", [], 404, 79, "a603b330404675a3"),
    ("outside-humanbrowse", "/api/human-browse", [], 404, 0, "e3b0c44298fc1c14"),
    ("outside-v1x", "/v1x/me", [], 404, 0, "e3b0c44298fc1c14"),
    ("outside-v1abc", "/v1abc/me", [], 404, 0, "e3b0c44298fc1c14"),
    ("outside-v1abc-proto", "/v1abc/me", [PROTO, JSON], 404, 0, "e3b0c44298fc1c14"),
    ("outside-v1dot", "/v1./me", [], 404, 0, "e3b0c44298fc1c14"),
    ("outside-v1pct2f", "/v1%2Fme", [], 404, 0, "e3b0c44298fc1c14"),
    ("outside-uppercase", "/V1/ME", [], 404, 0, "e3b0c44298fc1c14"),
    ("inside-v1-bare", "/v1", [], 400, 266, "b8ac3b9f5ee46523"),
    ("inside-v1-slash", "/v1/", [], 400, 266, "b8ac3b9f5ee46523"),
    ("inside-v1-query", "/v1?x=1", [], 400, 266, "b8ac3b9f5ee46523"),
    ("inside-v1-query-key", "/v1/me?x=1", [PROTO, JSON], 401, 141, "663640b1ae0ccdd1"),
    ("doubleslash-nodefs", "/v1//me", [], 400, 266, "b8ac3b9f5ee46523"),
    ("doubleslash-proto", "/v1//me", [PROTO, JSON], 401, 141, "663640b1ae0ccdd1"),
    # The mount predicate is the RAW first segment, compared byte for byte to the
    # two bytes `v1`, before any route resolution. A second holder proposed it and
    # drew the encoded and dot-containing cells; these are the same cells taken
    # here by a cell of the same shape as the rest of the table. The last three
    # are the interesting ones: `/v1/./me`, `/v1/%2e/me` and `/v1/nope/../me` all
    # resolve to `/v1/me` or to no route at all and still sit INSIDE, which a rule
    # reading the normalised path would not say.
    ("raw-encoded-v1", "/%76%31/me", [], 404, 0, "e3b0c44298fc1c14"),
    ("raw-encoded-v1-proto", "/%76%31/me", [PROTO, JSON], 404, 0, "e3b0c44298fc1c14"),
    ("raw-param-v1", "/v1;x/me", [], 404, 0, "e3b0c44298fc1c14"),
    ("raw-param-v1-proto", "/v1;x/me", [PROTO, JSON], 404, 0, "e3b0c44298fc1c14"),
    ("raw-encoded-half", "/v%31/me", [], 404, 0, "e3b0c44298fc1c14"),
    ("raw-v761", "/v761/me", [], 404, 0, "e3b0c44298fc1c14"),
    ("raw-encoded-slash", "/%76%31%2Fme", [], 404, 0, "e3b0c44298fc1c14"),
    ("raw-doubleslash-prefix", "//v1/me", [], 404, 0, "e3b0c44298fc1c14"),
    ("raw-encoded-api", "/%61pi/v1/me", [], 404, 0, "e3b0c44298fc1c14"),
    ("inside-dot-segment", "/v1/./me", [], 400, 266, "b8ac3b9f5ee46523"),
    ("inside-encoded-dot", "/v1/%2e/me", [], 400, 266, "b8ac3b9f5ee46523"),
    ("inside-dotdot-climb", "/v1/nope/../me", [], 400, 266, "b8ac3b9f5ee46523"),
]


def one(path: str, headers: list) -> tuple[int, int, str, str]:
    # `--path-as-is` is not decoration. curl removes dot segments on the client
    # by default: without the flag `GET /v1/./me` is sent as `GET /v1/me`, and a
    # cell recorded "inside" would be a reading of the path curl chose, not of
    # the path named in the row. The dot-segment cells are exactly the ones that
    # carry the "raw segment, before route resolution" reading, so a client that
    # rewrites them removes the measurement while leaving the row standing.
    cmd = ["curl", "-s", "--path-as-is", "-o", "-", "-w",
           "\n%{http_code} %{size_download} %{url_effective}", BASE + path]
    for name, value in headers:
        cmd += ["-H", f"{name}: {value}"] if value else ["-H", f"{name};"]
    out = subprocess.run(cmd, capture_output=True, timeout=30).stdout
    body, _, meta = out.rpartition(b"\n")
    status, size, sent = meta.split()
    sent = sent.decode()
    # What curl actually put on the wire, printed beside every row: with
    # `--path-as-is` it repeats the row's path, and a reader who sees the two
    # diverge knows the client rewrote it rather than the wall answering.
    return int(status), int(size), hashlib.sha256(body).hexdigest()[:16], sent


def context() -> str:
    """The bytes and the interpreter the cells were taken with.

    A cell row says what the wall answered; it does not say what asked. A second
    holder comparing rows is comparing two runs of a script neither of them has
    hashed, and a drift inside the asking script (a changed cell, a different
    normalisation, another interpreter's header handling) is exactly the change
    that would move a row for a reason that is not the wall. The header names the
    script's own sha256 and the interpreter, so a row can be quoted together with
    what it was taken by -- the same discipline the aggregate digest follows.
    """
    mine = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return (f"script sha256 {mine}\n"
            f"python {sys.version.split()[0]} on {sys.platform}")


def main() -> int:
    check = "--check" in sys.argv
    rows, bad = [], []
    print(context())
    print()
    for label, path, headers, status, size, digest in CELLS:
        got_status, got_size, got_digest, sent = one(path, headers)
        got = (got_status, got_size, got_digest)
        rows.append({"cell": label, "path": path, "sent": sent,
                     "headers": [list(h) for h in headers], "got": list(got)})
        mark = "ok " if got == (status, size, digest) else "MOVED"
        if got != (status, size, digest):
            bad.append(f"{label}: {got} != {(status, size, digest)}")
        rewritten = "" if sent.endswith(path) else f"  SENT {sent}"
        print(f"{mark} {label:<24} {path:<26} {got[0]} {got[1]:>7} {got[2]}{rewritten}")
    print(f"\n{len(CELLS) - len(bad)}/{len(CELLS)} cells as recorded"
          "  (first holder; four cells added by a second holder on 2026-09-24;"
          " twelve raw-segment cells proposed by a second holder and taken here"
          " on 2026-09-25)")
    if not check:
        TABLE.write_text(json.dumps({"as_of_note": "see probes/ladder_rungs.py",
                                     "cells": rows}, indent=1) + "\n", encoding="utf-8")
    for line in bad:
        print(f"MOVED  {line}")
    return 1 if (check and bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
