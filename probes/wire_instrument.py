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
CASES = [
    ("url-with-fragment", ["http://127.0.0.1:%d/v1#x"],
     "GET /v1 HTTP/1.1"),
    ("target-with-fragment", ["--request-target", "/v1#x", "http://127.0.0.1:%d/"],
     "GET /v1#x HTTP/1.1"),
    ("target-fragment-slash", ["--request-target", "/v1#/me", "http://127.0.0.1:%d/"],
     "GET /v1#/me HTTP/1.1"),
    ("target-fragment-query", ["--request-target", "/v1#?x=1", "http://127.0.0.1:%d/"],
     "GET /v1#?x=1 HTTP/1.1"),
    ("target-absolute-form",
     ["--request-target", "http://example.com/v1/me", "http://127.0.0.1:%d/"],
     "GET http://example.com/v1/me HTTP/1.1"),
    ("target-no-scheme",
     ["--request-target", "example.com/v1/me", "http://127.0.0.1:%d/"],
     "GET example.com/v1/me HTTP/1.1"),
    ("target-percent-encoded", ["--request-target", "/v1%23x", "http://127.0.0.1:%d/"],
     "GET /v1%23x HTTP/1.1"),
]


def ask(args: list[str]) -> str:
    """One request against a loopback listener; return the request line."""
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(1)
    line = []

    def serve():
        conn, _ = srv.accept()
        first = conn.recv(8192).split(b"\r\n", 1)[0]
        line.append(first.decode("latin-1"))
        conn.sendall(b"HTTP/1.1 204 No Content\r\ncontent-length: 0\r\n\r\n")
        conn.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    cmd = ["curl", "-s", "-o", "/dev/null"] + [a % port if "%d" in a else a for a in args]
    subprocess.run(cmd, capture_output=True, timeout=15)
    t.join(timeout=5)
    srv.close()
    return line[0] if line else ""


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
    # What this probe does NOT measure, said here rather than left to be found:
    # the listener is the same machine, so it measures the client and nothing
    # about any wall; a client whose behaviour depends on the server's response
    # (a protocol downgrade, an authentication challenge) is not exercised here.
    for line in bad:
        print(f"MOVED  {line}")
    return 1 if (check and bad) else 0


if __name__ == "__main__":
    raise SystemExit(main())
