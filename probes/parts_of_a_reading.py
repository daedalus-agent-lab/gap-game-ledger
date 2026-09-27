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

A fixture this probe builds carries the files the copy READS, derived from the imports of
`fragments.py` rather than named in a tuple: a hand-written list is a sentence about what
the tree needed when it was written, and this probe's own selftest proved the cost -- a
helper beside the tree had begun to read `check.py`, and all ten fixtures were unreadable
trees that the arms reported as a broken probe.

Every line this probe can open with the refusal word carries an id in brackets, and the
rule is read off this file's own source (`unlabelled_refusal_sites`), not remembered:
bare, the word says a check spoke without saying which one.
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


def carry(src: pathlib.Path, into: pathlib.Path, names) -> None:
    """Copy the named files of `src` into a fixture, making the path they sit at."""
    for name in names:
        destination = into / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src / name, destination)


def paths_the_tree_opens(src: pathlib.Path, source: str) -> list:
    """The tree's own files that `fragments.py` opens BY PATH, resolved against its own
    directory.

    A module imported as a fixture must not depend on the process's directory, so a helper
    that reads a file of the tree builds the path from `__file__` and its own folder. A
    fixture carrying only `fragments.py` and `catches.json` then holds a helper that cannot
    read what it is checked with, and every mutant of this probe's selftest reads as a
    broken tree rather than as a reading. The list comes from the source: a helper that
    opens another file of the tree is carried because the tree opens it, not because its
    name was written down here.
    """
    out = []
    for node in ast.walk(ast.parse(source)):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)):
            continue
        parts = []
        cur = node
        while isinstance(cur, ast.BinOp) and isinstance(cur.op, ast.Div):
            if isinstance(cur.right, ast.Constant) and isinstance(cur.right.value, str):
                parts.append(cur.right.value)
            cur = cur.left
        if not parts:
            continue
        if not any(isinstance(sub, ast.Name) and sub.id == "__file__"
                   for sub in ast.walk(cur)):
            continue
        rel = "/".join(reversed(parts))
        if (src / rel).is_file() and rel not in out:
            out.append(rel)
    return out


def files_the_tree_reads(src: pathlib.Path) -> tuple:
    """The files a fixture must carry: the tree's own two, plus every module beside them
    that `fragments.py` imports. A hand-written list here is the same sentence the copy
    rule was: `("fragments.py", "catches.json")` named what the tree needed when it was
    written, and a helper added later reads `check.py`, so all ten fixtures of this
    probe's selftest were unreadable trees -- `0/19 helpers reported`, a traceback, and
    a selftest that read its own fixture as a broken probe. The derivation cannot rot:
    a new sibling module is carried because the tree imports it.
    The control itself is carried too, at this file's own path under the tree:
    a helper beside the tree reads it BY PATH, and a fixture without it is a
    tree whose first such helper raises -- which is how this probe's selftest
    died on its own fixture, with every reading unread and one traceback.
    A file the tree opens BY PATH (`__file__`'s folder and then some) is carried too, and
    that list comes from the source as well: a helper that reads the harness it is checked
    against is a helper a fixture must hand that harness to.
    """
    names = ["fragments.py", "catches.json"]
    source = (src / "fragments.py").read_text(encoding="utf-8")
    modules = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            modules += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    for module in modules:
        candidate = src / (module.split(".")[0] + ".py")
        if candidate.exists() and candidate.name not in names:
            names.append(candidate.name)
    for rel in paths_the_tree_opens(src, source):
        if rel not in names:
            names.append(rel)
    control = pathlib.Path(__file__).resolve()
    try:
        besidethe_tree = control.relative_to(src).as_posix()
    except ValueError:
        besidethe_tree = None
    if besidethe_tree and besidethe_tree not in names:
        names.append(besidethe_tree)
    return tuple(names)
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


def readings(root: pathlib.Path, only: str | None = None):
    """Every helper in `fragments.py`, its two halves, and the entries that read it.

    `only` narrows the reading to one helper by name. It exists because a control whose
    cost outgrows the run that must exercise it is not a control: this probe's own
    selftest runs this check on ten mutant trees, and a check that reads every helper
    each time cannot finish inside the run's own timeout. The arms that expect a refusal
    name the helper they planted; the arm that expects a green copy still reads all of
    them, because "every helper agrees" is not a claim about one name.
    """
    source = (root / "fragments.py").read_text(encoding="utf-8")
    defs = defs_of(source)
    mod, ledger = load(root)
    by_probe = readers_of_entries(ledger)
    rows = []
    for name, _body in defs.items():
        if not HELPER.match(f"def {name}("):
            continue
        if only is not None and name != only:
            continue
        try:
            answer = getattr(mod, name)()
        except Exception as exc:
            # A helper that refuses because no control stands beside the tree is not a
            # broken helper: this probe names it UNREAD, so a fixture that carries the
            # entry's own pair as its answer is not green. Anything else is a broken tree
            # and stays an error.
            if type(exc).__name__ != "NoControlBesideThisTree":
                raise
            rows.append((name, {"unread": exc.args[0] if exc.args else "no control"},
                         probes_that_read(name, defs), [], None))
            continue
        halves = normalise(answer)
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
    # The rule in force is read out of the harness beside the tree, so a caller can hand
    # the helper another rule and the half that answers for the repair must move with it.
    # A helper that copies one measurement into both units -- the shape that passes every
    # arm of this class and its own gate -- cannot follow this input.
    "_readings_of_a_count_of_lines_read_as_a_count_of_what_was_printed": {
        "the_rule": "wc -l",
    },
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

