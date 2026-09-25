#!/usr/bin/env python3
"""Which names the registry registers, and which of them no claim reads.

`fragments.NAMESPACES` maps a lie class to the callables that carry it, and a class's
`probe` is evaluated inside that namespace. A name registered there is a claim that
something exercises it. Nothing checked that claim: the ledger counted DISTINCT
fragments, never READ ones, so a namespace could shelter any number of callables
nothing names -- and both numbers would stay green.

    python3 unread_fragments.py            # list them
    python3 unread_fragments.py --check    # exit 1 when the promise holds or the reading stops discriminating

This probe does NOT restate the rule: it imports `unread_registrations` and
`what_a_registry_without_readers_carries` from `fragments.py`, so the registry the
probe measures is the registry the ledger uses.

WHAT THIS DOES NOT DO: the reading of "read" is by NAME (see the docstring of
`read_names_of_the_claims`); it does not show that a READ fragment is exercised by
the claim that names it, and it says nothing about the two `lang=javascript` entries,
which this registry does not carry.
"""
import argparse
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEDGER = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    frag = load("pg_fragments_unread", LEDGER / "fragments.py")
    counts = frag.what_a_registry_without_readers_carries()
    print(f"namespaces                        {counts['namespaces']}")
    print(f"callable registrations            {counts['registrations']}")
    print(f"distinct objects among them       {counts['distinct_objects']}")
    print(f"claims (entries + repeats)        {counts['claims']}")
    print(f"registrations named by no claim   {counts['unread']}")
    for name in frag.unread_registrations():
        print(f"    unread  {name}")
    if args.check:
        if frag.every_registration_is_read():
            print("REFUSED: nothing is unread, so this probe can no longer fail")
            return 1
        if counts["registrations"] <= counts["unread"]:
            print("REFUSED: the reading is not discriminating")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
