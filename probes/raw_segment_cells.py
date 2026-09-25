"""Independent cells for the raw-segment question: one request per cell, sha16 over the body."""
import hashlib
import http.client
import sys

HOST = "getpostingboard.dev"
CELLS = [
    ("/%76%31/me", "none"),
    ("/%76%31/me", "proto+json"),
    ("/v1;x/me", "none"),
    ("/v1;x/me", "proto+json"),
    ("/v1/./me", "none"),
    ("/v1/%2e/me", "none"),
    ("/v1/nope/../me", "none"),
    ("/api/v1/me", "none"),
    ("//v1/me", "none"),
    ("/%61pi/v1/me", "none"),
    ("/v1/me", "none"),
    ("/v1/nope", "none"),
]


def one(path, headers):
    conn = http.client.HTTPSConnection(HOST, timeout=20)
    h = {"User-Agent": "cell-probe/1"}
    if headers == "proto+json":
        h["X-Agent-Protocol"] = "getpostingboard/1"
        h["Accept"] = "application/json"
    conn.request("GET", path, headers=h)
    r = conn.getresponse()
    body = r.read()
    conn.close()
    return r.status, len(body), hashlib.sha256(body).hexdigest()[:16]


if __name__ == "__main__":
    for path, hdr in CELLS:
        try:
            st, n, d = one(path, hdr)
            print(f"{path:<16} {hdr:<10} {st} {n:<6} {d}")
        except Exception as exc:
            print(f"{path:<16} {hdr:<10} ERROR {type(exc).__name__}: {exc}")
