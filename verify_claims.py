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
    m = re.search(r"instances with an address that is SHAPED like a public message "
                  r"(\d+)/(\d+) \((\d+) of them quote", out)
    if not m:
        code2, out2 = check(tree)
        m = re.search(r"instances with an address that is SHAPED like a public message "
                      r"(\d+)/(\d+) \((\d+) of them quote", out2)
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

    def build_lambda(source: str):
        """A snippet bound to one name whose value is a lambda."""
        counter[0] += 1
        src = textwrap.dedent(source).strip() + "\n"
        name = f"<lam{counter[0]}>"
        linecache.cache[name] = (len(src), None, src.splitlines(True), name)
        ns: dict = {}
        exec(compile(src, name, "exec"), ns)
        return ns[src.split("=")[0].strip()]

    def same_lambda(left: str, right: str) -> bool:
        return fingerprint(build_lambda(left)) == fingerprint(build_lambda(right))

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
    # A bare lambda is a fragment too, and it used to be dumped as it stands --
    # nothing erased its argument, so two spellings of one piece of logic read as
    # two. The second pair is the rider an outside reader put on the property:
    # alpha-renaming onto a name that is free in the fragment changes the
    # meaning, so the fingerprint must move, and moving is the correct answer.
    lambda_shape = [
        ("a bare lambda's argument is a bound name",
         "f = lambda x: x + y\n", "g = lambda z: z + y\n"),
    ]
    lambda_separate = [
        ("renaming a lambda's argument onto a free name is a different meaning",
         "f = lambda x: x + y\n", "g = lambda y: y + y\n"),
    ]
    # Order-independence has its own half: renaming during the walk made a
    # comprehension target, a nested def's name and a walrus target score as
    # different logic, because each is read before it is visited. Every entry
    # above is such a case, so a return to renaming-during-the-walk fails here.
    bad_sep = [label for label, l, r in separate if same(l, r)]
    bad_one = [label for label, l, r in one_shape if not same(l, r)]
    bad_cap = [label for label, l, r in capture if same(l, r)]
    bad_lam = [label for label, l, r in lambda_shape if not same_lambda(l, r)]
    bad_lam_sep = [label for label, l, r in lambda_separate if same_lambda(l, r)]
    if bad_sep or bad_one or bad_cap or bad_lam or bad_lam_sep:
        return False, (f"boundary moved: not separate={bad_sep} not one shape={bad_one} "
                       f"captured={bad_cap} lambda_not_erased={bad_lam} "
                       f"lambda_capture={bad_lam_sep}")

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


def t_a_store_read_by_a_caller_not_in_the_ast(tree):
    """A store read by eval/locals/dir is not a dead store.

    The dead-store pass sees reads that are names in the tree. `eval("x + 1")`
    carries no name `x`, so the pass removed the store and two functions that
    answer 42 and NameError shared one fingerprint. The repair keeps everything
    in a fragment that calls a dynamic reader: erasing less is visible, erasing
    a live store is not.
    """
    import builtins
    import sys
    import importlib.util
    spec = importlib.util.spec_from_file_location("chk", HERE / "check.py")
    chk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chk)

    def ev_a():
        x = 41
        return eval("x + 1")

    def ev_b():
        return eval("x + 1")

    def loc_a():
        x = 1
        return locals()

    def loc_b():
        return locals()

    def dr_a():
        secret = 1
        return dir()

    def dr_b():
        return dir()

    # The reach is not always a BARE name. A qualified reader (builtins.eval),
    # a frame path (sys._getframe().f_locals) and a reader one frame down all
    # reach the same mapping while carrying no name of the reader set, and each
    # was a hole found after the one before it.
    def q_a():
        x = 41
        return builtins.eval("x")

    def q_b():
        return builtins.eval("x")

    def fr_a():
        secret = 1
        return "secret" in sys._getframe().f_locals

    def fr_b():
        return "secret" in sys._getframe().f_locals

    def callee():
        return "secret" in sys._getframe(1).f_locals

    def cal_a():
        secret = 1
        return callee()

    def cal_b():
        return callee()

    def plain_pad(xs):
        _pad = None
        return max(xs)

    def plain(xs):
        return max(xs)

    pairs = ((ev_a, ev_b), (loc_a, loc_b), (dr_a, dr_b),
             (q_a, q_b), (fr_a, fr_b), (cal_a, cal_b))
    separated = all(chk.fingerprint(a) != chk.fingerprint(b) for a, b in pairs)
    still_drops = chk.fingerprint(plain_pad) == chk.fingerprint(plain)
    # And the answers really do differ, so the separation is not two spellings of
    # the same behaviour: a pair that agrees proves nothing about the guard.
    live = (ev_a() != ev_b, loc_a() != loc_b, dr_a() != dr_b,
            q_a() != q_b, fr_a() != fr_b, cal_a() != cal_b)
    # Every half must really behave differently from its partner: a pair that
    # agrees proves nothing about the guard, and a row that accepted one live
    # pair out of six would pass while five of them were two spellings of the
    # same behaviour.
    return separated and still_drops and all(live), \
        ("six reaches keep their store (bare, qualified, frame path, callee), "
         f"plain padding is still invisible, every pair's answers differ {live}")


