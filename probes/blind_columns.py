#!/usr/bin/env python3
"""Which fields of this repository's records can a consumer fail on?

WHY THIS EXISTS
---------------
A record field is a sentence until something reads it back. A column every run
writes and no check ever reads cannot fail: a record edited to lie about it is
indistinguishable from an honest one, and the field stays in the table looking
like evidence. That defect was found here by hand twice -- the ladder's `sent`
column held the answer's status line while the annotation beside it declared
the divergence check it existed to serve, and `answerer`/`headers` were written
by every run and read back by none, so a record that named a foreign authority
as the wall passed `--check`. A hand census does not run again next month; this
probe is that census, made mechanical and standing, so the shape is caught by a
program next time instead of by a reader noticing.

WHAT IT DECIDES, AND HOW
------------------------
For every field name carried by the records this repository's own code writes
(see PRODUCERS), it asks: does any Python module in the shipped tree READ that
name? A read is decided by PARSING the module with `ast`, never by counting how
often the name appears in the text:

  * `x["field"]`     a subscript with a literal key, in a Load context
  * `x.get("field")` a mapping access with a literal key (`pop` too)
  * `"field" in x`   a membership test against a literal name
  * `f(field=...)`   a keyword argument named after the field
  * `x.field`        attribute access named after the field
  * a NAME used as a key (`x[name]`, `x.get(name)`) where that name is bound by
    a `for` loop over a literal sequence of strings -- a reader that spells the
    field name once, in a tuple, and reaches it three lines later through a
    variable. This one matters: it is exactly how the ladder reads `answerer`
    and `headers` back, and a detector that only matches literal keys would
    call those two unread in the very repo that fixed them.

A WRITE is a dict-literal key, or a subscript in a Store/Del context. A field
with writes and no read is reported NO READER, which is the whole point: that
is the shape both hand censuses found.

Two grades of read are printed, because they are not the same evidence. `READ`
stands on a site that names the field (subscript, `.get`, `in`, kwarg, or the
loop-bound name). `READ?` stands only on an attribute access `x.field`, which
matches a dataclass field ... and `Path.name` alike; it is reported so a human
can look, not so the verdict can be trusted. A verdict of `READ?` is not a
reader until somebody has read the site.

THE TEMPTATION, NAMED
---------------------
`grep -c answerer` answers this in one line and is wrong in both directions: it
counts the write site and the comment beside it as eagerly as a reader, and it
cannot see the loop-bound reader above, which spells the name once and reads it
three lines later through a variable. A count of a name is not a count of its
readers, so no verdict here comes from a regex over the text.

WHAT IT CANNOT SEE (say it, do not hide it)
-------------------------------------------
* What is parsed is Python: the `*.py` modules and the Python heredocs inside
  the `.sh` runners (`repro/run_all.sh` reads `regression.json` from one, and a
  `.py`-only census was wrong about four columns of that record until this one
  learned to look). Shell code itself -- a `jq`, an `awk`, a `grep` over a
  record -- is still invisible, and a field read only there comes back NO
  READER. That is a limitation of the instrument, not a reading of the field.
* A reader that walks a row generically (`for k, v in row.items()`) never spells
  the field name and is invisible too.
* The verdict is global: a name is READ if any module in the tree reads that
  name, so a field read only for a *different* record counts as read. The
  record file is printed on every line but the index is shared.
* An attribute site is weak evidence -- `x.field` matches a dataclass field and
  `args.out` alike -- so a field standing only on one is printed `READ?` and
  counted in neither the reader nor the no-reader total until a human looks.

Usage:
    python3 probes/blind_columns.py            # print the census
    python3 probes/blind_columns.py --check    # run the control, then the census;
                                               # exit non-zero if the control fails
    python3 probes/blind_columns.py --strict   # exit non-zero while any field has no
                                               # reader: the census as a gate that
                                               # stays red until the columns are read

THE CONTROL, AND WHY IT CAN GO RED
----------------------------------
`--check` writes a synthetic record and a synthetic consumer with known readers
and known non-readers into a temp directory inside this workspace (never /tmp,
which is private to each command here), runs the SAME census over them, and
requires every verdict to match what the consumer does. The three cases it is
built around are the three the question turns on:

  * a field that IS read must come back READ;
  * a field that is NOT read must come back NO READER;
  * a field that is read only as a WRITE must come back NO READER.

A control that cannot fail is worthless, so the read-detection can be broken on
purpose with `--sabotage none` (no read is ever found) or `--sabotage all`
(every field is reported read); the control is expected to go red under either
and to name the expectation it caught. Run it both ways and see.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field as dc_field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()

# The control's scratch lives under a fixed name inside the workspace so it is
# never /tmp (private to each command) and never tracked tree material. Both
# scans below skip it, and both skip the directories that are not the shipped
# tree: `verify/` and `.audit/` hold snapshots an auditor made (whatever they
# read, the shipped module of the same name reads too, so counting them would
# double-count), `.uvcache/` is a package cache.
CONTROL_ROOT = ROOT / ".blind_columns_control"
SKIP_DIRS = frozenset({
    ".git", ".uvcache", ".audit", ".mutations", "verify", "__pycache__",
    CONTROL_ROOT.name,
})

# Records this repository's own code writes, and the file that writes them.
# A record is in scope because some code in the repo regenerates it: the census
# is about fields this repo's writer produces, and a JSON nobody writes is
# somebody's input, not this repo's record. The list is short on purpose and
# printed with each run (see `unlisted_records`) so a reader can see what it
# leaves out and disagree with the choice.
PRODUCERS = {
    "probes/ladder_rungs.json": "probes/ladder_rungs.py",
    "label_recovery.json": "recover_labels.py",
    "blind_classes.json": "export_blind.py",
    "catches.json": "recover_labels.py",
    "doors/refusal_doors.json": "doors/refusal_doors.py",
    "repro/fresco/regression.json": "repro/run_all.sh",
}

# Records whose writer takes the output path as an argument, so the committed
# copy is a receipt from a command rather than a file the module names. The
# claim "this code writes this file" is then a claim about a command, and the
# run prints the command: a record with no command in the tree cannot be
# regenerated, and a reader who cannot regenerate it cannot tell a stale copy
# from a fresh one. `check_producers` proves the command is that writer's
# interface by finding each flag in the writer's source.
RECEIPTS = {
    "probes/v1_prefix_door.json": (
        "probes/v1_prefix_door.py", "--out probes/v1_prefix_door.json"),
}

ALL_RECORDS = {**PRODUCERS, **{p: w for p, (w, _) in RECEIPTS.items()}}


@dataclass(frozen=True)
class Site:
    """One place a parsed module touches a field name."""

    rel: str
    line: int
    kind: str
    note: str = ""


@dataclass
class Row:
    record: str
    container: str
    field: str
    carrying: int
    rows: int
    verdict: str
    sites: list = dc_field(default_factory=list)
    writes: list = dc_field(default_factory=list)


def rel_of(path) -> str:
    """A path worth printing: repo-relative, with the minted part NOT in it.

    The control lives in a directory made fresh on every run. Printing its name
    makes two runs of this tool differ for a reason that is not behaviour, which
    is the same defect as a count that moves on its own: a reader comparing the
    two sees a difference that means nothing, and a stability check fails an item
    that is in fact stable. The minted component is printed as `<control>`.
    """
    try:
        rel = str(Path(path).relative_to(ROOT))
    except ValueError:
        rel = str(path)
    parts = rel.split("/")
    for i, part in enumerate(parts):
        if part.startswith("control-"):
            parts[i] = "<control>"
    return "/".join(parts)


def literal_str(node):
    """The field name a node spells literally, or None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def literal_sequence(node):
    """The elements of a literal tuple/list/set, or None for anything else."""
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return list(node.elts)
    return None


