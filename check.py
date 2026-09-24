#!/usr/bin/env python3
"""Re-run every probe in catches.json and check the divergence it claims.

The ledger claims three things per entry: the promise, the fact, and that
they differ. This script re-checks all three:

  * `probe` evaluated against the reproduction in fragments.py  ==  `observed`
  * `observed` != `expected`
  * a raising probe is recorded as the exception's class name

Usage:
    python3 check.py                 # verify the whole ledger
    python3 check.py --class <name>
    python3 check.py --lookup "raises ValueError when low > high"

Exit code 0 means every executable entry held. A non-zero exit names the
entries that did not.

What the ledger deliberately does not do: it does not name who saw a lie
first, and it cannot tell you that your fragment is a re-post — only that
its class is not new.
"""

import argparse
import ast
import hashlib
import inspect
from collections import Counter
import json
import os
import re
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)

from fragments import NAMESPACES  # noqa: E402

LEDGER = HERE / "catches.json"
INDEX = HERE / "CLASSES.md"


def load() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def literal(text: str):
    """A ledger literal, evaluated with no builtins in reach.

    With `{}` the builtins are still injected, so `open(...)` inside a stored
    `expected` string ran on every green run -- a ledger literal could do file
    I/O. With no `__builtins__` the parser still reads dict, list, tuple, set
    and number literals, which is all a literal is.
    """
    return eval(text, {"__builtins__": {}})


FREE_PREFIX = "g:"

BUILTINS = {
    "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "isinstance",
    "len", "list", "max", "min", "next", "print", "range", "reversed", "round",
    "set", "sorted", "str", "sum", "tuple", "type", "zip",
}


class _DropDeadStores(ast.NodeTransformer):
    """Remove assignments to names the node never reads.

    `_pad = None` is not a second fragment; without this the fingerprint of a
    function could be changed by padding, so a copy could pass as distinct and
    a distinct pair could pass as a copy. Dead stores are the cheapest padding
    there is, so they go before names are normalised away.

    The pass only knows what a name in the tree reads. A store can also be read
    by a caller that carries no name: `eval("x + 1")`, `locals()`, `vars()`,
    `dir()`, `exec`. Dropping the store there removes a read the fragment makes,
    and two functions that answer differently then share one fingerprint. When a
    fragment calls one of those, nothing in it is dropped: the pass cannot see
    what reads what, so it keeps everything and the fingerprint stays honest
    about how little it erased.
    """

    DYNAMIC_READERS = {"eval", "exec", "locals", "vars", "dir", "globals"}

    def _reads(self, node) -> set:
        return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)
                and isinstance(n.ctx, ast.Load)}

    def _reads_by_a_caller(self, node) -> bool:
        return any(
            isinstance(n, ast.Name) and n.id in self.DYNAMIC_READERS
            and isinstance(n.ctx, ast.Load)
            for n in ast.walk(node)
        )

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)

    def visit_FunctionDef(self, node):
        if self._reads_by_a_caller(node):
            self.generic_visit(node)
            return node
        body, reads = [], set()
        for stmt in node.body:
            reads |= self._reads(stmt)
        for stmt in node.body:
            targets = []
            if isinstance(stmt, ast.Assign):
                targets = [t for t in stmt.targets if isinstance(t, ast.Name)]
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                targets = [stmt.target]
            if targets and all(t.id not in reads for t in targets):
                continue
            body.append(stmt)
        node.body = body or [ast.Pass()]
        self.generic_visit(node)
        return node


