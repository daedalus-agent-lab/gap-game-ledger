#!/usr/bin/env python3
"""Which single header opens the /v1 browser door, and what each one alone buys.

The door is declared in skill.md as Browser Fetch Metadata / Origin / HTML
Accept / UA. Declared together is not the same as required together: this runs
each trigger alone against a live route and prints the body it gets, so the
cheapest trigger and the redundant ones are both readable.

    python3 probes/v1_door_triggers.py
"""
import hashlib
import subprocess

BASE = "https://getpostingboard.dev"
PATH = "/v1/me"
TRIGGERS = [
    ("none (control)", []),
    ("Origin", ["Origin: https://example.com"]),
    ("Sec-Fetch-Mode", ["Sec-Fetch-Mode: navigate"]),
    ("Sec-Fetch-Site", ["Sec-Fetch-Site: cross-site"]),
    ("Accept: text/html", ["Accept: text/html"]),
    ("UA Mozilla", ["User-Agent: Mozilla/5.0 (X11; Linux x86_64)"]),
    ("Accept: text/html,application/json", ["Accept: text/html,application/json"]),
    ("Referer", ["Referer: https://example.com/"]),
    ("X-Requested-With", ["X-Requested-With: XMLHttpRequest"]),
    ("Origin + Accept: application/json", ["Origin: https://example.com",
                                           "Accept: application/json"]),
]


def probe(headers: list) -> dict:
    cmd = ["curl", "-s", "-o", "/dev/stdout", "-w", "\n%{http_code}"]
    for h in headers:
        cmd += ["-H", h]
    cmd.append(BASE + PATH)
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    raw = out.stdout
    body, _, status = raw.rpartition("\n")
    enc = body.encode("utf-8")
    return {"status": status.strip(), "bytes": len(enc), "chars": len(body),
            "sha16": hashlib.sha256(enc).hexdigest()[:16],
            "code": (body[:80].replace("\n", " ") if body else "")}


print(f"{'trigger':<36} {'code':>4} {'B':>5} {'ch':>5}  sha16             error code")
for label, headers in TRIGGERS:
    r = probe(headers)
    code = r["code"].split('"code":"')[-1].split('"')[0] if '"code"' in r["code"] else r["code"][:26]
    print(f"  {label:<34} {r['status']:>4} {r['bytes']:>5} {r['chars']:>5}  {r['sha16']:<16} {code}")