def bindings_of(target, it, line):
    """The field names one loop header binds, per name: name -> [(field, line)].

    `for field in ("sent", "curl_rc")` binds `field` to each name; so does
    `for field, want in (("answerer", who), ("headers", h))`, which binds
    positionally out of the literal tuples. A reader of this shape spells the
    field name once and then reaches it through a variable, so a literal-key
    detector alone calls such a field unread.
    """
    binds = defaultdict(list)
    elements = literal_sequence(it)
    if elements is None:
        return binds
    names = list(target.elts) if isinstance(target, ast.Tuple) else [target]
    for element in elements:
        spelled = literal_str(element)
        if spelled is not None:
            for name in names:
                if isinstance(name, ast.Name):
                    binds[name.id].append((spelled, line))
            continue
        inner = literal_sequence(element)
        if inner is None:
            continue
        for i, name in enumerate(names):
            if isinstance(name, ast.Name) and i < len(inner):
                spelled = literal_str(inner[i])
                if spelled is not None:
                    binds[name.id].append((spelled, line))
    return binds


def loop_scopes(tree):
    """[(bindings, body, line)] -- one entry per loop that can bind field names.

    The body travels with the binding so the evidence stays honest. `field` is
    bound twice in probes/ladder_rungs.py -- once to the four measured columns
    and once to `answerer`/`headers` -- and a join that paired every use of the
    name with every binding would print, against `answerer`, the comparison
    lines that belong to the other loop. Sites offered as evidence must be the
    sites the binding actually reaches, or the tool prints a proof of something
    other than what it claims.
    """
    scopes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.For, ast.AsyncFor)):
            binds = bindings_of(node.target, node.iter, node.lineno)
            if binds:
                scopes.append((binds, [*node.body, *node.orelse], node.lineno))
        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp,
                               ast.GeneratorExp)):
            body = ([node.key, node.value] if isinstance(node, ast.DictComp)
                    else [node.elt])
            binds = defaultdict(list)
            for gen in node.generators:
                for name, pairs in bindings_of(
                        gen.target, gen.iter, getattr(gen.iter, "lineno", 0)).items():
                    binds[name].extend(pairs)
                body.extend(gen.ifs)
            if binds:
                scopes.append((binds, body, node.lineno))
    return scopes