FUNC_SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)
COMP_SCOPES = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def scope_bindings(node) -> tuple:
    """The names each scope binds, kept apart per scope, plus the names declared
    external.

    Renaming during the walk made the erasure depend on traversal order: a
    comprehension target is visited after the expression that uses it, a nested
    def's name is visited in the middle of the body, and a walrus target appears
    inside the condition that reads it first. Three copies scored as different
    logic for renaming a target alone. Collecting the bound names in one pass
    first removed the order from the question.

    One flat set was the other half of the same mistake. Python binds a name in
    the scope that assigns it, so a store inside a nested def, a lambda or a
    comprehension binds nothing in the enclosing function. With one set, an
    outer `helper(xs)` stopped looking like a reference to something outside the
    fragment the moment an unrelated nested function happened to use `helper` as
    a local -- two copies of one piece of logic read as different. Bindings are
    now collected per scope and looked up along the enclosing chain. A `global`
    or `nonlocal` declaration is the opposite case: the function states that the
    name is not its own, so it is external and stays free wherever it is read.
    """
    scopes: dict = {}
    external: set = set()

    def handle(child, cur) -> None:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            new = {a.arg for a in (*child.args.posonlyargs, *child.args.args,
                                   *child.args.kwonlyargs)}
            if child.args.vararg:
                new.add(child.args.vararg.arg)
            if child.args.kwarg:
                new.add(child.args.kwarg.arg)
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cur.add(child.name)          # a def binds its name outside itself
                new.add(child.name)          # and may call itself
            scopes[id(child)] = new
            for extra in (getattr(child, "decorator_list", None) or []):
                walk(extra, cur)             # decorators run in the outer scope
            for d in (*child.args.defaults, *child.args.kw_defaults):
                if d is not None:
                    walk(d, cur)             # defaults too
            for a in (*child.args.posonlyargs, *child.args.args,
                      *child.args.kwonlyargs):
                if a.annotation is not None:
                    walk(a.annotation, cur)
            if getattr(child, "returns", None) is not None:
                walk(child.returns, cur)
            for stmt in (child.body if isinstance(child.body, list) else [child.body]):
                handle(stmt, new)
        elif isinstance(child, ast.ClassDef):
            cur.add(child.name)
            for extra in (*child.decorator_list, *child.bases, *child.keywords):
                walk(extra, cur)
            new = {child.name}
            scopes[id(child)] = new
            for stmt in child.body:
                handle(stmt, new)
        elif isinstance(child, COMP_SCOPES):
            new = {t.id for g in child.generators for t in ast.walk(g.target)
                   if isinstance(t, ast.Name)}
            scopes[id(child)] = new
            for sub in ast.iter_child_nodes(child):
                handle(sub, new)
        else:
            if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
                cur.add(child.id)
            elif isinstance(child, ast.alias) and child.asname:
                # an explicit `as` name is the author's choice; a bare
                # `import json` binds the module under its own name, which is a
                # reference to something outside the fragment and stays free
                cur.add(child.asname)
            elif isinstance(child, ast.ExceptHandler):
                # an `as` name lives only inside its handler: Python deletes it
                # when the handler ends, so it binds nothing in the enclosing
                # scope and a later read of that identifier is a global
                new = {child.name} if child.name else set()
                scopes[id(child)] = new
                if child.type is not None:
                    handle(child.type, cur)
                for stmt in child.body:
                    handle(stmt, new)
                return
            elif isinstance(child, (ast.Global, ast.Nonlocal)):
                external.update(child.names)
            walk(child, cur)

    def walk(n, cur) -> None:
        for child in ast.iter_child_nodes(n):
            handle(child, cur)

    handle(node, set())
    return scopes, external


class _Normalise(ast.NodeTransformer):
    """Rename bound identifiers by order of first appearance; keep free ones.

    A name the function binds -- an argument, a local, a target -- carries
    nothing but the author's choice of letter, so it is erased. A name the
    function never binds is a reference to something outside the fragment: a
    module, a helper, another fragment. Erasing those made `json.loads(x)` and
    `pickle.loads(x)` one fingerprint -- different subjects under one verb --
    and the fingerprint is what decides whether a repeat repeats a class or is a
    copy of it. A free name is kept under a `g:` prefix so it can never collide
    with an assigned `vN`, and the prefix is not a builtin, so the erasure of
    bound names is unchanged.

    Which names count as bound is read from the scope the name sits in, so a
    store inside a nested function no longer erases the same identifier in the
    enclosing one.
    """

    def __init__(self, scopes: dict, external: set):
        self.seen = {}
        self.scopes = scopes
        self.external = external
        self.stack: list = []

    def _rename(self, name: str) -> str:
        if name.startswith("__"):
            return name
        if name in BUILTINS and not self._bound(name):
            # A name the fragment binds is the author's choice of letter even
            # when it shadows a builtin: `def f(list, x)` and `def f(dict, x)`
            # differ in nothing else, and asking BUILTINS first read them as two
            # pieces of logic. An unbound `len` still refers to the builtin and
            # stays as it is written.
            return name
        if name not in self.seen:
            self.seen[name] = f"v{len(self.seen)}"
        return self.seen[name]

    def _bound(self, name: str) -> bool:
        if name.startswith(FREE_PREFIX):
            return False          # already marked free by an earlier pass
        if name in self.external:
            return False
        return any(name in scope for scope in self.stack)

    def _push(self, node):
        self.stack.append(self.scopes.get(id(node), set()))

    def _pop(self):
        self.stack.pop()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and not self._bound(node.id):
            if not node.id.startswith(FREE_PREFIX):
                # a name already carrying the prefix is the output of an earlier
                # pass over the same tree: marking it again would make the
                # erasure a function of how many times it ran
                node.id = FREE_PREFIX + node.id
            return node
        node.id = self._rename(node.id)
        return node

    def visit_arg(self, node):
        node.arg = self._rename(node.arg)
        return node

    def visit_FunctionDef(self, node):
        node.name = self._rename(node.name)
        self._push(node)
        self.generic_visit(node)
        self._pop()
        return node

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)

    def visit_Lambda(self, node):
        self._push(node)
        self.generic_visit(node)
        self._pop()
        return node

    def visit_ClassDef(self, node):
        node.name = self._rename(node.name)
        self._push(node)
        self.generic_visit(node)
        self._pop()
        return node

    def _comp(self, node):
        self._push(node)
        self.generic_visit(node)
        self._pop()
        return node

    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = _comp

    def visit_ExceptHandler(self, node):
        if node.name:
            node.name = self._rename(node.name)
        self._push(node)
        self.generic_visit(node)
        self._pop()
        return node

    def visit_alias(self, node):
        if node.asname:
            node.asname = self._rename(node.asname)
        return node


