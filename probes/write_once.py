#!/usr/bin/env python3
"""Which write paths does a write-once registry actually refuse?

A registry that must not lose a registration can be guarded two ways: statically, by
reading the source (what `check.py:duplicate_declarations` does for this ledger), or at
run time, by a dict that raises when a key is written twice. The static guard sees the
code it is handed; the run-time guard sees only the writes that reach it, and Python's
dict has several write paths that do not all go through `__setitem__`.

This probe runs both questions over the same write paths, because "the guard
refuses the second write" is a claim about a path, not about the guard. The paths are
named by `PATHS` and `SOURCES`, never by a number written beside them:

  []=         R['k'] = v              -- calls `__setitem__`
  update      R.update(k=v)           -- C `dict.update` does not call `__setitem__`
  |=          R |= {'k': v}           -- `dict.__ior__` calls update, not `__setitem__`
  setdefault  R.setdefault('k', v)    -- silent in both; the FIRST write wins, so the
                                         loss is the other way round from the others
  decorator   @register('k')          -- the helper writes through `registry['k']`, so
                                         the write reaches the container like `[]=`

A label is not a path. `decorator` above is a helper whose body is `R['k'] = v`; a real
`@decorator` applied twice is a different piece of code and a separate column.

A silent path is not one outcome: `second-wins` means the first registration is gone,
`first-wins` means the second one is. Both are losses and both are printed.

The decorator column is measured twice. A helper that checks the registry itself
before writing refuses on EVERY container, a plain `dict` included -- which is not the
container guarding anything, it is the helper. That row is printed separately, because
counting it as the container's refusal is exactly the mistake this probe exists to
avoid: with the checking helper the plain-dict deafness check fires, and the probe
reports it.

Asked of the LEDGER's guard as well: the same paths written as source text, run through
the guard this ledger uses, so a reader can see which paths a static guard can cover
that a run-time one cannot -- and which it misses anyway. Three sources below are loss
shapes the guard is silent on and that the runtime columns do not reach either, because
the reply this probe answers named them as the same defect and a silent path is one
reading per source, not a footnote.

    python3 write_once.py            # the table, measured
    python3 write_once.py --check    # the table must equal what this file declares
    python3 write_once.py --selftest # a plain dict refuses nothing, so the
                                     # instrument is not answering a constant

WHAT THIS DOES NOT DO, named rather than hidden:
  * It does not test `collections.ChainMap`, `types.MappingProxyType` or a shelve-like
    store; the two classes here are the two a reader of the reply would reach for first.
  * "Refused" is a raised `KeyError`. A guard that overwrote quietly and logged would
    be reported `silent` here, which is right for this question.
  * The source-text column asks the guard about the ledger's registry NAME. A guard
    watching a different registry would have to be pointed at it.
"""
import argparse
import collections
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

PATHS = ("[]=", "update", "|=", "setdefault", "decorator",
         "decorator-update", "data[]")
# Measured by this file, declared here so that a change to the paths or to the two
# guards fails `--check` instead of quietly printing a different table.
DECLARED = {
    "OnceDict": {"refused": ["[]=", "decorator"],
                 "silent": {"update": "second-wins",
                            "|=": "second-wins",
                            "setdefault": "first-wins",
                            "decorator-update": "second-wins"},
                 # `data[]` is UserDict's own store; a plain dict has no such name.
                 "not_applicable": ["data[]"]},
    "OnceUserDict": {"refused": ["[]=", "update", "decorator", "decorator-update"],
                     "silent": {"|=": "second-wins",
                                "setdefault": "first-wins",
                                # The second write goes into the inner mapping, past
                                # `__setitem__`, and survives: a reader named this
                                # path and it was not among the six measured here.
                                "data[]": "second-wins"},
                     "not_applicable": []},
    "checking helper": {"refused_on": ["dict", "OnceDict", "OnceUserDict"]},
    "ledger guard": {"fires": ["[]=", "|=", "subscript-union", "two assignment sites"],
                     "silent": ["real decorator", "setdefault", "two subscript unions",
                                "two whole-registry unions", "union then assign",
                                "update (method)", "update (tool call)"]},
}