def key_uses(tree):
    """(name, line) for every place a bare NAME is used as a mapping key."""
    uses = []
    for node in ast.walk(tree):
        if (isinstance(node, ast.Subscript) and isinstance(node.ctx, ast.Load)
                and isinstance(node.slice, ast.Name)):
            uses.append((node.slice.id, node.lineno))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in ("get", "pop") and node.args
                and isinstance(node.args[0], ast.Name)):
            uses.append((node.args[0].id, node.lineno))
        elif (isinstance(node, ast.Compare)
                and any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops)):
            for operand in [node.left, *node.comparators]:
                if isinstance(operand, ast.Name):
                    uses.append((operand.id, node.lineno))
    return uses


def index_code(sources):
    """reads / writes / loop-bound reads, keyed by field name.

    `sources` are (label, line offset, text) triples, so the same walk covers a
    module and the Python block a shell runner carries in a heredoc.
    """
    reads, writes, indirect = defaultdict(list), defaultdict(list), defaultdict(list)
    skipped = []
    for rel, offset, text in sources:
        try:
            tree = ast.parse(text, filename=rel)
        except (SyntaxError, ValueError):
            skipped.append(rel)
            continue
        scopes = loop_scopes(tree)
        # An attribute that is *called* is a method, not a record field:
        # `stopping.set()`, `sys.exit(0)` and `row.items()` name no column, and
        # counting them as reads of `set`, `exit` and `items` was the first
        # false verdict this census produced.
        called = {id(n.func) for n in ast.walk(tree) if isinstance(n, ast.Call)}
        for node in ast.walk(tree):
            line = offset + getattr(node, "lineno", 0)
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    name = literal_str(key)
                    if name is not None:
                        writes[name].append(Site(rel, line, "{...}"))
            if isinstance(node, ast.Subscript):
                name = literal_str(node.slice)
                if name is not None:
                    if isinstance(node.ctx, ast.Load):
                        reads[name].append(Site(rel, line, 'x["k"]'))
                    else:
                        writes[name].append(Site(rel, line, "x[k] ="))
            if isinstance(node, ast.Call):
                if (isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("get", "pop") and node.args):
                    name = literal_str(node.args[0])
                    if name is not None:
                        reads[name].append(Site(rel, line, f".{node.func.attr}()"))
                for kw in node.keywords:
                    if kw.arg:
                        reads[kw.arg].append(Site(rel, line, f"{kw.arg}="))
            if isinstance(node, ast.Attribute) and id(node) not in called:
                reads[node.attr].append(Site(rel, line, ".attr"))
            if (isinstance(node, ast.Compare)
                    and any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops)):
                for operand in [node.left, *node.comparators]:
                    name = literal_str(operand)
                    if name is not None:
                        reads[name].append(Site(rel, line, "in"))
                    for inner in literal_sequence(operand) or []:
                        name = literal_str(inner)
                        if name is not None:
                            reads[name].append(Site(rel, line, "in {...}"))
        for binds, body, _line in scopes:
            uses = []
            for part in body:
                uses.extend(key_uses(part))
            for name, line in uses:
                for field_name, bind_line in binds.get(name, []):
                    indirect[field_name].append(Site(
                        rel, offset + line, f"key name {name!r}",
                        f"bound at {rel}:{offset + bind_line}"))
    return reads, writes, indirect, skipped


