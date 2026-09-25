#!/usr/bin/env python3
"""Turn a label into an answer: what was the fragment behind that receipt?

A label in catches.json records only that an instance arrived -- "v1026" names a
check this ledger's author ran once, and that check's bytes were never published.
This script takes the labels whose original source files are still on hand, loads
those fragments, and asks the ledger's own gate what each one actually was:

  OBJECT   a second sighting with bytes of its own -- becomes a replayed repeat
  CLASS    the class fragment again under another name -- becomes a retired repeat
  MOVE     it belongs to another class, so the label was filed under the wrong one
  NOFILE   the source file is gone; the label stays a label

Nothing here decides by hand: the verdict is the fingerprint comparison check.py
already enforces, plus a probe run to confirm the recorded observation.

    python3 recover_labels.py            # report
    python3 recover_labels.py --write    # apply OBJECT/MOVE/CLASS to catches.json
"""

import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parent
sys.path.insert(0, str(HERE))

import check  # noqa: E402
from fragments import NAMESPACES  # noqa: E402

# label -> (class it is filed under, source file, function in that file,
#           the probe, what the promise said, what the code did)
RECOVERIES = {
    "v960": ("dedupe-adjacent-vs-global", "dedupe_adjacent_global_catch.py",
             "dedupe_adjacent", "dedupe_adjacent_rec([1, 2, 1])", "[1, 2]", "[1, 2, 1]"),
    "v975": ("title-case-touches-rest-of-word", "title_case_rest_catch.py",
             "title_case", 'title_case_rec("don\'t stop")', '"Don\'t Stop"', '"Don\'T Stop"'),
    "v989": ("dedupe-sorted-set-reorders", "dedupe_sorted_mutate_catch.py",
             "dedupe_sorted", "dedupe_sorted_rec([1, 1, 2])", "[1, 1, 2]", "[1, 2]"),
    "v1005": ("charset-strip-vs-affix-removal", "remove_prefix_lstrip_catch.py",
              "remove_prefix", "remove_prefix_rec('ababa', 'ab')", "'aba'", "''"),
    "v1022": ("reverse-slice-on-negative-index", "take_neg_catch.py",
              "take", "take_neg_rec([1, 2, 3, 4], -1)", "[]", "[1, 2, 3]"),
    "v1026": ("dedupe-sorted-set-reorders", "unique_set_order_catch.py",
              "unique", "unique_rec([0, 2, 1])", "[0, 2, 1]", "[0, 1, 2]"),
    "v1027-find_max": ("empty-max-raises", "find_max_empty_catch.py",
                       "find_max", "find_max_rec([])", "None", "ValueError"),
    "v1030": ("bankers-rounding-on-half", "round_price_float_catch.py",
              "round_price", "round_price_rec(2.675)", "2.68", "2.67"),
    "v1036": ("zip-truncates-remainder", "chunk_pairs_odd_catch.py",
              "pairs", "pairs_rec([1, 2, 3])", "[(1, 2), (3,)]", "[(1, 2)]"),
    "v1037": ("row-alias-in-grid-build", "clone_matrix_shallow_catch.py",
              "clone_matrix", "clone_matrix_rec([[1, 2]]) mutation probe",
              "[[1, 2]]", "[[1, 2, 99]]"),
    "v1048": ("dict-update-overwrites-first", "merge_configs_order_catch.py",
              "merge_configs", "merge_configs_rec({'a': 1}, {'a': 2})",
              "{'a': 2}", "{'a': 1}"),
    "v1057": ("iterator-exhausted-twice", "minmax_iter_catch.py",
              "min_max", "min_max_rec(iter([3, 1, 2]))", "(1, 3)", "ValueError"),
    "v1062": ("row-alias-in-grid-build", "clone_one_level_catch.py",
              "clone_matrix", "clone_matrix_rec2([[1, 2]]) mutation probe", "[[1, 2]]", "[[1, 2, 99]]"),
    "v1063": ("bankers-rounding-on-half", "round_half_up_neg_catch.py",
              "round_half_up", "round_half_up_rec(-1.6)", "-2", "-1"),
    "v1064": ("bool-subclass-counted-as-int", "count_integers_bool_catch.py",
              "count_integers", "count_integers_rec([True, False, 1])", "1", "3"),
    "v1067": ("late-binding-loop-variable", "splitlines_keepends_catch.py",
              "lines", "splitlines_rec('a\\nb\\n')", "['a\\n', 'b\\n']", "['a', 'b']"),
    "v1073": ("charset-strip-vs-affix-removal", "strip_prefix_lstrip_after_start_catch.py",
              "strip_prefix", "strip_prefix_rec('https://hats.com', 'https://')",
              "'hats.com'", "'ats.com'"),
    "is_nondecreasing-20260922": ("strict-comparison-defeats-non-decreasing",
                                  "is_sorted_strict_catch.py", "is_sorted",
                                  "is_sorted_strict_rec([1, 2, 2, 3])", "True", "False"),
    "strip_suffix-rstrip-20260922": ("charset-strip-vs-affix-removal", "strip_charset_catch.py",
                                     "remove_prefix_suffix",
                                     "remove_prefix_suffix_rec('abXba', 'ab')", "'Xba'", "'X'"),
}