# Ways the tree under test can be READ: a call through one of these can answer differently
# on a different tree, so a half that contains one is a measurement. The list is written as
# what reads, not as what is pure, and that is the whole point: a list of pure modules has
# to name every module that only transforms its arguments, so it has no bottom, and a decoy
# spelled through the first one nobody named is the entry written a second time. Measured on
# this tree: the entry's own values as `statistics.mode([2, 2])`, `math.floor(2.5)` and
# `shlex.split('"a b"')` passed `--check` with `halves written as literals rather than
# measured 0` on five spellings, while the same values written as a plain literal were
# refused. A module this list does not name is read as a function of its arguments only, so
# its answer over constants is a constant -- and a module that can read the tree is named
# here once, when a helper that uses it says so.
READERS = frozenset({"subprocess", "os", "sys", "pathlib", "shutil", "tempfile", "glob",
                     "socket", "ssl", "sqlite3", "mmap", "fcntl", "select", "pty",
                     "resource", "io"})
READING_BUILTINS = frozenset({"open"})


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
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # A function this file defines is a way of writing a value down: `def _half():
            # return 2` called from a half is the constant 2 in two steps. Recorded so a
            # call to it can be read through its body with its parameters bound.
            values[node.name] = node
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
            # `varies` reads as a name that can not vary -- and only for the modules that
            # open, run or ask something (`READERS`); `subprocess` there counts as
            # measurement, because a helper reading the world through it is not writing its
            # entry into the source.
            for alias in node.names:
                out[alias.asname or alias.name.split(".")[0]] = node
    # A function defined INSIDE the helper is a name in it. `_own_nodes` leaves nested
    # definitions out so their body is not walked as the helper's own -- which also meant
    # the name was not recorded, so `def _half(): return {…}` followed by `_half()` was an
    # unresolved call, read as measurement: the entry typed into the source, exit 0, and an
    # independent review found it. The name is recorded here so the call is read through
    # that body instead.
    for node in ast.walk(fn):
        if node is not fn and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out[node.name] = node
    # A name the helper fills at run time through `exec` is not the expression the file
    # shows it holding. `planted = {}` followed by `exec(...)` holding a rule leaves a name
    # whose initializer is a lie about its value: read from the initializer it is an empty
    # dict, so a half that calls `planted["scan"](source)` was refused as "written as a
    # literal" although it computes -- measured on this tree, one helper flagged, `halves
    # written as literals rather than measured 1`, the probe's own exit 1. A name handed to
    # `exec` is dropped from the map, which makes every read of it unresolved -- the same
    # answer this file gives a parameter of the helper. Only `exec` does it: a container the
    # helper fills with `d[k] = ...` stays its initializer, because the values it is later
    # given are not what the half's expression computes from. The cost is measured in
    # `--selftest`: a helper that returns a name filled by `exec` is accepted, so a constant
    # can still hide inside code the tree writes at run time.
    written_to = set()
    for node in _own_nodes(fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in ("exec", "eval", "execfile"):
            for argument in [*node.args, *[k.value for k in node.keywords]]:
                if isinstance(argument, ast.Name):
                    written_to.add(argument.id)
    for name in written_to:
        out.pop(name, None)
    return out


def varies(expr, local: dict, module: dict, imported: set, depth: int = 0) -> bool:
    """Could this half's value depend on something outside the file?

    The question the literal rule asks is not "are there literal nodes in here" but
    "could this value change if the tree changed". `dict(a=1)` is a call over literals
    and a rule that reads call nodes as measurement accepts it; so is `json.loads('{}')`
    and so is a module-level name whose value is a dict. Three things can make a half
    vary: a name this file does not bind (a parameter of the helper, or a global someone
    else sets), a builtin that reads (`open`), or a call through a module on `READERS`.
    A module that is not on that list is read as a function of its arguments, so a call
    through it over constants is a literal with a step in the middle; and a call to a
    function this file defines is read through that function's body with the call's
    arguments bound to its parameters, because one line of indirection is where a
    constant hides from a rule that only reads the line the return stands on.
    """
    if depth > 20:
        return True
    if isinstance(expr, (ast.Import, ast.ImportFrom)):
        roots = {alias.name.split(".")[0] for alias in expr.names}
        return bool(roots & READERS)
    if isinstance(expr, ast.Constant):
        return False
    if isinstance(expr, ast.Name):
        if expr.id in local:
            return varies(local[expr.id], local, module, imported, depth + 1)
        if expr.id in module:
            return varies(module[expr.id], local, module, imported, depth + 1)
        if expr.id in imported:
            return imported[expr.id] in READERS
        if expr.id in BUILTIN_NAMES:
            return expr.id in READING_BUILTINS
        return True  # a parameter of the helper, or a global this file does not bind
    if isinstance(expr, (ast.List, ast.Tuple, ast.Set)):
        return any(varies(e, local, module, imported, depth + 1) for e in expr.elts)
    if isinstance(expr, ast.Dict):
        return (any(varies(k, local, module, imported, depth + 1) for k in expr.keys
                    if k is not None)
                or any(varies(v, local, module, imported, depth + 1) for v in expr.values))
    if isinstance(expr, ast.Call):
        defined = _called_function(expr, local, module)
        if defined is not None:
            inner = dict(local)
            params = [*defined.args.posonlyargs, *defined.args.args,
                      *defined.args.kwonlyargs]
            values = [*expr.args, *[k.value for k in expr.keywords]]
            for parameter, value in zip(params, values):
                inner[parameter.arg] = value
            # A function that READS an argument it was handed is a way of computing, not a
            # way of writing a value down, and the value it computes is a function of what
            # was passed: stopping at "its body is made of constants" refused five helpers
            # of this tree whose halves are models over a fixture typed in the source --
            # `as_written(TREES)`, `shape(written)` -- which are readings of a scenario and
            # not the entry copied out. A function that declares an argument and never
            # reads it is the other case, and it is refused below like the literal it is.
            used = {node.id for node in ast.walk(defined) if isinstance(node, ast.Name)}
            if any(parameter.arg in used for parameter in params):
                return True
            if isinstance(defined, ast.Lambda):
                returns = [defined.body]
            else:
                returns = [node.value for node in _own_nodes(defined)
                           if isinstance(node, ast.Return) and node.value is not None]
            if not returns:
                return True
            return any(varies(value, inner, module, imported, depth + 1)
                       for value in returns)
        return (_kwargs_varies(expr, local, module, imported, depth)
                or varies(expr.func, local, module, imported, depth + 1)
                or any(varies(a, local, module, imported, depth + 1) for a in expr.args))
    if isinstance(expr, ast.Lambda):
        inner = dict(local)
        for parameter in [*expr.args.posonlyargs, *expr.args.args,
                          *expr.args.kwonlyargs]:
            inner.pop(parameter.arg, None)  # a free parameter can be anything
        return varies(expr.body, inner, module, imported, depth + 1)
    if isinstance(expr, (ast.FunctionDef, ast.AsyncFunctionDef)):
        inner = dict(local)
        for parameter in [*expr.args.posonlyargs, *expr.args.args,
                          *expr.args.kwonlyargs]:
            inner.pop(parameter.arg, None)  # a free parameter can be anything
        returns = [node.value for node in _own_nodes(expr)
                   if isinstance(node, ast.Return) and node.value is not None]
        return any(varies(value, inner, module, imported, depth + 1)
                   for value in returns) if returns else False
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


def _called_function(call, local, module):
    """The function this call names, when the file defines it -- else None."""
    if not isinstance(call.func, ast.Name):
        return None
    node = local.get(call.func.id) or module.get(call.func.id)
    return node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) \
        else None


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
        if isinstance(halves, dict) and "unread" in halves:
            # Not green and not refused here: no reading could be taken. `main` decides
            # whether that is allowed, so a tree that carries a control cannot use this to
            # look green.
            lines.append(f"unread   {name} -- {halves['unread']}")
            continue
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
                # The helper's name goes in the line. A refusal that names only the entry
                # leaves the reader to guess which helper it is about, and a control that
                # reports entries but not every helper is a census of records, not of the
                # file: three helpers in this tree were refused by name of their entry
                # alone, so an arm asking that every helper be reported saw them missing.
                lines.append(f"FAIL[ENTRY-DISAGREES] {record_name(entry)}: the helper "
                             f"{name}'s {'written' if not written_ok else 'repaired'} half "
                             f"is not the one the entry records")
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