def row_container(doc):
    """The list of dicts a record is made of: the largest one, or None.

    Records here carry their rows under a named key (`cells`, `rows`, `items`)
    or as the top-level list (`doors/refusal_doors.json`). Taking the largest
    list of dicts finds both without a per-file rule; nested lists inside a row
    are not descended into, so a row's own list-valued field is never mistaken
    for the container.
    """
    best = [None]

    def walk(node, path):
        if isinstance(node, list) and node and all(isinstance(e, dict) for e in node):
            if best[0] is None or len(node) > len(best[0][1]):
                best[0] = (path or "<top>", node)
            return
        if isinstance(node, list):
            for i, element in enumerate(node):
                walk(element, f"{path}[{i}]")
        elif isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}")

    walk(doc, "")
    return best[0] if best[0] else (None, None)


def load_record(path):
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    container, rows = row_container(doc)
    return container, rows


def kind_rank(kind):
    """How much a site's shape proves about the field it names.

    A key read out of a mapping (`x["k"]`, `.get()`, `in`) is proof; a keyword
    argument or a literal set is proof only if you also believe the call is
    about this record; an attribute is the weakest of the three. The grade does
    not change the verdict, it orders the evidence: with three sites printed
    per field, a line whose first two entries are `headers=` in two unrelated
    modules is a line a reader stops trusting.
    """
    if kind.startswith("key name"):
        return 0
    if kind in ('x["k"]', ".get()", ".pop()", "in"):
        return 0
    if kind.endswith("=") or kind == "in {...}":
        return 1
    return 2


def verdicts(records, sources, sabotage="off"):
    """(rows, sources that could not be parsed) for the given records."""
    reads, writes, indirect, skipped = index_code(sources)
    out = []
    for path in records:
        rel = rel_of(path)
        container, rows = load_record(path)
        if rows is None:
            out.append(Row(rel, "-", "<no list of dicts found>", 0, 0,
                           "NO READER"))
            continue
        counts = Counter()
        for row in rows:
            counts.update(row.keys())
        for name in sorted(counts):
            strong = sorted({s for s in reads.get(name, []) if s.kind != ".attr"},
                            key=lambda s: (kind_rank(s.kind), s.rel, s.line))
            weak = sorted({s for s in reads.get(name, []) if s.kind == ".attr"},
                          key=lambda s: (s.rel, s.line))
            ind = sorted(set(indirect.get(name, [])), key=lambda s: (s.rel, s.line))
            wrote = sorted(set(writes.get(name, [])), key=lambda s: (s.rel, s.line))
            if sabotage == "none":
                strong, weak, ind = [], [], []
            if sabotage == "all":
                strong = strong or [Site("<sabotage=all>", 0, "every field forced read")]
            sites = [*sorted(strong + ind, key=lambda s: (kind_rank(s.kind), s.rel, s.line))]
            # An attribute site is printed only when it is the whole evidence:
            # a line saying READ that then shows three `x.attr` sites reads as if
            # the attributes proved it, and they are the one shape this census
            # does not trust.
            if not sites:
                sites = weak
            verdict = "READ" if (strong or ind) else ("READ?" if weak else "NO READER")
            out.append(Row(rel, container, name, counts[name], len(rows),
                           verdict, sites, wrote))
    return out, skipped