def fingerprint(fn) -> str:
    """The logic of a function with the names it binds thrown away.

    Bound names -- arguments, locals -- are the author's choice of letter and are
    erased. A name the function never binds refers to something outside the
    fragment, so it is kept: erasing it called `json.loads(x)` and
    `pickle.loads(x)` one shape, and the cost of keeping it is that a copy which
    renames the helper it delegates to reads as different logic instead.

    Two functions with the same fingerprint do the same thing; a repeat whose
    fragment fingerprints identically to the class fragment is the class probe
    again, not a second sighting.
    """
    tree = ast.parse(inspect.getsource(fn).lstrip())
    node = tree.body[0]
    # A named function is not the only fragment worth reading. A bare lambda is
    # a fragment too, and it used to be dumped as it stands: `lambda x: x + y`
    # and `lambda z: z + y` read as two pieces of logic because nothing erased
    # the argument. The policy below is the one every fragment gets; what changes
    # is only whether there is a docstring to drop, which there is when the node
    # has a body of statements.
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if (
            node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        ):
            node.body = node.body[1:]
    elif (
        isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.value, ast.Lambda)
    ):
        # A lambda read through inspect.getsource arrives as the assignment that
        # binds it: the target names the fragment, the lambda is the fragment.
        node = node.value
    elif not isinstance(node, (ast.Lambda, ast.ClassDef)):
        # A call, a bare expression, any other assignment: statements around it
        # are the author's scaffolding and ast.dump of the node as it stands is
        # the whole reading. An async def is one of the named functions.
        return ast.dump(node)
    _DropDeadStores().visit(node)
    scopes, external = scope_bindings(node)
    _Normalise(scopes, external).visit(node)
    return ast.dump(node)


def called_names(source: str) -> set:
    """The identifiers this expression actually calls.

    A substring test cannot tell a call from a mention: a probe that merely
    names a function in a string or a comment would be read as exercising it,
    and `primary` could be steered onto a different fragment of the class. The
    AST knows the difference; a probe that parses is asked, and one that does
    not parse returns the empty set and is refused for having no call at all.
    """
    try:
        tree = ast.parse(source.strip(), mode="eval")
    except SyntaxError:
        return set()
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                out.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                out.add(fn.attr)
    return out


def fingerprint_control() -> tuple[bool, str]:
    """Whether the fingerprint is still measuring what the ledger asks it to.

    A verdict of `duplicate` is a measurement only while the instrument that
    produced it separates a pair known to differ and joins a pair known to be
    one piece of logic. `fragments.CONTROL_PAIRS` names one such pair per rule of
    the policy -- free names kept, bound letters erased, a live store kept, a
    dead store removed -- so a broken rule fails the control on its own pair
    instead of hiding behind the other three. The first pair is the one that
    found the erasure hole. When the control fails, every duplicate verdict in
    the run is withdrawn as `not measured`: agreement between two things an
    instrument cannot tell apart is not agreement.
    """
    import fragments as F
    broken = []
    for left, right, same, rule in F.CONTROL_PAIRS:
        got = fingerprint(getattr(F, left)) == fingerprint(getattr(F, right))
        if got != same:
            broken.append(
                f"{left}/{right}: {'joined' if got else 'separated'} a pair it must "
                f"{'join' if same else 'separate'} ({rule})"
            )
    pair_rules = {rule for _l, _r, _s, rule in F.CONTROL_PAIRS}
    for rule, covered_by in F.RULES_WITHOUT_A_PAIR:
        if not covered_by.strip():
            broken.append(f"{rule}: declared without a pair and without a row covering it")
        if rule in pair_rules:
            broken.append(f"{rule}: declared both as a pair and as uncovered")
    if broken:
        return False, "; ".join(broken)
    return True, (f"{len(F.CONTROL_PAIRS)} pairs, one per rule of the policy, each "
                  "answers as its rule requires")


def primary(entry: dict) -> str | None:
    """The fragment the entry's own probe calls: the class's bytes."""
    ns = NAMESPACES.get(entry["class"], {})
    called = called_names(entry.get("probe", ""))
    for name in ns:
        if name in called:
            return name
    return None


