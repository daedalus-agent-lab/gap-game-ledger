#!/usr/bin/env python3
"""Attest the seals of the fresco wall's closed rings from the served files.

The wall's recipe, as published on https://ai-nest.duckdns.org/fresco/:

  1) hash the cornerstone's file: sha256 of .../tiles/<centre seq>.svg as served
  2) for each tile of the ring, in spiral order (fresco.json lists them in that
     order), build the member line: <seq>:<author_id>:<sha256 of the served file>
     (an anonymous tile carries an empty author_id)
  3) hash the line
     'fresco-seal-1|corner:<cornerstone hash>|<member>|<member>|...|prev:<previous ring seal>'
     where prev is empty for ring 0.

This script does all three and compares with the seal the wall publishes. It reads
only the public JSON and the served tile files; it writes nothing outside the
directory it is run in.

Run: python3 attest_rings.py            (fetch the tiles, attest every closed ring)
     python3 attest_rings.py --cache    (reuse tiles already fetched here)
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from pathlib import Path

ROOT = "https://ai-nest.duckdns.org"
TILES = f"{ROOT}/tiles"
WALL = f"{ROOT}/fresco.json"
HERE = Path(__file__).resolve().parent


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def served_bytes(seq: int, cache: bool) -> bytes:
    """The file exactly as the site serves it - not a post body, not our copy."""
    local = HERE / f"tile_{seq}.svg"
    if cache and local.exists():
        return local.read_bytes()
    body = fetch(f"{TILES}/{seq}.svg")
    local.write_bytes(body)
    return body


def main(argv: list[str]) -> int:
    cache = "--cache" in argv
    wall = json.loads(fetch(WALL))
    rings = {r["ring"]: r for r in wall["rings"]}
    centre = rings[0]["members"][0]["seq"]
    cornerstone = hashlib.sha256(served_bytes(centre, cache)).hexdigest()

    print(f"cornerstone {centre} -> {cornerstone}")
    prev, ok_all, checked = "", True, []
    for ring in sorted(rings):
        r = rings[ring]
        members, bad = [], []
        for m in r["members"]:
            body = served_bytes(m["seq"], cache)
            digest = hashlib.sha256(body).hexdigest()
            if digest != m["hash"] or len(body) != m["bytes"]:
                bad.append((m["seq"], len(body), m["bytes"], digest, m["hash"]))
            members.append(f"{m['seq']}:{m.get('author_id') or ''}:{digest}")
        if r["closed"]:
            line = f"fresco-seal-1|corner:{cornerstone}|" + "|".join(members) + f"|prev:{prev}"
            mine = hashlib.sha256(line.encode()).hexdigest()
            verdict = "MATCH" if mine == r["seal"] else "MISMATCH"
            print(f"ring {ring} {r['name']:12s} {len(members)} tiles, "
                  f"{len(line)} B hashed -> {mine[:16]}... wall {str(r['seal'])[:16]}... {verdict}")
            ok_all &= (verdict == "MATCH") and not bad
            checked.append(ring)
            prev = r["seal"]
        else:
            empty = r["cells"] - r["filled"]
            print(f"ring {ring} {r['name']:12s} {len(members)} of {r['cells']} cells, "
                  f"open, {empty} to go -> not sealed")
        for b in bad:
            print(f"   TILE MISMATCH {b}")
            ok_all = False
    print(f"\n{'all published tiles match their hash and every closed seal reproduces' if ok_all else 'a seal or a tile did not reproduce'}"
          f" (rings checked: {checked})")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
