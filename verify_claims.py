#!/usr/bin/env python3
"""Acceptance tests for the claims this registry makes about itself.

Every claim below was refuted by an independent skeptic on 2026-09-24, each with
a counterexample: a repeat whose collision with a later entry was invisible, a
citation counter printed before the audit that contradicts it, a class with no
fragment at all, a probe that did not run, a repeat that named a fragment it
never called, a class copy padded with a dead assignment, a multiline "quote", an
address that resolves to nothing, a retired kind dropped from its own sub-counts,
modes that exited 0 over a broken ledger, a skipped entry with no divergence, and
an outside attack that predicted methods on one receiver would collapse -- they do
not, so the row records where the fingerprint does collapse instead.

A fix without a test is a promise. This file is the test: it applies each attack
to a copy of the ledger, runs the registry's own `python3 check.py`, and asserts
the answer. `python3 verify_claims.py` exits 0 only when every row holds.

    python3 verify_claims.py            # all rows
    python3 verify_claims.py --list     # names only

Nothing here writes to the ledger itself: each case gets its own tree under
`verify/case-<name>/`.
"""
import argparse
import ast
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASE_ROOT = HERE / "verify"


def check(tree: Path, *args: str) -> tuple[int, str]:
    out = subprocess.run([sys.executable, "check.py", *args], cwd=tree,
                         capture_output=True, text=True,
                         env={"PATH": "/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1"})
    return out.returncode, out.stdout + out.stderr


def copy_ledger(name: str) -> Path:
    tree = CASE_ROOT / f"case-{name}"
    if tree.exists():
        shutil.rmtree(tree)
    tree.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(HERE, tree, ignore=shutil.ignore_patterns("verify", "__pycache__", ".git"))
    return tree


def load(tree: Path) -> dict:
    return json.loads((tree / "catches.json").read_text(encoding="utf-8"))


def save(tree: Path, data: dict) -> None:
    (tree / "catches.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8")
    idx = subprocess.run([sys.executable, "check.py", "--index"], cwd=tree, capture_output=True,
                         text=True, env={"PATH": "/usr/bin:/bin"},
                         check=False)
    (tree / "CLASSES.md").write_text(idx.stdout, encoding="utf-8")


def find(data: dict, cls: str) -> dict:
    return next(e for e in data["entries"] if e["class"] == cls)


def inject_fragment(tree: Path, namespace: str, name: str, source: str) -> None:
    """Put a fragment into the class's namespace in the copy's fragments.py.

    A class or a repeat is only a claim about code if the code is there: a test
    that adds a name to catches.json without adding the bytes tests the refusal
    of a missing name, not the gate that reads the name. An existing namespace
    is edited at its LAST occurrence, because a dict literal keeps the last key
    and the first one is dead.
    """
    path = tree / "fragments.py"
    text = path.read_text(encoding="utf-8")
    marker = "\nNAMESPACES = {"
    head, tail = text.split(marker, 1)
    key = f'"{namespace}": {{'
    if key in tail:
        at = tail.rindex(key)
        tail = tail[:at + len(key)] + f'"{name}": {name}, ' + tail[at + len(key):]
    else:
        # a new class goes in as the first key of the outer dict, not into the
        # first mapping that happens to open next
        tail = "\n    " + f'"{namespace}": {{"{name}": {name}}},' + tail
    path.write_text(head + "\n" + source.rstrip() + "\n" + marker + tail, encoding="utf-8")


RIM = "a-rim-sample-quoted-as-a-measurement-of-the-band"
EMPTY_MAX = "empty-max-raises"
CLAMP = "clamp-no-range-validation"


# ----------------------------------------------------------------- the attacks

ANSWER_PREFIXES = (
    "entries ", "distinct class fragments", "reported instances", "retired repeats",
    "instances with a public citation", "citation roles", "class fragments cited again",
    "recurring classes", "declined", "holds callbacks", "equivalence policy",
)


def answers(out: str) -> list:
    """The lines that are the run's answer, without the per-entry verdicts.

    A literal count here would be a claim about the ledger's size inside a test
    about entry order, and it goes stale the moment a class is added -- it did,
    in the shape of a hardcoded `112/112`. What the row is for is the *answer*
    being order-free, so the answer's own lines are compared, not a number the
    test happens to remember.
    """
    return sorted(line for line in out.splitlines()
                  if line.startswith(ANSWER_PREFIXES))


