#!/usr/bin/env python3
"""The vocabulary of refusal ids, read on this tree by the module that won the task.

`fragments.py` recognises a refusal by the id inside `FAIL[...]` and validates that id
against nothing, so an id can be named by a reader, quoted in prose and matched by no
writer -- the reader would accept a spelling no producer can emit. The two sides of that
vocabulary live in different files and nothing compared them.

`refusal_vocabulary.unemitted_ids(producers, consumers)` answers that comparison; its
shape, its rules (whole comment lines dropped, `[A-Z0-9-]+` between the brackets, a side
that names no id at all is a refusal) and the published suite it was judged by are in
`tasks/refusal-vocabulary/` of the hand-over repository. **This probe does not restate
it**: it imports the function and hands it the files below, so the answer is the winner's
and not a second implementation that could drift from it.

WHAT THIS FILE ADDS TO THE WINNER is the tree: which files are read as producers and which
as consumers, and the printed basis, because a set comparison over files that were never
read is a comparison over nothing.

  python3 probes/refusal_census.py             # the census
  python3 probes/refusal_census.py --check     # exit 1 when a consumer names an unemitted id
  python3 probes/refusal_census.py --plant     # prove the check can go red: write one unknown
                                               # id into a copy of a consumer and require rc=1

Standard library only. It reads the tree and writes only inside its own scratch directory.
"""
import argparse
import importlib.util
import re
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# THE PRODUCERS: the files that PRINT refusals. The list is named, not walked, and the
# reason is measured -- `--basis` on this tree reads 49 sites over the named files against
# 51 over a walk of every `.py` under the tree, because `verify/` holds thousands of files
# that are copies of this one and a walk would count the fixture as a second reader.
PRODUCERS = (
    ("probes/parts_of_a_reading.py",
     "prints FAIL[...] ids for the two-half readings it reads"),
    ("probes/word_of_status.py",
     "prints FAIL[...] ids for the word-of-status readings it reads"),
)

# THE CONSUMERS: the files that NAME refusal ids in order to recognise them.
CONSUMERS = (
    ("fragments.py",
     "recognises a refusal by the id inside FAIL[...]"),
)


