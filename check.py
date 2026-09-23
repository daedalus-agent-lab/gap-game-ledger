#!/usr/bin/env python3
"""Re-run every probe in catches.json and check the divergence it claims.

The ledger claims three things per entry: the promise, the fact, and that
they differ. This script re-checks all three:

  * `probe` evaluated against the reproduction in fragments.py  ==  `observed`
  * `observed` != `expected`
  * a raising probe is recorded as the exception's class name

Usage:
    python3 check.py                 # verify the whole ledger
    python3 check.py --class <name>
    python3 check.py --lookup "raises ValueError when low > high"

Exit code 0 means every executable entry held. A non-zero exit names the
entries that did not.

What the ledger deliberately does not do: it does not name who saw a lie
first, and it cannot tell you that your fragment is a re-post — only that
its class is not new.
"""

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)

from fragments import NAMESPACES  # noqa: E402

LEDGER = HERE / "catches.json"


def load() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def literal(text: str):
    return eval(text, {})  # ledger literals only


def evaluate(entry: dict):
    """Run one probe. Returns (status, actual) with status ok|miss|skip."""
    if entry.get("lang") != "python" or entry.get("executable") is False:
        return "skip", None
    ns = dict(NAMESPACES.get(entry["class"], {}))
    raised = None
    try:
        actual = eval(entry["probe"], ns)
    except Exception as exc:  # a raising probe is itself the observation
        raised = type(exc).__name__
        actual = raised
    try:
        if raised is not None:
            # a raising probe is compared by exception class name
            if entry["observed"] != raised:
                return "miss", f"probe raised {raised}, ledger says {entry['observed']!r}"
            if entry["expected"] == raised:
                return "miss", "ledger's expected == observed; that is not a divergence"
            return "ok", raised
        observed = literal(entry["observed"])
        expected = literal(entry["expected"])
    except Exception as exc:
        return "miss", f"bad ledger literal: {exc}"
    if actual != observed:
        return "miss", f"probe gave {actual!r}, ledger says {observed!r}"
    if observed == expected:
        return "miss", "ledger's expected == observed; that is not a divergence"
    # extra probes folded into this class by a later merge: each must also
    # reproduce its own observed value and differ from its own expected one.
    for extra in entry.get("also") or []:
        try:
            got = eval(extra["probe"], dict(ns))
        except Exception as exc:
            got = type(exc).__name__
        try:
            want = literal(extra["observed"])
            promised = literal(extra["expected"])
        except Exception as exc:
            return "miss", f"bad ledger literal in also: {exc}"
        if got != want:
            return "miss", f"also probe gave {got!r}, ledger says {want!r}"
        if want == promised:
            return "miss", "also probe: expected == observed; not a divergence"
    return "ok", actual


def lookup(query: str) -> int:
    words = query.lower().split()
    hits = 0
    for entry in load()["entries"]:
        haystack = " ".join(
            str(entry.get(k, ""))
            for k in ("class", "promise", "fact", "probe", "aliases")
        ).lower()
        if all(word in haystack for word in words):
            hits += 1
            repeats = entry.get("repeats") or []
            print(
                f"{entry['class']}  (first seen {entry['first_seen']}; "
                f"{len(repeats)} repeat(s): {repeats or '-'})\n"
                f"  promise : {entry['promise']}\n"
                f"  fact    : {entry['fact']}\n"
                f"  probe   : {entry['probe']}  ->  {entry['observed']}"
            )
    if not hits:
        print("no entry matches — this class may be new")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="only")
    ap.add_argument("--lookup")
    args = ap.parse_args()

    if args.lookup:
        return lookup(args.lookup)

    data = load()
    entries = data["entries"]
    unknown = False
    if args.only:
        entries = [e for e in entries if e["class"] == args.only]
        if not entries:
            print(f"unknown class {args.only!r} — 0 checks performed")
            unknown = True

    ok = miss = skip = 0
    for entry in entries:
        status, detail = evaluate(entry)
        if status == "ok":
            ok += 1
            print(f"ok    {entry['class']:<50} {entry['probe']} -> {detail!r}")
        elif status == "skip":
            skip += 1
            print(f"skip  {entry['class']:<50} (lang={entry['lang']}; run it by hand)")
        else:
            miss += 1
            print(f"MISS  {entry['class']:<50} {detail}")

    recurring = [e["class"] for e in data["entries"] if e.get("repeats")]
    instances = len(data["entries"]) + sum(
        len(e.get("repeats") or []) for e in data["entries"]
    )
    holds_fail = 0
    try:
        from holds import HOLDS
    except ImportError:
        HOLDS = {}
    by_class = {e["class"]: e for e in entries}
    for name, spec in HOLDS.items():
        if name not in by_class:
            continue
        entry = by_class[name]
        fn = spec["fn"]
        prefix = spec["prefix"]
        try:
            expected_val = literal(entry["expected"])
            observed_val = literal(entry["observed"])
        except Exception as exc:
            holds_fail += 1
            print(f"HOLD  {name:<50} bad ledger literal: {exc}")
            continue
        exp = fn(*prefix, expected_val)
        obs = fn(*prefix, observed_val)
        if exp is True and obs is False:
            print(f"hold  {name:<50} expected holds, observed does not")
        else:
            holds_fail += 1
            print(
                f"HOLD  {name:<50} expected={exp!r} observed={obs!r} "
                "(want True / False)"
            )

    print()
    print(f"entries {len(data['entries'])}  ok {ok}  miss {miss}  skipped {skip}")
    print(f"reported instances {instances}")
    print(f"recurring classes  {len(recurring)}: {', '.join(recurring)}")
    print(f"holds callbacks    {len(HOLDS)} fail {holds_fail}")
    if unknown:
        return 2
    return 1 if miss or holds_fail else 0


if __name__ == "__main__":
    sys.exit(main())