# Every line this probe can open with the refusal word carries an id, and this table says
# what each id means. A word is what a reader greps for and what a gate reads: bare, it
# says a check spoke without saying which. The table is not the rule; the rule is
# computed from the expression each print site prints (`_print_openings`), and `main`
# refuses on a site the table does not cover. A site whose opening cannot be computed is
# counted separately: an answer of zero from a scan that read nothing is not an answer.
ARM_IDS = {
    "UNTOUCHED-COPY": "the copy this probe lives in is not a tree this probe refuses",
    "UNREPORTED-HELPER": "a helper defined beside this file was never reported",
    "NO-HELPER": "the copy under test defines no helper this probe can read",
    "NO-ENTRY": "the copy under test carries no entry reading the helper named",
    "NOT-REFUSED": "a tree carrying a defect this arm plants was not refused",
    "NOT-CAUGHT": "the refusal this arm asked for did not carry the id it asked for",
    "SILENT-ON-MODEL": "a half computed from an argument was read as a literal",
    "PHRASE-FOR-ID": "a line carrying the phrase under another id was taken for the id",
    "UNLABELLED-SITE": "a print site here can open a line with the refusal word and no id",
    "FIXTURE-FILES": "a file a copy of the tree reads was not carried into the fixture beside it",
}


REFUSAL_WORD = "FAIL"


def _opening_strings(node, assigns, depth=0):
    """Every string an expression can open a printed line with, or None if unreadable.

    `None` is not `[]`: it says this file cannot compute the opening, which is a
    different answer from "the opening is something else". What matters here is the first
    characters of the line, so a resolvable expression yields its strings whole.
    """
    if depth > 12:
        return None
    if isinstance(node, ast.Constant):
        return [node.value] if isinstance(node.value, str) else None
    if isinstance(node, ast.Name):
        value = assigns.get(node.id)
        return None if value is None else _opening_strings(value, assigns, depth + 1)
    if isinstance(node, ast.IfExp):
        head = _opening_strings(node.body, assigns, depth + 1)
        tail = _opening_strings(node.orelse, assigns, depth + 1)
        return None if head is None or tail is None else head + tail
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _opening_strings(node.left, assigns, depth + 1)
        right = _opening_strings(node.right, assigns, depth + 1)
        if left is None or right is None:
            return None
        return [a + b for a in left for b in right]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
        template = _opening_strings(node.left, assigns, depth + 1)
        args = node.right.elts if isinstance(node.right, ast.Tuple) else [node.right]
        if template is None or len(args) != 1:
            return None
        argument = _opening_strings(args[0], assigns, depth + 1)
        if argument is None:
            return None
        out = []
        for text in template:
            if "%" not in text:
                out.append(text)
                continue
            head, _, rest = text.partition("%")
            if not rest.startswith("s") or "%" in rest[1:]:
                return None
            out.extend(head + a + rest[1:] for a in argument)
        return out
    if isinstance(node, ast.JoinedStr):
        acc = [""]
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                piece = [part.value]
            elif isinstance(part, ast.FormattedValue):
                piece = _opening_strings(part.value, assigns, depth + 1)
            else:
                return None
            if piece is None:
                return None
            acc = [a + p for a in acc for p in piece]
        return acc
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "format"):
        return _opening_strings(node.func.value, assigns, depth + 1)
    return None


