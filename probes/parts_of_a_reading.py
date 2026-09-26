#!/usr/bin/env python3
"""The second half of a two-half reading, and whether anything ever reads it.

A class whose two readings are computed side by side carries a helper --
`_readings_of_<something>` -- that returns `{"as_written": ..., "as_repaired": ...}`,
and a public fragment that returns `helper()["as_written"]`. `check.py` runs the PUBLIC
fragment and compares its answer with the entry's `observed`; the entry's `expected` is
the repaired half. Nothing in the repository called the helper for the repaired half, so
the half that says what the repair DOES was measured by nothing: a helper whose repaired
reading is a constant, or whose two halves are the same value, left `check.py`,
`selftest.py` and `verify_claims.py` all green.

This item reads the helper rather than the fragment. For every `_readings_of_*` in
`fragments.py` it requires:

  * both halves present, and the two halves DIFFERENT -- a helper whose repaired reading
    equals the written one has nothing to say about the repair, whichever of the two
    shapes it answers in (a dict of two halves, or the older `(written, repaired)` tuple);
  * `repr(as_written)` equal to the `observed` of the entry that probes it, and
    `repr(as_repaired)` equal to that entry's `expected`, so the repaired half is read,
    compared and quoted by a suite item rather than described in prose;
  * at least one ledger entry whose probe reads that helper, so a half cannot be added
    without something reading it -- a class's own `probe`, or the `fn` of one of its
    repeats: both records carry `observed`/`expected`, and a reader that walked `probe`
    alone read a helper named only by a repeat as one nothing reads.

    python3 probes/parts_of_a_reading.py            # every helper, and its verdict
    python3 probes/parts_of_a_reading.py --check    # exit 1 when a half is unmeasured
    python3 probes/parts_of_a_reading.py --selftest # build four trees, require three reds

WHAT THIS DOES NOT DO: it compares the halves against the ENTRY, so an entry whose
`expected` was typed from the same wrong reading passes here -- the second half is then
measured against itself. What it does reach is the case that occurred: a repaired half
that nothing called at all.
"""
import argparse
import importlib.util
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
HELPER = re.compile(r"^def (_readings_of_\w+)\s*\(", re.M)
PUBLIC = re.compile(r"^def (\w+)\s*\(", re.M)


def load(root: pathlib.Path):
    """The fragments module and the ledger of `root`, read from that tree."""
    spec = importlib.util.spec_from_file_location("fragments_probe_subject",
                                                  root / "fragments.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ledger = json.loads((root / "catches.json").read_text(encoding="utf-8"))
    return mod, ledger


def defs_of(source: str) -> dict:
    """Top-level function name -> its body, in the order they appear."""
    marks = [(m.start(), m.group(1)) for m in PUBLIC.finditer(source)]
    out = {}
    for i, (start, name) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(source)
        out[name] = source[start:end]
    return out


def probes_that_read(helper: str, defs: dict) -> list:
    """Public fragments that call this helper."""
    return sorted(name for name, body in defs.items()
                  if name != helper and f"{helper}()" in body)


def readers_of_entries(ledger: dict) -> dict:
    """`<fragment>()` -> `(entry index, repeat index or None, the record with the halves)`.

    A helper is read against a record that carries `observed` and `expected`. For a class
    that record is the entry; for a repeat it is the repeat's own fingers on the same
    bytes. Walking `probe` alone made a helper named by a repeat's `fn` look unread, so the
    witness a repeat's fragment gives was not counted.
    """
    out = {}
    for i, entry in enumerate(ledger["entries"]):
        if entry.get("probe"):
            out.setdefault(entry["probe"], (i, None, entry))
        for j, rep in enumerate(entry.get("repeats") or []):
            if isinstance(rep, dict) and rep.get("fn"):
                out.setdefault(f"{rep['fn']}()", (i, j, rep))
    return out


def record_name(record: dict) -> str:
    """What to call the record in a line: its class, or the shape its repeat names."""
    return record.get("class") or record.get("id") or "an unnamed record"


def normalise(answer):
    """A helper's answer as the two halves, whichever of the two shapes it uses.

    This repository writes the pair both ways: `{"as_written": ..., "as_repaired":
    ...}`, and the older `(written, repaired)` tuple that the public fragment reads as
    `[0]`. Both are read here rather than one convention being declared the rule.
    """
    if isinstance(answer, dict) and set(answer) == {"as_written", "as_repaired"}:
        return answer
    if isinstance(answer, tuple) and len(answer) == 2:
        return {"as_written": answer[0], "as_repaired": answer[1]}
    return answer


def readings(root: pathlib.Path):
    """Every helper in `fragments.py`, its two halves, and the entries that read it."""
    source = (root / "fragments.py").read_text(encoding="utf-8")
    defs = defs_of(source)
    mod, ledger = load(root)
    by_probe = readers_of_entries(ledger)
    rows = []
    for name, _body in defs.items():
        if not HELPER.match(f"def {name}("):
            continue
        halves = normalise(getattr(mod, name)())
        readers = probes_that_read(name, defs)
        measured = []
        for reader in readers:
            found = by_probe.get(f"{reader}()")
            if found is None:
                continue
            entry = found[2]
            measured.append((reader, entry,
                             repr(halves.get("as_written")) == entry["observed"],
                             repr(halves.get("as_repaired")) == entry["expected"]))
        rows.append((name, halves, readers, measured))
    return rows


def helper_names_typed_into(source: str) -> list:
    """Every literal list of `_readings_of_*` names written into `fragments.py`.

    A list typed into the source is a sentence about the file on the day it was typed.
    One such list stood beside the comment "every `_readings_of_*` in fragments.py" and
    named eight of the fourteen helpers the file defines: the class it was the data for
    published a tally of eight helpers, and nothing compared the list with the file. The
    question this asks is the one the comment claimed: does the list cover the file?
    """
    import ast

    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.List, ast.Tuple)) or len(node.elts) < 2:
            continue
        names = []
        for element in node.elts:
            if isinstance(element, ast.Constant) and isinstance(element.value, str):
                names.append(element.value)
            elif isinstance(element, ast.Tuple) and element.elts and isinstance(
                    element.elts[0], ast.Constant) and isinstance(element.elts[0].value, str):
                names.append(element.elts[0].value)
            else:
                names = []
                break
        if names and all(n.startswith("_readings_of_") for n in names):
            found.append((node.lineno, names))
    return found