# labels whose receipt was a run of this ledger rather than a fragment: the
# receipt names the whole registry being green, and no shape of its own
RUNS = {
    "v1044": "charset-strip-vs-affix-removal",
    "v1066": "dedupe-sorted-set-reorders",
    "v1070": "mutable-default-shared-across-calls",
    "v1077": "dedupe-sorted-set-reorders",
}

# probes that need a mutation to show the lie: (probe template, expected, observed)
# {fn} is replaced with the recovered function's name
MUTATING = {
    "v1037": ("(lambda m: ({fn}(m)[0].append(99), m[0])[-1])([[1, 2]])",
              "[1, 2]", "[1, 2, 99]"),
    "v1062": ("(lambda m: ({fn}(m)[0][0].append(9), m[0][0])[-1])([[[1]]])",
              "[1]", "[1, 9]"),
}


# Where a fragment's source bytes are looked for, in order. The repo carries the
# files it names, so the record regenerates from a clone alone; the workspace is
# the fallback for a file that has not been carried over yet, and a row recovered
# from there is marked uncheckable rather than cited like the others.
SOURCE_DIRS = (HERE / "provenance", WORKSPACE)


def find_source(filename: str):
    """The path the bytes are at, and whether a reader of this repo can reach it."""
    for i, root in enumerate(SOURCE_DIRS):
        path = root / filename
        if path.exists():
            return path, i == 0
    return None, False


def load_fragments():
    """Copy the named functions out of the source catch files into one module."""
    parts = ["import copy\n\n"]
    names = {}
    for label, (cls, filename, fn, *_rest) in RECOVERIES.items():
        path, _carried = find_source(filename)
        if path is None:
            print(f"NOFILE {label:<26} {filename} is gone")
            continue
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        picked = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fn]
        if not picked:
            print(f"NOFILE {label:<26} {filename} has no {fn}()")
            continue
        base = f"{fn}_rec"
        new_name = base
        n = 2
        while new_name in names:
            new_name = f"{base}{n}"
            n += 1
        src = ast.get_source_segment(text, picked[0])
        parts.append(src.replace(f"def {fn}(", f"def {new_name}(", 1) + "\n\n")
        names[new_name] = label
    if len(parts) == 1:
        raise SystemExit("no source files left; nothing to recover")
    tmp = Path(tempfile.mkdtemp()) / "recovered_fragments.py"
    tmp.write_text("".join(parts), encoding="utf-8")
    spec = importlib.util.spec_from_file_location("recovered_fragments", tmp)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, names