# The write paths as source, twice each, for the static guard. The two union forms are
# two different pieces of code and the guard reads them separately; the real decorator,
# the tool-call `update` and the two unions before an assignment are here because the
# guard reads them as NOTHING, which is the column a reader asked for.
SOURCES = {
    "[]=": ("NAMESPACES = {}\n"
            "NAMESPACES['c'] = {'n': lambda: 1}\n"
            "NAMESPACES['c'] = {'m': lambda: 2}\n"),
    # `.update(...)` as a method on the registry name.
    "update (method)": ("NAMESPACES = {}\n"
                        "NAMESPACES['c'] = {'n': lambda: 1}\n"
                        "NAMESPACES['c'].update({'m': lambda: 2})\n"),
    "|=": ("NAMESPACES = {}\n"
           "NAMESPACES['c'] = {'n': lambda: 1}\n"
           "NAMESPACES |= {'c': {'m': lambda: 2}}\n"),
    "subscript-union": ("NAMESPACES = {}\n"
                        "NAMESPACES['c'] = {'n': lambda: 1}\n"
                        "NAMESPACES['c'] |= {'n': lambda: 2}\n"),
    "setdefault": ("NAMESPACES = {}\n"
                   "NAMESPACES['c'] = {'n': lambda: 1}\n"
                   "NAMESPACES.setdefault('c', {}).update({'m': lambda: 2})\n"),
    "two assignment sites": ("NAMESPACES = {}\n"
                  "def register_n():\n"
                  "    NAMESPACES['c'] = {'n': lambda: 1}\n"
                  "def register_m():\n"
                  "    NAMESPACES['c'] = {'m': lambda: 2}\n"),
    # `.update(...)` as a tool call rather than as a method on the registry name.
    "update (tool call)": ("NAMESPACES = {}\n"
               "NAMESPACES['c'] = {'n': lambda: 1}\n"
               "d = {'m': lambda: 2}\n"
               "NAMESPACES['c'].update(**d)\n"),
    # Union before the assignment that follows it: the union is lost wholesale.
    "union then assign": ("NAMESPACES = {}\n"
                          "NAMESPACES |= {'c': {'n': lambda: 1}}\n"
                          "NAMESPACES['c'] = {'m': lambda: 2}\n"),
    # Two whole-registry unions for one class: the second replaces the class body.
    "two whole-registry unions": ("NAMESPACES = {}\n"
                                  "NAMESPACES |= {'c': {'n': lambda: 1}}\n"
                                  "NAMESPACES |= {'c': {'m': lambda: 2}}\n"),
    # Two subscript unions against one literal: the same key is written twice into one
    # mapping and the guard needs both writes to see it.
    "two subscript unions": ("NAMESPACES = {'c': {}}\n"
                             "NAMESPACES['c'] |= {'n': lambda: 1}\n"
                             "NAMESPACES['c'] |= {'n': lambda: 2}\n"),
    # A REAL decorator: one write site, two call sites. The loss is real (the second
    # call replaces the first mapping) and the guard sees one assignment, so it is
    # silent -- which the row above, made of two visible assignments, is not. Printed
    # separately, because "the guard covers the decorator form" was measured on the
    # row above, which contains no decorator.
    "real decorator": ("NAMESPACES = {}\n"
                       "def register(cls, name):\n"
                       "    def deco(fn):\n"
                       "        NAMESPACES[cls] = {name: fn}\n"
                       "        return fn\n"
                       "    return deco\n"
                       "@register('c', 'n')\n"
                       "def a():\n"
                       "    pass\n"
                       "@register('c', 'm')\n"
                       "def b():\n"
                       "    pass\n"),
}


class OnceDict(dict):
    """A dict that refuses a second write through `__setitem__`."""

    def __setitem__(self, key, value):
        if key in self:
            raise KeyError(key)
        super().__setitem__(key, value)


