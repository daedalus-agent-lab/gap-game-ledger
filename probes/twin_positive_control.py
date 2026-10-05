#!/usr/bin/env python3
"""The positive control `behavioural_twin.py` needs before its negative means anything.

The twin scan reported 2637 pairs compared and 4 candidates, all false. That is a
statement about the tool until somebody shows the tool CAN find a true one --
otherwise "zero twins" is indistinguishable from "blind to twins", which is the
class `a-probe-pointed-at-the-wrong-function` one level up.

This plants twins it should catch, of two kinds, and reports the hit rate:

  A. an exact DELEGATION wrapper: `def t(*a, **k): return orig(*a, **k)`. Exactly
     equivalent on every input, so a tool that compares outputs must flag it.
  B. an ALPHA-RENAMED copy: the fragment's own source with its parameters and
     locals renamed, which is a second SPELLING of one logic -- exactly case 1,
     the hole the scan was built to look for.

It calls `find_twins` from `behavioural_twin.py` rather than re-implementing the
comparison: a control that runs its own copy of the rule measures the copy.

    python3 probes/twin_positive_control.py
"""
from __future__ import annotations

import ast
import functools
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "probes"))

import check  # noqa: E402
import behavioural_twin as bt  # noqa: E402

SECONDS = 1
HOW_MANY = 12


def rename_fragment(fn):
    """A second spelling of `fn`: parameters and locals renamed, behaviour intact.

    Returns (new_fn, note). Renames only names bound in the function's TOP scope --
    parameters, assignment targets, loop and `with`/`except` targets -- and refuses
    a fragment with a nested `def`/`lambda`, where a flat rename could move a name
    across a scope boundary and change behaviour. A refusal is reported, not hidden.
    """
    import inspect
    import textwrap

    try:
        src = textwrap.dedent(inspect.getsource(fn))
    except (OSError, TypeError) as exc:
        return None, "source unavailable: %s" % type(exc).__name__
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return None, "source does not parse"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Lambda,)) or (
            isinstance(node, ast.FunctionDef) and node is not tree.body[0]
        ):
            return None, "nested scope: a flat rename could change behaviour"

    top = tree.body[0]
    if not isinstance(top, ast.FunctionDef):
        return None, "not a function"

    bound = {a.arg for a in top.args.args + top.args.kwonlyargs}
    if top.args.vararg:
        bound.add(top.args.vararg.arg)
    if top.args.kwarg:
        bound.add(top.args.kwarg.arg)
    for node in ast.walk(top):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            bound.add(node.id)
        elif isinstance(node, ast.alias):
            bound.add((node.asname or node.name).split(".")[0])

    mapping = {name: "_r_%s" % name for name in sorted(bound)}
    if not mapping:
        return None, "nothing bound, so nothing to rename"

    class Rename(ast.NodeTransformer):
        def visit_Name(self, node):
            node.id = mapping.get(node.id, node.id)
            return node

        def visit_arg(self, node):
            node.arg = mapping.get(node.arg, node.arg)
            return node

    new_tree = Rename().visit(tree)
    ast.fix_missing_locations(new_tree)
    # Executed in the fragment's OWN module globals, not in an empty namespace. An
    # empty one was the control's second defect: the copy lost every helper the
    # original calls, raised NameError on every input, and its constant all-error
    # vector was then silenced by the constant rule -- so the control reported
    # "MISSED" for a twin whose comparison had never happened.
    ns: dict = dict(getattr(fn, "__globals__", {}))
    try:
        exec(compile(new_tree, "<renamed>", "exec"), ns)  # noqa: S102 -- test fixture
    except Exception as exc:  # noqa: BLE001
        return None, "the renamed copy does not even build: %s" % type(exc).__name__
    return ns[top.name], "renamed %d name(s)" % len(mapping)


def delegation(fn):
    """An exactly equivalent wrapper: same answers on every input, other bytes.

    `functools.wraps` is not decoration here. A bare `*a, **k` wrapper has a
    VARIADIC signature, `inspect.signature` follows `__wrapped__` only when wraps
    has set it, and `arity` refuses a variadic signature -- so the first version of
    this control planted twelve twins that the scan dropped before comparing them,
    and the drops read as misses.
    """

    def wrapper(*a, **k):
        return fn(*a, **k)

    functools.update_wrapper(wrapper, fn)
    wrapper.__name__ = "delegates_to_" + getattr(fn, "__name__", "f")
    return wrapper


