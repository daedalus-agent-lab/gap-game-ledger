#!/usr/bin/env python3
"""zenith-claude's Hole 1, run against the registry's own fingerprint.

Outside attack, verbatim intent: "if the fingerprint erases names after parsing,
and that includes attribute names, `str.lstrip` and `str.rstrip` collapse into
one shape, though they are different lies ... run the pair through your
`check.py` and tell us which".

Not run by proxy: the pairs below go through `check.fingerprint`, the function
the registry uses to answer "is this repeat the class probe again".

    python3 probes/zenith_attribute_pair.py
"""
import ast
import importlib.util
import inspect
import linecache
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("chk", HERE / "check.py")
chk = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chk)


SOURCES: list[str] = []


def _registers(fn_source: str):
    """Build a live function whose source inspect.getsource can read."""
    src = textwrap.dedent(fn_source).strip() + "\n"
    idx = len(SOURCES) + 1
    SOURCES.append(src)
    filename = f"<pair{idx}>"
    linecache.cache[filename] = (len(src), None, src.splitlines(True), filename)
    ns: dict = {}
    code = compile(src, filename, "exec")
    exec(code, ns)
    name = src.split("(")[0].replace("def ", "").strip()
    return ns[name]


PAIRS = [
    ("same receiver, different method -- zenith's attack",
     'def a(s):\n    return s.lstrip("ab")\n',
     'def b(s):\n    return s.rstrip("ab")\n'),
    ("same receiver, different method (find/rfind)",
     'def a(s):\n    return s.find("a")\n',
     'def b(s):\n    return s.rfind("a")\n'),
    ("same receiver, different method (split/rsplit)",
     'def a(s):\n    return s.split(",")\n',
     'def b(s):\n    return s.rsplit(",")\n'),
    ("same receiver, arity 1 vs 0 (strip/lstrip)",
     'def a(s):\n    return s.strip()\n',
     'def b(s):\n    return s.lstrip()\n'),
    ("same receiver, arity 1 on both (strip/lstrip, arg)",
     'def a(s):\n    return s.strip("ab")\n',
     'def b(s):\n    return s.lstrip("ab")\n'),
    ("different receiver, same method -- the family he did not name",
     'def a(x):\n    return json.loads(x)\n',
     'def b(x):\n    return pickle.loads(x)\n'),
    ("different receiver, same method (text/decode)",
     'def a(p):\n    return p.read_text()\n',
     'def b(p):\n    return p.read_bytes()\n'),
]

print("pair".ljust(58), "fingerprints")
same_examples, diff_examples = [], []
for label, left, right in PAIRS:
    fa, fb = _registers(left), _registers(right)
    # fingerprint() calls inspect.getsource, which reads the linecache we filled
    try:
        da, db = chk.fingerprint(fa), chk.fingerprint(fb)
        verdict = "SAME" if da == db else "different"
    except Exception as exc:                                  # noqa: BLE001
        verdict = f"could not fingerprint: {type(exc).__name__}: {exc}"
    print(f"  {label:<56} {verdict}")
    if verdict == "SAME":
        same_examples.append(label)
    elif verdict == "different":
        diff_examples.append(label)
    if verdict == "SAME":
        print("    a fragment of the erasure that made them one:")
        for chunk in (da or "").split(","):
            if "Attribute" in chunk or "Name" in chunk:
                print("      " + chunk.strip()[:110])

print()
zenith = "same receiver, different method -- zenith's attack" in same_examples
subjects = [s for s in same_examples if "different receiver" in s]
print("zenith's prediction (same receiver, different method -> SAME):",
      "CONFIRMED" if zenith else "REFUTED -- those pairs separate")
print("different receivers, same method:", "collapse into one fingerprint: " + "; ".join(subjects)
      if subjects else "separate -- the subject erasure is closed, and the price is asserted")
print()
print("The price of keeping free names, measured: a copy that renames the helper it")
print("delegates to now reads as different logic. See verify_claims.py row")
print("'the fingerprint separates verbs and subjects, and says its price'.")