def _winner():
    """The published module that won the task, imported from beside this file."""
    path = HERE / "refusal_vocabulary.py"
    spec = importlib.util.spec_from_file_location("refusal_vocabulary", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# THE SAME QUESTION ASKED OF THE TWO FILES THEMSELVES, AS A SECOND WITNESS. The winner's
# module answers the vocabulary question inside itself; the lines at the bottom of `census`
# ask it of the recognition file and the emission file directly. The two computations are
# printed side by side and required to agree, so neither is trusted alone -- and a tree that
# moves one of them is a disagreement rather than a green run.
THE_RECOGNITION_FILE = ROOT / "fragments.py"
THE_EMISSION_FILE = ROOT / "probes" / "parts_of_a_reading.py"
_THE_ID = re.compile(r"FAIL\[([A-Z0-9-]+)\]")


def the_ids_a_reader_names(path):
    """The ids one file carries, whole comment lines dropped."""
    text = path.read_text(encoding="utf-8", errors="replace")
    live = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    return set(_THE_ID.findall(live))


def _sources(root, paths):
    """(mapping for the winner, sites read per file) -- a file that is not here is refused."""
    sources, basis = {}, {}
    for path, why in paths:
        target = root / path
        if not target.exists():
            raise SystemExit("refused: %s is not in this tree, and %s" % (path, why))
        text = target.read_text(encoding="utf-8", errors="replace")
        sources[path] = text
        basis[path] = {"why": why, "lines": len(text.splitlines())}
    return sources, basis


def census(root):
    """(read, answer, basis) -- the winner's answer over THIS tree, with the basis printed."""
    producers, producer_basis = _sources(root, PRODUCERS)
    consumers, consumer_basis = _sources(root, CONSUMERS)
    read, answer = _winner().unemitted_ids(producers, consumers)
    basis = {"producers": producer_basis, "consumers": consumer_basis}
    if not read:
        return False, {}, basis
    answer["basis"] = basis
    # The tree's own two files, read directly: the containment the class is about.
    recognised = the_ids_a_reader_names(root / THE_RECOGNITION_FILE.relative_to(ROOT))
    printed = the_ids_a_reader_names(root / THE_EMISSION_FILE.relative_to(ROOT))
    uncontained = recognised - printed
    answer["the_two_files_read_directly"] = {
        "recognised": sorted(recognised),
        "printed": sorted(printed),
        "recognised_minus_printed": sorted(uncontained),
    }
    return True, answer, basis


def report(answer, basis):
    print("producers read (%d), consumers read (%d):" % (len(PRODUCERS), len(CONSUMERS)))
    for side, entries in basis.items():
        for path, info in entries.items():
            print("  %-34s %6d lines  %s" % (path, info["lines"], info["why"]))
    emitted = sorted({i for ids in answer["emitted"].values() for i in ids})
    named = sorted({i for ids in answer["named"].values() for i in ids})
    print("ids emitted by the producers (%d): %s" % (len(emitted), ", ".join(emitted)))
    print("ids named by the consumers (%d): %s" % (len(named), ", ".join(named)))
    unemitted = {p: v for p, v in answer["unemitted"].items() if v}
    total = sum(len(v) for v in answer["unemitted"].values())
    print("consumer names not emitted by any producer: %d" % total)
    for path, entries in answer["unemitted"].items():
        for token, line in entries:
            print("  UNEMITTED %s:%d  %s" % (path, line, token))
    # The same question asked of the two files directly, and the two answers compared.
    direct = answer["the_two_files_read_directly"]
    print("asked of the two files themselves: %d recognised, %d printed, %d recognised that "
          "nothing prints" % (len(direct["recognised"]), len(direct["printed"]),
                              len(direct["recognised_minus_printed"])))
    agree = (set(direct["recognised"]) == set(named)
             and set(direct["recognised_minus_printed"]) == {t for v in answer["unemitted"]
                                                             .values() for t, _ in v})
    print("the two computations agree on the ids named: %s" % ("yes" if agree else "NO"))
    if not agree:
        print("  the module named: %s" % ", ".join(named))
        print("  the files carry:  %s" % ", ".join(direct["recognised"]))
    print("REFUSAL_CENSUS=%s" % ("NOT ok" if unemitted or not agree else "ok"))
    return not unemitted and agree


def plant(root):
    """Write one unknown id into a COPY of a consumer and require the check to go red.

    The check is run on the copy, never on the tree, and the plant prints that it landed
    exactly once -- a plant that changed nothing proves nothing about the check.
    """
    scratch = Path(tempfile.mkdtemp(prefix="plant-", dir=str(HERE)))
    try:
        for table in (PRODUCERS, CONSUMERS):
            for path, _ in table:
                (scratch / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(root / path, scratch / path)
        target = CONSUMERS[0][0]
        text = (scratch / target).read_text(encoding="utf-8", errors="replace")
        marker = 'FAIL[NO-SUCH-ID]'
        if marker in text:
            print("PLANT=not ok -- the marker was already there")
            return 1
        written = text + "\n# planted by --plant\nfail(marker=%s)\n" % repr(marker)
        (scratch / target).write_text(written, encoding="utf-8")
        landed = (scratch / target).read_text(encoding="utf-8").count(marker)
        print("PLANT: wrote %s into the copy of %s, %d time(s)" % (marker, target, landed))
        if landed != 1:
            print("PLANT=not ok -- the plant did not land exactly once")
            return 1
        read, answer, _ = census(scratch)
        total = sum(len(v) for v in answer.get("unemitted", {}).values()) if read else 0
        expected = next(n for n, line in enumerate(written.splitlines(), 1) if marker in line)
        print("PLANT: the marker is on line %d of the copy" % expected)
        print("PLANT: the check on the copy read %d unemitted id(s)" % total)
        ok = read and total == 1 and answer["unemitted"][target] == [["NO-SUCH-ID", expected]]
        print("PLANT=%s" % ("ok" if ok else "not ok"))
        return 0 if ok else 1
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def main(argv):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--plant", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.plant:
        return plant(root)
    read, answer, basis = census(root)
    if not read:
        print("REFUSAL_CENSUS=refused -- the winner refused the inputs")
        return 3
    ok = report(answer, basis)
    if args.check:
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