def main() -> int:
    data = check.load()
    subjects, dropped = bt.subjects_of(data)
    print(f"real subjects: {len(subjects)}   (not entered: {len(dropped)})")

    # Only arity >= 1: the scan excludes arity 0 by construction, so planting there
    # would test the exclusion, not the comparison.
    pool = [s for s in subjects if s["n"] >= 1]
    print(f"real subjects the control can draw from (arity >= 1): {len(pool)}")

    planted = []          # (kind, original_class, twin_class, note)
    extra = []
    for s in pool[:HOW_MANY]:
        renamed, note = rename_fragment(s["fn"])
        if renamed is not None:
            twin = dict(s, cls=s["cls"] + "~alpha-renamed", fn=renamed)
            extra.append(twin)
            planted.append(("B alpha-rename", s["cls"], twin["cls"], note))
        else:
            planted.append(("B alpha-rename", s["cls"], None, "REFUSED: " + note))
        d = dict(s, cls=s["cls"] + "~delegation", fn=delegation(s["fn"]))
        extra.append(d)
        planted.append(("A delegation", s["cls"], d["cls"], "wrapper"))

    print(f"planted twins: {len(extra)} "
          f"({sum(1 for k, *_ in planted if k == 'A delegation')} delegation, "
          f"{sum(1 for k, _, t, _ in planted if k == 'B alpha-rename' and t)} renamed)")

    twins, pairs, unmeasurable, single = bt.find_twins(subjects + extra, SECONDS)
    flagged = {frozenset((a, b)) for _n, a, b, _v in twins}
    real_classes = {s["cls"] for s in subjects}
    by_cls = {s["cls"]: s for s in subjects + extra}
    dropped_classes = {c for c, _why in dropped}

    print()
    print("PLANTED PAIRS -- did the tool flag the pair it was handed?")
    hits = {}
    comparable = 0
    for kind, orig, twin, note in planted:
        if twin is None:
            continue
        hit = frozenset((orig, twin)) in flagged
        a, b = by_cls.get(orig), by_cls.get(twin)
        if hit:
            why = ""
        elif b is None:
            why = "NOT ENTERED (its signature was refused)"
        elif a is None:
            why = "NOT ENTERED (the original was refused)"
        elif a.get("answered_nothing") or b.get("answered_nothing"):
            # The pool never reached the fragment: every input raised. Not a
            # disagreement between the two, an absent measurement of both.
            why = "NOT COMPARABLE: the pool never reached it (all inputs raised)"
        elif a.get("timed_out") or b.get("timed_out"):
            why = "NOT COMPARABLE: it outran the bound"
        else:
            why = "COMPARED AND NOT FLAGGED -- a false negative"
        if hit or why.startswith("COMPARED"):
            comparable += 1
        hits[kind] = hits.get(kind, 0) + (1 if hit else 0)
        print(f"  {'CAUGHT ' if hit else 'MISSED '} {kind:<16} {orig}\n"
              f"             as {twin}  [{note}]{'' if hit else chr(10) + '             ' + why}")

    unplanted = [(a, b) for _n, a, b, _v in twins
                 if a in real_classes and b in real_classes]
    print()
    print(f"pairs compared: {pairs}   candidates: {len(twins)}   "
          f"unmeasurable: {len(unmeasurable)}   arity-0 excluded: {len(single)}")
    print(f"candidates between two REAL classes (the negative being controlled): "
          f"{len(unplanted)}")

    print()
    print("=== VERDICT ===")
    for kind in sorted(hits):
        n = sum(1 for k, _, t, _ in planted if k == kind and t is not None)
        print(f"{kind:<16} caught {hits[kind]}/{n}")
    print(f"planted pairs the tool actually put on the table (caught or compared "
          f"and rejected): {comparable} of "
          f"{sum(1 for _k, _o, t, _n in planted if t is not None)}")
    refused = [(o, note) for k, o, t, note in planted if t is None]
    if refused:
        print(f"alpha-rename REFUSED on {len(refused)} fragment(s) (not scored):")
        for o, note in refused:
            print(f"   {o}: {note}")
    print()
    if comparable == 0:
        print("The tool never put a single planted twin on the table, so its count of "
              "candidates among the real classes says nothing about the ledger.")
    else:
        print(f"The tool caught {sum(hits.values())} of {comparable} planted twins it "
              f"could compare, so its count of candidates between two REAL classes "
              f"is a measurement of the ledger on this pool.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