def v_the_control_table_names_its_naming_dial(tree):
    """The table's verdicts are conditional on how the pass PRINTS a name.

    A row reading `different -> same` on R11 and R14 is a property of the rule
    AND of the naming dial the pass uses, because the flip appears only when a
    bound name is printed canonically: a pass that prints names as written
    answers `different` under both the policy and the break, and a second holder
    measured exactly that on CPython 3.11.16. Publishing the verdict without the
    dial offers a conditional reading as an unconditional one.
    """
    text = (HERE / "probes" / "control_table.md").read_text(encoding="utf-8")
    named = "naming dial" in text and "b:0" in text
    return named, "the published control table names the dial its verdicts depend on"


def u_bound_name_shadowing_a_builtin_is_still_a_letter(tree):
    """A parameter named `list` is the author's letter, not the builtin.

    The normaliser asked BUILTINS before asking what the fragment binds, so a
    parameter called `list` kept its name while the same function with the
    parameter called `dict` kept another: two spellings of one piece of logic
    read as two pieces of logic. An unbound `len` is the builtin and stays.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("chk", HERE / "check.py")
    chk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chk)

    def f_one(list, x):
        return list + x

    def f_two(dict, x):
        return dict + x

    def g_one(xs):
        return len(xs)

    def g_two(ys):
        return len(ys)

    shadowed = chk.fingerprint(f_one) == chk.fingerprint(f_two)
    builtin_still_free = chk.fingerprint(g_one) == chk.fingerprint(g_two)
    return shadowed and builtin_still_free, \
        "a bound `list` is a letter, an unbound `len` is the builtin"


def x_the_policy_cannot_quietly_lose_a_rule(tree):
    """A rule deleted with its pair, its mutation and its fragments is still a loss.

    Every count in this repository ranges over the policy the tree carries, so a
    rule removed from that policy removes itself from the scope the coverage count
    is taken over: measured on a copy, deleting R9 and everything named after it
    left check.py exit 0, this file 29/29 and the mutation harness green. The
    committed scope in check.py is the oracle: a rule the hand-written tuple names
    and the policy does not is a failure, and a rule the policy carries and the
    tuple does not is a failure too.

    Two copies are made, one for each direction, and **both** are required to be
    refused by name -- the second because it is the state I was actually in when a
    rule was added to the policy, and I had never run the oracle there. A constant
    of independence that is not run in the state where it disagrees with the thing
    it is independent of is a promise, not a check; the state where it agrees
    proves nothing.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("chk", HERE / "check.py")
    chk = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(chk)
    ok, detail = chk.policy_still_names_every_rule_it_named()
    if not ok:
        return False, detail
    # And the oracle must be able to fail: drop a rule from the policy on a copy
    # and the same comparison has to refuse it, or the oracle is a sentence.
    import shutil
    import subprocess
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="scope-gap-"))
    try:
        for name in ("check.py", "fragments.py"):
            shutil.copy(HERE / name, tmp / name)
        text = (tmp / "fragments.py").read_text(encoding="utf-8")
        text = text.replace('    ("R9", "a dunder name is left as written"),\n', "", 1)
        (tmp / "fragments.py").write_text(text, encoding="utf-8")
        out = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util as u, sys;"
             f"s=u.spec_from_file_location('c', {str(tmp / 'check.py')!r});"
             "m=u.module_from_spec(s); sys.path.insert(0,"
             f"{str(tmp)!r}); s.loader.exec_module(m);"
             "ok,why=m.policy_still_names_every_rule_it_named();"
             "print('REFUSES' if not ok else 'ACCEPTS', why)"],
            capture_output=True, text=True).stdout.strip()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    refused = out.startswith("REFUSES") and "R9" in out
    # The other direction: a rule that ARRIVES in the policy without being
    # committed. This is the state the author was in and never measured, and the
    # oracle has to refuse it by name or the first direction was the only one.
    tmp2 = Path(tempfile.mkdtemp(prefix="scope-arrival-"))
    try:
        for name in ("check.py", "fragments.py"):
            shutil.copy(HERE / name, tmp2 / name)
        text = (tmp2 / "fragments.py").read_text(encoding="utf-8")
        anchor = '    ("R15", "a fragment that calls a name it does not bind keeps its stores:'
        assert anchor in text
        text = text.replace(anchor, '    ("R17", "a rule nobody committed"),\n' + anchor, 1)
        (tmp2 / "fragments.py").write_text(text, encoding="utf-8")
        out2 = subprocess.run(
            [sys.executable, "-c",
             "import importlib.util as u, sys;"
             f"s=u.spec_from_file_location('c', {str(tmp2 / 'check.py')!r});"
             "m=u.module_from_spec(s); sys.path.insert(0,"
             f"{str(tmp2)!r}); s.loader.exec_module(m);"
             "ok,why=m.policy_still_names_every_rule_it_named();"
             "print('REFUSES' if not ok else 'ACCEPTS', why)"],
            capture_output=True, text=True).stdout.strip()
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)
    refused2 = out2.startswith("REFUSES") and "R17" in out2
    return refused and refused2, (
        f"{detail}; and the oracle refuses a policy with R9 dropped ({out[:80]}), "
        f"and a policy carrying a rule nobody committed ({out2[:80]})")


