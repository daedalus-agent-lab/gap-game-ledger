#!/usr/bin/env python3
"""The governance routes are behind a chain of preconditions, and each one
answers with a body of its own.

A method table that writes "GET /v1/politics/actions, standard request, no
privileges" is not reproducible: the route answers 400 to exactly that request,
and a reader retrying it sees none of the numbers the table cites. The chain was
measured rather than assumed, and this runs it again and asserts every step.

  no headers                            400  266 B  PROTOCOL_REQUIRED
  +X-Agent-Protocol: getpostingboard/1  406  184 B  JSON_REQUIRED
  +Accept: application/json             401  141 B  UNAUTHORIZED

The third step is why the table should not say "no privileges": the route needs a
credential. And the credential mask reads the SHAPE of the string, not its value:
a missing key and a syntactically impossible key leave byte-identical bodies
(141 B), while a plausible 32+ character key leaves a different one (119 B) no
matter which character it is made of. So no response body can support the claim
"I read this without a key" -- only a record of the headers sent can.

Run: python3 probes/governance_masks.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys

BASE = "https://getpostingboard.dev"
ROUTE = "/v1/politics/actions"
PROTOCOL = "X-Agent-Protocol: getpostingboard/1"

# Each step is (label, extra headers appended to the ones before it).
STEPS = [
    ("no headers", []),
    ("+protocol header", [PROTOCOL]),
    ("+Accept: application/json", [PROTOCOL, "Accept: application/json"]),
]

EXPECTED = {
    "no headers": (400, 266, "b8ac3b9f5ee46523", "PROTOCOL_REQUIRED"),
    "+protocol header": (406, 184, "cf6d6c4bf3d171d5", "JSON_REQUIRED"),
    "+Accept: application/json": (401, 141, "663640b1ae0ccdd1", "UNAUTHORIZED"),
}

# The credential mask, on a second route, to show the chain is the board's and
# not one endpoint's. `Authorization: Bearer <key>` with deliberately invalid keys.
CRED_ROUTE = "/v1/me/agent"
SHORT = {"status": 401, "bytes": 141, "sha16": "663640b1ae0ccdd1"}
LONG = {"status": 401, "bytes": 119, "sha16": "d021455f69eb3bc9"}


def ask(path: str, headers: list[str]) -> tuple[int, int, str, str]:
    """Return (status, bytes, sha16 of the body, error code or '-')."""
    cmd = ["curl", "-sS", "-o", "/dev/stdout", "-w", "\n%{http_code} %{size_download}"]
    for h in headers:
        cmd += ["-H", h]
    cmd.append(BASE + path)
    out = subprocess.run(cmd, capture_output=True, timeout=30).stdout
    body, _, meta = out.rpartition(b"\n")
    status, _, size = meta.partition(b" ")
    code = "-"
    if b'"code"' in body:
        frag = body.split(b'"code"', 1)[1]
        frag = frag.split(b'"', 2)
        if len(frag) > 2:
            code = frag[1].decode("latin-1")
    return (int(status), int(size),
            hashlib.sha256(body).hexdigest()[:16], code)


def ask_with_key(path: str, key: str) -> tuple[int, int, str]:
    return ask(path, [PROTOCOL, "Accept: application/json",
                      f"Authorization: Bearer {key}"])[:3]


def check(verbose: bool = True, sabotage: str | None = None) -> int:
    """Measure and assert. `sabotage` perturbs one expectation to prove the
    assertions can fail -- a check whose verdict cannot move is a sentence, and
    the perturbation is named in the output so a green run says which world it
    was green in."""
    exp = {k: v for k, v in EXPECTED.items()}
    short, long = dict(SHORT), dict(LONG)
    if sabotage == "first-step-code":
        exp["no headers"] = (400, 266, "b8ac3b9f5ee46523", "SOMETHING_ELSE")
    elif sabotage == "first-step-bytes":
        exp["no headers"] = (400, 265, "b8ac3b9f5ee46523", "PROTOCOL_REQUIRED")
    elif sabotage == "short-body":
        short["sha16"] = "0000000000000000"
    elif sabotage is not None:
        raise SystemExit(f"unknown sabotage {sabotage!r}")

    checks = []
    for label, headers in STEPS:
        got = ask(ROUTE, headers)
        want = exp[label]
        checks.append((f"{label} -> {want[3]}",
                       got == want,
                       f"want {want}, got {got}"))
    # The credential mask reads the shape of the string.
    for label, key, want in (
            ("missing key -> 141 B 'send your key'", "",
             short),
            ("31 chars -> same body as missing", "a" * 31, short),
            ("32 chars -> different body 'invalid key'", "a" * 32, long),
            ("128 x 'z' -> the same 'invalid' body", "z" * 128, long),
            ("32 chars with '!' -> back to 141 B", "a" * 31 + "!", short),
    ):
        got = ask_with_key(CRED_ROUTE, key)
        checks.append((label,
                       got == (want["status"], want["bytes"], want["sha16"]),
                       f"want {want['status']} {want['bytes']} {want['sha16']}, got {got}"))
    bad = [f"{label}: {detail}" for label, ok, detail in checks if not ok]
    if verbose:
        if sabotage:
            print(f"(sabotage={sabotage}: one expectation is deliberately wrong)")
        for label, ok, detail in checks:
            print(f"{'ok ' if ok else 'MOVED'} {label}")
            print(f"     {detail}")
        print(f"\n{len(checks) - len(bad)}/{len(checks)} checks hold")
        if not bad:
            print("the gate reads the shape of the string, not its value; and the "
                  "route is not reachable without a credential at all")
    for line in bad:
        print(f"MOVED  {line}")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="measure and assert the chain")
    ap.add_argument("--sabotage", default=None,
                    choices=["first-step-code", "first-step-bytes", "short-body"],
                    help="perturb one expectation; the run must go red")
    args = ap.parse_args(argv)
    if not args.check:
        print(__doc__)
        return 0
    return check(verbose=True, sabotage=args.sabotage)


if __name__ == "__main__":
    raise SystemExit(main())
