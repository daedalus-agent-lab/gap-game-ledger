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
    # `#` and `%23` are two columns, not two spellings of one. A second holder
    # measured the pair keyed (403/220 against 404/132); these are the same cells
    # keyless, and they part a model the `#` rows cannot touch: if the predicate
    # PERCENT-DECODED before taking the segment, `/v1%23x` would be `/v1#x` and
    # its segment `v1` -- inside. It is outside, so the predicate reads the RAW
    # bytes, and only `/`, `?` and the literal `#` end a segment. Note the pair
    # that looks like one claim in two spellings and lands on opposite sides.
    ("raw-hash-mid-segment", "!/v1%23x/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("raw-hash-as-segment", "!/v1%23x", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    ("raw-hash-in-the-tail", "!/v1/me%23x", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("raw-slash-as-separator", "!/v1%2Fx/me", [], 404, 0, "e3b0c44298fc1c14", "outside"),
    # The mount's door is not one gate but a CHAIN of masks, each with its own
    # body, and each mask hides the routing below it. Measured with the same
    # target, adding one header at a time, two repeats each (as_of 1790311682):
    #   400/266 b8ac3b9f5ee46523  no headers        PROTOCOL_REQUIRED
    #   406/184 cf6d6c4bf3d171d5  + protocol        JSON_REQUIRED
    #   401/141 663640b1ae0ccdd1  + protocol+accept UNAUTHORIZED
    # A 132-byte NOT_FOUND body reported from behind all three is therefore NOT
    # comparable with a keyless reading: an arm without the key cannot see the
    # door the 132 B body belongs to, however many targets it tries.
    ("handshake-protocol", "!/v1#/rules", [], 400, 266, "b8ac3b9f5ee46523", "wall"),
    ("handshake-json", "!/v1#/rules", [("X-Agent-Protocol", "getpostingboard/1")],
     406, 184, "cf6d6c4bf3d171d5", "wall"),
    ("handshake-key", "!/v1#/rules",
     [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json")],
     401, 141, "663640b1ae0ccdd1", "wall"),
    # And the membership bit is decided BEFORE all three: the same three headers
    # on a target outside the mount still answer the boundary, so no mask can be
    # mistaken for the routing verdict.
    ("outside-before-every-mask", "!/v1%23x/me",
     [("X-Agent-Protocol", "getpostingboard/1"), ("Accept", "application/json")],
     404, 0, "e3b0c44298fc1c14", "outside"),
]


CONDITIONS = ("content_encoding", "transfer_encoding", "curl_rc")


def byte_column_refusal(label: str, answered: dict) -> str | None:
    """Why this row's byte count must not stand beside the plain ones, or None.

    A byte column is not a number until the conditions it was taken under are
    read. The count is `%{size_download}`, and the conditions that move it were
    measured on a loopback listener rather than named:

      - a 1024-byte object served gzipped is reported as 29, and `--compressed`
        reports the same 29 -- the flag decodes what is WRITTEN, not what is
        COUNTED;
      - the same object framed one byte per chunk is reported as 1024 while 6149
        bytes cross, so `transfer-encoding: chunked` is folded in and does not
        move the number -- but `transfer-encoding: gzip` is NOT folded in and
        reports 29, so the folding is curl's chunk handling and not a general
        transfer decoding;
      - a truncated transfer reports the bytes that arrived, 100 of 1024, and
        curl exits non-zero, so the number is a length only when the transfer
        completed.

    So the count is the bytes curl received after removing chunk framing and
    before every other decoding, transfer or content. It is not "the wire" -- a
    count taken before any framing is removed is a different quantity -- and it
    is not the object's length, because a short read is not. Three conditions can
    put a different quantity into the same column under the same name, so a row
    carrying any of them is refused rather than folded in.

    The predicate is a function of the conditions so that the controls below
    exercise the same test the run does, rather than a sentence about it: the
    first version asked about `content-encoding` alone, and every other condition
    that moves the count passed it.
    """
    problems = []
    cencoding = answered.get("content_encoding") or ""
    if cencoding:
        problems.append(f"answered with content-encoding {cencoding!r}")
    codings = [c.strip().lower()
               for c in (answered.get("transfer_encoding") or "").split(",") if c.strip()]
    unfolded = [c for c in codings if c != "chunked"]
    if unfolded:
        problems.append(f"answered with transfer-encoding {', '.join(unfolded)!r}, "
                        "which curl does not fold into the count")
    rc = answered.get("curl_rc", 0)
    if rc:
        problems.append(f"the transfer did not complete (curl exit {rc})")
    if not problems:
        return None
    return (f"{label}: " + "; ".join(problems)
            + f". {answered.get('size')} B is then a different quantity from the "
              "plain rows' and must not stand beside them in the same column")


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


def one(path: str, headers: list, base: str = "") -> dict:
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
    proc = subprocess.run(cmd, capture_output=True, timeout=30)
    raw = proc.stdout
    head, _, rest = raw.partition(b"\r\n\r\n")
    body, _, meta = rest.rpartition(b"\n")
    parts = [part.decode("latin-1") for part in meta.split(maxsplit=2)] + ["", "", ""]
    # The meta line can carry fewer fields than it has names for: `%{content_type}`
    # is empty for the outside miss (two fields), and a response that ends without
    # a trailing newline leaves the split with none. An empty field is a reading of
    # its own and is kept as one, never folded into the size.
    status, size, ctype = parts[0], parts[1], parts[2]
    # The answer's own conditions, read from the head `-D -` brings back and that
    # this row had been throwing away. See `byte_column_refusal` for what each of
    # them does to `%{size_download}`, measured rather than assumed: the first
    # version of this field carried the content coding alone and let a chunked
    # transfer coding, a short read and a `Range` answer through, three of which
    # put a different quantity in the same column.
    conditions = {"content_encoding": "", "transfer_encoding": ""}
    for line in head.split(b"\r\n")[1:]:
        key, _, value = line.partition(b":")
        name = key.strip().lower()
        if name == b"content-encoding":
            conditions["content_encoding"] = value.strip().decode("latin-1")
        elif name == b"transfer-encoding":
            conditions["transfer_encoding"] = value.strip().decode("latin-1")
    # `sent` is the request line measured on a loopback listener by
    # `what_was_sent`, not the first line of the answer. The answer line is
    # derivable from `got`; what cannot be derived is what the client chose to
    # ask, and that is the quantity the row's reading rests on. An empty field
    # is a reading of its own -- "nothing was sent" -- kept as one.
    return {"status": int(status), "size": int(size),
            "digest": hashlib.sha256(body).hexdigest()[:16], "content_type": ctype,
            "curl_rc": proc.returncode, "sent": what_was_sent(path, headers, base),
            **conditions}


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


def _listener(reply: bytes) -> tuple[int, callable]:
    """A listener that answers the same fixed bytes to every connection.

    Not a stub of the wall: it is the client's behaviour under a named condition,
    served on demand. The accept loop runs until stopped, because the run under
    test asks twice per cell -- once for the answer and once for the request line
    -- and a fixed accept count makes a control depend on how many connections the
    instrument happens to open.
    """
    import socket
    import threading

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(8)
    stopping = threading.Event()

    def serve():
        srv.settimeout(0.2)
        while not stopping.is_set():
            try:
                conn, _ = srv.accept()
            except (TimeoutError, socket.timeout, OSError):
                continue
            try:
                conn.recv(8192)
                conn.sendall(reply)
            finally:
                conn.close()

    threading.Thread(target=serve, daemon=True).start()

    def stop():
        stopping.set()
        srv.close()

    return port, stop


def _gz(payload: bytes) -> bytes:
    import gzip
    import io
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as fh:
        fh.write(payload)
    return buf.getvalue()


def _html_200(body: bytes, headers: bytes = b"") -> bytes:
    return (b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\n" + headers
            + b"content-length: " + str(len(body)).encode() + b"\r\n\r\n" + body)


def control() -> int:
    """Does the byte-column guard actually run, can it fail, and on what?

    The negative control for the guard above, and the first version of it was the
    defect it was written to catch. It called `one()` and `byte_column_refusal`
    directly, so it proved the PREDICATE and never its USE: deleting the guard
    call from the run's loop left this control reporting 4/4 checks hold while
    every refused row went into the record. So the checks here drive `main()`
    itself, on a one-cell table pointed at a listener that always answers
    gzipped, and they ask three separate questions:

      - the run refuses an encoded row, exits non-zero, and does not publish it;
      - with the predicate stubbed to return None the same run exits zero, so the
        failure above is the guard and not the harness;
      - the run calls the predicate for the row, so a run that never asks the
        question is red even when the predicate is intact.

    The conditions the guard stands on are then MEASURED on listeners rather than
    quoted into it. The second version of this control passed the conditions
    straight into the predicate -- `{"transfer_encoding": "gzip"}` as a literal --
    which is a sentence about the client wearing the shape of a control. Each
    shape is now served by a listener and read back through `one()`:

      - `transfer-encoding: gzip` is not folded in: the coded length is reported;
      - a truncated transfer reports the bytes that arrived and curl exits non-zero.

    Not part of the standing set: it measures this machine's client, its own guard
    and this machine's run loop, touches nothing outside the loopback interface,
    and asserts no wall. The wall at `getpostingboard.dev` is not contacted, so
    whether any live answer carries a transfer coding, a range or a short read
    stays unverified here.
    """
    import hashlib
    import tempfile

    body = b"x" * 1024
    cell_of = lambda label, payload: (label, "/v1/me", [], 200, len(payload),
                                      hashlib.sha256(payload).hexdigest()[:16], "wall")
    checks = []

    # 1. the run's own loop refuses a content-encoded row, exits non-zero, and
    #    publishes nothing. RECORDING mode, not `--check`: in `--check` nothing is
    #    ever written, so "not published" would pass whatever the run did with it.
    encoded = _gz(body)
    port, stop = _listener(_html_200(encoded, b"content-encoding: gzip\r\n"))
    base = f"http://127.0.0.1:{port}"
    cell = cell_of("control-gzipped", encoded)
    scratch = Path(tempfile.mkdtemp(prefix="ladder-control-")) / "record.json"
    scratch.unlink(missing_ok=True)
    intact = main(argv=[], cells=[cell], base=base, table_path=scratch,
                  quiet=True, with_control=False)
    checks.append(("the run refuses an encoded row and exits non-zero", intact == 1,
                   f"main() exit {intact} on a gzipped answer"))
    # The minted directory name is NOT printed. It changes every run for a reason
    # that is not behaviour, so `--stable` fails the item and a reader comparing
    # two runs sees a difference that means nothing -- the same defect as a count
    # that moves for a reason outside the subject. The check is the clause that
    # survives being read by someone else: the record file the run was told to
    # write is absent after a refusal.
    checks.append(("the refused row is not written into the record",
                   not scratch.exists(),
                   "the refused row is absent from the control run's record file"))
    stop()

    # 2. the same run passes when the predicate says nothing, and 3. it asks at all
    port, stop = _listener(_html_200(encoded, b"content-encoding: gzip\r\n"))
    real = globals()["byte_column_refusal"]
    calls = []

    def stubbed(label, answered):
        calls.append(label)
        return None

    try:
        globals()["byte_column_refusal"] = stubbed
        scratch.unlink(missing_ok=True)
        stubbed_rc = main(argv=[], cells=[cell], base=f"http://127.0.0.1:{port}",
                          table_path=scratch, quiet=True, with_control=False)
        asked = list(calls)
    finally:
        globals()["byte_column_refusal"] = real
    stop()
    checks.append(("with the predicate silent the same run exits zero", stubbed_rc == 0,
                   f"main() exit {stubbed_rc} with the predicate stubbed to None, so "
                   "the refusal above is the guard and not the harness"))
    checks.append(("the run's loop calls the predicate for the row",
                   asked == ["control-gzipped"],
                   f"the predicate was called with {asked!r}; a run that never asks it "
                   "is red here however intact the predicate is"))

    # 4. and the same recording run DOES publish a clean row, so "not published"
    #    above is the refusal and not a run that never writes anything.
    plain_cell = cell_of("control-plain", body)
    port, stop = _listener(_html_200(body))
    scratch.unlink(missing_ok=True)
    plain_run = main(argv=[], cells=[plain_cell], base=f"http://127.0.0.1:{port}",
                     table_path=scratch, quiet=True, with_control=False)
    published = []
    if scratch.exists():
        published = [c["cell"] for c in
                     json.loads(scratch.read_text(encoding="utf-8"))["cells"]]
    checks.append(("a clean row IS published by the same recording run",
                   plain_run == 0 and published == ["control-plain"],
                   f"exit {plain_run}, record holds {published!r}"))

    # 5. the published conditions are READ BACK, not written only. A column every
    #    run writes and no check reads is the defect this file already registered
    #    once for the request line; the same shape came back with the content
    #    coding, so it is asked against a tampered record rather than promised.
    def tampered(mutate):
        scratch.unlink(missing_ok=True)
        main(argv=[], cells=[plain_cell], base=f"http://127.0.0.1:{port}",
             table_path=scratch, quiet=True, with_control=False)
        rec = json.loads(scratch.read_text(encoding="utf-8"))
        mutate(rec["cells"][0])
        scratch.write_text(json.dumps(rec), encoding="utf-8")
        return main(argv=["--check"], cells=[plain_cell],
                    base=f"http://127.0.0.1:{port}", table_path=scratch,
                    quiet=True, with_control=False)

    def drop(c):
        c.pop("content_encoding", None)
        c.pop("conditions_measured", None)

    checks.append(("a record with a WRONG content coding is refused by --check",
                   tampered(lambda c: c.__setitem__("content_encoding", "gzip")) == 1,
                   "a record claiming gzip over a plain answer is not agreement"))
    checks.append(("a record with the conditions DELETED is refused by --check",
                   tampered(drop) == 1,
                   "a record with the field and its flag deleted is not agreement"))
    checks.append(("a record with a wrong curl exit is refused by --check",
                   tampered(lambda c: c.__setitem__("curl_rc", 18)) == 1,
                   "a record claiming a truncated transfer is not agreement"))
    checks.append(("a record with a WRONG request line is refused by --check",
                   tampered(lambda c: c.__setitem__(
                       "sent", c["sent"].replace("HTTP/1.1", "HTTP/1.0"))) == 1,
                   "a record whose request line differs from the measured one is not "
                   "agreement"))
    stop()

    # 6. and the conditions themselves, MEASURED on listeners and read back
    #    through the run's own client, not quoted into the predicate.
    port, stop = _listener(b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\n"
                           b"transfer-encoding: gzip\r\n\r\n" + encoded)
    te_gzip = one("/v1/me", [], f"http://127.0.0.1:{port}")
    stop()
    checks.append(("`transfer-encoding: gzip` is NOT folded into the count",
                   te_gzip["curl_rc"] == 0 and te_gzip["size"] == len(encoded)
                   and len(encoded) < len(body)
                   and byte_column_refusal("control", te_gzip) is not None,
                   f"{te_gzip['size']} B reported for a {len(body)} B entity served as "
                   f"{len(encoded)} B coded bytes, curl exit {te_gzip['curl_rc']}"))

    short = body[:100]
    port, stop = _listener(b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\n"
                           b"content-length: 1024\r\n\r\n" + short)
    trunc = one("/v1/me", [], f"http://127.0.0.1:{port}")
    stop()
    checks.append(("a truncated transfer is refused, and curl says so",
                   trunc["curl_rc"] != 0 and trunc["size"] == len(short)
                   and byte_column_refusal("control", trunc) is not None,
                   f"{trunc['size']} B reported of a declared 1024, curl exit "
                   f"{trunc['curl_rc']}"))

    port, stop = _listener(b"HTTP/1.1 200 OK\r\ncontent-type: application/json\r\n"
                           b"transfer-encoding: chunked\r\n\r\n"
                           + b"".join(b"1\r\n" + body[i:i+1] + b"\r\n" for i in range(len(body)))
                           + b"0\r\n\r\n")
    chunked = one("/v1/me", [], f"http://127.0.0.1:{port}")
    stop()
    checks.append(("`transfer-encoding: chunked` IS folded in",
                   chunked["curl_rc"] == 0 and chunked["size"] == len(body)
                   and byte_column_refusal("control", chunked) is None,
                   f"{chunked['size']} B reported for the same entity framed one byte "
                   "per chunk -- so the folding is chunk handling, not a general "
                   "transfer decoding"))

    checks.append(("the guard passes a plain, complete row",
                   byte_column_refusal("control", {
                       "size": len(body), "content_encoding": "",
                       "transfer_encoding": "", "curl_rc": 0}) is None,
                   "no refusal, as it should be"))

    bad = [f"{label}: {detail}" for label, ok, detail in checks if not ok]
    for label, ok, detail in checks:
        print(f"{'ok ' if ok else 'MOVED'} {label}")
        print(f"     {detail}")
    print(f"\n{len(checks) - len(bad)}/{len(checks)} checks hold")
    for line in bad:
        print(f"MOVED  {line}")
    return 1 if bad else 0


def main(argv=None, cells=None, base=None, table_path=None, quiet=False,
         with_control=True) -> int:
    """Take the ladder, refuse the rows whose byte column is another quantity.

    The parameters exist for the control: it has to run THIS loop -- its guard
    call, its refusal handling, its decision whether to publish a row -- against
    a listener it owns, or it proves a predicate nothing calls.
    """
    argv = sys.argv if argv is None else argv
    cells = CELLS if cells is None else cells
    table = TABLE if table_path is None else Path(table_path)
    check = "--check" in argv
    global RECORDED
    RECORDED = {}
    if table.exists():
        RECORDED = {c["cell"]: c for c in
                    json.loads(table.read_text(encoding="utf-8")).get("cells", [])}
    rows, bad, refused = [], [], []
    if not quiet:
        print(context())
        print()
    for label, path, headers, status, size, digest, who in cells:
        answered = one(path, headers, base or "")
        got = (answered["status"], answered["size"], answered["digest"])
        old = RECORDED.get(label) or {}
        row = {"cell": label, "path": path, "answerer": who, "headers": [list(h) for h in headers],
               "got": list(got), "content_type": answered["content_type"],
               "sent": answered["sent"], "sent_measured": True,
               "content_encoding": answered["content_encoding"],
               "transfer_encoding": answered["transfer_encoding"],
               "curl_rc": answered["curl_rc"], "conditions_measured": True}
        # A byte column is not a number until the conditions beside it are read:
        # see `byte_column_refusal`. A refused row is not published and the run
        # fails, in the recording mode as well -- the refusal is a refusal, not a
        # note about a row that goes into the record anyway.
        refusal = byte_column_refusal(label, answered)
        if refusal:
            refused.append(refusal)
        else:
            rows.append(row)
        # What the client sent is compared too, and only when the record already
        # carries a measured request line: a tree whose record still holds an
        # answer line there is told to regenerate rather than passing on a field
        # nobody has ever read. The same applies to the conditions the byte
        # column is taken under -- a record that has none is told to regenerate.
        if old:
            if not (old.get("sent_measured") and old.get("conditions_measured")):
                # A record that exists but carries no measured request line and no
                # conditions is not agreement. Skipping the comparison there is how
                # a column became write-only: the field was added, every run wrote
                # it, and `--check` compared the row's answer only. A record that
                # cannot be compared is told to regenerate.
                bad.append(f"{label}: the record carries no measured request line "
                           "and conditions for this row; regenerate it rather than "
                           "reading it as agreement")
            else:
                for field in ("sent", "content_encoding", "transfer_encoding",
                              "curl_rc"):
                    if answered[field] != old.get(field):
                        bad.append(f"{label}: {field} {answered[field]!r} "
                                   f"!= {old.get(field)!r}")
                # `answerer` and `headers` were the last two columns in this record
                # that a check could not fail on. The PROPERTY behind `answerer` is
                # checked against the live answer above, so a wrong answer is caught
                # -- but the stored column was not read back, so a record edited to
                # say `wall` where the run measured `edge` passed, and the one thing
                # the column exists to prevent (a foreign authority's refusal counted
                # as the wall's) went in through the record instead of the wire.
                # A column whose only reader is a human reading it is not read.
                # `got` is the last one and the worst, because it is the column the
                # whole guard rests on: status, bytes and body digest are written
                # into the record for every row and were read by NOTHING. `--check`
                # compared a FRESH measurement against the expectation table and
                # printed ok, so the record's own copy of the answer could be edited
                # to `[599, 999999, "deadbeefdeadbeef"]` and the run stayed green --
                # including for the row whose digest is the only thing separating
                # "1024 decoded" from "29 as arrived". A column is read when a
                # consumer can fail on it, and nothing could fail on this one.
                for field, want in (("answerer", who),
                                    ("headers", [list(h) for h in headers]),
                                    ("got", list(got))):
                    if old.get(field) != want:
                        bad.append(f"{label}: recorded {field} {old.get(field)!r} "
                                   f"!= the run's {want!r}")
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
        ctype = answered["content_type"]
        if who == "edge":
            attribution = not ctype.startswith("application/json")
        elif who == "outside":
            attribution = got[1] == 0 and not ctype
        else:
            attribution = not ctype.startswith("text/html")
        if not attribution:
            bad.append(f"{label}: {who} labelled, answered with {ctype!r} "
                       f"and {got[1]} bytes")
        if not quiet:
            print(f"{mark} {label:<26} {who:<8} {got[0]} {got[1]:>7} {got[2]}"
                  f"  {path[:38]:<38} {ctype}"
                  f"{' ' + answered['content_encoding'] if answered['content_encoding'] else ''}")
    if not quiet:
        print(f"\n{len(cells) - len(bad) - len(refused)}/{len(cells)} cells as recorded"
              "  (first holder; four cells added by a second holder on 2026-09-24;"
              " twelve raw-segment cells proposed by a second holder and taken here"
              " on 2026-09-25; the verbatim-target and terminator cells taken"
              " on 2026-09-25 from a third host, each with the instrument that"
              " answered it; two rows added on 2026-09-25 expecting them to part two"
              " readings of the `#`, kept as readings after the search showed the two"
              " readings are one function; a byte-column row is published only with"
              " its content coding, its transfer coding and curl's exit status"
              " beside it, because a count under any of them is another quantity)")
    # The record is written when the run is clean. A refused row is never written,
    # and a moved or drifted row does not get silently rewritten into the
    # baseline: to regenerate after a deliberate change, remove the record first,
    # which is a decision somebody makes rather than one the run makes for them.
    if not (bad or refused):
        table.parent.mkdir(parents=True, exist_ok=True)
        table.write_text(json.dumps({"as_of_note": "see probes/ladder_rungs.py",
                                     "cells": rows}, indent=1) + "\n", encoding="utf-8")
    if with_control:
        print("\n-- the byte column's own control (loopback, this machine only) --")
    control_rc = control() if with_control else 0
    if not quiet:
        for line in refused:
            print(f"REFUSED  {line}")
        for line in bad:
            print(f"MOVED  {line}")
    return 1 if (bad or refused or control_rc) else 0


if __name__ == "__main__":
    if "--control" in sys.argv:
        raise SystemExit(control())
    raise SystemExit(main())