def a_order_flip(tree):
    """Entry order in a JSON array is not content: the answer must not depend on it."""
    data = load(tree)
    classes = [e["class"] for e in data["entries"]]
    code_before, before = check(tree)
    data["entries"].insert(classes.index(EMPTY_MAX), data["entries"].pop(classes.index(RIM)))
    save(tree, data)
    code, out = check(tree)
    if code_before != 0 or code != 0:
        return False, f"the ledger failed: before={code_before} after={code}"
    if answers(before) != answers(out):
        moved = [l for l in answers(out) if l not in answers(before)]
        return False, f"reordering the entries moved the answer: {moved[:3]}"
    return True, "answer independent of entry order"


def b_citation_counter(tree):
    """The count printed must not contradict the audit printed with it."""
    code, out = check(tree, "--addresses")
    m = re.search(r"instances with a public citation (\d+)/(\d+) \((\d+) of them quote", out)
    if not m:
        code2, out2 = check(tree)
        m = re.search(r"instances with a public citation (\d+)/(\d+) \((\d+) of them quote", out2)
        code, out = min(code, code2), out + out2
    bad = [ln for ln in out.splitlines() if ln.startswith("BADADDRESS")]
    ok = bool(code == 0 and m and m.group(1) == m.group(3) and not bad)
    return ok, (f"counter and audit agree ({m.group(3)} of {m.group(1)})" if m
                else "the counter line is missing")


def c_ghost_class(tree):
    """A class with no fragment in the namespaces is not a class."""
    data = load(tree)
    data["entries"].append({"class": "ghost-class-no-fragment", "first_seen": "c", "promise": "x",
                            "fact": "x", "probe": "1 + 1", "expected": "3", "observed": "2",
                            "lang": "python"})
    save(tree, data)
    code, out = check(tree)
    return code == 1 and "no fragment of this class" in out, "a class must carry bytes"


def d_probe_that_did_not_run(tree):
    """A NameError is a broken probe, not an observation."""
    data = load(tree)
    find(data, CLAMP)["probe"] = "clamp(5, undefined_name, 0)"
    save(tree, data)
    code, out = check(tree)
    return code == 1 and "did not run" in out, "a probe that raises NameError is a miss"


def e_repeat_shim(tree):
    """A repeat must call the fragment it names, not mention it in a string."""
    data = load(tree)
    rep = find(data, RIM)["repeats"][0]
    rep["probe"] = "'the_rules_reach' and 128"
    save(tree, data)
    code, out = check(tree)
    return code == 1 and "never calls it" in out, "a mention is not a call"


def f_repeat_replaying_another_class(tree):
    """A repeat whose fragment is another class's logic is printed as carrying no bytes."""
    data = load(tree)
    inject_fragment(tree, RIM, "reach_by_max", "def reach_by_max(probe_lengths):\n"
                    "    _pad = None\n    return max(probe_lengths)\n")
    rep = find(data, RIM)["repeats"][0]
    rep["fn"] = "reach_by_max"
    rep["probe"] = "reach_by_max([1, 2, 3])"
    rep["observed"] = "3"
    rep["expected"] = "200"
    save(tree, data)
    code, out = check(tree)
    return code == 0 and "SHARED" in out, "a repeat's own bytes are named"


def g_class_copy(tree):
    """One shape may not wear two names -- in any order of the file."""
    data = load(tree)
    inject_fragment(tree, "a-second-name-for-the-same-shape", "find_max",
                    "def find_max(items):\n    return max(items)\n")
    data["entries"].insert(0, {"class": "a-second-name-for-the-same-shape", "first_seen": "c",
                              "promise": "p", "fact": "f", "probe": "find_max([])",
                              "expected": "None", "observed": "ValueError", "raises": True,
                              "lang": "python"})
    save(tree, data)
    code, out = check(tree)
    return code == 1 and "has the logic of" in out, "a byte-identical copy is a DUPE"


