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
import ast
import inspect
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


BUILTINS = {
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "isinstance",
    "len", "list", "max", "min", "next", "print", "range", "reversed", "round",
    "set", "sorted", "str", "sum", "tuple", "type", "zip",
}


class _Normalise(ast.NodeTransformer):
    """Rename every identifier that is not a builtin, by order of first appearance."""

    def __init__(self):
        self.seen = {}

    def _rename(self, name: str) -> str:
        if name in BUILTINS or name.startswith("__"):
            return name
        if name not in self.seen:
            self.seen[name] = f"v{len(self.seen)}"
        return self.seen[name]

    def visit_Name(self, node):
        node.id = self._rename(node.id)
        return node

    def visit_arg(self, node):
        node.arg = self._rename(node.arg)
        return node

    def visit_FunctionDef(self, node):
        node.name = self._rename(node.name)
        self.generic_visit(node)
        return node


def fingerprint(fn) -> str:
    """The logic of a function with the names it chose thrown away.

    Two functions with the same fingerprint do the same thing; a repeat whose
    fragment fingerprints identically to the class fragment is the class probe
    again, not a second sighting.
    """
    tree = ast.parse(inspect.getsource(fn).lstrip())
    node = tree.body[0]
    if (
        node.body
        and isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ):
        node.body = node.body[1:]
    _Normalise().visit(node)
    return ast.dump(node)


def primary(entry: dict) -> str | None:
    """The fragment the entry's own probe calls: the class's bytes."""
    ns = NAMESPACES.get(entry["class"], {})
    probe = entry.get("probe", "")
    for name in ns:
        if name in probe:
            return name
    return None


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
    # a repeat entered as an object carries its own promise, fact and probe;
    # it is replayed here exactly like the class probe.
    for rep in entry.get("repeats") or []:
        if isinstance(rep, str):
            continue  # legacy label: records that a claim arrived, not the claim
        if not isinstance(rep, dict) or not rep.get("probe"):
            return "miss", f"repeat {rep!r} is neither a label nor a probe object"
        missing = [k for k in ("id", "promise", "fact", "probe", "expected",
                               "observed", "fn") if k not in rep]
        if missing:
            return "miss", f"repeat {rep.get('id', rep)!r} lacks {', '.join(missing)}"
        fn_name = rep["fn"]
        if fn_name not in ns:
            return "miss", f"repeat {rep['id']!r} names {fn_name!r}, not in the class"
        if fn_name not in rep["probe"]:
            return "miss", (
                f"repeat {rep['id']!r} names {fn_name!r} but its probe never calls it"
            )
        base = primary(entry)
        if base and fn_name == base:
            return "miss", (
                f"repeat {rep['id']!r} replays {base}, the class fragment itself: "
                "that is the class probe, not a second sighting"
            )
        if base and fingerprint(ns[base]) == fingerprint(ns[fn_name]):
            return "miss", (
                f"repeat {rep['id']!r}: {fn_name} fingerprints like {base}; "
                "that is the class probe again, not a second sighting"
            )
        try:
            got = eval(rep["probe"], dict(ns))
        except Exception as exc:  # a raising repeat probe is the observation
            got = type(exc).__name__
            if rep["observed"] != got:
                return "miss", (
                    f"repeat {rep['id']!r} raised {got}, ledger says {rep['observed']!r}"
                )
            if rep["expected"] == got:
                return "miss", f"repeat {rep['id']!r}: expected == observed, not a divergence"
            continue
        try:
            want = literal(rep["observed"])
            promised = literal(rep["expected"])
        except Exception as exc:
            return "miss", f"bad ledger literal in repeat {rep['id']!r}: {exc}"
        if got != want:
            return "miss", f"repeat {rep['id']!r} gave {got!r}, ledger says {want!r}"
        if want == promised:
            return "miss", f"repeat {rep['id']!r}: expected == observed, not a divergence"
    for gone in entry.get("retired") or []:
        if not isinstance(gone, dict) or not gone.get("id") or not gone.get("why"):
            return "miss", f"retired entry {gone!r} needs an id and a why"
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


def class_collisions(data: dict) -> tuple[int, list[str]]:
    """Two class names for one shape of lie.

    Every class stands for a shape, so the fragment its own probe calls must not
    fingerprint like another class's fragment. A hit means the ledger counted the
    same lie twice under two names, or a repeat was filed against the wrong class.
    """
    seen: dict[str, str] = {}
    problems: list[str] = []
    counted = 0
    for entry in data["entries"]:
        ns = NAMESPACES.get(entry["class"], {})
        base = primary(entry)
        if not base:
            continue
        counted += 1
        fp = fingerprint(ns[base])
        if fp in seen:
            problems.append(
                f"{entry['class']}.{base} has the logic of {seen[fp]}"
            )
        else:
            seen[fp] = f"{entry['class']}.{base}"
        for rep in entry.get("repeats") or []:
            if not isinstance(rep, dict) or rep.get("fn") not in ns:
                continue
            other = seen.get(fingerprint(ns[rep["fn"]]))
            if other and not other.startswith(entry["class"] + "."):
                problems.append(
                    f"repeat {rep['id']} replays the logic of {other}"
                )
    return counted, problems


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
    all_repeats = [r for e in data["entries"] for r in (e.get("repeats") or [])]
    materialised = sum(1 for r in all_repeats if isinstance(r, dict))
    retired = [g for e in data["entries"] for g in (e.get("retired") or [])]
    instances = len(data["entries"]) + len(all_repeats)
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

    collision_count, collisions = class_collisions(data)
    for line in collisions:
        print(f"DUPE  {'':<50} {line}")

    print()
    print(f"entries {len(data['entries'])}  ok {ok}  miss {miss}  skipped {skip}")
    print(
        f"distinct class fragments {collision_count - len(collisions)}"
        f"/{collision_count}  (no class is another class under a new name)"
    )
    print(
        f"reported instances {instances} "
        f"(repeats {len(all_repeats)}: {materialised} replayed by this script, "
        f"{len(all_repeats) - materialised} label-only)"
    )
    print(
        f"retired repeats    {len(retired)} "
        "(recovered and found not distinct from the class fragment)"
    )
    addressed = sum(1 for e in data["entries"] if e.get("address")) + sum(
        1 for r in all_repeats if isinstance(r, dict) and r.get("address")
    )
    print(
        f"instances with a public address {addressed}/{instances}"
        "  (the rest are remembered, not shown)"
    )
    print(f"recurring classes  {len(recurring)}: {', '.join(recurring)}")
    print(f"holds callbacks    {len(HOLDS)} fail {holds_fail}")
    if unknown:
        return 2
    return 1 if miss or holds_fail or collisions else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # `python3 check.py | head` is a normal way to read this tool; a reader
        # closing the pipe is not a ledger failure. Redirect stdout to devnull
        # so the interpreter's final flush does not raise again.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
