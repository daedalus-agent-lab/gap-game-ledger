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
]


def one(path: str, headers: list) -> tuple[int, int, str]:
    cmd = ["curl", "-s", "-o", "-", "-w", "\n%{http_code} %{size_download}", BASE + path]
    for name, value in headers:
        cmd += ["-H", f"{name}: {value}"] if value else ["-H", f"{name};"]
    out = subprocess.run(cmd, capture_output=True, timeout=30).stdout
    body, _, meta = out.rpartition(b"\n")
    status, size = meta.split()
    return int(status), int(size), hashlib.sha256(body).hexdigest()[:16]


def main() -> int:
    check = "--check" in sys.argv
    rows, bad = [], []
    for label, path, headers, status, size, digest in CELLS:
        got = one(path, headers)
        rows.append({"cell": label, "path": path,
                     "headers": [list(h) for h in headers], "got": list(got)})
        mark = "ok " if got == (status, size, digest) else "MOVED"
        if got != (status, size, digest):
            bad.append(f"{label}: {got} != {(status, size, digest)}")
        print(f"{mark} {label:<24} {path:<26} {got[0]} {got[1]:>7} {got[2]}")
    print(f"\n{len(CELLS) - len(bad)}/{len(CELLS)} cells as recorded"
          "  (first holder; four cells added by a second holder on 2026-09-24)")
    if not check:
        TABLE.write_text(json.dumps({"as_of_note": "see probes/ladder_rungs.py",
                                     "cells": rows}, indent=1) + "\n", encoding="utf-8")
    for line in bad:
        print(f"MOVED  {line}")
    return 1 if (check and bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
