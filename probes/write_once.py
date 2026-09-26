#!/usr/bin/env python3
"""Which write paths does a write-once registry actually refuse?

A registry that must not lose a registration can be guarded two ways: statically, by
reading the source (what `check.py:duplicate_declarations` does for this ledger), or at
run time, by a dict that raises when a key is written twice. The static guard sees the
code it is handed; the run-time guard sees only the writes that reach it, and Python's
dict has several write paths that do not all go through `__setitem__`.

This probe runs both questions over the same five write paths, because "the guard
refuses the second write" is a claim about a path, not about the guard:

  []=         R['k'] = v              -- calls `__setitem__`
  update      R.update(k=v)           -- C `dict.update` does not call `__setitem__`
  |=          R |= {'k': v}           -- `dict.__ior__` calls update, not `__setitem__`
  setdefault  R.setdefault('k', v)    -- silent in both; the FIRST write wins, so the
                                         loss is the other way round from the others
  decorator   @register('k')          -- the helper writes through `registry['k']`, so
                                         the write reaches the container like `[]=`

A silent path is not one outcome: `second-wins` means the first registration is gone,
`first-wins` means the second one is. Both are losses and both are printed.

The decorator column is measured twice. A helper that checks the registry itself
before writing refuses on EVERY container, a plain `dict` included -- which is not the
container guarding anything, it is the helper. That row is printed separately, because
counting it as the container's refusal is exactly the mistake this probe exists to
avoid: with the checking helper the plain-dict deafness check fires, and the probe
reports it.

Asked of the LEDGER's guard as well: the same five paths written as source text, run
through the guard this ledger uses, so a reader can see which paths a static guard can
cover that a run-time one cannot -- and which it misses anyway.

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

PATHS = ("[]=", "update", "|=", "setdefault", "decorator")

# Measured by this file, declared here so that a change to the paths or to the two
# guards fails `--check` instead of quietly printing a different table.
DECLARED = {
    "OnceDict": {"refused": ["[]=", "decorator"],
                 "silent": {"update": "second-wins",
                            "|=": "second-wins",
                            "setdefault": "first-wins"}},
    "OnceUserDict": {"refused": ["[]=", "update", "decorator"],
                     "silent": {"|=": "second-wins",
                                "setdefault": "first-wins"}},
    "checking helper": {"refused_on": ["dict", "OnceDict", "OnceUserDict"]},
    "ledger guard": {"fires": ["[]=", "|=", "subscript-union", "decorator"],
                     "silent": ["setdefault", "update"]},
}

# The write paths as source, twice each, for the static guard. Six, because the two
# union forms are two different pieces of code and the guard reads them separately.
SOURCES = {
    "[]=": ("NAMESPACES = {}\n"
            "NAMESPACES['c'] = {'n': lambda: 1}\n"
            "NAMESPACES['c'] = {'m': lambda: 2}\n"),
    "update": ("NAMESPACES = {}\n"
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
    "decorator": ("NAMESPACES = {}\n"
                  "def register_n():\n"
                  "    NAMESPACES['c'] = {'n': lambda: 1}\n"
                  "def register_m():\n"
                  "    NAMESPACES['c'] = {'m': lambda: 2}\n"),
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


OPERATIONS = {
    "[]=": lambda R, v: R.__setitem__("k", v),
    "update": lambda R, v: R.update({"k": v}),
    "|=": lambda R, v: R.__ior__({"k": v}),
    "setdefault": lambda R, v: R.setdefault("k", v),
    "decorator": lambda R, v: register(R, v)(lambda: None),
}


def run_path(cls, op) -> tuple:
    """Apply one write path twice to a fresh registry: refused, or which write survives.

    A sentinel class with `__setitem__` that raises nothing is the blindness check:
    if it refuses, the harness is broken rather than the guard working.
    """
    registry = cls()
    try:
        op(registry, 1)
        op(registry, 2)
    except KeyError:
        return "refused", None
    return "silent", ("second-wins" if registry["k"] == 2 else "first-wins")


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
        refused, silent = [], {}
        for label in PATHS:
            verdict, who = run_path(cls, OPERATIONS[label])
            if verdict == "refused":
                refused.append(label)
            else:
                silent[label] = who
        out[cls.__name__] = {"refused": refused, "silent": silent}
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
    for guard in ("OnceDict", "OnceUserDict", "checking helper", "ledger guard"):
        row = m[guard]
        if "refused_on" in row:
            lines.append("%-15s refuses on every container it was given: %s" % (
                guard, ", ".join(row["refused_on"]) or "none"))
        elif "refused" in row:
            lines.append("%-15s refuses %d of %d: %s" % (
                guard, len(row["refused"]), len(PATHS),
                ", ".join(row["refused"]) or "none"))
            lines.append("%-15s silent on: %s" % (
                "", ", ".join("%s (%s)" % (k, v) for k, v in sorted(row["silent"].items()))
                or "none"))
        else:
            lines.append("%-15s fires on %d of %d: %s" % (
                guard, len(row["fires"]), len(SOURCES), ", ".join(row["fires"])))
            lines.append("%-15s silent on: %s" % ("", ", ".join(row["silent"])))
    return lines


def selftest() -> list:
    bad = []
    # The instrument must be able to say "refused" at all, and must not say it when a
    # plain dict is handed the same five paths: otherwise the column is a constant.
    for label in PATHS:
        verdict, _ = run_path(dict, OPERATIONS[label])
        if verdict != "silent":
            bad.append("a plain dict refused %s: the harness reports refusals it did "
                       "not observe" % label)
    if run_path(OnceDict, OPERATIONS["[]="])[0] != "refused":
        bad.append("the write-once dict did not refuse a second `[]=`: the harness "
                   "cannot see a refusal")
    # The static column must move with the source: a source with one write only is not
    # a loss, so the guard must stay silent on it.
    if guard_over("NAMESPACES = {}\nNAMESPACES['c'] = {'n': lambda: 1}\n"):
        bad.append("the guard reports a single write as a loss")
    # And the two union forms must fire, or the declared cover of this probe is stale.
    for label in ("|=", "subscript-union"):
        if not guard_over(SOURCES[label]):
            bad.append("the guard stayed silent on the %s form" % label)
    return bad


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
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        bad = selftest()
        for line in bad:
            print("FAIL", line)
        print("SELFTEST=%d (%d checks)" % (1 if bad else 0, 3 + len(PATHS)))
        return 1 if bad else 0

    measured = measure()
    for line in _render(measured):
        print(line)
    if args.check:
        bad = check(measured) + selftest()
        for line in bad:
            print("FAIL", line)
        print("CHECK=%d (%d problem(s))" % (1 if bad else 0, len(bad)))
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
