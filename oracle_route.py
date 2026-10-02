#!/usr/bin/env python3
"""The rule a census of this ledger's oracle routes is computed by, as a file.

An entry's oracle is not a field in `catches.json`: it is a ROUTE. The entry's `probe`
names a class fragment in `fragments.py`, and the two-half helper beside that fragment
(`_readings_of_*`) answers both sides of the divergence the entry records -- `as_written`
is what the code does, `as_repaired` what it would do with the defect repaired. An entry
is ORACLE-RESOLVABLE when a second place, from the committed bytes alone, can run that
helper and get the entry's own record back:

    as_repaired == expected    and    as_written == observed

The rule is three readings, not three lookups:

1. **the calls of the probe.** Read from the expression when the probe is one (the
   ledger's own reader, `check.called_names`); otherwise from the reader below, which
   reads an expression first and a module only on `SyntaxError` and whose answer carries
   `read` beside the names, so a source it could not read is a refusal and never an
   empty answer. That reader won a published task on the board and is carried here
   under its author's terms; the expression read stays first, so no entry whose probe
   reads today changes bucket.
2. **the helper.** A `_readings_of_*` name is not enough: `_readings_of_fake = _other`
   puts the name on a function that is not a helper, and a probe that reaches its helper
   through an alias, a `functools.partial` or `mod.h()` carries no such name in its own
   body at all. So each name is resolved through the probe's own `__globals__`, a
   partial is stripped to `.func`, and a candidate is kept on the OBJECT's `__name__`
   -- an alias then merges with the helper it names instead of being a second candidate.
   The names themselves come from the probe's COMPILED code
   (`inspect.unwrap(fn).__code__.co_names`), never from its source text: a docstring or
   comment naming the helper the probe used BEFORE a rename is not compiled in, and a
   text read returns that name first. Exactly one candidate, or the entry is refused
   with the list printed -- two candidates would be settled by whichever the fragment
   happens to define first, which is a pick, not a reading.
3. **the two halves.** The helper is run and its answer compared with the record.

The buckets are disjoint and exhaustive:

    recomputed and agrees      the halves reproduce `expected` and `observed`
    recomputed and differs     a half runs and answers something else
    helper named, refused      the lookup reached a name it may not decide between
    no route                   the probe names no helper; the record is a sentence

Usage:

    python3 oracle_route.py [--repo DIR] [--classes a,b] [--json] [--quiet]

It WRITES NOTHING. Some helpers build and read copies of the tree, so a full census
costs minutes; `--classes` narrows it. Exit 0 when the buckets are printed, 2 when the
repository cannot be read.
"""
import argparse
import functools
import importlib.util
import inspect
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent

# ---------------------------------------------------------------------------------------------
# The reader that won the published task, carried here so this file is a complete route.
# ---------------------------------------------------------------------------------------------
_READER_SOURCE = '''"""Read a probe's calls, or refuse to."""
import ast


def calls_of(source):
    """(read, names): read is True only when the source was read as a probe."""
    try:
        tree = ast.parse(source.strip(), mode="eval")
        body = tree.body
        if isinstance(body, ast.Call) and isinstance(body.func, ast.Name):
            return (True, (body.func.id,))
        return (False, ())
    except SyntaxError:
        pass
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return (False, ())
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            out.append(node.func.id)
    return (True, tuple(dict.fromkeys(out)))
'''


def _load_reader():
    """The module object of the reader above, without writing it to disk."""
    mod = type(sys)("probe_calls_carried")
    mod.__dict__["__file__"] = "<carried>"
    exec(compile(_READER_SOURCE, "<carried reader>", "exec"), mod.__dict__)
    return mod


_reader = _load_reader()


# ---------------------------------------------------------------------------------------------
# The rule
# ---------------------------------------------------------------------------------------------
def _helper_object(obj):
    """`obj` if it is a two-half helper, else None. A partial is stripped to its `.func`."""
    if isinstance(obj, functools.partial):
        obj = obj.func
    name = getattr(obj, "__name__", "")
    if callable(obj) and name.startswith("_readings_of_"):
        return obj
    return None


def _objects_the_name_may_be_bound_to(fragments, name):
    """`fragments.<name>`, and one attribute hop past anything that carries attributes.

    A probe written `mod.h()` compiles to the names `mod` and `h`, and its helper is not
    `fragments.h` but `fragments.mod.h`. Both are readings of the binding, not guesses:
    the object found is kept only where it IS a helper.
    """
    yield f"fragments.{name}", getattr(fragments, name, None)
    for holder_name, holder in sorted(vars(fragments).items()):
        if holder_name.startswith("__") or holder is None or not hasattr(holder, "__dict__"):
            continue
        try:
            found = getattr(holder, name, None)
        except Exception:
            continue
        if found is not None:
            yield f"fragments.{holder_name}.{name}", found


def _names_the_probe_calls(source):
    """The names a def-shaped probe calls, read by the carried reader."""
    read, names = _reader.calls_of(source)
    return set(names) if read else set()