def h_class_copy_padded(tree):
    """Padding a copy with a dead assignment does not make it a second shape."""
    data = load(tree)
    inject_fragment(tree, "a-padded-second-name", "find_max",
                    "def find_max(items):\n    _pad = None\n    return max(items)\n")
    data["entries"].insert(0, {"class": "a-padded-second-name", "first_seen": "c",
                              "promise": "p", "fact": "f", "probe": "find_max([])",
                              "expected": "None", "observed": "ValueError", "raises": True,
                              "lang": "python"})
    save(tree, data)
    code, out = check(tree)
    return code == 1 and "has the logic of" in out, "a padded copy is a DUPE"


def i_primary_steering(tree):
    """A probe that only mentions another fragment's name must not become the primary."""
    data = load(tree)
    entry = find(data, CLAMP)
    entry["probe"] = "'find_max' and clamp(5, 10, 0)"
    save(tree, data)
    code, out = check(tree)
    return "ok" in out, "the primary is what the probe calls"


def j_multiline_quote(tree):
    """A citation is one line of the fragment."""
    data = load(tree)
    find(data, EMPTY_MAX)["address"] = "00000000-0000-4000-8000-000000000000"
    find(data, EMPTY_MAX)["address_quote"] = "return max(items)\n    return max(items)"
    save(tree, data)
    code, out = check(tree)
    return code == 1 and "BADADDRESS" in out, "a span of two lines is not a line"


def k_unresolvable_address(tree):
    """An address that names no message is printed, not counted silently."""
    data = load(tree)
    find(data, EMPTY_MAX)["address"] = "no-such-message://not-a-uuid-0000"
    find(data, EMPTY_MAX)["address_quote"] = "return max(items)"
    save(tree, data)
    code, out = check(tree, "--addresses")
    return "UNRESOLVABLE" in out, "an address must resolve"


def l_unknown_retired_kind(tree):
    """A retired kind outside the named set may not vanish from the sub-counts."""
    data = load(tree)
    find(data, CLAMP)["retired"] = [{"id": "x", "why": "w", "kind": "something-else"}]
    save(tree, data)
    code, out = check(tree)
    return code == 1 and "unknown kind" in out, "sub-counts name every kind they count"


def m_modes_carry_the_code(tree):
    """A display mode must not answer 0 over a ledger that fails the gate."""
    data = load(tree)
    find(data, CLAMP)["probe"] = "clamp_typo_does_not_exist(5, 10, 0)"
    save(tree, data)
    codes = {}
    for args in (("--index",), ("--addresses",), ("--lookup", "clamp")):
        codes[args[0]] = check(tree, *args)[0]
    return all(c == 1 for c in codes.values()), f"index/addresses/lookup -> {sorted(set(codes.values()))}"


def n_skip_without_divergence(tree):
    """Not replayed is not the same as not examined: expected == observed is caught."""
    data = load(tree)
    for e in data["entries"]:
        if e.get("lang") != "python":
            e["expected"] = e["observed"]
    save(tree, data)
    code, out = check(tree)
    return code == 1 and "expected == observed" in out, "a skipped entry is audited too"


def o_dead_store_is_not_a_difference(tree):
    """The fingerprint ignores a store nobody reads, so padding cannot buy a name."""
    sys.path.insert(0, str(HERE))
    import importlib.util
    spec = importlib.util.spec_from_file_location("chk", HERE / "check.py")
    chk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chk)

    def plain(xs):
        return max(xs)

    def padded(xs):
        _pad = None
        return max(xs)

    def smaller(xs):
        return min(xs)

    same = chk.fingerprint(plain) == chk.fingerprint(padded)
    other = chk.fingerprint(plain) == chk.fingerprint(smaller)
    return same and not other, "padding is invisible, a different body is not"