class OnceUserDict(collections.UserDict):
    """The same rule on `UserDict`, whose `update` does route through `__setitem__`."""

    def __setitem__(self, key, value):
        if key in self.data:
            raise KeyError(key)
        self.data[key] = value


def register(registry, value):
    """The decorator form: the helper itself writes through `registry['k']`."""
    def deco(fn):
        registry["k"] = value
        return fn
    return deco


def register_checking(registry, value):
    """The same helper with the registry read first: a guard in the HELPER."""
    def deco(fn):
        if "k" in registry:
            raise KeyError("k")
        registry["k"] = value
        return fn
    return deco


def register_via_update(registry, value):
    """A decorator whose helper writes through `update`, not through `[]=`.

    The decorator is syntax, not a write path: which container refuses it is decided by
    the helper's body. This one is here so the probe measures that instead of asserting
    it -- on `OnceUserDict` `update` routes through `__setitem__`, so this variant IS
    refused there while the `[]=`-bodied one is refused on both.
    """
    def deco(fn):
        registry.update({"k": value})
        return fn
    return deco


OPERATIONS = {
    "[]=": lambda R, v: R.__setitem__("k", v),
    "update": lambda R, v: R.update({"k": v}),
    "|=": lambda R, v: R.__ior__({"k": v}),
    "setdefault": lambda R, v: R.setdefault("k", v),
    "decorator": lambda R, v: register(R, v)(lambda: None),
    "decorator-update": lambda R, v: register_via_update(R, v)(lambda: None),
    # UserDict keeps its mapping in `.data`; writing there does not pass through the
    # container's `__setitem__` at all.
    "data[]": lambda R, v: R.data.__setitem__("k", v),
}


def run_path(cls, op) -> tuple:
    """Apply one write path twice to a fresh registry: refused, silent, or unreadable.

    A sentinel class with `__setitem__` that raises nothing is the blindness check:
    if it refuses, the harness is broken rather than the guard working.

    Three answers rather than two, because a write path can lie outside the container
    the harness is asking about: `data[]` on a plain dict raises AttributeError -- a
    path that cannot be applied is NOT a refusal -- and a path writing a name the
    container does not read back leaves the harness unable to say who won. Both used
    to crash the caller, which reads as "the probe is broken" rather than "the probe
    cannot judge this path".
    """
    registry = cls()
    try:
        op(registry, 1)
        op(registry, 2)
    except KeyError:
        return "refused", None
    except (AttributeError, TypeError):
        return "not-applicable", None
    try:
        seen = registry["k"]
    except KeyError:
        return "not-this-key", None
    return "silent", ("second-wins" if seen == 2 else "first-wins")


def load_guard():
    """The ledger's guard, imported as the ledger imports it."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import importlib
    return importlib.import_module("check").duplicate_declarations


def guard_over(text: str) -> list:
    """Run the ledger's guard over a source, in the directory it reads."""
    guard = load_guard()
    with tempfile.TemporaryDirectory(prefix="write-once-") as d:
        (Path(d) / "fragments.py").write_text(text, encoding="utf-8")
        cwd = os.getcwd()
        os.chdir(d)
        try:
            return guard()
        finally:
            os.chdir(cwd)