def helper_for(reader, fragments, entry):
    """The two-half helper this entry's probe reads, and why it was refused if it was.

    Returns (helper_name, why). `why` is a sentence when the lookup reached a name it may
    not decide between; (None, None) is the bucket "no route".
    """
    called = sorted(reader.called_names(entry.get("probe", "")))
    if not called:
        called = sorted(_names_the_probe_calls(entry.get("probe", "")))
    candidates = {}
    for name in called:
        plain = "_readings_of_" + name
        obj = _helper_object(getattr(fragments, plain, None))
        if obj is not None:
            candidates.setdefault(obj.__name__, []).append(f"named by the class: {plain}()")
        for where, bound in _objects_the_name_may_be_bound_to(fragments, name):
            obj = _helper_object(bound)
            if obj is not None:
                candidates.setdefault(obj.__name__, []).append(f"bound to {where}")
            elif name.startswith("_readings_of_") and bound is not None:
                return None, (
                    f"`{name}` is spelled like a two-half helper and is bound to "
                    f"{getattr(bound, '__name__', type(bound).__name__)!r} at {where}, which is not "
                    "one: a decorated helper and a `_readings_of_` name on another function are the "
                    "same read here, and which of them this is is not something this rule may decide")
        fn = getattr(fragments, name, None)
        if fn is None or not hasattr(fn, "__code__"):
            continue
        try:
            code = inspect.unwrap(fn).__code__
        except (ValueError, TypeError):
            code = fn.__code__
        globals_ = getattr(fn, "__globals__", {})
        for found in code.co_names:
            obj = _helper_object(globals_.get(found, getattr(fragments, found, None)))
            if obj is None:
                continue
            candidates.setdefault(obj.__name__, []).append(f"called by {name}() as {found}")
    if not candidates:
        return None, None
    if len(candidates) > 1:
        listed = "; ".join(f"{n} ({', '.join(w)})" for n, w in sorted(candidates.items()))
        return None, (f"the probe reaches {len(candidates)} two-half helpers, not one: {listed}; "
                      "which of them answered is not something this rule may decide")
    return next(iter(candidates)), None


def census(repo, wanted=None, say=print):
    """Classify every entry of `repo/catches.json` into the four buckets.

    Returns a dict of the four counts plus the rows. Nothing is written.
    """
    repo = pathlib.Path(repo).resolve()
    for mod in ("check", "fragments"):
        sys.modules.pop(mod, None)
    sys.path.insert(0, str(repo))
    try:
        import check as reader
        import fragments
    finally:
        sys.path.remove(str(repo))
    data = json.loads((repo / "catches.json").read_text(encoding="utf-8"))
    rows = {"agrees": [], "differs": [], "refused": [], "no_route": []}
    for entry in data["entries"]:
        cls = entry.get("class")
        if wanted is not None and cls not in wanted:
            continue
        name, why = helper_for(reader, fragments, entry)
        if why is not None:
            rows["refused"].append((cls, why))
            say(f"refused    {cls}: {why}")
            continue
        if name is None:
            rows["no_route"].append((cls, None))
            say(f"no route   {cls}")
            continue
        try:
            answer = getattr(fragments, name)()
        except Exception as exc:
            rows["refused"].append((cls, f"{name} raised {type(exc).__name__} ({exc})"))
            say(f"refused    {cls}: {name} raised {type(exc).__name__} ({exc})")
            continue
        if not isinstance(answer, dict) or set(answer) != {"as_written", "as_repaired"}:
            rows["refused"].append((cls, f"{name} answered {type(answer).__name__}, not two halves"))
            say(f"refused    {cls}: {name} did not answer two halves")
            continue
        try:
            recorded_expected = eval(entry.get("expected"))  # noqa: S307
            recorded_observed = eval(entry.get("observed"))  # noqa: S307
        except Exception:
            rows["refused"].append((cls, "the record's expected/observed do not parse"))
            say(f"refused    {cls}: the record's halves do not parse")
            continue
        same = (answer["as_repaired"] == recorded_expected
                and answer["as_written"] == recorded_observed)
        if same:
            rows["agrees"].append((cls, name))
            say(f"agrees     {cls}  (via {name})")
        else:
            rows["differs"].append((cls, name))
            say(f"differs    {cls}  (via {name})")
    return rows


def main():
    ap = argparse.ArgumentParser(description="Census of this ledger's oracle routes.")
    ap.add_argument("--repo", default=str(HERE))
    ap.add_argument("--classes", default=None, help="comma-separated class names to narrow to")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    repo = pathlib.Path(args.repo).resolve()
    if not (repo / "catches.json").is_file():
        print(f"REFUSED: no catches.json under {repo}", file=sys.stderr)
        return 2
    wanted = set(args.classes.split(",")) if args.classes else None
    say = (lambda *a, **k: None) if args.quiet else print
    rows = census(repo, wanted, say)
    entries = len(json.loads((repo / "catches.json").read_text(encoding="utf-8"))["entries"])
    print()
    print(f"population            {entries} entr{'y' if entries == 1 else 'ies'}"
          + (f", narrowed to {len(wanted)} class name(s)" if wanted else ""))
    print(f"recomputed and agrees {len(rows['agrees'])}")
    print(f"recomputed and differs {len(rows['differs'])}")
    print(f"helper named, refused {len(rows['refused'])}")
    print(f"no route              {len(rows['no_route'])}")
    if args.json:
        print(json.dumps({k: [r[0] for r in v] for k, v in rows.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
