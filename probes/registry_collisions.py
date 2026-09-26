#!/usr/bin/env python3
"""Which of the ways a registration can be lost does the registry's guard cover?

A registration is a (class, fragment name) pair. The registry `NAMESPACES` can lose
one in three forms, and they are not the same code:

  F1  the whole-dict literal `NAMESPACES = {...}` declares one class twice -- a dict
      literal accepts a repeated key and keeps the last, so the earlier mapping is
      live in the source a reader edits first and dead as soon as the module loads;
  F2  `NAMESPACES['cls'] = {...}` is written twice for one class -- same keeping
      rule, one level down: the first assignment's fragment name is gone;
  F3  one dict literal declares the same fragment name twice, so the first fragment
      body is replaced by the second.

F2 and F3 are the forms that actually bit this ledger: a repair commit replaced a
second `NAMESPACES['cls'] = {...}` with `NAMESPACES.setdefault('cls', {}).update(...)`,
because the second assignment had silently dropped a name the first one carried.

`check.py:duplicate_declarations` is the guard. This probe asks it the question three
times, on three mutated copies of the real source, one per form -- the rule is called
as `check.py` calls it, in a directory where `fragments.py` is the mutant, so the probe
is not restating the rule -- and prints which forms it refuses. The declared cover is a
constant in this file: a form this guard covers because the code was widened to cover
it is declared, not discovered.

    python3 registry_collisions.py            # the guard's cover and the live census
    python3 registry_collisions.py --selftest # the guard fires on the mutants, and
                                              # the body scan sees a replaced body

WHAT THIS DOES NOT DO, named rather than hidden:
  * It reads the source text and the loaded module; it does not run `check.py` to the
    end, so it says nothing about whether the ledger is otherwise green.
  * "A name whose body comes from two definition sites" is a reading of `__code__`
    filenames and line numbers. Two functions built from the same text by two `exec`
    calls would read as one site.
"""
import argparse
import importlib
import os
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = ROOT / "fragments.py"

# Which forms the guard in check.py is DECLARED to cover. F1 alone is what it covered
# before this probe existed: it walks top-level assignments whose target is the NAME
# `NAMESPACES`, which is the whole-dict form only.
DECLARED_COVER = ("F1", "F2", "F3")

MUTANTS = {
    "F1": "\nNAMESPACES = {'zzz-mutant-f1': {}, 'zzz-mutant-f1': {}}\n",
    "F2": ("\nNAMESPACES['zzz-mutant-f2'] = {'n': None}\n"
           "NAMESPACES['zzz-mutant-f2'] = {'m': None}\n"),
    "F3": "\nNAMESPACES['zzz-mutant-f3'] = {'n': None, 'n': None}\n",
}