def v_control_fails_when_a_rule_of_the_policy_is_broken(tree):
    """A duplicate verdict is a measurement only while every rule of the policy
    has a pair that fails when the rule is broken.

    The guard is removed from a copy -- exactly the hole that was reported -- and
    the run must withdraw its duplicate verdicts and name the rule, rather than
    report agreement between two fragments it can no longer tell apart.
    """
    src = (tree / "check.py").read_text(encoding="utf-8")
    guard = ("        if (self._reads_by_a_caller(node)\n"
             "                or self._calls_a_name_the_fragment_does_not_bind(node)):\n"
             "            self.generic_visit(node)\n"
             "            return node\n")
    if guard not in src:
        return False, "the guard is not where this case expects it"
    (tree / "check.py").write_text(src.replace(guard, "", 1), encoding="utf-8")
    code, out = check(tree)
    named = "store_read_by_eval" in out
    withdrawn = "NOT MEASURED" in out
    return code == 1 and named and withdrawn, \
        f"exit {code}, rule named {named}, verdicts withdrawn {withdrawn}"


def w_control_is_a_pair_per_rule(tree):
    """Every rule of the policy answers for itself, so a broken rule cannot hide
    behind the ones still working.

    The count here is over rule ids from `fragments.POLICY_RULES`, not over the
    labels of the pairs: an attacker ran six mutations of the policy past a table
    whose six labels printed `one per rule`, because two of the labels guarded one
    rule and no pair exercised the parameter its label claimed.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("frag", HERE / "fragments.py")
    frag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frag)
    spec2 = importlib.util.spec_from_file_location("chk", HERE / "check.py")
    chk = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(chk)
    rules = {rid for rid, _text in frag.POLICY_RULES}
    guarded = {rule for *_rest, rule in frag.CONTROL_PAIRS}
    declared = {rid for rid, _row in frag.RULES_WITHOUT_A_PAIR}
    pairs = [(l, r) for l, r, _s, _rule in frag.CONTROL_PAIRS]
    uncovered = sorted(rules - guarded - declared, key=str)
    ok = (bool(pairs) and len(set(pairs)) == len(pairs) and not uncovered
          and chk.fingerprint_control()[0])
    return ok, (f"{len(pairs)} pairs over {len(rules)} rules, {len(guarded)} guarded, "
                f"{len(declared)} declared, uncovered {uncovered or 'none'}")


def x_the_declared_gap_points_at_a_row_that_exists(tree):
    """A gap named with a pointer that has rotted is not a declared gap.

    A rule of the policy without a control pair names the acceptance row that
    covers it; that row must be a function defined in this file, or the
    declaration is prose about a check nobody runs. The mutation harness goes one
    step further and *runs* it on a copy with the rule broken.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("frag", HERE / "fragments.py")
    frag = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(frag)
    defined = {fn.__name__ for _label, fn in CASES}
    missing = [f"{rule} -> {row}" for rule, row in frag.RULES_WITHOUT_A_PAIR
               if row not in defined]
    rules = {rid for rid, _text in frag.POLICY_RULES}
    unknown = [rule for rule, _row in frag.RULES_WITHOUT_A_PAIR if rule not in rules]
    return not missing and not unknown, \
        (f"{len(frag.RULES_WITHOUT_A_PAIR)} gap rules declared, "
         f"{len(frag.CONTROL_PAIRS)} pairs, dead pointers {missing or 'none'}")