def measure() -> dict:
    out = {}
    for cls in (OnceDict, OnceUserDict):
        refused, silent, not_applicable, not_this_key = [], {}, [], []
        for label in PATHS:
            verdict, who = run_path(cls, OPERATIONS[label])
            if verdict == "refused":
                refused.append(label)
            elif verdict == "not-applicable":
                not_applicable.append(label)
            elif verdict == "not-this-key":
                not_this_key.append(label)
            else:
                silent[label] = who
        out[cls.__name__] = {"refused": refused, "silent": silent,
                             "not_applicable": not_applicable,
                             "not_this_key": not_this_key}
    # Is the decorator column an independent path, or the same write under a second
    # name? Measured per container rather than assumed from the helper's text.
    out["decorator is another name"] = {
        cls.__name__: run_path(cls, OPERATIONS["decorator"]) == run_path(cls, OPERATIONS["[]="])
        for cls in (OnceDict, OnceUserDict)}
    fires, silent = [], []
    for label in SOURCES:
        (fires if guard_over(SOURCES[label]) else silent).append(label)
    out["ledger guard"] = {"fires": sorted(fires), "silent": sorted(silent)}
    refused_on = []
    for cls in (dict, OnceDict, OnceUserDict):
        registry = cls()
        try:
            register_checking(registry, 1)(lambda: None)
            register_checking(registry, 2)(lambda: None)
        except KeyError:
            refused_on.append(cls.__name__)
    out["checking helper"] = {"refused_on": refused_on}
    return out


def table() -> list:
    return [l for l in _render(measure())]


def _render(m: dict) -> list:
    lines = []
    for guard in ("OnceDict", "OnceUserDict", "checking helper",
                  "-- the ledger's static guard, on source text --", "ledger guard",
                  "decorator is another name"):
        if guard.startswith("--"):
            lines.append(guard)
            continue
        row = m[guard]
        if guard == "decorator is another name":
            lines.append("%-15s %s" % (
                guard, ", ".join("%s: %s" % (k, v) for k, v in sorted(row.items()))))
        elif "refused_on" in row:
            lines.append("%-15s refuses on every container it was given: %s" % (
                guard, ", ".join(row["refused_on"]) or "none"))
        elif "refused" in row:
            lines.append("%-15s refuses %d of %d: %s" % (
                guard, len(row["refused"]), len(PATHS),
                ", ".join(row["refused"]) or "none"))
            lines.append("%-15s silent on: %s" % (
                "", ", ".join("%s (%s)" % (k, v) for k, v in sorted(row["silent"].items()))
                or "none"))
            lines.append("%-15s not applicable: %s" % (
                "", ", ".join(row.get("not_applicable") or []) or "none"))
            if row.get("not_this_key"):
                lines.append("%-15s leaves this key untouched: %s" % (
                    "", ", ".join(row["not_this_key"])))
        else:
            lines.append("%-15s fires on %d of %d: %s" % (
                guard, len(row["fires"]), len(SOURCES), ", ".join(row["fires"])))
            lines.append("%-15s silent on: %s" % ("", ", ".join(row["silent"])))
    return lines


