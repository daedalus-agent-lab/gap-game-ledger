"""What the asking instrument actually puts on the wire.

A cell in `ladder_rungs.py` whose row carries a `#` is a reading of the wall
ONLY if the `#` was sent. curl removes a fragment from a URL it is given: asked
for `http://host/v1#x` it puts `GET /v1 HTTP/1.1` on the wire, and a cell taken
that way would report the wall's answer to `/v1` while the row claims to be about
`/v1#x`. `--request-target` is the way to send the raw target, and this probe
measures that it does -- on a loopback listener, so the assertion is about the
client and touches nothing outside this machine.

The same question decides the verbatim-target cells of the ladder: an absolute
target and a target with no scheme are only measurable if the client sends them
as written, and where a client silently rewrote one of them the ladder's cell
would be a reading of the rewrite.

A second question, raised on the board by a second holder against the ladder's
byte column: `curl -w '%{size_download}'` is not a count of the OBJECT. Where on
the decoding chain it counts was measured here rather than guessed, because the
first answer given for it was wrong: it is NOT a count of the wire. A plain
1024-byte entity crosses the wire as 1065 bytes (status line and headers) and is
reported as 1024; the same entity framed one byte per chunk crosses as 6196 bytes
and is STILL reported as 1024, so transfer decoding is folded in and
`transfer-encoding` cannot move the number. The same entity served gzipped is
reported as 29, because content decoding is NOT folded in. So the number is the
entity after transfer decoding and before content decoding, and the one condition
beside it that changes it is `content-encoding` -- which the ladder never read.

What `curl` sends by default, what `--compressed` adds, and what the byte column
does when the answer is encoded are each measured here:

    accepting-encoding   no flag  -> no `accept-encoding` sent at all
                         --compressed  -> `deflate, gzip, br, zstd`
    size_download        object 1024 B served gzip -> 29, with and without
                         --compressed, so the flag decodes what is WRITTEN and
                         does not change what is COUNTED

A byte column is not a number until the encoding beside it is read.

Usage:
    python3 probes/wire_instrument.py            # print what was sent
    python3 probes/wire_instrument.py --check    # exit 1 if the client moved
"""

from __future__ import annotations

import hashlib
import socket
import subprocess
import sys
import threading

# (label, curl arguments after the command, the request line expected on the wire)
#
# `{port}` is replaced by the loopback listener's port. The token is spelled out
# rather than left to `%`-formatting because a row's target may carry a `%` of its
# own (`/v1%23x`, `/v1%2F`): asked to format such a string, `%` reads `%23` as a
# conversion of its own and the substitution decides which bytes the client is
# given. The instrument must not rewrite the thing it is measuring.
CASES = [
    ("url-with-fragment", ["http://127.0.0.1:{port}/v1#x"],
     "GET /v1 HTTP/1.1"),
    ("target-with-fragment", ["--request-target", "/v1#x", "http://127.0.0.1:{port}/"],
     "GET /v1#x HTTP/1.1"),
    ("target-fragment-slash", ["--request-target", "/v1#/me", "http://127.0.0.1:{port}/"],
     "GET /v1#/me HTTP/1.1"),
    ("target-fragment-query", ["--request-target", "/v1#?x=1", "http://127.0.0.1:{port}/"],
     "GET /v1#?x=1 HTTP/1.1"),
    ("target-absolute-form",
     ["--request-target", "http://example.com/v1/me", "http://127.0.0.1:{port}/"],
     "GET http://example.com/v1/me HTTP/1.1"),
    ("target-no-scheme",
     ["--request-target", "example.com/v1/me", "http://127.0.0.1:{port}/"],
     "GET example.com/v1/me HTTP/1.1"),
    ("target-percent-encoded", ["--request-target", "/v1%23x", "http://127.0.0.1:{port}/"],
     "GET /v1%23x HTTP/1.1"),
    ("url-percent-encoded", ["http://127.0.0.1:{port}/v1%23x"],
     "GET /v1%23x HTTP/1.1"),
]


def ask_head(args: list[str], reply: bytes = b"HTTP/1.1 204 No Content\r\n"
             b"content-length: 0\r\n\r\n") -> str:
    """One request against a loopback listener; return the whole request head.

    The head, not the request line: the questions this probe now answers are
    about a HEADER (`accept-encoding`) and about what the answer does to the byte
    column, and both are invisible from the first line alone. The listener
    answers with `reply` so the same instrument can serve a plain body and an
    encoded one, and the client is the only thing under test either way.
    """
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(1)
    seen = []

    def serve():
        conn, _ = srv.accept()
        seen.append(conn.recv(8192).decode("latin-1"))
        conn.sendall(reply)
        conn.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    cmd = ["curl", "-s", "-o", "/dev/null"] + [a.replace("{port}", str(port))
                                               for a in args]
    subprocess.run(cmd, capture_output=True, timeout=15)
    t.join(timeout=5)
    srv.close()
    return seen[0] if seen else ""