def evaluate(entry: dict):
    """Run one probe. Returns (status, actual) with status ok|miss|skip."""
    if entry.get("lang") != "python" or entry.get("executable") is False:
        # Not replayed here, so its run cannot be judged -- but its divergence
        # can be, in the ledger's own text and without a Python parser: two
        # skipped entries recording the same text on both sides are not a
        # divergence whatever the language.
        if str(entry["expected"]).strip() == str(entry["observed"]).strip():
            return "miss", "skipped entry whose expected == observed"
        return "skip", None
    ns = dict(NAMESPACES.get(entry["class"], {}))
    if primary(entry) is None:
        return "miss", (
            "the probe calls no fragment of this class: a class must be carried by "
            "the bytes of the fragment its own probe exercises"
        )
    raised = None
    try:
        actual = eval(entry["probe"], ns)
    except (NameError, SyntaxError, IndentationError) as exc:
        return "miss", (
            f"the probe did not run: {type(exc).__name__} ({exc}). A name that is not "
            "there is a broken probe, not an observation"
        )
    except Exception as exc:
        # A raising probe is an observation only when the entry declares it as
        # one; otherwise a fragment that cannot run would be replayed green.
        if not entry.get("raises"):
            return "miss", (
                f"the probe raised {type(exc).__name__} and the entry does not declare "
                'a raise ("raises": true), so this is a broken probe, not a divergence'
            )
        raised = type(exc).__name__
        actual = raised
    try:
        if raised is not None:
            # a raising probe is compared by exception class name
            if entry["observed"] != raised:
                return "miss", f"probe raised {raised}, ledger says {entry['observed']!r}"
            if entry["expected"] == raised:
                return "miss", "ledger's expected == observed; that is not a divergence"
            return "ok", raised
        observed = literal(entry["observed"])
        expected = literal(entry["expected"])
    except Exception as exc:
        return "miss", f"bad ledger literal: {exc}"
    if actual != observed:
        return "miss", f"probe gave {actual!r}, ledger says {observed!r}"
    if observed == expected:
        return "miss", "ledger's expected == observed; that is not a divergence"
    # a repeat entered as an object carries its own promise, fact and probe;
    # it is replayed here exactly like the class probe.
    for rep in entry.get("repeats") or []:
        if isinstance(rep, str):
            continue  # legacy label: records that a claim arrived, not the claim
        if not isinstance(rep, dict) or not rep.get("probe"):
            return "miss", f"repeat {rep!r} is neither a label nor a probe object"
        missing = [k for k in ("id", "promise", "fact", "probe", "expected",
                               "observed", "fn") if k not in rep]
        if missing:
            return "miss", f"repeat {rep.get('id', rep)!r} lacks {', '.join(missing)}"
        fn_name = rep["fn"]
        if fn_name not in ns:
            return "miss", f"repeat {rep['id']!r} names {fn_name!r}, not in the class"
        if fn_name not in called_names(rep["probe"]):
            return "miss", (
                f"repeat {rep['id']!r} names {fn_name!r} but its probe never calls it "
                "(a mention is not a call)"
            )
        base = primary(entry)
        if base and fn_name == base:
            return "miss", (
                f"repeat {rep['id']!r} replays {base}, the class fragment itself: "
                "that is the class probe, not a second sighting"
            )
        if base and fingerprint(ns[base]) == fingerprint(ns[fn_name]):
            return "miss", (
                f"repeat {rep['id']!r}: {fn_name} fingerprints like {base}; "
                "that is the class probe again, not a second sighting"
            )
        try:
            got = eval(rep["probe"], dict(ns))
        except Exception as exc:  # a raising repeat probe is the observation
            got = type(exc).__name__
            if rep["observed"] != got:
                return "miss", (
                    f"repeat {rep['id']!r} raised {got}, ledger says {rep['observed']!r}"
                )
            if rep["expected"] == got:
                return "miss", f"repeat {rep['id']!r}: expected == observed, not a divergence"
            continue
        try:
            want = literal(rep["observed"])
            promised = literal(rep["expected"])
        except Exception as exc:
            return "miss", f"bad ledger literal in repeat {rep['id']!r}: {exc}"
        if got != want:
            return "miss", f"repeat {rep['id']!r} gave {got!r}, ledger says {want!r}"
        if want == promised:
            return "miss", f"repeat {rep['id']!r}: expected == observed, not a divergence"
    for gone in entry.get("retired") or []:
        if not isinstance(gone, dict) or not gone.get("id") or not gone.get("why"):
            return "miss", f"retired entry {gone!r} needs an id and a why"
        if gone.get("kind", "class-fragment") not in ("class-fragment", "not-a-fragment"):
            return "miss", (
                f"retired entry {gone.get('id')!r} declares an unknown kind "
                f"{gone['kind']!r}; the sub-counts name only class-fragment and "
                "not-a-fragment, so an unnamed kind would vanish from them"
            )
    return "ok", actual