def tallies_that_do_not_cover_the_file(source: str) -> list:
    """The typed lists that do not name every helper this file defines.

    The rule reads the list against the file one way: a list that claims the file and
    misses some of it is the defect this asks about. Names that no helper answers to are
    reported with the line but are not a refusal -- a tree under test may name a helper of
    its neighbour, and the case of a helper REMOVED from the file with its name left behind
    is a different class, measured in this repository as
    `a-census-taken-from-the-thing-it-counts`.
    """
    defined = set(HELPER.findall(source))
    out = []
    for line, names in helper_names_typed_into(source):
        missing = sorted(defined - set(names))
        if missing:
            out.append((line, len(names), sorted(defined), missing,
                        sorted(set(names) - defined)))
    return out


def verdicts(rows) -> list:
    """One line per helper, and whether this tree may be green."""
    lines, bad = [], 0
    for name, halves, readers, measured in rows:
        if not isinstance(halves, dict) or set(halves) != {"as_written", "as_repaired"}:
            lines.append(f"FAIL {name} does not answer with two halves: "
                         f"{type(halves).__name__} {halves!r}"[:160])
            bad += 1
            continue
        if repr(halves["as_written"]) == repr(halves["as_repaired"]):
            lines.append(f"FAIL {name} has two halves with one value: the repaired "
                         f"reading is the written one")
            bad += 1
        if not measured:
            lines.append(f"FAIL {name} is read by no ledger entry: "
                         f"{readers or 'no public fragment calls it'}")
            bad += 1
            continue
        for reader, entry, written_ok, repaired_ok in measured:
            if written_ok and repaired_ok:
                lines.append(f"ok   {name} -- both halves read against "
                             f"{record_name(entry)}")
            else:
                lines.append(f"FAIL {record_name(entry)}: the helper's "
                             f"{'written' if not written_ok else 'repaired'} half is not "
                             f"the one the entry records")
                bad += 1
    return lines, bad


# ---------------------------------------------------------------- selftest

REDEFINE = '''

_first_helper = %s
def %s():
    r = _first_helper()
    if isinstance(r, dict):
        r["as_repaired"] = r["as_written"]
    else:
        r = (r[0], r[0])
    return r
'''

TYPED_LIST = '''

def _a_list_typed_before_the_file_grew():
    # every _readings_of_* in fragments.py
    NAMES = [%s]
    return NAMES
'''


def entry_index_for(root: pathlib.Path, helper: str):
    """Where the record that reads this helper lives: `(entry index, repeat index or None)`."""
    source = (root / "fragments.py").read_text(encoding="utf-8")
    defs = defs_of(source)
    ledger = json.loads((root / "catches.json").read_text(encoding="utf-8"))
    readers = probes_that_read(helper, defs)
    found = readers_of_entries(ledger)
    for reader in readers:
        hit = found.get(f"{reader}()")
        if hit is not None:
            return hit[0], hit[1]
    return None


def patch(root: pathlib.Path, name: str, kind: str) -> None:
    """Break one half of one helper, in a throwaway copy of the two files."""
    frag = root / "fragments.py"
    if kind == "same-value":
        frag.write_text(frag.read_text(encoding="utf-8") + REDEFINE % (name, name),
                        encoding="utf-8")
        return
    ledger_path = root / "catches.json"
    data = json.loads(ledger_path.read_text(encoding="utf-8"))
    index = entry_index_for(root, name)
    if index is None:
        raise SystemExit(f"the copy under test has no entry reading {name}")
    i, j = index
    record = (data["entries"][i] if j is None
              else data["entries"][i]["repeats"][j])
    if kind == "expected-is-written":
        record["expected"] = record["observed"]
    elif kind == "no-reader":
        if j is None:
            del data["entries"][i]
        else:
            del data["entries"][i]["repeats"][j]
    ledger_path.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True),
                           encoding="utf-8")