def r_idempotence(tree):
    """The erasure is a fixed point on its own output.

    Applying the pass twice to one tree must leave the second application with
    nothing to do. The letters it writes are unspellable -- neither the free-name
    prefix nor the erased-letter prefix is an identifier -- so it can tell its own
    output from a name an author wrote, and two fragments that differ only in how
    many times the instrument ran cannot read as two pieces of logic. This is the
    row the declared gap for that rule points at, and the mutation harness runs it
    on a copy with the guard removed: the second pass then prefixes again, and the
    row must fail.
    """
    import importlib
    cases = [
        ("a padded function", "def f(xs):\n    _pad = None\n    return max(xs)\n"),
        ("a free name and a bound one", "def f(xs):\n    return helper(xs) + len(xs)\n"),
        ("a global declaration", "def f(xs):\n    global counter\n    counter = 1\n"
                                 "    return counter + len(xs)\n"),
        ("a nested local", "def f(xs):\n    def g(x):\n        return x\n    return g(xs)\n"),
        ("a comprehension target", "def f(xs):\n    return [y for y in xs]\n"),
        ("a bare lambda", "f = lambda x: x + y\n"),
        ("an import with an alias", "def f(t):\n    import json as j\n    return j.loads(t)\n"),
        ("a builtin-named argument", "def f(list, xs):\n    return list(xs)\n"),
    ]
    sys.path.insert(0, str(tree))
    saved = {k: sys.modules.pop(k, None) for k in ("fragments", "check")}
    try:
        chk = importlib.import_module("check")
        moved = []
        for label, src in cases:
            node = ast.parse(src).body[0]
            chk._DropDeadStores().visit(node)
            scopes, external = chk.scope_bindings(node)
            chk._Normalise(scopes, external).visit(node)
            first = ast.dump(node)
            chk._Normalise(scopes, external).visit(node)
            if ast.dump(node) != first:
                moved.append(label)
    finally:
        for k in ("fragments", "check"):
            sys.modules.pop(k, None)
        for k, v in saved.items():
            if v is not None:
                sys.modules[k] = v
        sys.path.remove(str(tree))
    return not moved, (f"{len(cases)} fragments, the second pass moves {len(moved)}"
                       + (f": {moved}" if moved else ""))


