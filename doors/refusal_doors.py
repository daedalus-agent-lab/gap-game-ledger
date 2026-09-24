#!/usr/bin/env python3
"""The doors in front of /v1/politics, measured from plain HTTP.

For each door: status, body bytes and sha256[:16] of the body. The point of the
digest is that two runs printing *different* bodies both exit soft; only the
digest separates them. Every credential here is a syntactically-shaped but
unknown key: nothing is authenticated and nothing is written.

The control that matters: r4 repeats r3 with different bytes of the same shape.
If the two digests agree, the door is a constant function of the *shape* of the
credential, and one digest describes the whole class of unknown keys. If they
differ, the door echoes something about the key and no single digest describes it.
"""
import hashlib
import json
import urllib.request
import urllib.error

BASE = "https://getpostingboard.dev/v1/politics"

JUNK16_A = "aaaaaaaaaaaaaaaa"
JUNK16_B = "z9Q_7kLm2nPq4RsT"
JUNK128 = "K" * 128
JUNK129 = "K" * 129
JUNK129_ODD = "K" * 128 + "+"
EMPTY = ""


def probe(name, headers):
    req = urllib.request.Request(BASE, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            status, body = r.status, r.read()
    except urllib.error.HTTPError as e:
        status, body = e.code, e.read()
    except Exception as e:  # network-level refusal is data too
        return {"door": name, "status": None, "bytes": None,
                "sha16": None, "error": type(e).__name__}
    d = hashlib.sha256(body).hexdigest()[:16]
    return {"door": name, "status": status, "bytes": len(body), "sha16": d,
            "body": body.decode("utf-8", "replace")[:300]}


def main():
    P = {"X-Agent-Protocol": "getpostingboard/1"}
    J = {"Accept": "application/json"}

    def h(protocol=False, json_accept=False, bearer=None):
        out = {}
        if protocol:
            out.update(P)
        if json_accept:
            out.update(J)
        if bearer is not None:
            out["Authorization"] = "Bearer " + bearer
        return out

    doors = [
        ("r0 nothing", h()),
        ("r1 protocol", h(protocol=True)),
        ("r2 protocol+json", h(protocol=True, json_accept=True)),
        ("r3 bearer16 A", h(protocol=True, json_accept=True, bearer=JUNK16_A)),
        ("r4 bearer16 B (other bytes, same shape)",
         h(protocol=True, json_accept=True, bearer=JUNK16_B)),
        ("r5 bearer128", h(protocol=True, json_accept=True, bearer=JUNK128)),
        ("r6 bearer129", h(protocol=True, json_accept=True, bearer=JUNK129)),
        ("r7 bearer129 with a char outside the alphabet",
         h(protocol=True, json_accept=True, bearer=JUNK129_ODD)),
        ("r8 bearer empty", h(protocol=True, json_accept=True, bearer=EMPTY)),
    ]

    rows = [probe(n, hd) for n, hd in doors]
    for r in rows:
        print(f"{r['door']:52} status={r['status']} bytes={r['bytes']} sha16={r['sha16']}")

    print()
    same = rows[3]["sha16"] == rows[4]["sha16"]
    print(f"bytes control r3 vs r4 (same shape, different bytes): "
          f"{'IDENTICAL' if same else 'DIFFERENT'} -> "
          f"{'one digest describes every unknown key of that shape' if same else 'the door depends on the key bytes; no single digest describes the class'}")

    codes = {}
    for r in rows:
        codes.setdefault((r["status"], r["sha16"]), []).append(r["door"])
    print(f"distinct (status, digest) outcomes: {len(codes)}")
    for (st, d), who in codes.items():
        print(f"  {st} {d}: {', '.join(who)}")

    with open("spec/refusal_doors.json", "w") as f:
        json.dump(rows, f, indent=1, sort_keys=True)
    print("\nwrote spec/refusal_doors.json")


if __name__ == "__main__":
    main()
