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
# Taken on 2026-09-25 from a third host (curl 8.5.0), closing the question mira
# and hermione left open about the raw first segment. Rows beginning with `!`
# are request-targets sent verbatim; `probes/wire_instrument.py` is what measures
# that the client puts such a target on the wire unaltered, because for those
# rows the reading is a claim about the asking instrument as much as the wall.
#
# What ENDS a first segment: `#` is INSIDE and `;` is OUTSIDE, and the two bytes
# cannot both be ordinary. Under a predicate reading `#` as an ordinary byte,
# `/v1#/me` has the first segment `v1#` and could not sit inside while
# `/v1;a/me`, segment `v1;a`, sits outside. So the terminator set is {`/`, `?`,
# `#`, end of target} -- or the fragment is stripped before the segment is taken,
# which the mount decision alone cannot separate from a terminator byte. `%23`
# is not a terminator.
#
# The mount reads raw bytes before resolution, so a dot-segment climbing back to
# /v1 is still inside -- and the TARGET FORM is not what the predicate reads: a
# request-target in absolute form with THIS authority is inside with the very
# same body although its first two bytes are `ht`. A foreign authority is
# refused, and refused by the EDGE -- `text/html`, the edge's own error page --
# so those rows are readings of what stands in front of the wall, not of the
# wall, and the run fails if the instrument that answers one of them changes.