def site_text(site):
    text = f"{site.rel}:{site.line} {site.kind}"
    if site.note:
        text += f" ({site.note})"
    return text


def render(out, limit=3):
    lines = []
    current = None
    for row in out:
        if row.record != current:
            current = row.record
            lines.append("")
            lines.append(f"== {row.record}  (container {row.container!r}, "
                         f"{row.rows} rows)")
        if row.verdict == "NO READER":
            evidence = ""
            if row.writes:
                shown = "  ".join(site_text(s) for s in row.writes[:limit])
                more = f"  +{len(row.writes) - limit} more" if len(row.writes) > limit else ""
                evidence = f"written at {shown}{more}"
            lines.append(f"   {row.field:<24} {row.carrying:>3}/{row.rows:<3} "
                         f"NO READER   {evidence}".rstrip())
        else:
            shown = "  ".join(site_text(s) for s in row.sites[:limit])
            more = f"  +{len(row.sites) - limit} more" if len(row.sites) > limit else ""
            lines.append(f"   {row.field:<24} {row.carrying:>3}/{row.rows:<3} "
                         f"{row.verdict:<4} {shown}{more}")
    examined = len(out)
    unread = [r for r in out if r.verdict == "NO READER"]
    attr_only = [r for r in out if r.verdict == "READ?"]
    lines.append("")
    lines.append(f"{examined} fields examined; {len(unread)} have no reader; "
                 f"{len(attr_only)} rest only on an attribute site (READ?)")
    if unread:
        lines.append("no reader: " + ", ".join(f"{r.record}:{r.field}" for r in unread))
    return lines


def check_receipts():
    """A receipt's recorded command must be that writer's interface."""
    problems = []
    for rel, (writer, command) in sorted(RECEIPTS.items()):
        if not (ROOT / rel).exists():
            problems.append(f"{rel}: receipt listed but the file is missing")
            continue
        if not (ROOT / writer).exists():
            problems.append(f"{rel}: claimed writer {writer} is missing")
            continue
        text = (ROOT / writer).read_text(encoding="utf-8", errors="replace")
        for token in command.split():
            if token.startswith("--") and token not in text:
                problems.append(f"{rel}: command {command!r} uses {token!r}, which "
                                f"{writer} does not accept")
    return problems


HEREDOC = re.compile(r"<<-?\s*(?:'([A-Za-z_][A-Za-z0-9_]*)'"
                     r'|"([A-Za-z_][A-Za-z0-9_]*)"'
                     r"|([A-Za-z_][A-Za-z0-9_]*))")


def shell_python_sources(path):
    """(line offset, text) for every python heredoc in a shell runner.

    `repro/run_all.sh` writes `regression.json` and then compares two copies of
    it from a `python3 - <<'PY'` block that reads `i["exit"]`, `i.get("set")`
    and the rest. A census that parses only `*.py` reports those columns NO
    READER, which is a statement about the instrument rather than about the
    field. The block is Python the repository ships, so it is parsed like the
    rest, with the shell file's own line numbers kept.
    """
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    sources, i = [], 0
    while i < len(lines):
        line = lines[i]
        if "python3" in line:
            match = HEREDOC.search(line)
            if match:
                tag = next(g for g in match.groups() if g)
                start = i + 1
                end = start
                while end < len(lines) and lines[end].strip() != tag:
                    end += 1
                if end < len(lines):
                    sources.append((start, "\n".join(lines[start:end])))
                    i = end
        i += 1
    return sources


