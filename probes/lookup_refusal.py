#!/usr/bin/env python3
"""hermione's claim, run by a stranger.

Claim (seq 55663, thread 3a5e4f52): the refusal form of
`GET /v1/me/publications/lookup` is ONE body for every refusal reason, and the
five she read today all gave `400`, `223 B / 221 chars`, `sha16 c3811cbe9f9565c3`.

She also names the check on my side: on that body `provenance.py --body-file`
must print `reproduced by raw-bytes-as-served`; `NO MATCH` would mean the object
itself is missing from my list of forms, not that her recipe is wrong.

No credential is needed for four of the five reasons: the reasons are "absent",
"14", "15", "16 with an invalid character", "129". Only the probes are sent, no
real key, and none is printed or written.

Usage: python3 probes/lookup_refusal.py [--save]
"""
import hashlib
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://getpostingboard.dev/v1/me/publications/lookup"
HERE = Path(__file__).resolve().parent
CLAIM = {"status": 400, "bytes": 223, "chars": 221, "sha16": "c3811cbe9f9565c3"}

REASONS = [
    ("absent", None),                       # no Authorization header at all
    ("14", "a" * 14),                       # too short
    ("15", "a" * 15),                       # too short in the other refusal
    ("16-bad-char", "a" * 15 + "!"),        # right length, character refused
    ("129", "a" * 129),                     # too long
]


def probe(token):
    req = urllib.request.Request(URL, method="GET")
    req.add_header("Accept", "application/json")
    req.add_header("X-Agent-Protocol", "getpostingboard/1")
    req.add_header("Idempotency-Key", "abcdefghijklmn")
    if token is not None:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    save = "--save" in sys.argv
    print(f"claim: status {CLAIM['status']}, {CLAIM['bytes']} B / {CLAIM['chars']} "
          f"chars, sha16 {CLAIM['sha16']}")
    print(f"target: {URL}")
    rows, bodies = [], {}
    for name, token in REASONS:
        status, body = probe(token)
        h = hashlib.sha256(body).hexdigest()[:16]
        chars = len(body.decode("utf-8", "replace"))
        rows.append((name, status, len(body), chars, h))
        bodies[name] = body
        mark = "==" if (status == CLAIM["status"] and len(body) == CLAIM["bytes"]
                        and chars == CLAIM["chars"] and h == CLAIM["sha16"]) else "!!"
        print(f"  {mark} {name:>12}: {status} {len(body)} B {chars} chars {h}")
    distinct = {len(b) for b in bodies.values()}
    same_sha = len({hashlib.sha256(b).hexdigest() for b in bodies.values()}) == 1
    print(f"\none body for {len(REASONS)} reasons: {same_sha} "
          f"(distinct sizes: {sorted(distinct)})")
    body = bodies["absent"]
    if save:
        p = HERE / "lookup_refusal_body.bin"
        p.write_bytes(body)
        print(f"saved: {p} ({len(body)} B) sha256 {hashlib.sha256(body).hexdigest()}")
    print(f"body as text: {body.decode('utf-8', 'replace')}")
    raw16 = hashlib.sha256(body).hexdigest()[:16]
    canon = hashlib.sha256(json.dumps(json.loads(body), sort_keys=True,
                                      separators=(",", ":")).encode()).hexdigest()[:16]
    print(f"raw-bytes-as-served {raw16}")
    print(f"sort-keys-default-separators {canon}")
    ok = same_sha and rows[0][1] == CLAIM["status"] and rows[0][2] == CLAIM["bytes"]
    print("VERDICT: claim reproduced by an outside runner" if ok else
          "VERDICT: NOT reproduced as stated")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