def _print_openings(source: str):
    """`(line, openings)` for every print call; openings is None when unreadable."""
    tree = ast.parse(source)
    assigns = {}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            name = node.targets[0].id
            if name in assigns:
                assigns[name] = None  # written twice: this file cannot read it
            else:
                assigns[name] = node.value
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            continue
        openings = _opening_strings(node.args[0], assigns) if node.args else [""]
        out.append((node.lineno, openings))
    return out


def unlabelled_refusal_sites(source: str) -> list:
    """The line numbers of print sites that can open the refusal word without an id.

    The question is about the line a site can print, so the answer is computed from the
    expression it prints -- constants, names this source binds to a constant,
    concatenation, `%`, conditionals, f-strings and `.format`. A site that holds the word
    in a name prints the word; a site that mentions the word away from the opening of its
    line prints something else. Sites whose opening cannot be computed are reported by
    `print_sites_with_unreadable_openings`, never silently passed over.
    """
    out = []
    for line, openings in _print_openings(source):
        if openings is None:
            continue
        if any(s.startswith(REFUSAL_WORD) and not s.startswith(REFUSAL_WORD + "[")
               for s in openings):
            out.append(line)
    return sorted(set(out))


def print_sites_with_unreadable_openings(source: str) -> list:
    """The line numbers of print sites whose opening this file cannot compute.

    These are the sites the scan above cannot answer for. Counting them as "no site"
    would be the vacuity this rule exists against: a zero from a scan that read nothing.
    """
    return sorted({line for line, openings in _print_openings(source)
                   if openings is None})