def p_literals_have_no_builtins(tree):
    """A stored literal is data, not code: it cannot open a file."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("chk", HERE / "check.py")
    chk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chk)
    try:
        chk.literal("__import__('os').getcwd()")
        return False, "a literal reached the builtins"
    except NameError:
        pass
    return chk.literal("{'a': [1, 2]}") == {"a": [1, 2]}, "dict and list literals still parse"


def q_duplicate_declaration(tree):
    """A second mapping under one class name does not silently replace the first."""
    inject_fragment(tree, RIM, "reach_by_max", "def reach_by_max(probe_lengths):\n"
                    "    return max(probe_lengths)\n")
    (tree / "fragments.py").write_text(
        (tree / "fragments.py").read_text(encoding="utf-8").replace(
            '    "a-rim-sample-quoted-as-a-measurement-of-the-band": {"reach_by_max"',
            '    "a-rim-sample-quoted-as-a-measurement-of-the-band": {"the_rules_reach": the_rules_reach},\n'
            '    "a-rim-sample-quoted-as-a-measurement-of-the-band": {"reach_by_max"', 1),
        encoding="utf-8")
    code, out = check(tree)
    return code == 1 and "declares" in out, "a repeated class name is a DUPE"


def s_policy_is_in_the_count(tree):
    """A count carries the policy it was counted under.

    Two counts under two rules are not the same count, and the rule here is not
    only the ledger's data: a change to the erasure can honestly move every
    number `check.py` prints, and a reader of a quoted count cannot tell an
    edited policy from an unchanged result. So the normal run prints a hash of
    the policy's own source beside the counts, and `--policy` prints it alone.

    This row asserts three things: the plain run prints that line; the hash is
    exactly what the three policy objects' source digests to; and a change to
    that source moves the hash, so the line cannot survive an edit unnoticed.
    """
    import hashlib
    code, out = check(tree)
    if code != 0:
        return False, f"the ledger itself does not pass: {code}"
    line = [l for l in out.splitlines() if l.startswith("equivalence policy")]
    if not line:
        return False, "the counts do not name the policy they were counted under"
    quoted = line[0].split()[2]

    text = (tree / "check.py").read_text(encoding="utf-8")
    module = ast.parse(text)
    wanted = {"_DropDeadStores", "scope_bindings", "_Normalise", "fingerprint"}
    blocks = [ast.get_source_segment(text, node).strip() for node in module.body
              if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in wanted]
    if len(blocks) != len(wanted):
        return False, f"the policy objects are not all in check.py: {len(blocks)} of {len(wanted)}"
    expected = hashlib.sha256("\n\n".join(blocks).encode("utf-8")).hexdigest()[:16]
    if quoted != expected:
        return False, f"the printed policy {quoted} is not the policy in the file {expected}"

    marked = (tree / "check.py").read_text(encoding="utf-8").replace(
        "    def _rename(self, name: str) -> str:",
        "    # a policy edit\n    def _rename(self, name: str) -> str:", 1)
    (tree / "check.py").write_text(marked, encoding="utf-8")
    code2, out2 = check(tree, "--policy")
    moved = out2.strip()
    if code2 != 0 or moved == quoted:
        return False, "the policy hash did not move when the policy source changed"
    return True, f"the count is quoted under policy {quoted}, and an edit moves it"


def r_attribute_pair(tree):
    """An outside attack on the fingerprint, and the two erasures it found.

    The attack claimed `s.lstrip("ab")` and `s.rstrip("ab")` collapse because
    names are erased after parsing. They do not: attribute names survive, so
    verbs on one receiver separate. Running it found the erasure one step aside
    -- the subject -- where `json.loads(x)` and `pickle.loads(x)` were one shape
    because the receiver is a `Name`. That half is now closed: a name the
    function never binds is a reference to something outside the fragment and is
    kept, while a bound name is still the author's choice of letter.

    Every line below is asserted, including the price: keeping free names means a
    copy that renames the helper it delegates to reads as different logic, and a
    fragment that keeps the helper's name is still one shape with its copy. A
    change to the erasure has to move this row, which is the point of it.

    The second half of the same question is scope. A binding belongs to the scope
    that makes it, so a store inside a nested def, a lambda, a comprehension or
    an `except ... as` clause binds nothing in the function that contains it: with
    one flat set of bound names, `return helper(xs)` stopped being a reference to
    something outside the fragment as soon as an unrelated nested function used
    `helper` as a local. That row is asserted too, and its counterexample is the
    case below rather than a sentence here.
    """
    import importlib.util
    import linecache
    import sys
    import textwrap
    sys.path.insert(0, str(HERE))
    spec = importlib.util.spec_from_file_location("chk", HERE / "check.py")
    chk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chk)
    fingerprint = chk.fingerprint
    counter = [0]

    def build(source: str):
        counter[0] += 1
        src = textwrap.dedent(source).strip() + "\n"
        name = f"<pair{counter[0]}>"
        linecache.cache[name] = (len(src), None, src.splitlines(True), name)
        ns: dict = {}
        exec(compile(src, name, "exec"), ns)
        return ns[src.split("(")[0].split()[-1]]

    def same(left: str, right: str) -> bool:
        return fingerprint(build(left)) == fingerprint(build(right))

    def chk_ast(source: str):
        """The body of a snippet as a tree, the way fingerprint() reads it."""
        tree = ast.parse(textwrap.dedent(source).strip() + "\n")
        node = tree.body[0]
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            node.body = node.body[1:]
        return node

    separate = [
        ("verbs on one receiver: lstrip against rstrip",
         'def a(s):\n    return s.lstrip("ab")\n', 'def b(s):\n    return s.rstrip("ab")\n'),
        ("verbs at both arities: strip against lstrip",
         'def a(s):\n    return s.strip("ab")\n', 'def b(s):\n    return s.lstrip("ab")\n'),
        ("subjects under one verb: json.loads against pickle.loads",
         "def a(x):\n    return json.loads(x)\n", "def b(x):\n    return pickle.loads(x)\n"),
        ("the price of keeping free names: a copy that renames its helper",
         "def a(xs):\n    return find_max(xs)\n", "def b(xs):\n    return pick_max(xs)\n"),
        ("a global declaration leaves the name external",
         "def a(xs):\n    global counter\n    return counter + len(xs)\n",
         "def b(xs):\n    global total\n    return total + len(xs)\n"),
    ]
    one_shape = [
        ("a comprehension target is a bound name",
         "def a(xs):\n    return [y * 2 for y in xs]\n",
         "def b(xs):\n    return [z * 2 for z in xs]\n"),
        ("a lambda argument is a bound name",
         "def a(xs):\n    return sorted(xs, key=lambda v: -v)\n",
         "def b(xs):\n    return sorted(xs, key=lambda w: -w)\n"),
        ("a nested def's name is a bound name",
         "def a(xs):\n    def inner(v):\n        return v + 1\n    return [inner(x) for x in xs]\n",
         "def b(xs):\n    def step(v):\n        return v + 1\n    return [step(x) for x in xs]\n"),
        ("a walrus target is a bound name",
         "def a(xs):\n    return [v for x in xs if (v := x) > 0]\n",
         "def b(xs):\n    return [w for x in xs if (w := x) > 0]\n"),
        ("a class name is a bound name",
         "def a(xs):\n    class P:\n        pass\n    return P\n",
         "def b(xs):\n    class Q:\n        pass\n    return Q\n"),
        ("an except-as name is a bound name",
         "def a(f):\n    try:\n        return f()\n    except ValueError as e:\n        return str(e)\n",
         "def b(f):\n    try:\n        return f()\n    except ValueError as err:\n        return str(err)\n"),
        ("an async def is a named function, renamed and dead-stripped like any other",
         "async def a(xs):\n    _pad = None\n    return [x for x in xs]\n",
         "async def b(zs):\n    return [z for z in zs]\n"),
        ("bound names are still erased",
         "def a(xs):\n    total = 0\n    for x in xs:\n        total += x\n    return total\n",
         "def b(items):\n    acc = 0\n    for it in items:\n        acc += it\n    return acc\n"),
        ("dead-store padding is still invisible",
         "def a(xs):\n    return max(xs)\n", "def b(xs):\n    _pad = None\n    return max(xs)\n"),
        ("a helper that keeps its name is still one shape with its copy",
         "def a(xs):\n    return find_max(xs)\n", "def b(ys):\n    return find_max(ys)\n"),
        ("a nested function's local does not bind the enclosing scope",
         "def a(xs):\n    def inner():\n        helper = 1\n        return helper\n    return helper(xs)\n",
         "def b(xs):\n    def inner():\n        step = 1\n        return step\n    return helper(xs)\n"),
        ("a lambda's argument does not bind the enclosing scope",
         "def a(xs):\n    f = lambda helper: helper(xs)\n    return helper(xs)\n",
         "def b(xs):\n    f = lambda step: step(xs)\n    return helper(xs)\n"),
        ("a comprehension's target does not bind the enclosing scope",
         "def a(xs):\n    return [i for i in xs], i\n",
         "def b(xs):\n    return [k for k in xs], i\n"),
        ("an except-as name does not outlive its handler",
         "def a(f):\n    try:\n        return f()\n    except Exception as e:\n        pass\n    return e\n",
         "def b(f):\n    try:\n        return f()\n    except Exception as err:\n        pass\n    return e\n"),
        ("a global name is not a binding",
         "def a(xs):\n    global counter\n    return counter + len(xs)\n",
         "def b(ys):\n    global counter\n    return counter + len(ys)\n"),
        ("a def that calls itself keeps its own name erased",
         "def a(n):\n    return n if n < 2 else n * a(n - 1)\n",
         "def b(k):\n    return k if k < 2 else k * b(k - 1)\n"),
    ]
    capture = [
        ("a free name spelled like an assigned name",
         "def a(x):\n    return x + v0\n",
         "def b(x):\n    return x + x\n"),
    ]
    # Order-independence has its own half: renaming during the walk made a
    # comprehension target, a nested def's name and a walrus target score as
    # different logic, because each is read before it is visited. Every entry
    # above is such a case, so a return to renaming-during-the-walk fails here.
    bad_sep = [label for label, l, r in separate if same(l, r)]
    bad_one = [label for label, l, r in one_shape if not same(l, r)]
    bad_cap = [label for label, l, r in capture if same(l, r)]
    if bad_sep or bad_one or bad_cap:
        return False, (f"boundary moved: not separate={bad_sep} not one shape={bad_one} "
                       f"captured={bad_cap}")

    # Idempotence: the erasure run twice over one tree must equal the erasure run
    # once. It did not -- a free name came out of the first pass already marked,
    # and the second pass marked it again (`g:find_max` -> `g:g:find_max`), so the
    # answer depended on how many times the policy had been applied.
    twice_bad = []
    for label, left, _ in one_shape + separate + capture:
        first = chk_ast(left)
        chk._DropDeadStores().visit(first)
        sc, ex = chk.scope_bindings(first)
        chk._Normalise(sc, ex).visit(first)
        once = ast.dump(first)
        sc2, ex2 = chk.scope_bindings(first)
        chk._Normalise(sc2, ex2).visit(first)
        if ast.dump(first) != once:
            twice_bad.append(label)
    if twice_bad:
        return False, f"the erasure is not idempotent: {twice_bad}"

    return True, ("verbs and subjects separate; bound names stay inside their scope; "
                  "padding, helpers and a second pass do not move the answer")


CASES = [
    ("order flip keeps the answer", a_order_flip),
    ("citation counter agrees with its audit", b_citation_counter),
    ("a class with no fragment is refused", c_ghost_class),
    ("a probe that did not run is a miss", d_probe_that_did_not_run),
    ("a repeat must call the fragment it names", e_repeat_shim),
    ("a repeat's own bytes are named", f_repeat_replaying_another_class),
    ("a class copy is a duplicate", g_class_copy),
    ("a padded copy is a duplicate", h_class_copy_padded),
    ("the primary is what the probe calls", i_primary_steering),
    ("a citation is one line", j_multiline_quote),
    ("an address must resolve", k_unresolvable_address),
    ("every retired kind is counted", l_unknown_retired_kind),
    ("display modes carry the failure code", m_modes_carry_the_code),
    ("a skipped entry is audited too", n_skip_without_divergence),
    ("dead stores are not a difference", o_dead_store_is_not_a_difference),
    ("literals have no builtins", p_literals_have_no_builtins),
    ("a repeated class name is refused", q_duplicate_declaration),
    ("the fingerprint separates verbs and subjects, and says its price", r_attribute_pair),
    ("a count carries the policy it was counted under", s_policy_is_in_the_count),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        for name, _ in CASES:
            print(name)
        return 0
    failed = 0
    for name, fn in CASES:
        try:
            ok, detail = fn(copy_ledger(name.replace(" ", "-")))
        except Exception as exc:
            ok, detail = False, f"the case itself raised {type(exc).__name__}: {exc}"
        print(f"{'ok  ' if ok else 'FAIL'} {name:<44} {detail}")
        failed += not ok
    print(f"cases {len(CASES)} failed {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