def selftest() -> int:
    """Three broken trees must be refused, and the untouched copy must not."""
    src = ROOT
    bad = 0
    with tempfile.TemporaryDirectory(prefix="parts-reading-") as td:
        base = pathlib.Path(td) / "base"
        base.mkdir()
        for name in ("fragments.py", "catches.json"):
            shutil.copy(src / name, base / name)
        code = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                               "--check", "--root", str(base)],
                              capture_output=True, text=True)
        ok = code.returncode == 0
        bad += 0 if ok else 1
        # The copy under test is the tree this probe lives in. When that tree carries the
        # defect, the first refusal is the finding, not a broken fixture -- so the line
        # names it instead of leaving the reader to guess which of the two happened.
        why = next((ln for ln in code.stdout.splitlines() if ln.startswith("FAIL")), "")
        print(f"{'ok  ' if ok else 'FAIL'} an untouched copy is not refused "
              f"(exit {code.returncode})" + (f": {why}" if why else ""))

        # Every helper in the tree must be REPORTED, not merely looked at: a control that
        # silently drops a shape from its own universe -- the tuple convention three of
        # these helpers still use -- shows a shorter list and an unbroken exit code.
        source_names = set(HELPER.findall((src / "fragments.py").read_text(encoding="utf-8")))
        unreported = sorted(n for n in source_names if n not in code.stdout)
        bad += 1 if unreported else 0
        print(f"{'ok  ' if not unreported else 'FAIL'} every helper in the tree is reported "
              f"({len(source_names) - len(unreported)}/{len(source_names)})"
              + (f": unreported {unreported}" if unreported else ""))

        rows = readings(base)
        first = rows[0][0] if rows else None
        if first is None:
            print("FAIL the copy under test has no helper at all")
            return 1
        for kind, what in (("same-value", "a helper whose two halves are one value"),
                           ("expected-is-written", "an entry recording the written half "
                                                   "as its expected"),
                           ("no-reader", "a helper no entry reads")):
            tree = pathlib.Path(td) / kind
            tree.mkdir()
            for name in ("fragments.py", "catches.json"):
                shutil.copy(src / name, tree / name)
            patch(tree, first, kind)
            code = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                                   "--check", "--root", str(tree)],
                                  capture_output=True, text=True)
            caught = code.returncode == 1
            bad += 0 if caught else 1
            print(f"{'ok  ' if caught else 'FAIL'} {what} is refused "
                  f"(exit {code.returncode})")

        # A list typed into the source is a tally of the file on the day it was typed. The
        # one this arm builds names every helper the file defines but one, and the arm that
        # would have caught the eight-name list standing beside "every _readings_of_*".
        tree = pathlib.Path(td) / "typed-list"
        tree.mkdir()
        for name in ("fragments.py", "catches.json"):
            shutil.copy(src / name, tree / name)
        frag = tree / "fragments.py"
        defined = sorted(set(HELPER.findall((src / "fragments.py").read_text(encoding="utf-8"))))
        typed = ", ".join('"%s"' % n for n in defined[:-1])
        frag.write_text(frag.read_text(encoding="utf-8") + TYPED_LIST % typed,
                        encoding="utf-8")
        code = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                               "--check", "--root", str(tree)],
                              capture_output=True, text=True)
        caught = code.returncode == 1
        bad += 0 if caught else 1
        print(f"{'ok  ' if caught else 'FAIL'} a list typed beside the file that does not "
              f"name every helper it defines is refused (exit {code.returncode})")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    root = pathlib.Path(args.root)
    source = (root / "fragments.py").read_text(encoding="utf-8")
    rows = readings(root)
    lines, bad = verdicts(rows)
    for line in lines:
        print(line)
    stale = tallies_that_do_not_cover_the_file(source)
    for line, named, defined, missing, extra in stale:
        print(f"FAIL fragments.py:{line} types {named} name(s) beside the file's "
              f"{len(defined)}: never named {missing or '[]'}, not defined {extra or '[]'}")
    print(f"helpers with two halves  {len(rows)}")
    print(f"halves not read against an entry  {bad}")
    print(f"typed lists that do not cover the file  {len(stale)}")
    if args.check and (bad or stale):
        print("REFUSED: a helper's half is not the one the entry records, or nothing in this "
              "repository reads it -- either way the half that says what the repair does is "
              "unwitnessed, so it can be a constant and every suite stays green; or a list "
              "typed into fragments.py no longer covers the helpers the file defines, so a "
              "tally taken from it is a sentence about an older file")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
