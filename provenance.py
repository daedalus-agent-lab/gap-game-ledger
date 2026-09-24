#!/usr/bin/env python3
"""Which named function produced this digest?

A digest is only comparable to another digest when both name the function that
produced them. This tool takes the bytes and the number and answers with the
names, out of a published list, whose run on those bytes yields that number --
or says NO MATCH, bounded by that list.

    python3 provenance.py --body-file body.bin --digest e22142089a2defa0
    python3 provenance.py --selftest

NO MATCH is not "the number is wrong". It means no function on this list
produced it; the list is the division below which this tool is blind, and the
tool prints it with every verdict.

The list is deliberately small and printed in full by --list. Add a form only
with the bytes it was checked against.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys

DIGEST_CHARS = 16


def sha16(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()[:DIGEST_CHARS]


def _loads(b: bytes):
    return json.loads(b.decode("utf-8"))


# Each form is (name, function over the raw served bytes). The name says the
# recipe; a reader re-runs it, not trusts it.
FORMS = {
    "raw-bytes-as-served": lambda b: b,
    "gpb-json-c14n/1": lambda b: json.dumps(
        _loads(b), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"),
    "sort-keys-default-separators": lambda b: json.dumps(_loads(b), sort_keys=True).encode("utf-8"),
    "as-written-default-separators": lambda b: json.dumps(_loads(b)).encode("utf-8"),
    "sort-keys-separators-indent-2": lambda b: json.dumps(
        _loads(b), sort_keys=True, separators=(",", ": "), indent=2
    ).encode("utf-8"),
    "message-field-only": lambda b: _loads(b)["error"]["message"].encode("utf-8"),
    "sort-keys-separators-ensure-ascii-True": lambda b: json.dumps(
        _loads(b), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8"),
}

# A form is a dial only where it moves the bytes. ensure_ascii is a dial on a
# body carrying non-ASCII and is not one on an ASCII-only body, where both
# settings give the same number: two forms, one answer, and the difference
# between them is a question about the object, not about the function.

FIXTURE = (
    b'{"error":{"code":"NOT_FOUND","message":"Unknown route or method. '
    b'See /openapi.json."},"docs":"https://getpostingboard.dev/skill.md"}'
)
FIXTURE_EXPECTED = {
    "raw-bytes-as-served": "e22142089a2defa0",
    "gpb-json-c14n/1": "568b6312c5c8a466",
    "sort-keys-separators-ensure-ascii-True": "568b6312c5c8a466",
    "sort-keys-default-separators": "97d5a79e56fb35a8",
    "as-written-default-separators": "6f28e3653ef4cbab",
}

# The recipe for obtaining an object is part of the receipt, beside the digest
# and the function: a digest over bytes nobody can obtain is unverifiable by
# construction, and that is a fact about the object, not a missing check.
FIXTURE_RECIPE = "GET /v1/nope without a key, first 132 bytes of the body as served"


def forms_for(body: bytes) -> dict[str, str]:
    """Every form in the list, run on these bytes, name -> sha16."""
    out = {}
    for name, fn in FORMS.items():
        try:
            out[name] = sha16(fn(body))
        except Exception as exc:  # a form that cannot parse these bytes is not a form here
            out[name] = f"cannot-apply ({type(exc).__name__})"
    return out


def reproduces(body: bytes, digest: str) -> list[str]:
    """The names whose run on these bytes gives this digest. Empty is NO MATCH."""
    d = digest.strip().lower()
    return sorted(n for n, v in forms_for(body).items() if v == d)


def selftest() -> int:
    bad = 0
    got = forms_for(FIXTURE)
    for name, want in FIXTURE_EXPECTED.items():
        ok = got.get(name) == want
        print(f"{'ok  ' if ok else 'FAIL'} {name:34s} {got.get(name)} (expected {want})")
        bad += 0 if ok else 1
    hits = reproduces(FIXTURE, FIXTURE_EXPECTED["raw-bytes-as-served"])
    ok = hits == ["raw-bytes-as-served"]
    print(f"{'ok  ' if ok else 'FAIL'} lookup of {FIXTURE_EXPECTED['raw-bytes-as-served']}: {hits}")
    bad += 0 if ok else 1
    a = got.get("gpb-json-c14n/1")
    b = got.get("sort-keys-separators-ensure-ascii-True")
    ok = a == b and a is not None
    print(f"{'ok  ' if ok else 'FAIL'} ensure_ascii is not a dial on an ASCII body: {a} == {b}")
    bad += 0 if ok else 1
    print(f"object recipe: {FIXTURE_RECIPE}")
    miss = reproduces(FIXTURE, "0000000000000000")
    ok = miss == []
    print(f"{'ok  ' if ok else 'FAIL'} lookup of an unknown digest: {miss or 'NO MATCH'}")
    bad += 0 if ok else 1
    print(f"\nforms tried: {len(got)}  ->  NO MATCH is bounded by this list, not by all functions")
    return 1 if bad else 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--body-file", help="the bytes as served")
    p.add_argument("--digest", help="the digest to look for, 16 hex chars of sha256")
    p.add_argument("--list", action="store_true", help="print every form and its digest for the bytes")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)

    if a.selftest:
        return selftest()
    if not a.body_file:
        p.error("--body-file is required unless --selftest")
    body = open(a.body_file, "rb").read()
    got = forms_for(body)
    if a.list or not a.digest:
        print(f"bytes {len(body)}")
        for name, v in sorted(got.items()):
            print(f"  {name:34s} {v}")
        print(f"forms tried: {len(got)}")
        return 0
    hits = reproduces(body, a.digest)
    if hits:
        print(f"{a.digest}: reproduced by {', '.join(hits)}  ({len(got)} forms tried)")
        print(f"  object: {len(body)} bytes as served; a receipt is (digest, function, object)")
        return 0
    print(f"{a.digest}: NO MATCH among {len(got)} forms tried")
    print("  this is a bound of the list, not a verdict about the number")
    return 2


if __name__ == "__main__":
    sys.exit(main())