def ask(args: list[str]) -> str:
    """The request line the client sends for these arguments."""
    head = ask_head(args)
    return head.split("\r\n", 1)[0] if head else ""


def header_of(head: str, name: str) -> str | None:
    """The value of one request header, or None when the header was not sent.

    `None` and the empty string are kept apart on purpose: "the client sent no
    `accept-encoding`" and "the client sent one with nothing in it" are two
    readings, and only the first one makes a plain byte count comparable with
    another plain byte count.
    """
    for line in head.split("\r\n")[1:]:
        key, _, value = line.partition(":")
        if key.strip().lower() == name.lower():
            return value.strip()
    return None


# --- the encoding axis ------------------------------------------------------
# The body a listener serves for the byte-column measurement. It is one kilobyte
# of a repeated byte, which gzip takes to a few dozen, so the wire count and the
# object count are far apart and a confusion between them cannot hide in a
# rounding. The same OBJECT is served twice: once as itself, once gzipped.
PLAIN_BODY = b"x" * 1024


def _gzip(body: bytes) -> bytes:
    import gzip
    import io

    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as fh:
        fh.write(body)
    return buf.getvalue()


def size_reported_by_curl(args: list[str], reply: bytes | None = None) -> tuple[int, int]:
    """Ask a loopback listener for a body; return (size_download, bytes served).

    The default answer is the gzipped object with `content-encoding: gzip`, and
    `bytes served` is what the listener actually put in the socket. Passing a
    reply lets the same measurement be taken on a body whose framing differs
    while its entity does not, which is how the transfer axis below is read: the
    question is where on the decoding chain the client counts, and a variable is
    needed to ask it.
    """
    if reply is None:
        encoded = _gzip(PLAIN_BODY)
        reply = (b"HTTP/1.1 200 OK\r\ncontent-encoding: gzip\r\ncontent-length: "
                 + str(len(encoded)).encode() + b"\r\n\r\n" + encoded)
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(1)

    def serve():
        conn, _ = srv.accept()
        conn.recv(8192)
        conn.sendall(reply)
        conn.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    cmd = ["curl", "-s", "-o", "/dev/null", "-w", "%{size_download}"] + [
        a.replace("{port}", str(port)) for a in args]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=15).stdout
    t.join(timeout=5)
    srv.close()
    head, _, body = reply.partition(b"\r\n\r\n")
    del head
    return int(out.strip() or 0), len(body)


def chunked_entity() -> bytes:
    """A 1024-byte entity framed one byte per chunk, which crosses as 6196 bytes."""
    return (b"".join(b"1\r\n" + PLAIN_BODY[i:i + 1] + b"\r\n"
                     for i in range(len(PLAIN_BODY))) + b"0\r\n\r\n")


def transfer_axis() -> list[tuple[str, str, str]]:
    """Where on the decoding chain the client counts. `transfer-encoding` is
    folded in, `content-encoding` is not -- so the condition the byte column
    needs beside it is the content encoding, and the transfer encoding is not a
    second one."""
    plain_reply = (b"HTTP/1.1 200 OK\r\ncontent-length: "
                   + str(len(PLAIN_BODY)).encode() + b"\r\n\r\n" + PLAIN_BODY)
    framed = chunked_entity()
    chunk_reply = b"HTTP/1.1 200 OK\r\ntransfer-encoding: chunked\r\n\r\n" + framed
    rows = []
    for label, reply in (("content-length", plain_reply), ("chunked", chunk_reply)):
        size, served = size_reported_by_curl(["http://127.0.0.1:{port}/x"], reply)
        rows.append((label, f"{size} reported", f"{served} B served"))
    return rows


def context() -> str:
    version = subprocess.run(["curl", "--version"], capture_output=True,
                             text=True).stdout.splitlines()[0]
    mine = hashlib.sha256(open(__file__, "rb").read()).hexdigest()
    return f"{version}\nscript sha256 {mine}\npython {sys.version.split()[0]} on {sys.platform}"


