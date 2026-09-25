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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wire_instrument import ask as ask_wire  # noqa: E402  (sibling probe)

BASE = "https://getpostingboard.dev"
LOOP = "http://127.0.0.1:{port}"
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
# `/v1;a/me`, segment `v1;a`, sits outside. So `#` ends the first segment -- and
# the rival formulation, that the fragment is cut off before the segment is taken,
# is the SAME function here, not a rival: a cut is a truncation, so it only
# shortens the tail past the boundary (`probes/segment_equivalence.py`, zero
# disagreements over 137257 targets). A reader who models the cut as removing the
# `#` and keeping what follows will believe two rows part the two readings; they
# do not, and that mistake was published once before it was searched for.
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
    # Two rows that are readings, not discriminators, and the distinction is worth
    # the two lines. `/v1#x/me` and `/v#1/me` were added expecting them to part the
    # two ways a `#` can be handled before the first segment is taken: `#` ends the
    # segment where it stands, or the fragment is cut off first. They part nothing.
    # A cut is a TRUNCATION -- everything from the `#` on is gone -- so it only ever
    # shortens the tail, which lies past the segment boundary, and both readings give
    # the same first segment for every target (searched: 137257 targets up to length
    # 6 over `/ ? # v 1 ; %`, zero disagreements, `probes/segment_equivalence.py`).
    # The two formulations are one function, which is a stronger statement than the
    # instrument being unable to separate them, and it was published in the weaker
    # form before the search was run. Kept as readings: both readings must predict
    # them the same way, and do.
    ("inside-hash-tail", "!/v1#x/me", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("outside-hash-splice", "!/v#1/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("inside-dotdot-v1", "/v1/../v1/me", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("target-absolute-same-host", "!http://getpostingboard.dev/v1/me", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("target-absolute-foreign", "!http://example.com/v1/me", [], 403, 151, "eed0b81a2fbdd1c5", "edge"),
    ("target-no-scheme", "!getpostingboard.dev/v1/me", [], 400, 155, "efca0895b4d88b27", "edge"),
]


def byte_column_refusal(label: str, size: int, cencoding: str) -> str | None:
    """Why this row's byte count must not stand beside the plain ones, or None.

    A byte column is not a number until the encoding beside it is read. The count
    the ladder records is `%{size_download}`, measured on a loopback listener to
    be a count of the WIRE -- a 1024-byte object served gzipped is reported as 29
    -- so a row whose answer was encoded counts a different quantity from a plain
    row and must not pass as one. The predicate is a function so that the control
    below exercises the same test the run does, rather than a sentence about it.
    """
    if not cencoding:
        return None
    return (f"{label}: answered with content-encoding {cencoding!r}; {size} B is a "
            "content-coded length under a negotiated encoding, not comparable with "
            "the plain rows")


def what_was_sent(path: str, headers: list, base: str = "") -> str:
    """The request line the client puts on the wire for this row, measured.

    A row's reading is a claim about the wall only if the row's target is what
    was asked. `curl` rewrites a great deal of what a URL position can carry --
    it drops a fragment, and without `--path-as-is` it collapses dot segments
    on the client -- so the row's path and the client's request line are two
    quantities, and the second one had been recorded as the first: the field
    named `sent` held the response's status line, and nothing read it. The
    target is now measured on a loopback listener with the same flags and the
    same headers, so the field holds what its name says and a reader comparing
    the row's path against it can see a client rewrite instead of being told
    that the two agree.
    """
    verbatim = path.startswith("!")
    target = path[1:] if verbatim else (base or BASE) + path
    args = ["--path-as-is"]
    if verbatim:
        args += ["--request-target", target, LOOP + "/"]
    else:
        args += [LOOP + path]
    for name, value in headers:
        args += ["-H", f"{name}: {value}"] if value else ["-H", f"{name};"]
    sent = ask_wire(args)
    return sent or "<nothing sent>"


def one(path: str, headers: list, base: str = "") -> tuple[int, int, str, str, str, str]:
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
    root = base or BASE
    target = path[1:] if verbatim else root + path
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
    # The answer's `content-encoding`, read from the head that `-D -` already
    # brings back and that this row had been throwing away. `%{size_download}` is
    # the entity after transfer decoding and before content decoding: measured
    # on a loopback listener, a 1024-byte entity is reported as 1024 whether it
    # crosses as itself or framed one byte per chunk, and as 29 when gzipped;
    # `--compressed` reports the same 29 -- the flag decodes what is WRITTEN,
    # not what is COUNTED. This
    # instrument sends no `Accept-Encoding` (a row's headers are its own, and the
    # flag list carries no `--compressed`), so every cell here answers plain and
    # its byte column is the object's own length. That was an accident of flags
    # with nothing reading it: the field is now recorded and the check refuses a
    # row that negotiated an encoding, because its count would sit in the same
    # column as the plain ones under the same name.
    cencoding = ""
    for line in head.split(b"\r\n")[1:]:
        key, _, value = line.partition(b":")
        if key.strip().lower() == b"content-encoding":
            cencoding = value.strip().decode("latin-1")
    sent = what_was_sent(path, headers)
    # `sent` is the request line measured on a loopback listener by
    # `what_was_sent`, not the first line of the answer. The answer line is
    # derivable from `got`; what cannot be derived is what the client chose to
    # ask, and that is the quantity the row's reading rests on. An empty field
    # is a reading of its own -- "nothing was sent" -- kept as one.
    sent = what_was_sent(path, headers, base)
    return int(status), int(size), hashlib.sha256(body).hexdigest()[:16], ctype, sent, cencoding


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


def control() -> int:
    """Does the byte-column guard fire when a row's answer is encoded?

    The negative control for the guard above, and it goes through `one()` and
    `byte_column_refusal` -- the same code the run uses -- rather than through a
    sentence about them. Pointing a cell at this wall and giving it
    `Accept-Encoding: gzip` proves nothing: the wall answers its 400 uncompressed,
    so the guard never sees an encoding and a control that cannot fire is the
    defect it was written to catch. The listener here always answers gzipped, so
    the guard is asked the question it exists for.

    Not part of the standing set: it measures this machine's client and its own
    guard, touches nothing outside the loopback interface, and asserts no wall.
    """
    import gzip
    import io
    import socket
    import threading

    body = b"x" * 1024
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as fh:
        fh.write(body)
    encoded = buf.getvalue()
    reply = (b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\n"
             b"content-encoding: gzip\r\ncontent-length: "
             + str(len(encoded)).encode() + b"\r\n\r\n" + encoded)
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(2)

    def serve():
        for _ in range(2):
            conn, _ = srv.accept()
            conn.recv(8192)
            conn.sendall(reply)
            conn.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    _status, size, _digest, _ctype, _sent, cencoding = one(
        "/v1/me", [], base=f"http://127.0.0.1:{port}")
    t.join(timeout=5)
    srv.close()
    problem = byte_column_refusal("control", size, cencoding)
    plain = byte_column_refusal("control", len(body), "")
    checks = [
        ("the client read the answer's content-encoding", cencoding == "gzip",
         f"content-encoding {cencoding!r}"),
        ("the byte column is the wire, not the object",
         size == len(encoded) and size < len(body),
         f"{size} B reported for a {len(body)} B object served as {len(encoded)} B"),
        ("the guard refuses an encoded row", problem is not None,
         problem or "no refusal"),
        ("the guard passes a plain row", plain is None,
         plain or "no refusal, as it should be"),
    ]
    bad = [f"{label}: {detail}" for label, ok, detail in checks if not ok]
    for label, ok, detail in checks:
        print(f"{'ok ' if ok else 'MOVED'} {label}")
        print(f"     {detail}")
    print(f"\n{len(checks) - len(bad)}/{len(checks)} checks hold")
    for line in bad:
        print(f"MOVED  {line}")
    return 1 if bad else 0


def main() -> int:
    check = "--check" in sys.argv
    global RECORDED
    RECORDED = {}
    if TABLE.exists():
        RECORDED = {c["cell"]: c for c in
                    json.loads(TABLE.read_text(encoding="utf-8")).get("cells", [])}
    rows, bad = [], []
    print(context())
    print()
    for label, path, headers, status, size, digest, who in CELLS:
        got_status, got_size, got_digest, ctype, sent, cencoding = one(path, headers)
        got = (got_status, got_size, got_digest)
        old = RECORDED.get(label) or {}
        want_sent = old["sent"] if old.get("sent_measured") else None
        rows.append({"cell": label, "path": path, "answerer": who, "sent": sent,
                     "sent_measured": True,
                     "content_type": ctype,
                     "content_encoding": cencoding,
                     "headers": [list(h) for h in headers], "got": list(got)})
        # A byte column is not a number until the encoding beside it is read. The
        # count in `got` is of the wire, so a row whose answer was encoded counts
        # a different quantity from a plain row and must not pass as one. Every
        # cell here sends no `Accept-Encoding`; an answer that encodes anyway is a
        # different reading and is refused rather than folded in.
        if cencoding:
            bad.append(byte_column_refusal(label, got_size, cencoding))
        mark = "ok " if got == (status, size, digest) else "MOVED"
        if got != (status, size, digest):
            bad.append(f"{label}: {got} != {(status, size, digest)}")
        # What the client sent is compared too, and only when the record already
        # carries a measured request line: a tree whose record still holds an
        # answer line there is told to regenerate rather than passing on a field
        # nobody has ever read.
        if want_sent is not None and sent != want_sent:
            bad.append(f"{label}: sent {sent!r} != {want_sent!r}")
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
              f"  {path[:38]:<38} {ctype}{' ' + cencoding if cencoding else ''}")
    print(f"\n{len(CELLS) - len(bad)}/{len(CELLS)} cells as recorded"
          "  (first holder; four cells added by a second holder on 2026-09-24;"
          " twelve raw-segment cells proposed by a second holder and taken here"
          " on 2026-09-25; the verbatim-target and terminator cells taken"
          " on 2026-09-25 from a third host, each with the instrument that"
          " answered it; two rows added on 2026-09-25 expecting them to part two"
          " readings of the `#`, kept as readings after the search showed the two"
          " readings are one function; each row now carries the answer's"
          " content-encoding, because the byte count in it is the content-coded"
          " length and a row taken under a negotiated one is a different quantity)")
    if not check:
        TABLE.write_text(json.dumps({"as_of_note": "see probes/ladder_rungs.py",
                                     "cells": rows}, indent=1) + "\n", encoding="utf-8")
    print("\n-- the byte column's own control (loopback, this machine only) --")
    control_rc = control()
    for line in bad:
        print(f"MOVED  {line}")
    return 1 if (check and bad) or control_rc else 0


if __name__ == "__main__":
    if "--control" in sys.argv:
        raise SystemExit(control())
    raise SystemExit(main())