def selftest() -> tuple:
    bad = []
    checks = 0
    # The instrument must be able to say "refused" at all, and must not say it when a
    # plain dict is handed the same paths: otherwise the column is a constant.
    for label in PATHS:
        checks += 1
        verdict, _ = run_path(dict, OPERATIONS[label])
        # `not-applicable` is allowed: `data[]` is UserDict's store and a plain dict
        # has no such name. What must never appear is a refusal, which would be the
        # harness inventing a guard where there is none.
        if verdict not in ("silent", "not-applicable"):
            bad.append("a plain dict refused %s: the harness reports refusals it did "
                       "not observe" % label)
    checks += 1
    if run_path(OnceDict, OPERATIONS["[]="])[0] != "refused":
        bad.append("the write-once dict did not refuse a second `[]=`: the harness "
                   "cannot see a refusal")
    # Three answers, not two: a write path that does not apply to a container is not a
    # refusal, and a path that writes a name the container does not read back cannot be
    # scored at all. Both used to raise out of `run_path`, which reads as a broken probe.
    for label, container, expected in (("data[]", OnceDict, "not-applicable"),
                                       ("[]=", OnceDict, "refused"),
                                       ("data[]", OnceUserDict, "silent")):
        checks += 1
        got = run_path(container, OPERATIONS[label])[0]
        if got != expected:
            bad.append("run_path(%s, %s) answered %r, declared %r"
                       % (container.__name__, label, got, expected))
    checks += 1
    outside = run_path(OnceDict, lambda R, v: R.__dict__.__setitem__("elsewhere", v))[0]
    if outside != "not-this-key":
        bad.append("a write path that never touches the key was scored %r instead of "
                   "`not-this-key`" % outside)
    # The static column must move with the source: a source with one write only is not
    # a loss, so the guard must stay silent on it.
    checks += 1
    if guard_over("NAMESPACES = {}\nNAMESPACES['c'] = {'n': lambda: 1}\n"):
        bad.append("the guard reports a single write as a loss")
    # Every form this file DECLARES the guard covers must fire. The list is read from
    # DECLARED rather than retyped here: a form dropped from the constant or lost by the
    # guard has to fail the selftest, and a hand-written pair of labels did not.
    for label in SOURCES:
        declared_fires = label in DECLARED["ledger guard"]["fires"]
        checks += 1
        fired = bool(guard_over(SOURCES[label]))
        if declared_fires and not fired:
            bad.append("the guard stayed silent on the %s form, which this file "
                       "declares it covers" % label)
        if fired and not declared_fires:
            bad.append("the guard fired on the %s form, which this file declares it "
                       "does not cover -- the declaration is stale" % label)
    # A label written twice in one dict literal is not a dict with two entries: the
    # later source silently replaces the earlier one and the row for the first is
    # measured on a source nothing declares. This probe was written with that
    # defect -- two `update` keys, one source dropped -- so the counts below are
    # read from the file's own text rather than from the object they built.
    checks += 1
    dupes = duplicated_source_labels()
    if dupes:
        bad.append("these source labels are written twice in one literal, so the first "
                   "source is not the one measured: %s" % ", ".join(dupes))
    checks += 1
    written = len(source_literal_keys())
    if written != len(SOURCES) or written != len(DECLARED["ledger guard"]["fires"]) \
            + len(DECLARED["ledger guard"]["silent"]):
        bad.append("the SOURCES literal holds %d entry/entries, the object holds %d and "
                   "the declaration names %d: a count in a literal is not a count"
                   % (written, len(SOURCES),
                      len(DECLARED["ledger guard"]["fires"])
                      + len(DECLARED["ledger guard"]["silent"])))
    return bad, checks


def source_literal_keys() -> list:
    """The keys of the SOURCES literal as written, duplicates included."""
    import ast
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "SOURCES":
            return [k.value for k in node.value.keys]
    return []


def duplicated_source_labels() -> list:
    keys = sorted(l for l in source_literal_keys()
                  if source_literal_keys().count(l) > 1)
    return keys


def check(measured: dict) -> list:
    bad = []
    for guard, declared in DECLARED.items():
        got = measured.get(guard)
        if not got:
            bad.append("%s produced no measurement" % guard)
            continue
        key = "refused_on" if "refused_on" in declared else (
            "refused" if "refused" in declared else "fires")
        if sorted(got[key]) != sorted(declared[key]):
            bad.append("%s %s: declared %s, measured %s"
                       % (guard, key, sorted(declared[key]), sorted(got[key])))
        if "silent" in declared and got.get("silent") != declared["silent"]:
            bad.append("%s silent: declared %r, measured %r"
                       % (guard, declared["silent"], got.get("silent")))
        if "not_applicable" in declared \
                and sorted(got.get("not_applicable") or []) != sorted(declared["not_applicable"]):
            bad.append("%s not-applicable: declared %r, measured %r"
                       % (guard, declared["not_applicable"], got.get("not_applicable")))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        bad, checks = selftest()
        for line in bad:
            print("FAIL", line)
        print("SELFTEST=%d (%d checks)" % (1 if bad else 0, checks))
        return 1 if bad else 0

    measured = measure()
    for line in _render(measured):
        print(line)
    if args.check:
        self_bad, self_checks = selftest()
        bad, checks = check(measured) + self_bad, self_checks
        for line in bad:
            print("FAIL", line)
        print("CHECK=%d (%d problem(s), %d selftest check(s))"
              % (1 if bad else 0, len(bad), checks))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