def load_check():
    """The guard as the ledger loads it: check.py, with ROOT on the path."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return importlib.import_module("check")


def fires(check, text: str) -> list[str]:
    """Run the guard over a mutant in the directory it reads `fragments.py` from."""
    with tempfile.TemporaryDirectory(prefix="collisions-") as d:
        (Path(d) / "fragments.py").write_text(text, encoding="utf-8")
        cwd = os.getcwd()
        os.chdir(d)
        try:
            return check.duplicate_declarations()
        finally:
            os.chdir(cwd)


def cover(check, source: str) -> dict:
    """Which mutant each form makes the guard report, measured, not declared."""
    return {form: bool(fires(check, source + tail)) for form, tail in MUTANTS.items()}


def scan(namespaces) -> dict:
    """The live registry: how many names, and which of them are shared or replaced."""
    registrations = 0
    by_name = defaultdict(set)
    body = defaultdict(set)
    for cls, mapping in namespaces.items():
        for name, fn in mapping.items():
            registrations += 1
            by_name[name].add(cls)
            code = getattr(fn, "__code__", None)
            if code is not None:
                body[name].add((code.co_filename, code.co_firstlineno))
    shared = {n: sorted(c) for n, c in by_name.items()
              if len(c) > 1 and len(body.get(n, ())) == 1}
    replaced = sorted(n for n, sites in body.items() if len(sites) > 1)
    return {"classes": len(namespaces),
            "registrations": registrations,
            "distinct_names": len(by_name),
            "names_in_more_than_one_class": len([n for n, c in by_name.items()
                                                 if len(c) > 1]),
            "shared_one_body": shared,
            "names_with_replaced_bodies": replaced}


def selftest(source: str) -> list[str]:
    """The falsifiers. Each one fails the run when the instrument goes blind."""
    bad = []
    check = load_check()

    live = fires(check, source)
    if live:
        bad.append("the guard reports the REAL source: %r" % (live,))

    seen = cover(check, source)
    for form in sorted(MUTANTS):
        covered = form in DECLARED_COVER
        if covered and not seen[form]:
            bad.append("%s is declared covered and the guard stayed silent" % form)
        if not covered and seen[form]:
            bad.append("%s is not declared and the guard fired -- the declaration is stale"
                       % form)

    def fn_a():
        pass

    def fn_b():
        pass

    # A name shared by two classes with ONE body: the registry keys by the shape of the
    # lie, so this is the intended case and must not read as a loss.
    shared_ns = {"class-one": {"shared_name": fn_a}, "class-two": {"shared_name": fn_a}}
    s = scan(shared_ns)
    if s["names_with_replaced_bodies"]:
        bad.append("a name shared by two classes with one body read as replaced: %r"
                   % (s["names_with_replaced_bodies"],))
    if s["names_in_more_than_one_class"] != 1:
        bad.append("the shared case did not reach the census")

    # The same name carrying two bodies IS the loss F2/F3 produce.
    replaced_ns = {"class-one": {"lost_name": fn_a}, "class-two": {"lost_name": fn_b}}
    r = scan(replaced_ns)
    if r["names_with_replaced_bodies"] != ["lost_name"]:
        bad.append("a replaced body was not reported: %r"
                   % (r["names_with_replaced_bodies"],))

    # A namespace that dropped a registry entry entirely cannot be seen by scan(); it is
    # the census that would move, so the probe's own numbers must be internally sound.
    if sum(len(m) for m in shared_ns.values()) != 2:
        bad.append("the census does not count the registrations it walked")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="fail unless the measured cover equals the declared one")
    args = ap.parse_args()

    source = SOURCE.read_text(encoding="utf-8")

    if args.selftest:
        bad = selftest(source)
        for line in bad:
            print("FAIL", line)
        print("SELFTEST=%d (%d checks)" % (1 if bad else 0, 8))
        return 1 if bad else 0

    check = load_check()
    seen = cover(check, source)
    for form, tail in sorted(MUTANTS.items()):
        print("form %s  guard fires: %-5s  %s"
              % (form, seen[form], tail.strip().replace("\n", " | ")))
    live_guard = fires(check, source)
    print("live source   guard reports: %r" % (live_guard,))
    declared = sorted(DECLARED_COVER)
    measured = sorted(f for f, v in seen.items() if v)
    print("cover declared %s / measured %s" % (declared, measured))

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    frag = importlib.import_module("fragments")
    s = scan(frag.NAMESPACES)
    print("classes %(classes)d  registrations %(registrations)d  distinct names "
          "%(distinct_names)d  in more than one class %(names_in_more_than_one_class)d"
          % s)
    print("names with a replaced body: %r" % (s["names_with_replaced_bodies"],))
    for name, classes in sorted(s["shared_one_body"].items()):
        print("  shared one body: %s <- %s" % (name, ", ".join(classes)))

    bad = []
    if live_guard:
        bad.append("the guard reports the live source")
    if measured != declared:
        bad.append("cover declared %s, measured %s" % (declared, measured))
    if s["names_with_replaced_bodies"]:
        bad.append("a fragment body is replaced in the live registry: %r"
                   % (s["names_with_replaced_bodies"],))
    for line in bad:
        print("FAIL", line)
    print("CHECK=%d" % (1 if bad else 0))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