def y_a_second_claim_needs_a_different_measurement(tree):
    """A repeat on the class's own bytes is refused however its promise is worded,
    and kept only when it measures something the class does not.

    The gate used to ask whether the repeat's prose was written in the class's own
    words, and an independent reader injected exactly that: the class fragment, the
    class probe, the class's expected and observed results, and one paraphrased
    sentence, which the run then counted as a second sighting. The first half below
    is that injection and must now be refused; the second half is a repeat that asks
    a genuinely different question of the same bytes and must still be kept, because
    a gate that only ever tightens would drop real second claims. The old name of
    this row was `..._needs_a_different_promise`, and the row was green under the
    defect it was supposed to catch.
    """
    data = load(tree)
    entry = find(data, CLAMP)
    entry["repeats"].append({
        "id": "paraphrased-restatement",
        "promise": "clamp keeps val between low and high, even handed a bad pair",
        "fact": entry["fact"],
        "probe": entry["probe"], "expected": entry["expected"],
        "observed": entry["observed"], "fn": "clamp",
    })
    save(tree, data)
    code_same, out_same = check(tree)

    data = load(tree)
    entry = find(data, CLAMP)
    entry["repeats"][-1]["probe"] = "clamp(50, 100, 60)"
    entry["repeats"][-1]["expected"] = "100"
    entry["repeats"][-1]["observed"] = "60"
    save(tree, data)
    code_new, out_new = check(tree)
    return (code_same == 1 and "paraphrase of the promise is not a second claim" in out_same
            and code_new == 0 and "second claim on the same bytes" in out_new), \
        f"paraphrase refused (exit {code_same}), different measurement kept (exit {code_new})"


def z_the_policy_is_measured_not_described(tree):
    """Break every rule of the policy on a copy and check who notices.

    `probes/policy_mutations.py` applies each mutation in
    `fragments.POLICY_MUTATIONS` to check.py in memory: a guarded rule must make
    the control fail and name that rule's pair, a declared rule must leave the
    control passing and make the row the declaration points at fail. A rule in
    neither table, or a mutation that moves no fingerprint, is drift.
    """
    row = tree / "probes" / "policy_mutations.py"
    if not row.exists():
        return False, "the mutation harness is not in the copy"
    out = subprocess.run([sys.executable, str(row)], cwd=tree, capture_output=True,
                         text=True, env={"PATH": "/usr/bin:/bin"})
    tail = [l for l in (out.stdout + out.stderr).splitlines() if l.startswith("DRIFT")]
    return out.returncode == 0, (f"exit {out.returncode}, drifts {len(tail)}"
                                 + (f": {tail[:2]}" if tail else ""))


def zz_the_control_table_is_current(tree):
    """The published control table is generated from the tree, never edited.

    A reader who will not run my script works the table by hand, so the table is
    a deliverable and has to be the same bytes the tree produces -- otherwise the
    hand-play is played against a table no longer in force. And the row that
    matters is the one the class is about: for every rule, the verdict under the
    policy and the verdict under the broken policy must differ, because a pair
    that answers the same thing about both is a label. The `as_of` line is the
    one line dropped before comparing: it is the time of the reading, not of the
    table.
    """
    import subprocess
    gen = tree / "probes" / "policy_mutations.py"
    out = subprocess.run([sys.executable, str(gen), "--table"],
                         capture_output=True, text=True, cwd=str(tree))
    if out.returncode != 0:
        return False, f"the table generator exited {out.returncode}: {out.stderr.strip()[:120]}"

    def without_as_of(text):
        return "\n".join(l for l in text.splitlines()
                         if not l.startswith("as_of ")).strip()

    published = (tree / "probes" / "control_table.md").read_text(encoding="utf-8")
    if without_as_of(out.stdout) != without_as_of(published):
        return False, ("the published table does not match the one the tree generates: "
                       "regenerate with `python3 probes/policy_mutations.py --table "
                       "> probes/control_table.md`")
    rows = [l for l in out.stdout.splitlines() if l.startswith("| R")]
    fields = [l.split("|") for l in rows]
    frozen = [f[1].strip() for f in fields if f[4].strip() == f[5].strip()]
    if frozen:
        return False, (f"{len(frozen)} pair(s) answer the same under the policy and "
                       f"under its break, so they are labels: {frozen}")
    return True, f"{len(rows)} rows, current, every one moving when its rule is broken"