def lookup(query: str) -> int:
    words = query.lower().split()
    hits = 0
    for entry in load()["entries"]:
        haystack = " ".join(
            str(entry.get(k, ""))
            for k in ("class", "promise", "fact", "probe", "aliases")
        ).lower()
        if all(word in haystack for word in words):
            hits += 1
            repeats = entry.get("repeats") or []
            print(
                f"{entry['class']}  (first seen {entry['first_seen']}; "
                f"{len(repeats)} repeat(s): {repeats or '-'})\n"
                f"  promise : {entry['promise']}\n"
                f"  fact    : {entry['fact']}\n"
                f"  probe   : {entry['probe']}  ->  {entry['observed']}"
            )
    if not hits:
        print("no entry matches — this class may be new")
    return 0


def duplicate_declarations() -> list[str]:
    """A class or fragment name declared twice in NAMESPACES, the later one live.

    A dict literal accepts a repeated key and keeps the last, so a class whose
    name appears twice inside `NAMESPACES` is edited in the copy a reader sees
    first and answered by the copy nobody looked at: the dead one carries names
    the live one has never heard of. The source is read as text because the
    collision is invisible once the module is importable.
    """
    src = Path("fragments.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    out = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "NAMESPACES" for t in node.targets):
            continue
        outer = node.value
        keys = [k.value for k in outer.keys if isinstance(k, ast.Constant)]
        for k in set(keys):
            if keys.count(k) > 1:
                out.append(f"NAMESPACES declares {k!r} {keys.count(k)} times; the later mapping is live")
        for value in outer.values:
            if not isinstance(value, ast.Dict):
                continue
            inner = [k.value for k in value.keys if isinstance(k, ast.Constant)]
            for k in set(inner):
                if inner.count(k) > 1:
                    out.append(f"a class declares the fragment {k!r} {inner.count(k)} times")
    return out


def class_collisions(data: dict) -> tuple[int, list[str], list[str]]:
    """Two class names for one shape of lie, and fragments whose logic is shared.

    This used to walk the entries in file order, adding each class's own fragment
    to a map that a repeat's fragment was then looked up in. A repeat colliding
    with a class that came later in the file was invisible, so reordering two
    entries in `catches.json` turned a green run red -- an answer that depends on
    where in the file a claim sits is not an answer. Two passes now: every class
    fragment is collected first, then compared.

    A duplicate among class fragments is a failure: one shape wearing two names.
    A repeat fragment whose logic equals another class's fragment is not a
    failure -- a repeat claims an instance, not a shape -- but it is printed,
    because it means that repeat's claim is carried by its prose and its probe
    and not by any bytes of its own.
    """
    primaries = []
    for entry in data["entries"]:
        base = primary(entry)
        if base:
            primaries.append((entry["class"], base, NAMESPACES[entry["class"]][base]))
    seen: dict[str, str] = {}
    problems: list[str] = []
    for cls, name, fn in primaries:
        fp = fingerprint(fn)
        if fp in seen:
            problems.append(f"{cls}.{name} has the logic of {seen[fp]}")
        else:
            seen[fp] = f"{cls}.{name}"
    shared: list[str] = []
    for entry in data["entries"]:
        ns = NAMESPACES.get(entry["class"], {})
        for rep in entry.get("repeats") or []:
            if not isinstance(rep, dict) or rep.get("fn") not in ns:
                continue
            owner = seen.get(fingerprint(ns[rep["fn"]]))
            if owner and not owner.startswith(entry["class"] + "."):
                shared.append(f"repeat {rep['id']} carries no bytes of its own: the "
                              f"logic of {owner}")
    return len(primaries), problems, shared


def fragment_lines(namespace: str, fn: str) -> set:
    """The lines of one reproduction, stripped: what a citation may quote.

    A public citation is a line of the fragment. The older test flattened the
    whole source and searched the flat text, so a fragment of a longer line
    (`0 < n < 65535` out of `if not (0 < n < 65535):`) and a span of two lines
    both passed as "a line", while neither is a line a reader can find. A
    docstring line is a line of the file and is accepted; a slide of one line is
    not. The quote must also be one line, not two.
    """
    ns = NAMESPACES.get(namespace, {})
    if fn not in ns:
        return set()
    src = textwrap.dedent(inspect.getsource(ns[fn]))
    lines = {ln.strip() for ln in src.splitlines() if ln.strip()}
    # A docstring line reaches the file with its opening or closing quotes on it;
    # a reader who copies the sentence out of the file is quoting the same line.
    return lines | {ln.strip().strip('"').strip("'").strip() for ln in lines}


ADDRESS_UUID = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def address_resolves(addr: str) -> bool:
    """Whether a stored address names something a reader can go and fetch.

    The count says "instances with a public citation". An address that is a
    board message id or carries a `#<seq>` can be checked by a reader; anything
    else is a private note in the export shape of an address, and counting it
    puts a number in front of the word "citation" that no reader can act on.
    """
    a = str(addr).strip()
    return bool(ADDRESS_UUID.match(a)) or bool(re.search(r"#\d+", a))


def addresses(data) -> int:
    """Print every instance that carries a public citation and the line from it.

    An address without a line is a direction, not evidence: the reader has to
    trust that the fragment is in the message. With the line, they can fetch the
    message and look for it themselves. The role says whether the cited message
    prints the fragment as its own work or only quotes it from an earlier one.
    """
    rows = []
    for entry in data["entries"]:
        if entry.get("address") and not address_resolves(entry["address"]):
            print(f"    UNRESOLVABLE  {entry['class']}: {entry['address']!r} names no message")
        if entry.get("address"):
            rows.append((entry["class"], "class", entry["address"],
                         entry.get("address_quote", ""), entry.get("address_role", "undeclared")))
        for rep in entry.get("repeats") or []:
            if isinstance(rep, dict) and rep.get("address"):
                rows.append((entry["class"], rep["id"], rep["address"],
                             rep.get("address_quote", ""), rep.get("address_role", "undeclared")))
        for cit in entry.get("citations") or []:
            rows.append((entry["class"], "cited by " + str(cit.get("by", "?")), cit["address"],
                         cit.get("address_quote", ""), cit.get("address_role", "undeclared")))
    for name, what, addr, quote, role in rows:
        print(f"{name}  ({what})  {addr}  role={role}")
        print(f"    {quote or 'NO QUOTE — this address is a direction, not evidence'}")
    print(f"\n{len(rows)} citation(s) across {len(data['entries'])} classes")
    return 0


def render_index(data: dict) -> str:
    """The whole ledger as one page a stranger can read without cloning.

    It answers the question the board keeps asking in prose: has this shape
    already been claimed, and by whom. Built from the ledger, so a stale copy
    cannot describe a ledger that has moved on.
    """
    lines = [
        "# Classes",
        "",
        "Every class in `catches.json`, generated by `check.py --index`.",
        "A class is a shape of lie, not a fragment: two fragments with the same",
        "class are the same finding. Counts are instances (a class plus its",
        "repeats), not claims of independence.",
        "",
        f"Classes {len(data['entries'])}",
        "",
    ]
    for entry in sorted(data["entries"], key=lambda e: e["class"]):
        reps = entry.get("repeats") or []
        cites = entry.get("citations") or []
        lines += [
            f"## `{entry['class']}`",
            "",
            f"- promise: {entry['promise']}",
            f"- fact: {entry['fact']}",
            f"- probe: `{entry['probe']}` -> expected `{entry['expected']}`, observed `{entry['observed']}`",
            f"- instances: {1 + len(reps)}"
            + (f" (repeats: {', '.join(r['id'] for r in reps if isinstance(r, dict))})" if reps else ""),
        ]
        if reps:
            lines.append(f"- repeat fragments: {', '.join(sorted({r.get('fn', '?') for r in reps if isinstance(r, dict)}))}")
        if entry.get("address"):
            lines.append(
                f"- cited: `{entry['address']}` ({entry.get('address_role', 'undeclared')}) "
                f"— `{entry.get('address_quote', '')}`"
            )
        for cit in cites:
            lines.append(
                f"- seen again by {cit.get('by', '?')}: `{cit['address']}` "
                f"({cit.get('address_role', 'undeclared')}) — `{cit.get('address_quote', '')}`"
            )
        if entry.get("note"):
            lines.append(f"- note: {entry['note']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def quick_audit(data: dict) -> int:
    """The ledger's failure code, for the modes that print something else.

    `--index`, `--addresses` and `--lookup` printed their page and exited 0
    whatever the ledger said, so a stranger piping `--index > CLASSES.md` from a
    broken ledger got a green exit and a page that read as a description of a
    healthy ledger. The gate belongs to the ledger, not to the mode.
    """
    bad = 0
    for entry in data["entries"]:
        if evaluate(entry)[0] == "miss":
            print(f"MISS  {entry['class']:<50} (see `python3 check.py`)")
            bad = 1
    _, problems, _ = class_collisions(data)
    for line in problems:
        print(f"DUPE  {'':<50} {line}")
        bad = 1
    for entry in data["entries"]:
        for rep in entry.get("repeats") or []:
            if isinstance(rep, dict) and rep.get("address") and not rep.get("address_quote"):
                print(f"BADADDRESS  {entry['class']}/{rep['id']}: an address with no line")
                bad = 1
        for cit in entry.get("citations") or []:
            if cit.get("address_quote", "").strip() not in fragment_lines(entry["class"], primary(entry) or ""):
                print(f"BADADDRESS  {entry['class']} (cited by {cit.get('by', '?')})")
                bad = 1
        if entry.get("address") and entry.get("address_quote", "").strip() not in fragment_lines(
                entry["class"], primary(entry) or ""):
            print(f"BADADDRESS  {entry['class']}")
            bad = 1
    return bad


def policy_hash() -> str:
    """A short hash of the equivalence policy itself.

    A count is a claim about a rule, and two counts under two rules are not the
    same count. The rule here is not only the ledger's data but the erasure the
    counts are computed with: a change to it can honestly move every number in
    this file, and a reader of a quoted count has no way to tell an edited
    policy from an unchanged result. The hash names the policy's source -- the
    dead-store pass, the scope pass and the renamer -- so a count can be quoted
    together with what it was counted under instead of against whatever the
    reader happens to have checked out.
    """
    source = "\n\n".join(
        inspect.getsource(obj).strip()
        for obj in (_DropDeadStores, scope_bindings, _Normalise, fingerprint)
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--class", dest="only")
    ap.add_argument("--lookup")
    ap.add_argument("--addresses", action="store_true")
    ap.add_argument("--index", action="store_true", help="print CLASSES.md and exit")
    ap.add_argument("--policy", action="store_true",
                    help="print the hash of the equivalence policy and exit")
    args = ap.parse_args()

    if args.policy:
        print(policy_hash())
        return 0

    data = load()
    if args.lookup:
        lookup(args.lookup)
        return quick_audit(data)
    if args.index:
        bad = quick_audit(data)
        print(render_index(data), end="")
        return bad
    if args.addresses:
        bad = quick_audit(data)
        addresses(data)
        return bad
    entries = data["entries"]
    unknown = False
    if args.only:
        entries = [e for e in entries if e["class"] == args.only]
        if not entries:
            print(f"unknown class {args.only!r} — 0 checks performed")
            unknown = True

    ok = miss = skip = 0
    for entry in entries:
        status, detail = evaluate(entry)
        if status == "ok":
            ok += 1
            print(f"ok    {entry['class']:<50} {entry['probe']} -> {detail!r}")
        elif status == "skip":
            skip += 1
            print(f"skip  {entry['class']:<50} (lang={entry['lang']}; run it by hand)")
        else:
            miss += 1
            print(f"MISS  {entry['class']:<50} {detail}")

    recurring = [e["class"] for e in data["entries"] if e.get("repeats")]
    all_repeats = [r for e in data["entries"] for r in (e.get("repeats") or [])]
    materialised = sum(1 for r in all_repeats if isinstance(r, dict))
    retired = [g for e in data["entries"] for g in (e.get("retired") or [])]
    retired_kinds = Counter(g.get("kind", "class-fragment") for g in retired)
    instances = len(data["entries"]) + len(all_repeats)
    holds_fail = 0
    try:
        from holds import HOLDS
    except ImportError:
        HOLDS = {}
    by_class = {e["class"]: e for e in entries}
    for name, spec in HOLDS.items():
        if name not in by_class:
            continue
        entry = by_class[name]
        fn = spec["fn"]
        prefix = spec["prefix"]
        try:
            expected_val = literal(entry["expected"])
            observed_val = literal(entry["observed"])
        except Exception as exc:
            holds_fail += 1
            print(f"HOLD  {name:<50} bad ledger literal: {exc}")
            continue
        exp = fn(*prefix, expected_val)
        obs = fn(*prefix, observed_val)
        if exp is True and obs is False:
            print(f"hold  {name:<50} expected holds, observed does not")
        else:
            holds_fail += 1
            print(
                f"HOLD  {name:<50} expected={exp!r} observed={obs!r} "
                "(want True / False)"
            )

    # Every cited row, built once and used twice: the audit refuses rows the
    # counters must not then count. The counters used to be printed before the
    # audit ran, so a run could say `43 of 145 quote a line` while refusing one
    # of the 43 three lines further down.
    rows = []
    for entry in data["entries"]:
        cls = entry["class"]
        if entry.get("address"):
            rows.append((cls, "class", entry.get("address_quote", ""), cls,
                         primary(entry), entry.get("address_role", "undeclared")))
        for rep in entry.get("repeats") or []:
            if isinstance(rep, dict) and rep.get("address"):
                rows.append((f"{cls}/{rep['id']}", "repeat", rep.get("address_quote", ""),
                             cls, rep.get("fn"), rep.get("address_role", "undeclared")))
        for cit in entry.get("citations") or []:
            rows.append((f"{cls} (cited by {cit.get('by', '?')})", "citation",
                         cit.get("address_quote", ""), cls, primary(entry),
                         cit.get("address_role", "undeclared")))

    bad = []
    for name, kind, quote, cls, fn, role in rows:
        if not quote:
            bad.append((name, "has an address but no line from it"))
        elif "\n" in quote.strip():
            bad.append((name, "quotes more than one line; a citation is a line"))
        elif quote.strip() not in fragment_lines(cls, fn or ""):
            bad.append((name, f"quotes a line this fragment does not contain: {quote[:60]!r}"))
    refused = {name for name, _ in bad}

    collisions = []
    for line in duplicate_declarations():
        collisions.append(line)
    collision_count, collisions_2, shared = class_collisions(data)
    collisions += collisions_2
    control_ok, control_why = fingerprint_control()
    if not control_ok:
        collisions.append(f"fingerprint control failed: {control_why}")
    for line in collisions:
        print(f"DUPE  {'':<50} {line}")

    print()
    scope = f" (this class only, of {len(data['entries'])})" if args.only else ""
    print(f"entries {len(entries)}{scope}  ok {ok}  miss {miss}  skipped {skip}")
    print(
        f"distinct class fragments {collision_count - len(collisions)}"
        f"/{collision_count}  (class fragments only: no class is another class"
        " under a new name)"
    )
    if control_ok:
        print(f"fingerprint control ok  {control_why}")
        import fragments as _F
        for rule, covered_by in _F.RULES_WITHOUT_A_PAIR:
            print(f"fingerprint gap        {rule}  ->  {covered_by}")
    else:
        print(f"fingerprint control FAILED  {control_why}")
        print("NOT MEASURED  the fingerprint cannot tell a known-different pair"
              " apart, so every duplicate verdict above is withdrawn")
    print(f"equivalence policy {policy_hash()}  (python3 check.py --policy)")
    print(
        f"reported instances {instances} "
        f"(repeats {len(all_repeats)}: {materialised} replayed by this script, "
        f"{len(all_repeats) - materialised} label-only)"
    )
    print(
        f"retired repeats    {len(retired)} "
        f"(recovered: {retired_kinds['class-fragment']} were the class fragment, "
        f"{retired_kinds['not-a-fragment']} named no fragment)"
    )
    for line in collisions:
        print(f"DUPE  {'':<50} {line}")
    for line in shared:
        print(f"SHARED{'':<49} {line}")
    addressed = sum(1 for r in rows if r[1] in ("class", "repeat"))
    quoted = sum(1 for r in rows
                 if r[1] in ("class", "repeat") and r[2].strip() and r[0] not in refused)
    print(
        f"instances with a public citation {addressed}/{instances} "
        f"({quoted} of them quote a line of the fragment)"
        "  (cited, not shown to be independent)"
    )
    roles = Counter(r[5] for r in rows if r[0] not in refused)
    if sum(roles.values()):
        print(
            "citation roles     "
            + ", ".join(f"{n} {k}" for k, n in sorted(roles.items()))
            + "  (declared by the ledger's author, not machine-checked: a message that"
              " quotes another message prints the same lines)"
        )
    cited_again = [(e["class"], c) for e in data["entries"] for c in (e.get("citations") or [])]
    if cited_again:
        print(
            f"class fragments cited again {len(cited_again)} time(s) from "
            f"{len({c['address'] for _, c in cited_again})} message(s): "
            + ", ".join(f"{e} by {c.get('by', '?')}" for e, c in cited_again)
            + "  (a message that quotes the class fragment is a sighting of it, not a repeat"
              " of it: the repeat gate refuses a repeat that replays the class fragment)"
        )
    for name, why in bad:
        print(f"BADADDRESS  {name:<50} {why}")
    dropped = [e["class"] for e in data["entries"] if e.get("address_dropped")]
    dropped += [f"{e['class']}/{r['id']}" for e in data["entries"]
                for r in (e.get("repeats") or [])
                if isinstance(r, dict) and r.get("address_dropped")]
    if dropped:
        print(f"address(es) dropped for lack of a line: {len(dropped)} "
              + ", ".join(dropped))
    declined = data.get("declined") or []
    for dec in declined:
        if not (dec.get("address") and dec.get("reason") and dec.get("gate")):
            print(f"DECLINED  {'':<50} an entry needs address, gate and reason")
            bad.append(("declined", "missing field"))
    if declined:
        print(f"declined           {len(declined)}: "
              + ", ".join(sorted(f"{d_['gate']} {d_['address'][:8]} ({d_.get('class', '?')})"
                                   for d_ in declined)))
    # sorted: which classes recur is the answer, the order they happen to sit in
    # the JSON array is not. The answer used to move when the entries were
    # reordered, which is the same dependence a stranger found in the citation
    # counter, one line further down.
    print(f"recurring classes  {len(recurring)}: {', '.join(sorted(recurring))}")
    print(f"holds callbacks    {len(HOLDS)} fail {holds_fail}")
    if unknown:
        return 2
    stale = False
    written = render_index(data)
    if INDEX.exists():
        stale = INDEX.read_text() != written
    else:
        stale = True
    print()
    if stale:
        print(
            f"STALE  {INDEX.name} does not match the ledger: run "
            "`python3 check.py --index > CLASSES.md`"
        )
    else:
        print(f"index    {INDEX.name} is current")
    return 1 if miss or holds_fail or collisions or bad or stale else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:
        # `python3 check.py | head` is a normal way to read this tool; a reader
        # closing the pipe is not a ledger failure. Redirect stdout to devnull
        # so the interpreter's final flush does not raise again.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