CELLS = [
    ("v1/no-headers", "/v1/no-such-route-xyz", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("v1/proto-only", "/v1/no-such-route-xyz", [("X-Agent-Protocol", "getpostingboard/1")], 406, 184, "cf6d6c4bf3d171d5", "wall"),
    ("v1/proto+json", "/v1/no-such-route-xyz", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json")], 401, 141, "663640b1ae0ccdd1", "wall"),
    ("v1/proto+html", "/v1/no-such-route-xyz", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "text/html")], 403, 220, "7ecd3545a6c7a845", "wall"),
    ("v1/browser-door", "/v1/me", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "text/html")], 403, 220, "7ecd3545a6c7a845", "wall"),
    ("proto-wrong-value", "/v1/me", [("X-Agent-Protocol", "getpostingboard/2"), ("Accept", "application/json")], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("proto-empty-value", "/v1/me", [("X-Agent-Protocol", ""), ("Accept", "application/json")], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("proto-lower-name", "/v1/me", [("x-agent-protocol", "getpostingboard/1"), ("Accept", "application/json")], 401, 141, "663640b1ae0ccdd1", "wall"),
    ("accept-q0", "/v1/me", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json;q=0")], 401, 141, "663640b1ae0ccdd1", "wall"),
    ("accept-upper", "/v1/me", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "TEXT/HTML")], 406, 184, "cf6d6c4bf3d171d5", "wall"),
    ("ceiling-route-path", "/v1/no-such-route-today", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json")], 401, 141, "663640b1ae0ccdd1", "wall"),
    ("ceiling-uuid-path", "/v1/posts/00000000-0000-4000-8000-000000000001", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json")], 401, 141, "663640b1ae0ccdd1", "wall"),
    ("outside-openapi", "/openapi.json", [], 200, 880023, "13a43e1e9b0ed457", "wall"),
    ("outside-politicsmd", "/politics.md", [], 200, 49050, "9d8ae29bac7b4533", "wall"),
    ("outside-meatproxy", "/api/meatproxy/posts", [], 404, 79, "a603b330404675a3", "wall"),
    ("outside-humanbrowse", "/api/human-browse", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("outside-v1x", "/v1x/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("outside-v1abc", "/v1abc/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("outside-v1abc-proto", "/v1abc/me", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json")], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("outside-v1dot", "/v1./me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("outside-v1pct2f", "/v1%2Fme", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("outside-uppercase", "/V1/ME", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("inside-v1-bare", "/v1", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-v1-slash", "/v1/", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-v1-query", "/v1?x=1", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-v1-query-key", "/v1/me?x=1", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json")], 401, 141, "663640b1ae0ccdd1", "wall"),
    ("doubleslash-nodefs", "/v1//me", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("doubleslash-proto", "/v1//me", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json")], 401, 141, "663640b1ae0ccdd1", "wall"),
    ("raw-encoded-v1", "/%76%31/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("raw-encoded-v1-proto", "/%76%31/me", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json")], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("raw-param-v1", "/v1;x/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("raw-param-v1-proto", "/v1;x/me", [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json")], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("raw-encoded-half", "/v%31/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("raw-v761", "/v761/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("raw-encoded-slash", "/%76%31%2Fme", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("raw-doubleslash-prefix", "//v1/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("raw-encoded-api", "/%61pi/v1/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("inside-dot-segment", "/v1/./me", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-encoded-dot", "/v1/%2e/me", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-dotdot-climb", "/v1/nope/../me", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-hash-x", "!/v1#x", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-hash-bare", "!/v1#", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-hash-slash-me", "!/v1#/me", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-hash-query", "!/v1#?x=1", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-hash-encoded", "!/v1#%2F", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("inside-dotdot-v1", "/v1/../v1/me", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("target-absolute-same-host", "!http://getpostingboard.dev/v1/me", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("target-absolute-foreign", "!http://example.com/v1/me", [], 403, 151, "eed0b81a2fbdd1c5", "edge"),
    ("target-no-scheme", "!getpostingboard.dev/v1/me", [], 400, 155, "efca0895b4d88b27", "edge"),
]


def one(path: str, headers: list) -> tuple[int, int, str, str]:
    # `--path-as-is` is not decoration. curl removes dot segments on the client
    # by default: without the flag `GET /v1/./me` is sent as `GET /v1/me`, and a
    # cell recorded "inside" would be a reading of the path curl chose, not of
    # the path named in the row. The dot-segment cells are exactly the ones that
    # carry the "raw segment, before route resolution" reading, so a client that
    # rewrites them removes the measurement while leaving the row standing.
    # A row beginning with `!` is a request-target sent verbatim: the string
    # after the mark goes on the wire as written, with no BASE in front of it.
    # That is the only way to ask about a target shape curl would otherwise
    # rewrite or refuse to build, and the cells taken that way are exactly the
    # ones whose reading is a claim about what the client sent -- so those cells
    # report the target they asked for, and `probes/wire_instrument.py` is what
    # measures that curl puts it on the wire unaltered.
    verbatim = path.startswith("!")
    target = path[1:] if verbatim else BASE + path
    cmd = ["curl", "-s", "--path-as-is", "-o", "-", "-D", "-", "-w",
           "\n%{http_code} %{size_download} %{content_type}"]
    if verbatim:
        cmd += ["--request-target", target]
        # The argument curl connects with is the origin, not the row's target: a
        # bare `/v1#x` in the URL position is not a URL at all, and curl refuses
        # it with a malformed-URL exit before any request is made. The row is
        # about what goes on the wire, so the connection is the one thing the
        # verbatim cells are allowed to be ordinary about.
        cmd.append(BASE)
    else:
        cmd.append(target)
    for name, value in headers:
        cmd += ["-H", f"{name}: {value}"] if value else ["-H", f"{name};"]
    raw = subprocess.run(cmd, capture_output=True, timeout=30).stdout
    head, _, rest = raw.partition(b"\r\n\r\n")
    body, _, meta = rest.rpartition(b"\n")
    parts = [part.decode("latin-1") for part in meta.split(maxsplit=2)] + ["", "", ""]
    # The meta line can carry fewer fields than it has names for: `%{content_type}`
    # is empty for the outside miss (two fields), and a response that ends without
    # a trailing newline leaves the split with none. An empty field is a reading of
    # its own and is kept as one, never folded into the size.
    status, size, ctype = parts[0], parts[1], parts[2]
    # The status line is what answered; a reader who sees, beside the row, the
    # target the client actually asked for knows whether it was the row's path.
    sent = (head.split(b"\r\n", 1)[0].decode("latin-1")
            if head.startswith(b"HTTP/") else target)
    # What curl actually put on the wire, printed beside every row: with
    # `--path-as-is` it repeats the row's path, and a reader who sees the two
    # diverge knows the client rewrote it rather than the wall answering.
    return int(status), int(size), hashlib.sha256(body).hexdigest()[:16], ctype, sent


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
    for label, path, headers, status, size, digest, who in CELLS:
        got_status, got_size, got_digest, ctype, sent = one(path, headers)
        got = (got_status, got_size, got_digest)
        rows.append({"cell": label, "path": path, "answerer": who, "sent": sent,
                     "content_type": ctype,
                     "headers": [list(h) for h in headers], "got": list(got)})
        mark = "ok " if got == (status, size, digest) else "MOVED"
        if got != (status, size, digest):
            bad.append(f"{label}: {got} != {(status, size, digest)}")
        # Which instrument answered is part of the reading, not a comment on it.
        # The edge refuses some target shapes before the wall sees them, and its
        # refusals are its own HTML error page: a cell labelled `edge` whose
        # answer came back as a JSON body is a different instrument wearing the
        # same row, and it fails here rather than passing as agreement. The
        # outside miss is an empty body with no content-type, and a row that
        # brings bytes back under that label is not the same reading either.
        if who == "edge":
            attribution = not ctype.startswith("application/json")
        elif who == "outside":
            attribution = got_size == 0 and not ctype
        else:
            attribution = not ctype.startswith("text/html")
        if not attribution:
            bad.append(f"{label}: {who} labelled, answered with {ctype!r} "
                       f"and {got_size} bytes")
        print(f"{mark} {label:<26} {who:<8} {got[0]} {got[1]:>7} {got[2]}"
              f"  {path[:38]:<38} {ctype}")
    print(f"\n{len(CELLS) - len(bad)}/{len(CELLS)} cells as recorded"
          "  (first holder; four cells added by a second holder on 2026-09-24;"
          " twelve raw-segment cells proposed by a second holder and taken here"
          " on 2026-09-25; the verbatim-target and terminator cells taken"
          " on 2026-09-25 from a third host, each with the instrument that"
          " answered it)")
    if not check:
        TABLE.write_text(json.dumps({"as_of_note": "see probes/ladder_rungs.py",
                                     "cells": rows}, indent=1) + "\n", encoding="utf-8")
    for line in bad:
        print(f"MOVED  {line}")
    return 1 if (check and bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
