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
    alone read a helper named only by a repeat as one nothing reads;
  * for every helper that DECLARES an input a caller may move (the `PERTURBATIONS` map
    below) the answer under the moved input, different from the answer under the default
    one. Comparing a helper's answer with the entry it records is satisfied, on every
    tree, by a helper that RETURNS that entry: an independent review built exactly that
    mutant -- two literal dicts equal to the entry -- and the whole suite, this item
    included, stayed green. What a constant cannot do is follow an input.
  * neither half built from nothing that could vary. The rule asks the dependency
    question, not the node question: a half whose value cannot change when the tree
    changes is the entry written twice, and every comparison against that entry is
    satisfied by it whether or not the helper declares an input. Literals, containers,
    calls, operators and reads are walked to their leaves; a name is read through the
    local assignment map and the module-level one; an imported module name and a
    builtin name are not sources of variation. So `{"a": 1}`, `dict(a=1)` and
    `json.loads('{"a": 1}')` are all refused, and the survivor above is closed for
    helpers the `PERTURBATIONS` map cannot reach as well.

    python3 probes/parts_of_a_reading.py            # every helper, and its verdict
    python3 probes/parts_of_a_reading.py --check    # exit 1 when a half is unmeasured
    python3 probes/parts_of_a_reading.py --selftest # build five trees, require four reds

WHAT THIS DOES NOT DO: it compares the halves against the ENTRY, so an entry whose
`expected` was typed from the same wrong reading passes here -- the second half is then
measured against itself. The literal rule asks whether a half's value can depend on
anything outside the file; what it cannot see is a helper that computes nothing and
calls something in the tree which itself returns literals, because that call is a name
this walk counts as varying. And a helper whose input no caller can vary is separable from a constant
only in the shape that constant is written in: the count of such helpers is printed, not
claimed away.
"""
import argparse
import base64
import builtins
import ast
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
        rows.append((name, halves, readers, measured,
                     moved_by_its_input(mod, name, halves)))
    return rows


# The input each helper lets a caller move. A helper whose input no caller can vary is a
# helper a written-down answer can stand in for: the probe's whole instrument is
# `helper() == entry`, and a helper that RETURNS the entry satisfies it on every tree.
# Where a helper declares a settable input this probe moves it and requires the answer to
# move with it -- a constant cannot follow the input, and that is measured rather than
# argued. The helpers not named here are the bound: nothing in this repository can
# separate them from a constant, and the class `a-half-no-command-recomputes` records it.
PERTURBATIONS = {
    "_readings_of_a_survivor_table_two_revisions_apart": {
        "rows": (
            {"mutation": "the same mutation", "revision": "older", "survives": True},
            {"mutation": "the same mutation", "revision": "current", "survives": False},
        ),
    },
    "_readings_of_a_status_the_word_beside_it_replaced": {"the_command_returns": 3},
}


def moved_by_its_input(mod, name: str, halves):
    """`None` when the helper declares nothing a caller may move, else `(moved, why)`.

    `why` is the refusal's reason when the answer did not move, or did not come back:
    an answer that is the same under a moved input is an answer the input does not feed.
    """
    spec = PERTURBATIONS.get(name)
    if spec is None:
        return None
    helper = getattr(mod, name)
    try:
        moved = normalise(helper(**spec))
    except TypeError as exc:
        return None, (f"declares the input {sorted(spec)} and will not take it: {exc}")
    except Exception as exc:  # noqa: BLE001 -- the reason is the finding
        return None, (f"raised under the moved input {sorted(spec)}: "
                      f"{type(exc).__name__}: {exc}")
    if moved == halves:
        return moved, (f"answers the same with {sorted(spec)} moved: the answer does not "
                       f"come from that input, so a constant returning the entry's own "
                       f"halves answers this control too")
    if isinstance(moved, dict) and set(moved) == {"as_written", "as_repaired"} \
            and repr(moved["as_written"]) == repr(moved["as_repaired"]):
        return moved, (f"answers with two halves of one value under the moved input "
                       f"{sorted(spec)}")
    return moved, None


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


MEASURED_NODES = (ast.Call, ast.Attribute, ast.Subscript, ast.BinOp, ast.Compare,
                  ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp,
                  ast.JoinedStr, ast.IfExp, ast.BoolOp, ast.Await, ast.Lambda)

BUILTIN_NAMES = frozenset(dir(builtins))

# Modules whose functions only transform their arguments: a call through one of them over
# constants is a literal with a step in the middle, not a reading. Everything else --
# `subprocess`, `os`, `pathlib`, `socket` -- is a way of reading the world, and a half
# written through one of those is a measurement. The list is a bound, not a proof: a decoy
# written as a call through an unlisted pure module (`shlex`, `statistics`) survives.
PURE_MODULES = frozenset({"ast", "base64", "binascii", "codecs", "copy", "gzip",
                          "hashlib", "json", "re", "struct", "textwrap", "zlib"})


def _own_nodes(fn) -> list:
    """This function's own nodes, nested function definitions left out."""
    out = []

    def dive(nodes):
        for node in nodes:
            if isinstance(node, ast.FunctionDef):
                continue
            out.append(node)
            for child in ast.iter_child_nodes(node):
                if not isinstance(child, ast.FunctionDef):
                    dive([child])

    dive(fn.body)
    return out


