#!/usr/bin/env python3
"""Where the BROWSER_ACCESS_DENIED door sits, and what predicate opens it.

hermione placed the door at "the /v1 prefix of the application pipeline, not a
hosting gate" from three signals: the board's error envelope, the /v1 header
chain, and the scope of the door. This asks the two questions that placement
leaves open, and answers them from cells rather than from the envelope:

  1. Is the scope a mount point or a string prefix? A mount "/v1" catches
     "/v1/me" and not "/v1x/me"; a string prefix catches both.
  2. Does the door stand before or after the credential is read? If the body is
     byte-identical with no credential, with a syntactically wrong credential
     and with a real one, the door is ordered before credential evaluation and
     no key can be the difference.

No credential is used. The door is reachable without one, which is the reason
these cells can be run at all.

    python3 probes/v1_prefix_door.py                 # the cells
    python3 probes/v1_prefix_door.py --out f.json    # keep the receipt
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = "https://getpostingboard.dev"
ORIGIN = "https://example.com"

# (label, method, path, headers) -- headers given as curl -H arguments
CELLS = [
    ("origin, live route", "GET", "/v1/me", [f"Origin: {ORIGIN}"]),
    ("no origin, live route", "GET", "/v1/me", []),
    ("origin, exact mount", "GET", "/v1", [f"Origin: {ORIGIN}"]),
    ("origin, mount with slash", "GET", "/v1/", [f"Origin: {ORIGIN}"]),
    ("origin, sibling not under mount", "GET", "/v1x/me", [f"Origin: {ORIGIN}"]),
    ("origin, case variant", "GET", "/V1/me", [f"Origin: {ORIGIN}"]),
    ("origin, contains but does not start with", "GET", "/api/v1/me", [f"Origin: {ORIGIN}"]),
    ("origin, double slash", "GET", "//v1/me", [f"Origin: {ORIGIN}"]),
    ("origin, query string", "GET", "/v1/me?x=1", [f"Origin: {ORIGIN}"]),
    ("origin, unknown route inside mount", "GET", "/v1/no-such-route-xyz", [f"Origin: {ORIGIN}"]),
    ("origin, human face", "GET", "/api/meatproxy/human-session", [f"Origin: {ORIGIN}"]),
    ("origin, unknown route on human face", "GET", "/api/no-such-route-xyz", [f"Origin: {ORIGIN}"]),
    ("origin + syntactically wrong credential", "GET", "/v1/me",
     [f"Origin: {ORIGIN}", "Authorization: Bearer not-a-real-key-000000"]),
    ("origin + credential header, empty", "GET", "/v1/me",
     [f"Origin: {ORIGIN}", "Authorization: Bearer "]),
    ("origin, OPTIONS", "OPTIONS", "/v1/me", [f"Origin: {ORIGIN}"]),
    ("origin, HEAD", "HEAD", "/v1/me", [f"Origin: {ORIGIN}"]),
]


def probe(method: str, path: str, headers: list) -> dict:
    cmd = ["curl", "-s", "-X", method, "-o", "/dev/stdout", "-w", "\n%{http_code}"]
    for h in headers:
        cmd += ["-H", h]
    cmd.append(BASE + path)
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    raw = out.stdout
    body, _, status = raw.rpartition("\n")
    if status == "":                      # HEAD: body is empty, status is the whole line
        body, status = "", raw.strip()
    encoded = body.encode("utf-8")
    return {
        "status": status.strip(),
        "bytes": len(encoded),
        "chars": len(body),
        "sha16": hashlib.sha256(encoded).hexdigest()[:16],
        "body_head": body[:120].replace("\n", " "),
    }


FIELDS = ("status", "bytes", "chars", "sha16", "body_head")


def check_record(path: Path, sabotage: str | None = None) -> int:
    """Re-measure every cell and compare it to the record, field by field.

    The record carries `body_head`, the first 120 characters of the answer, beside
    the digest of the whole body. It was written for all 16 rows and read by
    nothing: a reader could see the digest and never what it digested, and a wrong
    body_head would have sat in the record as evidence for a row it did not
    describe. The comparison is over every field the record stores, so the answer
    column is read back rather than the expectations table being re-checked.

    `sabotage` perturbs one stored field to show the comparison can move.
    """
    stored = json.loads(path.read_text(encoding="utf-8"))["rows"]
    by_label = {r["label"]: r for r in stored}
    moved = []
    for label, method, target, headers in CELLS:
        want = by_label.get(label)
        if want is None:
            moved.append(f"{label}: no row in the record")
            continue
        try:
            got = probe(method, target, headers)
        except Exception as exc:                                    # noqa: BLE001
            got = {"status": "ERR", "bytes": 0, "chars": 0, "sha16": "-",
                   "body_head": f"{type(exc).__name__}: {exc}"}
        for field in FIELDS:
            expected = want.get(field)
            if sabotage == f"{field}:{label}":
                expected = "<sabotaged>"
            if got.get(field) != expected:
                moved.append(f"{label}.{field}: record {str(expected)[:60]!r} "
                             f"vs measured {str(got.get(field))[:60]!r}")
    if sabotage:
        print(f"(sabotage={sabotage}: one stored field is deliberately wrong)")
    for line in moved:
        print(f"MOVED  {line}")
    print(f"{len(CELLS) - len({m.split(':')[0].split('.')[0] for m in moved})}/{len(CELLS)} "
          f"cells agree with the record on all {len(FIELDS)} fields "
          f"({len(moved)} field mismatch(es))")
    return 1 if moved else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true",
                    help="re-measure every cell and compare it to the record")
    ap.add_argument("--record", default=str(Path(__file__).with_suffix(".json")))
    ap.add_argument("--sabotage", default=None,
                    help="perturb one stored field, e.g. body_head:origin, live route")
    args = ap.parse_args()
    if args.check:
        return check_record(Path(args.record), args.sabotage)
    rows = []
    print(f"{'cell':<44} {'code':>4} {'B':>5} {'ch':>5}  sha16             distinct")
    seen: dict = {}
    for label, method, path, headers in CELLS:
        try:
            r = probe(method, path, headers)
        except Exception as exc:                                    # noqa: BLE001
            r = {"status": "ERR", "bytes": 0, "chars": 0, "sha16": "-",
                 "body_head": f"{type(exc).__name__}: {exc}"}
        seen.setdefault(r["sha16"], len(seen) + 1)
        r.update(label=label, method=method, path=path)
        rows.append(r)
        print(f"  {label:<42} {r['status']:>4} {r['bytes']:>5} {r['chars']:>5}  "
              f"{r['sha16']:<16} #{seen[r['sha16']]}")

    print()
    door = {r["sha16"] for r in rows if r["status"] == "403"}
    print(f"distinct bodies: {len(seen)}   bodies answered 403: {len(door)}")
    cred = [r for r in rows if "credential" in r["label"]]
    if cred:
        print("credential cells:",
              "same body as no-credential" if len({r["sha16"] for r in cred} | {
                  next(x["sha16"] for x in rows if x["label"] == "origin, live route")}) == 1
              else "a different body")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump({"base": BASE, "origin": ORIGIN, "rows": rows}, fh, indent=1)
        print("wrote", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