def run_check(tree, only=None):
    """One `--check` of a planted tree, narrowed to one helper where the arm asks about it.

    A control whose cost outgrows the run is not a control: eleven un-narrowed checks in
    one `--selftest` did not finish inside the hour its job allowed (exit 124, 2026-09-27),
    and an instrument that cannot be run is not read at all. An arm that patches one helper
    only asks about that helper, so it names it; the arms whose question is about the whole
    tree -- the untouched copy, the tree that refuses to read, and the `no-reader` kind,
    whose orphan check a narrowed run does not take -- still run it whole.
    """
    argv = [sys.executable, str(pathlib.Path(__file__).resolve()), "--check",
            "--root", str(tree)]
    if only:
        argv[3:3] = ["--only", only]
    return subprocess.run(argv, capture_output=True, text=True)


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
        carry(src, base, files_the_tree_reads(src))
        code = run_check(base)
        ok = code.returncode == 0
        bad += 0 if ok else 1
        # The copy under test is the tree this probe lives in. When that tree carries the
        # defect, the first refusal is the finding, not a broken fixture -- so the line
        # names it instead of leaving the reader to guess which of the two happened.
        why = next((ln for ln in code.stdout.splitlines() if ln.startswith("FAIL")), "")
        print(f"{'ok  ' if ok else 'FAIL[UNTOUCHED-COPY]'} an untouched copy is not refused "
              f"(exit {code.returncode})" + (f": {why}" if why else ""))

        # Every helper in the tree must be REPORTED, not merely looked at: a control that
        # silently drops a shape from its own universe -- the tuple convention three of
        # these helpers still use -- shows a shorter list and an unbroken exit code.
        source_names = set(HELPER.findall((src / "fragments.py").read_text(encoding="utf-8")))
        unreported = sorted(n for n in source_names if n not in code.stdout)
        bad += 1 if unreported else 0
        print(f"{'ok  ' if not unreported else 'FAIL[UNREPORTED-HELPER]'} every helper in the "
              f"tree is reported "
              f"({len(source_names) - len(unreported)}/{len(source_names)})"
              + (f": unreported {unreported}" if unreported else ""))

        rows = readings(base)
        first = rows[0][0] if rows else None
        if first is None:
            print("FAIL[NO-HELPER] the copy under test has no helper at all")
            return 1
        for kind, what in (("same-value", "a helper whose two halves are one value"),
                           ("expected-is-written", "an entry recording the written half "
                                                   "as its expected"),
                           ("no-reader", "a helper no entry reads")):
            tree = pathlib.Path(td) / kind
            tree.mkdir()
            carry(src, tree, files_the_tree_reads(src))
            patch(tree, first, kind)
            code = run_check(tree, None if kind == "no-reader" else first)
            caught = code.returncode == 1
            bad += 0 if caught else 1
            print(f"{'ok  ' if caught else 'FAIL[NOT-REFUSED]'} {what} is refused "
                  f"(exit {code.returncode})")

        # A list typed into the source is a tally of the file on the day it was typed. The
        # one this arm builds names every helper the file defines but one, and the arm that
        # would have caught the eight-name list standing beside "every _readings_of_*".
        tree = pathlib.Path(td) / "typed-list"
        tree.mkdir()
        carry(src, tree, files_the_tree_reads(src))
        frag = tree / "fragments.py"
        defined = sorted(set(HELPER.findall((src / "fragments.py").read_text(encoding="utf-8"))))
        typed = ", ".join('"%s"' % n for n in defined[:-1])
        frag.write_text(frag.read_text(encoding="utf-8") + TYPED_LIST % typed,
                        encoding="utf-8")
        code = run_check(tree, first)
        caught = code.returncode == 1
        bad += 0 if caught else 1
        print(f"{'ok  ' if caught else 'FAIL[NOT-REFUSED]'} a list typed beside the file that "
              f"does not "
              f"name every helper it defines is refused (exit {code.returncode})")

        # A tree that carries the control and still answers from the entry has to be named,
        # not silently green: without this arm the only shape the refusal is read on is a
        # two-file fixture, so a full tree could refuse to read and pass.
        tree = pathlib.Path(td) / "no-control"
        (tree / "probes").mkdir(parents=True)
        carry(src, tree, files_the_tree_reads(src))
        shutil.copy(pathlib.Path(__file__).resolve(), tree / "probes" / "parts_of_a_reading.py")
        frag = tree / "fragments.py"
        frag.write_text(
            frag.read_text(encoding="utf-8") + "\n\n"
            "class NoControlBesideThisTree(Exception):\n"
            "    \"\"\"A tree without the control beside it has no reading, and says so.\"\"\"\n"
            "\n"
            "def _readings_of_a_tree_that_refuses_to_read():\n"
            "    raise NoControlBesideThisTree('no control beside this tree')\n",
            encoding="utf-8")
        code = run_check(tree)
        caught = code.returncode == 1 and "FAIL[NO-CONTROL]" in code.stdout
        bad += 0 if caught else 1
        print(f"{'ok  ' if caught else 'FAIL[NOT-CAUGHT]'} a tree that carries the control and "
              f"refuses to "
              f"read it is refused by name (exit {code.returncode})")

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
            carry(src, tree, files_the_tree_reads(src))
            index = entry_index_for(tree, name)
            if index is None:
                print(f"FAIL[NO-ENTRY] the copy under test has no entry reading {name}")
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
            code = run_check(tree, name)
            caught = code.returncode == 1
            bad += 0 if caught else 1
            why = next((ln for ln in code.stdout.splitlines() if ln.startswith("FAIL")), "")
            print(f"{'ok  ' if caught else 'FAIL[NOT-REFUSED]'} a helper replaced by a constant "
                  f"equal to "
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
            carry(src, tree, files_the_tree_reads(src))
            index = entry_index_for(tree, name)
            if index is None:
                print(f"FAIL[NO-ENTRY] the copy under test has no entry reading {name}")
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
            code = run_check(tree, name)
            named = [ln for ln in code.stdout.splitlines()
                     if ln.startswith(LITERAL_HALF_REFUSAL)]
            caught = code.returncode == 1 and bool(named)
            bad += 0 if caught else 1
            print(f"{'ok  ' if caught else 'FAIL[NOT-CAUGHT]'} a helper whose halves are literals "
                  f"equal "
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
            carry(src, tree, files_the_tree_reads(src))
            index = entry_index_for(tree, name)
            if index is None:
                print(f"FAIL[NO-ENTRY] the copy under test has no entry reading {name}")
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
            code = run_check(tree, name)
            named = [ln for ln in code.stdout.splitlines()
                     if ln.startswith(LITERAL_HALF_REFUSAL)]
            caught = code.returncode == 1 and bool(named)
            bad += 0 if caught else 1
            print(f"{'ok  ' if caught else 'FAIL[NOT-CAUGHT]'} a half written as a call over "
                  f"literals is "
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
        for shape in ("comprehension over literals", "decoder over literals",
                      "pickle round trip", "local function over literals",
                      "local lambda over literals"):
            # The whole shape in the name, not its first word: `local function over
            # literals` and `local lambda over literals` both begin with `local`, and a
            # directory named after the first word made the second shape's arm die in
            # `mkdir` -- one decoy less, reported as a traceback rather than as a shape.
            tree = pathlib.Path(td) / ("decoy-" + "-".join(shape.split()))
            tree.mkdir()
            carry(src, tree, files_the_tree_reads(src))
            index = entry_index_for(tree, quiet[0])
            if index is None:
                print(f"FAIL[NO-ENTRY] the copy under test has no entry reading {quiet[0]}")
                return 1
            i, j = index
            ledger = json.loads((tree / "catches.json").read_text(encoding="utf-8"))
            record = (ledger["entries"][i] if j is None
                      else ledger["entries"][i]["repeats"][j])
            halves, preludes = [], []
            for key in ("observed", "expected"):
                value = ast.literal_eval(record[key])
                if shape == "comprehension over literals":
                    halves.append("{k: v for k, v in %r.items()}" % (value,))
                    preludes.append("")
                elif shape == "pickle round trip":
                    # A module nobody put on the pure list, round-tripping the literal: the
                    # spelling that made the list-of-pure-modules rule bottomless.
                    halves.append("pickle.loads(pickle.dumps(%r))" % (value,))
                    preludes.append("    import pickle\n")
                elif shape == "local function over literals":
                    halves.append("_half_%s()" % len(halves))
                    preludes.append("    def _half_%s():\n"
                                    "        return %r\n" % (len(preludes), value))
                elif shape == "local lambda over literals":
                    # The same two steps down, with the function written as a name bound to
                    # a lambda: a rule that recognises only `def` reads this call as
                    # measurement and the entry goes into the source unwitnessed.
                    halves.append("_half_%s()" % len(halves))
                    preludes.append("    _half_%s = lambda: %r\n"
                                    % (len(preludes), value))
                else:
                    blob = json.dumps(value, sort_keys=True).encode("utf-8")
                    halves.append("json.loads(base64.b64decode('%s'))"
                                  % base64.b64encode(blob).decode("ascii"))
                    preludes.append("    import base64\n    import json\n")
            imports = "".join(preludes)
            frag = tree / "fragments.py"
            frag.write_text(
                frag.read_text(encoding="utf-8")
                + "\n\ndef %s(**kw):\n%s    return {'as_written': %s, 'as_repaired': %s}\n"
                % (quiet[0], imports, halves[0], halves[1]),
                encoding="utf-8")
            code = run_check(tree, quiet[0])
            named = [ln for ln in code.stdout.splitlines()
                     if ln.startswith(LITERAL_HALF_REFUSAL)]
            caught = code.returncode == 1 and bool(named)
            bad += 0 if caught else 1
            print(f"{'ok  ' if caught else 'FAIL[NOT-CAUGHT]'} a half written as the literals of "
                  f"its own entry behind a {shape} is refused by the literal arm "
                  f"(exit {code.returncode})" + (f": {named[0][:90]}" if caught else ""))
        # The other direction, and it cost five helpers of this tree to learn: a half that
        # is COMPUTED from an argument is not the entry written down. Following a call into
        # the body of the function it names is how the literal arm closed the local-function
        # hole; the same walk, taken one step further, reads `as_written(TREES)` and
        # `shape(written)` as constants -- models over a fixture typed in the source -- and
        # refused them. The rule now stops at a function that reads an argument it was
        # handed. This arm plants such a model and requires the arm to stay SILENT on it:
        # a rule no tree can satisfy is not a stricter rule, it is a broken one.
        tree = pathlib.Path(td) / "model-over-an-argument"
        tree.mkdir()
        carry(src, tree, files_the_tree_reads(src))
        frag = tree / "fragments.py"
        frag.write_text(
            frag.read_text(encoding="utf-8")
            + "\n\ndef %s(**kw):\n"
              "    def _model(rows):\n"
              "        return {'kept': sum(1 for row in rows if row['ok']),\n"
              "                'dropped': sum(1 for row in rows if not row['ok'])}\n"
              "    kept = {'ok': True}\n"
              "    dropped = {'ok': False}\n"
              "    return {'as_written': _model([kept]),\n"
              "            'as_repaired': _model([kept, dropped])}\n"
              % quiet[0],
            encoding="utf-8")
        code = run_check(tree, quiet[0])
        named = [ln for ln in code.stdout.splitlines()
                 if ln.startswith(LITERAL_HALF_REFUSAL) and quiet[0] in ln]
        bad += 1 if named else 0
        print(f"{'ok  ' if not named else 'FAIL[SILENT-ON-MODEL]'} a half computed by a function "
              f"that reads "
              f"its argument is not read as a literal"
              + (f": {named[0][:110]}" if named else ""))

        # A half that calls a rule the helper ASSEMBLED AT RUN TIME. The rule this file
        # carried resolved a local name to its initializer, so `planted = {}` filled by
        # `exec` was the empty dict and the call through it was read as a constant: measured
        # on this tree, `FAIL[LITERAL-HALF] _readings_of_a_refusal_that_names_no_rule: the
        # as_written half is written as a literal`, `halves written as literals rather than
        # measured 1`, and the probe exiting 1 on the tree it ships in. The arm plants the
        # shape and requires the literal arm to stay SILENT: refusing a half for calling
        # something is refusing a computation, whatever the rule can resolve.
        tree = pathlib.Path(td) / "rule-assembled-at-run-time"
        tree.mkdir()
        carry(src, tree, files_the_tree_reads(src))
        frag = tree / "fragments.py"
        frag.write_text(
            frag.read_text(encoding="utf-8")
            + "\n\ndef %s(**kw):\n"
              "    planted = {}\n"
              "    exec(compile('def scan(source):\\n    return [1]\\n', '<planted>',"
              " 'exec'), planted)\n"
              # Both halves call something here, and that is the point of the fixture: a
              # repaired half left as a bare dict is a half that computes nothing, which
              # this probe's literal arm refuses on its own account -- the first version of
              # this arm wrote `{'a': 2}` and was read as a literal, so it measured the
              # literal rule instead of the call it means to test.
              "    return {'as_written': {k: planted['scan'](k) for k in ['a']},\n"
              "            'as_repaired': {'a': len(planted['scan']('b'))}}\n"
              % quiet[0],
            encoding="utf-8")
        code = run_check(tree, quiet[0])
        named = [ln for ln in code.stdout.splitlines()
                 if ln.startswith(LITERAL_HALF_REFUSAL) and quiet[0] in ln]
        bad += 1 if named else 0
        print(f"{'ok  ' if not named else 'FAIL[LITERAL-HALF-ON-A-CALL]'} a half that calls a "
              f"rule the "
              f"helper assembled at run time is not read as a literal"
              + (f": {named[0][:110]}" if named else ""))

        # And the same rule's measured cost, printed rather than hidden: a name handed to
        # `exec` is unresolved, so a helper that hands its halves into an `exec` and returns
        # them out of it is accepted -- the constant is inside code the tree writes at run
        # time, which no reading of the source can follow. Registered as
        # `a-constant-hidden-in-code-the-helper-writes-at-run-time`.
        tree = pathlib.Path(td) / "constant-behind-exec"
        tree.mkdir()
        carry(src, tree, files_the_tree_reads(src))
        frag = tree / "fragments.py"
        frag.write_text(
            frag.read_text(encoding="utf-8")
            + "\n\ndef %s(**kw):\n"
              "    planted = {}\n"
              "    exec(compile(\"d = {'rows': 1}\\n\", '<planted>', 'exec'), planted)\n"
              "    return {'as_written': planted['d'], 'as_repaired': {'rows': 2}}\n"
              % quiet[0],
            encoding="utf-8")
        code = run_check(tree, quiet[0])
        hidden = [ln for ln in code.stdout.splitlines()
                  if ln.startswith(LITERAL_HALF_REFUSAL) and quiet[0] in ln]
        print(f"cost  a constant handed into `exec` and returned out of it is accepted by the "
              f"literal arm ({'refused' if hidden else 'not refused'}): the rule reads a name "
              f"`exec` was handed as unresolved, so it cannot tell a computation there from a "
              f"value written into code the tree runs")

        # The phrase is not a name. This line is another class's refusal -- a half that
        # disagrees with its entry -- reusing the words the literal arm used to match on,
        # and it is exactly the line the substring rule would have accepted.
        impostor = (f"{ENTRY_REFUSAL} an entry: the helper's written half is not the one "
                    f"the entry records, so it is written as a literal twice over")
        taken = [ln for ln in impostor.splitlines()
                 if ln.startswith(LITERAL_HALF_REFUSAL)]
        bad += 1 if taken else 0
        print(f"{'ok  ' if not taken else 'FAIL[PHRASE-FOR-ID]'} a refusal that reuses the phrase "
              f"under "
              f"another id is not taken for the literal refusal" + (f": {taken}" if taken
                                                                    else ""))


        # The word is what a reader greps for and a gate reads, and an id is what says
        # which check spoke. An independent review found sixteen sites in this file able
        # to print the word with no id beside it, and a run that exits 1 with a bare line
        # leaves the reader to guess -- exit 1 does not imply a named refusal exists. The
        # rule is measured here on this file's own source, and on a copy with one id
        # stripped, so the arm fails if the scan stops reading sites rather than matching
        # fewer of them.
        mine = pathlib.Path(__file__).read_text(encoding="utf-8")
        unlabelled = unlabelled_refusal_sites(mine)
        bad += 1 if unlabelled else 0
        print(f"{'ok  ' if not unlabelled else 'FAIL[UNLABELLED-SITE]'} every print site in this "
              f"file that can print the refusal word carries an id "
              f"({len(unlabelled)} without: {unlabelled[:4]})")
        stripped = mine.replace("FAIL[NO-HELPER] ", "FAIL ", 1)
        found = unlabelled_refusal_sites(stripped)
        bad += 0 if found else 1
        print(f"{'ok  ' if found else 'FAIL[UNLABELLED-SITE]'} a copy of this file with one id "
              f"stripped is read as an unlabelled site" + (f": lines {found}" if found else ""))


        # The scan above is a reading of a source, so it is measured on sources written
        # to be read by it. A site that holds the refusal word in a name is a site that
        # prints the word, and a site that mentions the word away from the opening of its
        # line is not one: a scan matching the text around a site misses the first and
        # flags the second, which is how these two shapes were found.
        held = 'word = "FAIL"\nprint(word + " the tree is broken")\n'
        found_held = unlabelled_refusal_sites(held)
        bad += 0 if found_held else 1
        print(f"{'ok  ' if found_held else 'FAIL[UNLABELLED-SITE]'} a site that holds the "
              f"refusal word in a name is a site that prints it ({found_held})")
        mid = 'print("the gate said FAIL, and the run continued")\n'
        found_mid = unlabelled_refusal_sites(mid)
        bad += 0 if not found_mid else 1
        print(f"{'ok  ' if not found_mid else 'FAIL[UNLABELLED-SITE]'} a site that mentions the "
              f"word away from the opening of its line is not one ({found_mid})")
        unreadable = print_sites_with_unreadable_openings('import sys\nprint(sys.argv[0])\n')
        bad += 0 if unreadable else 1
        print(f"{'ok  ' if unreadable else 'FAIL[UNLABELLED-SITE]'} a site whose opening this "
              f"file cannot compute is counted, not passed over ({unreadable})")

        # A `%`-template is not the line it renders. The reader answered with the template,
        # so `print("%s ..." % "FAIL")` -- a line that opens with the refusal word and no id --
        # was neither named nor counted: the site was invisible to both questions. Found by
        # asking the scan about shapes it was not written against, not by rereading it.
        via_percent = 'print("%s the tree is broken" % "FAIL")\n'
        found_percent = unlabelled_refusal_sites(via_percent)
        bad += 0 if found_percent else 1
        print(f"{'ok  ' if found_percent else 'FAIL[UNLABELLED-SITE]'} a site that renders the "
              f"refusal word through a template is a site that prints it ({found_percent})")
        odd_conversion = 'print("%d rows" % 3)\n'
        named_odd = unlabelled_refusal_sites(odd_conversion)
        unread_odd = print_sites_with_unreadable_openings(odd_conversion)
        bad += 0 if (not named_odd and unread_odd) else 1
        print(f"{'ok  ' if (not named_odd and unread_odd) else 'FAIL[UNLABELLED-SITE]'} a "
              f"template this file cannot render is counted, not answered "
              f"(named={named_odd}, unreadable={unread_odd})")


        # The fixture list, one level down from the copy rule: a hand-written tuple of
        # names carries what the tree needed when it was written. The tuple here was
        # `("fragments.py", "catches.json")`, a helper beside them reads `check.py`, and
        # every arm of this selftest printed `0/19 helpers reported` with a traceback --
        # a broken probe read as the defect it had planted. The list is derived from the
        # imports of the copy, and this arm adds a sibling module, imports it, and
        # requires the derivation to carry it.
        tree = pathlib.Path(td) / "reads-a-sibling"
        tree.mkdir()
        (tree / "fragments.py").write_text("import json\nimport helper_module\n",
                                           encoding="utf-8")
        (tree / "helper_module.py").write_text("VALUE = 1\n", encoding="utf-8")
        carried = files_the_tree_reads(tree)
        ok_sibling = "helper_module.py" in carried
        bad += 0 if ok_sibling else 1
        print(f"{'ok  ' if ok_sibling else 'FAIL[FIXTURE-FILES]'} a module a copy of the tree "
              f"imports is carried into the fixture beside it ({sorted(carried)})")

    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--only", default=None,
                    help="read one helper by name, so a control that plants one defect "
                         "does not pay for every other helper in the tree")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    root = pathlib.Path(args.root)
    source = (root / "fragments.py").read_text(encoding="utf-8")
    rows = readings(root, args.only)
    if args.only is not None and not rows:
        print("FAIL[NO-HELPER] --only names a helper this tree does not define; nothing "
              "was read")
        print(f"          the name asked for: {args.only}")
        return 1
    lines, bad = verdicts(rows)
    for line in lines:
        print(line)
    stale = tallies_that_do_not_cover_the_file(source)
    for line, named, defined, missing, extra in stale:
        print(f"FAIL[TYPED-LIST] fragments.py:{line} types {named} name(s) beside the file's "
              f"{len(defined)}: never named {missing or '[]'}, not defined {extra or '[]'}")
    # A narrowed run cannot answer this: the perturbations of every helper it did not
    # read are absent from `rows`, and a control read as missing is a false refusal.
    orphaned = [] if args.only else perturbations_no_helper_answers_to(rows)
    for name in orphaned:
        print(f"FAIL[ORPHAN-INPUT] this probe declares an input for {name}, and no helper answers to it")
    typed = halves_typed_rather_than_measured(source)
    for name, half, line, expr in typed:
        print(f"FAIL[LITERAL-HALF] {name}: the {half} half is written as a literal at "
              f"fragments.py:{line}: {expr} -- a half that calls nothing is a sentence "
              f"about the entry, not a reading of the tree")
    unvaryable = sorted(name for name, *_rest, moved in rows if moved is None)
    unread = sorted(name for name, halves, *_rest in rows
                    if isinstance(halves, dict) and "unread" in halves)
    carrying = (root / "probes" / "parts_of_a_reading.py").exists()
    for name in unread if carrying else []:
        print(f"FAIL[NO-CONTROL] {name}: this tree carries the control and the helper "
              f"refuses to read it, so the half stands on the entry rather than on the tree")
    print(f"helpers with two halves  {len(rows)}")
    print(f"helpers whose input no caller varies  {len(unvaryable)}")
    print(f"halves not read against an entry  {bad}")
    print(f"halves written as literals rather than measured  {len(typed)}")
    print(f"typed lists that do not cover the file  {len(stale)}")
    print(f"helpers with no control beside this tree  {len(unread)}")
    unlabelled = unlabelled_refusal_sites(pathlib.Path(__file__).read_text(encoding="utf-8"))
    for line in unlabelled:
        print(f"FAIL[UNLABELLED-SITE] this probe's print site at parts_of_a_reading.py:{line} "
              f"can open a line with the refusal word and no id beside it")
    print(f"print sites that can open the refusal word with no id  {len(unlabelled)}")
    unread_openings = print_sites_with_unreadable_openings(
        pathlib.Path(__file__).read_text(encoding="utf-8"))
    print(f"print sites whose opening this file cannot compute  {len(unread_openings)}")
    if args.check and (bad or stale or orphaned or typed or unlabelled
                      or (unread and carrying)):
        print("REFUSED: a helper's half is not the one the entry records, or nothing in this "
              "repository reads it, or its answer does not move with the input it declares "
              "-- either way the half that says what the repair does is unwitnessed, so it "
              "can be a constant and every suite stays green; or a list typed into "
              "fragments.py no longer covers the helpers the file defines, so a tally taken "
              "from it is a sentence about an older file; or this probe declares an input "
              "for a helper this tree does not carry, so that control tests nothing; or a "
              "half is written as a literal instead of computed, so it is the entry written "
              "a second time and every comparison against that entry is satisfied by it; or "
              "this tree carries the control beside it and a helper still answers that no "
              "control stands there, so that helper is read from its entry and not from the "
              "tree; or a print site in this probe can open a line with the refusal word "
              "and no id beside it, so a failing run names nothing")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