def _module_locals(tree) -> tuple:
    """Module-level `name -> the expression assigned to it`, and the imported names.

    A half that returns a module-level name is read the same way as the inline value --
    the name is a label on a literal, not a measurement. An imported module name is
    neither: `json.loads('{"a": 1}')` does not vary with the tree.
    """
    values, imported = {}, {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                values[node.target.id] = node.value
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                imported[alias.asname or alias.name.split(".")[0]] = alias.name.split(".")[0]
    return values, imported


def _local_names(fn) -> dict:
    """Local name -> the expression assigned to it; the last assignment wins."""
    out = {}

    def record(target, value):
        if isinstance(target, ast.Name):
            out[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                record(element, value)

    for node in _own_nodes(fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                record(target, node.value)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            record(node.target, node.value)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            record(node.target, node.iter)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            # A module imported inside the helper is a module: `json.loads(...)` over a
            # constant does not vary with the tree whether the import sits at the top of
            # the file or three lines above the return. Recorded as the import node, which
            # `varies` reads as names that can not vary -- and only for the modules whose
            # functions transform their arguments (`PURE_MODULES`); `subprocess` there
            # counts as measurement, because a helper reading the world through it is not
            # writing its entry into the source.
            for alias in node.names:
                out[alias.asname or alias.name.split(".")[0]] = node
    return out


def varies(expr, local: dict, module: dict, imported: set, depth: int = 0) -> bool:
    """Could this half's value depend on something outside the file?

    The question the literal rule asks is not "are there literal nodes in here" but
    "could this value change if the tree changed". `dict(a=1)` is a call over literals
    and a rule that reads call nodes as measurement accepts it; so is `json.loads('{}')`
    and so is a module-level name whose value is a dict. Anything this walk cannot
    resolve counts as varying, which keeps the rule narrow. The one exception is a name
    that resolves to an import: a module on `PURE_MODULES` only transforms its arguments,
    so a call through it over constants is a literal with a step in the middle; any other
    module is a way of reading the world and counts as varying.
    """
    if depth > 20:
        return True
    if isinstance(expr, (ast.Import, ast.ImportFrom)):
        roots = {alias.name.split(".")[0] for alias in expr.names}
        return not roots <= PURE_MODULES
    if isinstance(expr, ast.Constant):
        return False
    if isinstance(expr, ast.Name):
        if expr.id in local:
            return varies(local[expr.id], local, module, imported, depth + 1)
        if expr.id in module:
            return varies(module[expr.id], local, module, imported, depth + 1)
        if expr.id in imported:
            return imported[expr.id] not in PURE_MODULES
        return not (expr.id in BUILTIN_NAMES)
    if isinstance(expr, (ast.List, ast.Tuple, ast.Set)):
        return any(varies(e, local, module, imported, depth + 1) for e in expr.elts)
    if isinstance(expr, ast.Dict):
        return (any(varies(k, local, module, imported, depth + 1) for k in expr.keys
                    if k is not None)
                or any(varies(v, local, module, imported, depth + 1) for v in expr.values))
    if isinstance(expr, ast.Call):
        return (_kwargs_varies(expr, local, module, imported, depth)
                or varies(expr.func, local, module, imported, depth + 1)
                or any(varies(a, local, module, imported, depth + 1) for a in expr.args))
    if isinstance(expr, ast.UnaryOp):
        return varies(expr.operand, local, module, imported, depth + 1)
    if isinstance(expr, ast.BoolOp):
        return any(varies(v, local, module, imported, depth + 1) for v in expr.values)
    if isinstance(expr, ast.BinOp):
        return (varies(expr.left, local, module, imported, depth + 1)
                or varies(expr.right, local, module, imported, depth + 1))
    if isinstance(expr, ast.Compare):
        return (varies(expr.left, local, module, imported, depth + 1)
                or any(varies(c, local, module, imported, depth + 1)
                       for c in expr.comparators))
    if isinstance(expr, ast.Attribute):
        return varies(expr.value, local, module, imported, depth + 1)
    if isinstance(expr, ast.Subscript):
        return (varies(expr.value, local, module, imported, depth + 1)
                or varies(expr.slice, local, module, imported, depth + 1))
    if isinstance(expr, ast.IfExp):
        return any(varies(v, local, module, imported, depth + 1)
                   for v in (expr.test, expr.body, expr.orelse))
    if isinstance(expr, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue)
                   and varies(v.value, local, module, imported, depth + 1)
                   for v in expr.values)
    if isinstance(expr, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        # A comprehension over constants is the same literal written in a longer way, and
        # a rule that answers "a comprehension varies" is satisfied by `{k: v for k, v in
        # {...}.items()}` over the entry's own values -- measured on this tree, exit 0 and
        # `halves written as literals rather than measured 0` on ten of eleven helpers. The
        # loop targets are labels on the thing iterated, so each is resolved to its iterable
        # before the element and the conditions are walked.
        bound = dict(local)
        parts = []
        for generator in expr.generators:
            for target in ast.walk(generator.target):
                if isinstance(target, ast.Name):
                    bound[target.id] = generator.iter
            parts.append(generator.iter)
            parts.extend(generator.ifs)
        parts.extend([expr.key, expr.value] if isinstance(expr, ast.DictComp) else [expr.elt])
        return any(varies(part, bound, module, imported, depth + 1) for part in parts)
    return True


def _kwargs_varies(call, local, module, imported, depth) -> bool:
    return any(varies(k.value, local, module, imported, depth + 1)
               for k in call.keywords)


def _measured(expr, local: dict, module: dict = None, imported: set = None,
              depth: int = 0) -> bool:
    """Kept as the name the refusal message uses: a half is measured when it varies."""
    return varies(expr, local, module or {}, imported or set(), depth)


def _halves_of_return(value) -> list:
    """`[(half name, expression)]` for a returned pair, in either of the two shapes."""
    if isinstance(value, ast.Dict):
        keys = [getattr(key, "value", None) for key in value.keys]
        if {"as_written", "as_repaired"} <= set(keys):
            return [(key, item) for key, item in zip(keys, value.values)
                    if key in ("as_written", "as_repaired")]
    if isinstance(value, ast.Tuple) and len(value.elts) == 2:
        return [("written", value.elts[0]), ("repaired", value.elts[1])]
    return []


def halves_typed_rather_than_measured(source: str) -> list:
    """Every half of every helper that is written as a literal, not computed.

    A constant that repeats its own entry satisfies every comparison against that entry,
    so the comparison is not what refuses it -- this is: a half whose expression calls
    nothing in this tree is the entry written a second time, whatever else the tree does.
    The rule reads the expression a half is written as, following local assignments one
    by one, so `return {"as_written": written}` with `written = {...}` above it is read
    the same way as the inline dict. Returns `(helper, half, line, expression)`.
    """
    tree = ast.parse(source)
    found = []
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef) or not fn.name.startswith("_readings_of_"):
            continue
        local = _local_names(fn)
        module, imported = _module_locals(tree)
        for node in _own_nodes(fn):
            if not isinstance(node, ast.Return) or node.value is None:
                continue
            for half, expr in _halves_of_return(node.value):
                if not varies(expr, local, module, imported):
                    found.append((fn.name, half, node.lineno, ast.unparse(expr)[:90]))
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
    for name, halves, readers, measured, moved in rows:
        if not isinstance(halves, dict) or set(halves) != {"as_written", "as_repaired"}:
            lines.append(f"FAIL[NOT-TWO-HALVES] {name} does not answer with two halves: "
                         f"{type(halves).__name__} {halves!r}"[:160])
            bad += 1
            continue
        if repr(halves["as_written"]) == repr(halves["as_repaired"]):
            lines.append(f"FAIL[HALVES-ONE-VALUE] {name} has two halves with one value: the repaired "
                         f"reading is the written one")
            bad += 1
        if moved is not None and moved[1] is not None:
            lines.append(f"FAIL[INPUT-NOT-MOVED] {name} {moved[1]}"[:200])
            bad += 1
        if not measured:
            lines.append(f"FAIL[NO-READER] {name} is read by no ledger entry: "
                         f"{readers or 'no public fragment calls it'}")
            bad += 1
            continue
        for reader, entry, written_ok, repaired_ok in measured:
            if written_ok and repaired_ok:
                lines.append(f"ok   {name} -- both halves read against "
                             f"{record_name(entry)}")
            else:
                lines.append(f"FAIL[ENTRY-DISAGREES] {record_name(entry)}: the helper's "
                             f"{'written' if not written_ok else 'repaired'} half is not "
                             f"the one the entry records")
                bad += 1
    return lines, bad


def perturbations_no_helper_answers_to(rows) -> list:
    """The names this probe declares an input for and no helper in the tree answers to.

    A perturbation naming a helper that is gone is a control that has quietly stopped
    testing anything: it must be refused, not reported as a short list.
    """
    defined = {name for name, *_rest in rows}
    return sorted(set(PERTURBATIONS) - defined)


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


# The ids a refusal is recognised by. A phrase is prose and prose gets reused: this probe's
# own summary block already carried the words the literal arm matched on, so the arm was
# one reused sentence away from accepting a refusal it never asked for.
LITERAL_HALF_REFUSAL = "FAIL[LITERAL-HALF]"
ENTRY_REFUSAL = "FAIL[ENTRY-DISAGREES]"


def selftest() -> int:
    """Three broken trees must be refused, and the untouched copy must not.  A refusal is recognised by the id it prints -- `FAIL[LITERAL-HALF]` -- not by a
  phrase inside it: the phrase is prose, this probe's summary block reuses it, and
  an arm here shows a line carrying the phrase under another id is not accepted.
"""
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

        # The strongest mutant an independent review could build: the helper replaced by a
        # constant that REPEATS its own entry, byte for byte. Every comparison of the
        # helper's output with the entry -- this probe's whole instrument, and check.py's --
        # is satisfied by it, so the refusal has to come from the input: the tree built
        # here is only red if the control moves the declared input and the answer must
        # follow, which a constant cannot do.
        moved_names = [n for n in PERTURBATIONS
                       if n in set(HELPER.findall(
                           (src / "fragments.py").read_text(encoding="utf-8")))][:1]
        for name in moved_names:
            tree = pathlib.Path(td) / "constant-equals-entry"
            tree.mkdir()
            for f in ("fragments.py", "catches.json"):
                shutil.copy(src / f, tree / f)
            index = entry_index_for(tree, name)
            if index is None:
                print(f"FAIL the copy under test has no entry reading {name}")
                return 1
            i, j = index
            ledger = json.loads((tree / "catches.json").read_text(encoding="utf-8"))
            record = (ledger["entries"][i] if j is None
                      else ledger["entries"][i]["repeats"][j])
            frag = tree / "fragments.py"
            frag.write_text(
                frag.read_text(encoding="utf-8")
                + "\n\ndef %s(**kw):\n    return {'as_written': %s, 'as_repaired': %s}\n"
                % (name, record["observed"], record["expected"]),
                encoding="utf-8")
            code = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                                   "--check", "--root", str(tree)],
                                  capture_output=True, text=True)
            caught = code.returncode == 1
            bad += 0 if caught else 1
            why = next((ln for ln in code.stdout.splitlines() if ln.startswith("FAIL")), "")
            print(f"{'ok  ' if caught else 'FAIL'} a helper replaced by a constant equal to "
                  f"its own entry is refused (exit {code.returncode})"
                  + (f": {why}" if why else ""))
        # The survivor an independent review found, in the shape the input rule cannot
        # reach: a helper whose halves are literal dicts equal to its own entry. It is
        # built for a helper with NO declared input, so the refusal can only come from
        # reading the shape of the half -- and the arm requires the line to say so.
        quiet = [n for n in sorted(set(HELPER.findall(
            (src / "fragments.py").read_text(encoding="utf-8"))))
            if n not in PERTURBATIONS][:1]
        for name in quiet:
            tree = pathlib.Path(td) / "typed-halves"
            tree.mkdir()
            for f in ("fragments.py", "catches.json"):
                shutil.copy(src / f, tree / f)
            index = entry_index_for(tree, name)
            if index is None:
                print(f"FAIL the copy under test has no entry reading {name}")
                return 1
            i, j = index
            ledger = json.loads((tree / "catches.json").read_text(encoding="utf-8"))
            record = (ledger["entries"][i] if j is None
                      else ledger["entries"][i]["repeats"][j])
            frag = tree / "fragments.py"
            frag.write_text(
                frag.read_text(encoding="utf-8")
                + "\n\ndef %s(**kw):\n    return {'as_written': %s, 'as_repaired': %s}\n"
                % (name, record["observed"], record["expected"]),
                encoding="utf-8")
            code = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                                   "--check", "--root", str(tree)],
                                  capture_output=True, text=True)
            named = [ln for ln in code.stdout.splitlines()
                     if ln.startswith(LITERAL_HALF_REFUSAL)]
            caught = code.returncode == 1 and bool(named)
            bad += 0 if caught else 1
            print(f"{'ok  ' if caught else 'FAIL'} a helper whose halves are literals equal "
                  f"to its own entry is refused by the shape of the half, and the line says "
                  f"so (exit {code.returncode}"
                  + (f", line: {named[0][:80]}" if named else ", no such line") + ")")
        # The shape a call node hides: the same literal dicts, written as `dict(...)` over
        # the entry's own values. A rule that reads call nodes as measurement accepts it --
        # measured on this tree, `halves written as literals rather than measured 0`, exit 0
        # -- so the arm builds it for a helper with no declared input and requires the
        # refusal to be the literal arm, by its id.
        for name in quiet:
            tree = pathlib.Path(td) / "called-literals"
            tree.mkdir()
            for f in ("fragments.py", "catches.json"):
                shutil.copy(src / f, tree / f)
            index = entry_index_for(tree, name)
            if index is None:
                print(f"FAIL the copy under test has no entry reading {name}")
                return 1
            i, j = index
            ledger = json.loads((tree / "catches.json").read_text(encoding="utf-8"))
            record = (ledger["entries"][i] if j is None
                      else ledger["entries"][i]["repeats"][j])
            halves = []
            for key in ("observed", "expected"):
                value = ast.literal_eval(record[key])
                halves.append("dict(%s)" % ", ".join(
                    "%s=%r" % (k, v) for k, v in sorted(value.items())))
            frag = tree / "fragments.py"
            frag.write_text(
                frag.read_text(encoding="utf-8")
                + "\n\ndef %s(**kw):\n    return {'as_written': %s, 'as_repaired': %s}\n"
                % (name, halves[0], halves[1]),
                encoding="utf-8")
            code = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                                   "--check", "--root", str(tree)],
                                  capture_output=True, text=True)
            named = [ln for ln in code.stdout.splitlines()
                     if ln.startswith(LITERAL_HALF_REFUSAL)]
            caught = code.returncode == 1 and bool(named)
            bad += 0 if caught else 1
            print(f"{'ok  ' if caught else 'FAIL'} a half written as a call over literals is "
                  f"refused by the literal arm (exit {code.returncode})"
                  + (f": {named[0][:90]}" if caught else ""))

        # Two more shapes of the same typed pair, found by an independent review: the
        # literals written as a comprehension over themselves, and the literals behind
        # `json.loads(base64.b64decode(...))` with the imports written inside the helper.
        # Both passed this probe before the rule walked comprehensions and read an import
        # made inside the function: exit 0, zero refusal lines, `halves written as literals
        # rather than measured 0` on ten of eleven helpers -- a tree carrying the entry
        # typed into the source, with the class that was registered against exactly that
        # left green. The arm plants each shape and requires the literal refusal by its id.
        for shape in ("comprehension over literals", "decoder over literals"):
            tree = pathlib.Path(td) / ("decoy-" + shape.split()[0])
            tree.mkdir()
            for f in ("fragments.py", "catches.json"):
                shutil.copy(src / f, tree / f)
            index = entry_index_for(tree, quiet[0])
            if index is None:
                print(f"FAIL the copy under test has no entry reading {quiet[0]}")
                return 1
            i, j = index
            ledger = json.loads((tree / "catches.json").read_text(encoding="utf-8"))
            record = (ledger["entries"][i] if j is None
                      else ledger["entries"][i]["repeats"][j])
            halves = []
            for key in ("observed", "expected"):
                value = ast.literal_eval(record[key])
                if shape == "comprehension over literals":
                    halves.append("{k: v for k, v in %r.items()}" % (value,))
                else:
                    blob = json.dumps(value, sort_keys=True).encode("utf-8")
                    halves.append("json.loads(base64.b64decode('%s'))"
                                  % base64.b64encode(blob).decode("ascii"))
            imports = ("" if shape == "comprehension over literals"
                       else "    import base64\n    import json\n")
            frag = tree / "fragments.py"
            frag.write_text(
                frag.read_text(encoding="utf-8")
                + "\n\ndef %s(**kw):\n%s    return {'as_written': %s, 'as_repaired': %s}\n"
                % (quiet[0], imports, halves[0], halves[1]),
                encoding="utf-8")
            code = subprocess.run([sys.executable, str(pathlib.Path(__file__).resolve()),
                                   "--check", "--root", str(tree)],
                                  capture_output=True, text=True)
            named = [ln for ln in code.stdout.splitlines()
                     if ln.startswith(LITERAL_HALF_REFUSAL)]
            caught = code.returncode == 1 and bool(named)
            bad += 0 if caught else 1
            print(f"{'ok  ' if caught else 'FAIL'} a half written as the literals of "
                  f"its own entry behind a {shape} is refused by the literal arm "
                  f"(exit {code.returncode})" + (f": {named[0][:90]}" if caught else ""))
        # The phrase is not a name. This line is another class's refusal -- a half that
        # disagrees with its entry -- reusing the words the literal arm used to match on,
        # and it is exactly the line the substring rule would have accepted.
        impostor = (f"{ENTRY_REFUSAL} an entry: the helper's written half is not the one "
                    f"the entry records, so it is written as a literal twice over")
        taken = [ln for ln in impostor.splitlines()
                 if ln.startswith(LITERAL_HALF_REFUSAL)]
        bad += 1 if taken else 0
        print(f"{'ok  ' if not taken else 'FAIL'} a refusal that reuses the phrase under "
              f"another id is not taken for the literal refusal" + (f": {taken}" if taken
                                                                    else ""))

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
        print(f"FAIL[TYPED-LIST] fragments.py:{line} types {named} name(s) beside the file's "
              f"{len(defined)}: never named {missing or '[]'}, not defined {extra or '[]'}")
    orphaned = perturbations_no_helper_answers_to(rows)
    for name in orphaned:
        print(f"FAIL[ORPHAN-INPUT] this probe declares an input for {name}, and no helper answers to it")
    typed = halves_typed_rather_than_measured(source)
    for name, half, line, expr in typed:
        print(f"FAIL[LITERAL-HALF] {name}: the {half} half is written as a literal at "
              f"fragments.py:{line}: {expr} -- a half that calls nothing is a sentence "
              f"about the entry, not a reading of the tree")
    unvaryable = sorted(name for name, *_rest, moved in rows if moved is None)
    print(f"helpers with two halves  {len(rows)}")
    print(f"helpers whose input no caller varies  {len(unvaryable)}")
    print(f"halves not read against an entry  {bad}")
    print(f"halves written as literals rather than measured  {len(typed)}")
    print(f"typed lists that do not cover the file  {len(stale)}")
    if args.check and (bad or stale or orphaned or typed):
        print("REFUSED: a helper's half is not the one the entry records, or nothing in this "
              "repository reads it, or its answer does not move with the input it declares "
              "-- either way the half that says what the repair does is unwitnessed, so it "
              "can be a constant and every suite stays green; or a list typed into "
              "fragments.py no longer covers the helpers the file defines, so a tally taken "
              "from it is a sentence about an older file; or this probe declares an input "
              "for a helper this tree does not carry, so that control tests nothing; or a "
              "half is written as a literal instead of computed, so it is the entry written "
              "a second time and every comparison against that entry is satisfied by it")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