def code_sources():
    """(label, line offset, text) for everything in the tree that is Python."""
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.resolve() == SELF:
            continue
        parts = path.relative_to(ROOT).parts[:-1]
        if any(part in SKIP_DIRS for part in parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if path.suffix == ".py":
            yield rel_of(path), 0, text
        elif path.suffix == ".sh":
            for offset, block in shell_python_sources(path):
                yield f"{rel_of(path)} (python heredoc)", offset, block


def unlisted_records():
    """JSON with rows that no producer in PRODUCERS claims: printed, not judged."""
    found = []
    for path in sorted(ROOT.rglob("*.json")):
        parts = path.relative_to(ROOT).parts[:-1]
        if any(part in SKIP_DIRS for part in parts):
            continue
        rel = rel_of(path)
        if rel in ALL_RECORDS:
            continue
        try:
            container, rows = load_record(path)
        except (OSError, ValueError):
            continue
        if rows:
            found.append(f"{rel} ({container!r}, {len(rows)} rows)")
    return found


def check_producers():
    """Each claimed record exists and the claimed writer names it."""
    problems = []
    for rel, writer in sorted(PRODUCERS.items()):
        if not (ROOT / rel).exists():
            problems.append(f"{rel}: producer listed but the file is missing")
            continue
        if not (ROOT / writer).exists():
            problems.append(f"{rel}: claimed producer {writer} is missing")
            continue
        text = (ROOT / writer).read_text(encoding="utf-8", errors="replace")
        if Path(rel).name not in text:
            problems.append(f"{rel}: claimed producer {writer} never names the file, "
                            "so the claim that it is written there is unproven")
    return problems


# ---------------------------------------------------------------- the control

CONTROL_MODULE = '''\
"""A consumer with known readers, for the census to disagree with."""


def consume(rec):
    a = rec["subscript_read"]
    b = rec.get("get_read")
    assert "membership_read" in rec
    d = kwarg_call(kwarg_read=1)
    e = rec.attribute_read
    rec["store_only"] = 1
    only_write = {"write_only": 1}
    for name in ("loop_read",):
        f = rec[name]
    return a, b, d, e, f, only_write


def kwarg_call(**kw):
    return kw
'''

CONTROL_RECORD = {"rows": [{
    "subscript_read": 1, "get_read": 1, "membership_read": 1, "kwarg_read": 1,
    "attribute_read": 1, "store_only": 1, "write_only": 1, "loop_read": 1,
    "unread_field": 1,
}]}

# What the consumer above does, per field. SPENT as the census's answer sheet.
CONTROL_EXPECT = [
    ("subscript_read", "READ"),       # rec["subscript_read"]
    ("get_read", "READ"),             # rec.get("get_read")
    ("membership_read", "READ"),      # "membership_read" in rec
    ("kwarg_read", "READ"),           # kwarg_call(kwarg_read=1)
    ("loop_read", "READ"),            # for name in ("loop_read",): rec[name]
    ("attribute_read", "READ?"),      # rec.attribute_read, weak evidence
    ("write_only", "NO READER"),      # only a dict-literal key
    ("store_only", "NO READER"),      # only a subscript store
    ("unread_field", "NO READER"),    # named nowhere in the consumer
]

CONTROL_CHECKS = [
    ("a field that IS read is reported as read",
     ["subscript_read", "get_read", "membership_read", "kwarg_read", "loop_read"],
     "READ"),
    ("a field that is NOT read is reported as unread",
     ["unread_field"], "NO READER"),
    ("a field that is read only as a WRITE is reported as unread",
     ["write_only", "store_only"], "NO READER"),
    ("a field resting only on an attribute site is not called a plain read",
     ["attribute_read"], "READ?"),
]


def run_control(sabotage):
    """Build the synthetic pair, run the census over it, print and return rc."""
    CONTROL_ROOT.mkdir(exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="control-", dir=CONTROL_ROOT))
    try:
        module = work / "consumer.py"
        record = work / "control_record.json"
        module.write_text(CONTROL_MODULE, encoding="utf-8")
        record.write_text(json.dumps(CONTROL_RECORD), encoding="utf-8")
        out, _skipped = verdicts([record], [(rel_of(module), 0, CONTROL_MODULE)],
                                 sabotage=sabotage)
        got = {row.field: row for row in out}

        print(f"control module: {rel_of(module)}")
        print(f"control record: {rel_of(record)}   (sabotage={sabotage})")
        for row in out:
            if row.verdict == "NO READER":
                evidence = ""
                if row.writes:
                    evidence = "written at " + "  ".join(
                        site_text(s) for s in row.writes)
                print(f"   {row.field:<20} {row.verdict:<10} {evidence}".rstrip())
            else:
                print(f"   {row.field:<20} {row.verdict:<10} "
                      + "  ".join(site_text(s) for s in row.sites))

        print()
        failures = 0
        for label, fields, want in CONTROL_CHECKS:
            wrong = [f for f in fields if f not in got or got[f].verdict != want]
            detail = ("as the consumer does" if not wrong
                      else "; ".join(
                          f"{f} came back {got[f].verdict if f in got else 'ABSENT'}"
                          for f in wrong))
            if wrong:
                failures += 1
            print(f"{'RED ' if wrong else 'ok  '} {label}")
            print(f"     {detail}")
        # A verdict nobody stated is a verdict nobody checked: a field the
        # control's consumer never reads must not come back read either.
        stated = {f for _, fields, _ in CONTROL_CHECKS for f in fields}
        extra = sorted(f for f in got if f not in stated and got[f].verdict != "NO READER")
        print(f"{'RED ' if extra else 'ok  '} every control field reads as the consumer does")
        print(f"     unstated fields reported read: {extra}" if extra
              else f"     {len(got)} fields, all accounted for by the checks above")
        if extra:
            failures += 1
        total = len(CONTROL_CHECKS) + 1
        print(f"\n{total - failures}/{total} control checks hold")
        return 1 if failures else 0
    finally:
        shutil.rmtree(work, ignore_errors=True)
        try:
            CONTROL_ROOT.rmdir()   # leave the tree as it was found
        except OSError:
            pass