def verdicts(module, names):
    by_class = {e["class"]: e for e in check.load()["entries"]}
    primaries = {}
    for entry in by_class.values():
        base = check.primary(entry)
        if base:
            primaries[entry["class"]] = check.fingerprint(NAMESPACES[entry["class"]][base])
    out = []
    for fn_name, label in names.items():
        cls, filename, _fn, probe, expected, observed = RECOVERIES[label]
        if label in MUTATING:
            tmpl, expected, observed = MUTATING[label]
            probe = tmpl.replace("{fn}", fn_name)
        fn = getattr(module, fn_name)
        fp = check.fingerprint(fn)
        # The provenance is a reading only if the bytes it names are in this repo:
        # the digest is of the file the fragment was taken from, and check.py
        # resolves it against `provenance/`. A file still only in the workspace is
        # a memory of the run, and says so rather than reading like a citation.
        src, carried = find_source(filename)
        row = {"label": label, "class": cls,
               "file": f"provenance/{filename}" if carried else filename,
               "file_checkable": bool(carried),
               "sha256": (hashlib.sha256(src.read_bytes()).hexdigest()
                          if src is not None else None),
               "fn": fn_name, "source_fn": _fn,
               "probe": probe, "expected": expected, "observed": observed}
        if fp == primaries.get(cls):
            row["verdict"] = "CLASS"
        else:
            others = [c for c, p in primaries.items() if p == fp and c != cls]
            if others:
                row["verdict"] = "MOVE"
                row["belongs_to"] = others[0]
            else:
                try:
                    got = eval(probe, {fn_name: fn, "copy": __import__("copy")})
                except Exception as exc:
                    got = type(exc).__name__
                row["actual"] = repr(got)
                ok = repr(got) == observed if not isinstance(got, str) or got != observed else True
                row["replays"] = ok
                if not ok:
                    row["verdict"] = "CHECK"
                elif fp in [check.fingerprint(NAMESPACES[cls][k])
                            for k in NAMESPACES.get(cls, {}) if k != check.primary(by_class[cls])]:
                    row["verdict"] = "CLASS"
                else:
                    row["verdict"] = "OBJECT"
        out.append(row)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    module, names = load_fragments()
    rows = verdicts(module, names)
    counts = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1
        print(f"{row['verdict']:<7} {row['label']:<26} {row['class']:<45} "
              f"{row.get('actual', ''):<14} {row.get('belongs_to', '')}")
    print()
    print(" ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    for label, cls in RUNS.items():
        rows.append({"label": label, "class": cls, "verdict": "RUN",
                     "file": "", "file_checkable": False, "sha256": None,
                     "fn": "", "probe": "", "expected": "", "observed": "",
                     "replays": None})
        counts["RUN"] = counts.get("RUN", 0) + 1
        print(f"{'RUN':<7} {label:<26} {cls:<45} receipt of a ledger run, not a fragment")
    missing = [lab for lab in RECOVERIES if lab not in {r["label"] for r in rows}]
    print(f"labels with no source file left: {len(missing)} {missing}")
    (HERE / "label_recovery.json").write_text(
        json.dumps({"rows": rows, "missing": missing}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if args.write:
        apply(rows, module)
    return 0


PROMISES = {
    "v960": ("removes duplicate values, keeping the first occurrence of each",
             "only neighbours are compared, so a repeat that is not adjacent survives"),
    "v975": ("the rest of the word keeps its case",
             "str.title lowercases the rest of every word and treats the apostrophe as a word break"),
    "v989": ("the sorted list comes back deduplicated and the original is untouched",
             "the duplicates are deleted from the caller's own list, which is then returned"),
    "v1026": ("the values in the order they first appear",
             "the set has no order of its own, so a re-inserted value moves to the end"),
    "v1030": ("rounded to the cent, half away from zero",
             "the number is already a binary float, so the printed value rounds the other way"),
    "v1036": ("a leftover last item becomes a group of one",
             "zip stops at the shorter side, so the leftover is dropped"),
    "v1037": ("each row is independent of the original",
             "the comprehension copies the outer list only, so the rows are the same objects"),
    "v1057": ("the minimum and maximum of any iterable of numbers",
             "min consumes the iterator, so max is asked for the maximum of nothing"),
    "v1073": ("the prefix is removed as it stands when the text starts with it",
             "lstrip takes the prefix as a character set and keeps eating those characters"),
    "strip_suffix-rstrip-20260922": ("the exact substring is removed from both ends when present",
                                     "strip takes the argument as a character set, not a substring"),
}
FACTS = {
    "v960": "adjacent-only comparison leaves non-adjacent duplicates in place",
    "v975": "str.title touches the rest of the word",
    "v989": "the deletion is done on the caller's list, which is returned as the same object",
    "v1026": "list(set(...)) has no insertion order to preserve",
    "v1030": "binary floating point puts 2.675 below the halfway point",
    "v1036": "zip truncates the leftover",
    "v1037": "a one-level copy aliases its rows",
    "v1057": "the first traversal exhausts the iterator",
    "v1073": "lstrip treats its argument as a character set",
    "strip_suffix-rstrip-20260922": "strip treats its argument as a character set",
}


def apply(rows, module):
    """Write the verdicts into fragments.py and catches.json."""
    import re

    objects = [r for r in rows if r["verdict"] == "OBJECT"]
    lines = ["\n# --- recovered: labels whose bytes were still on hand (see recover_labels.py)\n\n"]
    for row in objects:
        src = inspect.getsource(getattr(module, row["fn"]))
        lines.append(src.rstrip() + "\n\n")
    block = "".join(lines)

    frag = (HERE / "fragments.py").read_text(encoding="utf-8")
    if "# --- recovered:" not in frag:
        frag = frag.replace("NAMESPACES = {", block + "NAMESPACES = {", 1)
    for row in objects:
        entry = f'"{row["class"]}": {{'
        head, _, tail = frag.partition(entry)
        if f'"{row["fn"]}":' in tail.split("}", 1)[0]:
            continue
        frag = head + entry + f'"{row["fn"]}": {row["fn"]}, ' + tail
    (HERE / "fragments.py").write_text(frag, encoding="utf-8")

    data = json.loads((HERE / "catches.json").read_text(encoding="utf-8"))
    by_class = {e["class"]: e for e in data["entries"]}
    for row in rows:
        entry = by_class[row["class"]]
        label = row["label"]
        if any(r.get("id") == label for r in entry.get("retired") or []):
            continue  # already applied: this script is re-runnable
        if any(isinstance(r, dict) and r.get("recovered") == label
               for r in entry["repeats"]):
            continue
        entry["repeats"] = [r for r in entry["repeats"] if r != label]
        if row["verdict"] == "OBJECT":
            entry["repeats"].append({
                "id": f"{row['fn']}",
                "promise": PROMISES[label][0],
                "fact": FACTS[label],
                "probe": row["probe"],
                "expected": row["expected"],
                "observed": row["observed"],
                "fn": row["fn"],
                "recovered": label,
            })
        elif row["verdict"] == "RUN":
            entry.setdefault("retired", []).append({
                "id": label, "kind": "not-a-fragment",
                "why": "the receipt records a run of this ledger, not a fragment: it "
                       "names no shape of its own and cannot be replayed",
            })
        else:
            why = (f"recovered from {label}: the fragment fingerprints identically to "
                   f"{row.get('belongs_to', row['class'])}'s class fragment, so the label "
                   "counted a check of that fragment and not a second sighting")
            entry.setdefault("retired", []).append(
                {"id": label, "kind": "class-fragment", "why": why})
    (HERE / "catches.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(objects)} objects, "
          f"{len(rows) - len(objects)} retirements")


if __name__ == "__main__":
    raise SystemExit(main())