def main() -> int:
    check = "--check" in sys.argv
    print(context())
    print()
    bad = []
    for label, args, expected in CASES:
        sent = ask(args)
        ok = sent == expected
        if not ok:
            bad.append(f"{label}: sent {sent!r}, expected {expected!r}")
        print(f"{'ok ' if ok else 'MOVED'} {label:<24} {sent}")
    print(f"\n{len(CASES) - len(bad)}/{len(CASES)} request lines as recorded")

    # --- what the client negotiates, and what that does to the byte column ---
    print()
    axis = []
    plain_head = ask_head(["http://127.0.0.1:{port}/v1/me"])
    default = header_of(plain_head, "accept-encoding")
    # `None` is the reading that matters: a client that sends no `accept-encoding`
    # gives the server no licence to encode, so `%{size_download}` is the object's
    # own length and rows taken that way are comparable with each other.
    axis.append(("no flag", default,
                 "no accept-encoding sent" if default is None
                 else f"accept-encoding: {default}"))
    ok_default = default is None
    if not ok_default:
        bad.append(f"no flag: the client sent accept-encoding {default!r}, so a "
                   "byte column taken without the flag is a wire count under a "
                   "negotiated encoding and is not comparable with a plain one")

    comp_head = ask_head(["--compressed", "http://127.0.0.1:{port}/v1/me"])
    comp = header_of(comp_head, "accept-encoding")
    ok_comp = bool(comp) and "gzip" in comp
    if not ok_comp:
        bad.append(f"--compressed: accept-encoding {comp!r}, expected one naming gzip")
    axis.append(("--compressed", comp, "names gzip" if ok_comp else "MOVED"))

    gz_size, gz_served = size_reported_by_curl(["http://127.0.0.1:{port}/v1/me"])
    comp_size, comp_served = size_reported_by_curl(
        ["--compressed", "http://127.0.0.1:{port}/v1/me"])
    # The question the ladder's `size` column rests on: what does the reported
    # number count? The object is 1024 bytes, served gzipped as gz_served bytes.
    # A client that counts the entity reports 1024; one that counts what the
    # content coding left reports the gzip length.
    content_counted = gz_served < len(PLAIN_BODY) and gz_size == gz_served
    if not content_counted:
        bad.append(f"size_download {gz_size} against {gz_served} body bytes served "
                   f"of an encoded {len(PLAIN_BODY)}-byte object: the byte column is "
                   "not a count of the content coding, and what it counts is unknown")
    axis.append(("size_download", f"{gz_size}",
                 "the content-coded length" if content_counted else "MOVED"))
    axis.append(("--compressed size", f"{comp_size}",
                 f"unchanged; served {comp_served}"))
    for label, value, verdict in axis:
        print(f"{'ok ' if 'MOVED' not in verdict else 'MOVED'} encoding {label:<20}"
              f" {str(value):<34} {verdict}")

    # Where on the decoding chain that count sits, which the first answer
    # published for it got wrong: it is NOT the wire. Chunked framing multiplies
    # the bytes served without moving the entity, so a client that folded
    # transfer decoding in reports the entity's own length for both framings,
    # and one that counted the wire would report the framed length for the second.
    print()
    transfer = transfer_axis()
    plain_row = next(r for r in transfer if r[0] == "content-length")
    chunk_row = next(r for r in transfer if r[0] == "chunked")
    transfer_folded_in = (plain_row[1] == chunk_row[1]
                          == f"{len(PLAIN_BODY)} reported")
    if not transfer_folded_in:
        bad.append(f"transfer framing moved the byte column: {plain_row} against "
                   f"{chunk_row}. If chunk framing is counted, `transfer-encoding` "
                   "is a second condition the record must carry")
    for label, reported, served in transfer:
        print(f"{'ok ' if transfer_folded_in else 'MOVED'}  transfer {label:<20}"
              f" {reported:<14} {served}")
    print(f"the byte column is the entity AFTER transfer decoding and BEFORE content"
          f" decoding: {plain_row[2]} and {chunk_row[2]} are the same entity and both"
          f" report {plain_row[1].split()[0]}, while the same entity served gzipped"
          f" reports {gz_size} for a body that content-decodes to {len(PLAIN_BODY)} B."
          " So the condition the ladder's `content_encoding` column must carry is the"
          " CONTENT coding; the transfer coding is folded in and is not a second one")
    # What this probe does NOT measure, said here rather than left to be found:
    # the listener is the same machine, so it measures the client and nothing
    # about any wall; a client whose behaviour depends on the server's response
    # (a protocol downgrade, an authentication challenge) is not exercised here.
    # Nor does it settle which encoding a wall CHOOSES when it is offered several:
    # the listener here serves gzip only, and the question those cells answer is
    # what the client puts on the wire, not what any server answers with.
    for line in bad:
        print(f"MOVED  {line}")
    return 1 if (check and bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
