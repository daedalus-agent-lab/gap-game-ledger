#!/usr/bin/env python3
"""Ask the ledger about an address before writing to it.

The ledger already records, per entry, the address the finding was filed against
(`address`), and it records the findings it declined or withdrew in `declined`,
keyed by the same kind of address. Both lists are in one file and neither was ever
queried before a reply was posted -- so a claim withdrawn as refuted was restated
in the thread it was withdrawn from, three weeks later, by its own author.

    python3 pre_post.py <address>       # what does the ledger say about this address?
    python3 pre_post.py --selftest      # the tool finds the known withdrawal

Exit 0 when the address is clean, 1 when the ledger holds a withdrawal or a
declined finding against it. A clean answer is not permission to post and not a
claim that the ledger is complete: it is the one query that exists to be run.
"""

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE / "catches.json"

# The address this tool exists for: a withdrawal whose own author later restated
# the claim in the thread it was withdrawn from. Named here so the tool's ability
# to find it is a test rather than a sentence.
KNOWN_WITHDRAWAL = "011070f9-ec73-4bd5-b764-aa4b710e622b"


def load() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def about(data: dict, address: str) -> tuple[list, list]:
    """(declined/withdrawn rows, live entries) filed against this address."""
    closed = [d for d in data.get("declined", []) if d.get("address") == address]
    live = [e for e in data.get("entries", []) if e.get("address") == address]
    return closed, live


def report(address: str) -> int:
    data = load()
    closed, live = about(data, address)
    print(f"address {address}")
    if not closed and not live:
        print("  the ledger holds nothing against it")
        print("  (clean, not permission: this checks one file, and the file is not "
              "the world)")
        return 0
    for row in closed:
        print(f"  CLOSED gate={row.get('gate', '?')} class={row.get('class', '?')}")
        reason = (row.get("reason") or "").strip()
        if reason:
            print("    " + reason[:600].replace("\n", "\n    "))
    for entry in live:
        print(f"  LIVE   class={entry.get('class', '?')} "
              f"first_seen={entry.get('first_seen', '?')}")
        for field in ("promise", "fact"):
            if entry.get(field):
                print(f"    {field}: {str(entry[field])[:200]}")
    if closed:
        print("\n  A CLOSED row means the finding was declined or withdrawn. Read the "
              "reason before\n  restating anything about this address: the claim may "
              "already be refuted, and\n  the refutation is the entry's own.")
        return 1
    return 0


def selftest() -> int:
    """The tool must find the known withdrawal, and must not invent one."""
    data = load()
    closed, _live = about(data, KNOWN_WITHDRAWAL)
    if not closed:
        print(f"RED  the known withdrawal {KNOWN_WITHDRAWAL} is not found")
        return 1
    if closed[0].get("gate") != "WITHDRAWN":
        print(f"RED  found it, but gate is {closed[0].get('gate')!r}, not WITHDRAWN")
        return 1
    # And the negative: an address the ledger has never seen must come back empty,
    # or the tool answers "closed" to everything and its warning means nothing.
    absent = "00000000-0000-0000-0000-000000000000"
    if about(data, absent)[0]:
        print("RED  an address the ledger has never seen came back closed")
        return 1
    print(f"ok   the known withdrawal is found (gate WITHDRAWN, "
          f"class {closed[0].get('class')})")
    print("ok   an unseen address comes back empty")
    print("2/2 selftest checks hold")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("address", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.address:
        ap.error("give an address, or --selftest")
    return report(args.address)


if __name__ == "__main__":
    sys.exit(main())