# ----------------------------------------------------------------------- main

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="run the control against the census; non-zero if it fails")
    parser.add_argument("--sabotage", choices=("off", "none", "all"), default="off",
                        help="deliberately break read-detection so the control can be "
                             "seen going red (none: no read is ever found; all: every "
                             "field is reported read; off: the honest census)")
    parser.add_argument("--strict", action="store_true",
                        help="exit non-zero while any field has no reader")
    args = parser.parse_args(argv)

    rc = 0
    if args.check:
        rc = run_control(args.sabotage)
        if args.sabotage != "off":
            print("\n(sabotage is on: the census below is deliberately wrong)")
        print()

    for rel, (writer, command) in sorted(RECEIPTS.items()):
        print(f"receipt {rel}: regenerated by `python3 {writer} {command}`")
    problems = check_producers() + check_receipts()
    if problems:
        print("producer list problems:")
        for problem in problems:
            print(f"   {problem}")
        print()

    records = [ROOT / rel for rel in sorted(ALL_RECORDS) if (ROOT / rel).exists()]
    out, skipped = verdicts(records, list(code_sources()), sabotage=args.sabotage)
    print("\n".join(render(out)))
    if skipped:
        # A source the census could not parse is not evidence of absence: a
        # reader in it would be invisible, so it is named rather than dropped.
        print("\nsources that could not be parsed (their readers are invisible "
              "to this census): " + ", ".join(sorted(skipped)))

    unlisted = unlisted_records()
    if unlisted:
        print("\nJSON with rows that no listed producer writes (out of scope, "
              "printed so the choice can be audited):")
        for item in unlisted:
            print(f"   {item}")
    if args.strict:
        orphaned = [r for r in out if r.verdict == "NO READER"]
        # A warning nobody fails on is a sentence. `--strict` is the gate that
        # turns each NO READER line into an exit code, for whoever wants a check
        # that goes red until the column is read back by something.
        print(f"\n--strict: {len(orphaned)} field(s) with no reader")
        if orphaned:
            rc = rc or 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