def q_provenance_is_a_reading(tree):
    """A recovered label's provenance must be bytes this repo carries.

    `label_recovery.json` names, for each recovered label, the file its fragment
    was taken from. Those files lived in a workspace outside the repo, so the
    field was a citation no reader could resolve -- and nothing read it at all.
    The bytes travel under `provenance/` now and `check.py` re-digests them.

    Three attacks, each on its own copy: a digest that does not match the file, a
    row that stops saying whether its provenance is checkable, and a verdict that
    rests on an observation recorded as not replaying. The clean copy is measured
    first, so a gate that is red for everything cannot pass this row.
    """
    clean, out = check(tree)
    if clean != 0:
        return False, f"the untouched copy already exits {clean}: {out.strip()[-200:]}"

    def attack(name, mutate):
        victim = copy_ledger(f"provenance-{name}")
        path = victim / "label_recovery.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        if not mutate(data):
            return f"{name}: no row to mutate"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        rc, text = check(victim)
        if rc == 0:
            return f"{name}: check.py still exits 0"
        if "UNPROVEN" not in text:
            return f"{name}: exits {rc} but names no unproven row"
        return None

    def bad_digest(data):
        for row in data["rows"]:
            if row.get("sha256"):
                row["sha256"] = "0" * 64
                return True
        return False

    def no_status(data):
        for row in data["rows"]:
            if row.get("file"):
                row.pop("file_checkable", None)
                return True
        return False

    def verdict_without_replay(data):
        for row in data["rows"]:
            if row.get("verdict") == "CLASS":
                row["replays"] = False
                return True
        return False

    problems = [p for p in (attack("digest", bad_digest),
                            attack("status", no_status),
                            attack("replay", verdict_without_replay)) if p]
    rows = len(json.loads((tree / "label_recovery.json").read_text(encoding="utf-8"))["rows"])
    return not problems, (f"clean copy exits 0; {rows} rows; "
                          + (f"attacks that did not redden: {problems}" if problems
                             else "all three attacks exit non-zero and name the row"))


def q2_evidence_citations_resolve(tree):
    """A file named in an entry's evidence must be a file this repo carries.

    The evidence block for `a-verdict-word-for-an-examination-that-never-read-the-value`
    named `review/key_shape_refutation.md` -- the review that refuted half its claim --
    and that document was never carried over, so the strongest support the entry
    advertised resolved to nothing. Nothing read the block, so nothing noticed.

    The attack removes one cited file from a copy and requires the run to go red and
    name it; the untouched copy is measured first, so a gate that is red for
    everything cannot pass this row.
    """
    clean, out = check(tree)
    if clean != 0:
        return False, f"the untouched copy already exits {clean}: {out.strip()[-200:]}"
    victim = copy_ledger("evidence-citation")
    target = victim / "review" / "key_shape_refutation.md"
    if not target.exists():
        return False, "the cited review is not in the clean copy either"
    target.unlink()
    rc, text = check(victim)
    if rc == 0:
        return False, "check.py still exits 0 with a cited file removed"
    if "review/key_shape_refutation.md" not in text:
        return False, f"exits {rc} but does not name the missing citation"
    return True, ("clean copy exits 0; removing one cited file gives exit "
                  f"{rc} and names it")


CASES = [
    ("order flip keeps the answer", a_order_flip),    ("citation counter agrees with its audit", b_citation_counter),
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
    ("a store read by a caller not in the ast is not dead", t_a_store_read_by_a_caller_not_in_the_ast),
    ("a bound name shadowing a builtin is still a letter", u_bound_name_shadowing_a_builtin_is_still_a_letter),
    ("the control table names its naming dial", v_the_control_table_names_its_naming_dial),
    ("a broken rule of the policy withdraws the duplicate verdicts", v_control_fails_when_a_rule_of_the_policy_is_broken),
    ("a rule cannot quietly leave the policy or arrive uncommitted",
     x_the_policy_cannot_quietly_lose_a_rule),
    ("the control is one pair per rule", w_control_is_a_pair_per_rule),
    ("a declared gap points at a row that exists", x_the_declared_gap_points_at_a_row_that_exists),
    ("a second claim needs a different measurement, not a different wording", y_a_second_claim_needs_a_different_measurement),
    ("the erasure is a fixed point on its own output", r_idempotence),
    ("every rule of the policy is broken by a mutation and somebody notices",
     z_the_policy_is_measured_not_described),
    ("the published control table is current and every row moves",
     zz_the_control_table_is_current),
    ("a recovered label's provenance is bytes this repo carries", q_provenance_is_a_reading),
    ("a file named in an entry's evidence is a file this repo carries",
     q2_evidence_citations_resolve),
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
