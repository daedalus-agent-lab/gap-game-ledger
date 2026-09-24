import importlib.util, linecache, textwrap, sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
spec = importlib.util.spec_from_file_location("chk", Path(".").resolve() / "check.py")
chk = importlib.util.module_from_spec(spec); spec.loader.exec_module(chk)
fp = chk.fingerprint
c = [0]
def build(src):
    c[0] += 1
    s = textwrap.dedent(src).strip() + "\n"
    name = f"<u{c[0]}>"
    linecache.cache[name] = (len(s), None, s.splitlines(True), name)
    ns = {}
    exec(compile(s, name, "exec"), ns)
    return ns[s.split("(")[0].split()[-1]]
cases = [
 ("free name shadowed by a nested local (the leak)",
  "def a(xs):\n    def inner():\n        helper = 1\n        return helper\n    return helper(xs)\n",
  "def b(xs):\n    def inner():\n        step = 1\n        return step\n    return helper(xs)\n", True),
 ("a real nested binding still erased",
  "def a(xs):\n    def inner():\n        v = 1\n        return v\n    return [inner(x) for x in xs]\n",
  "def b(xs):\n    def inner():\n        w = 1\n        return w\n    return [inner(x) for x in xs]\n", True),
 ("a lambda local no longer leaks out",
  "def a(xs):\n    f = lambda helper: helper(xs)\n    return helper(xs)\n",
  "def b(xs):\n    f = lambda step: step(xs)\n    return helper(xs)\n", True),
 ("outer local still erased where it is the outer local",
  "def a(xs):\n    helper = make()\n    return helper(xs)\n",
  "def b(xs):\n    step = make()\n    return step(xs)\n", True),
 ("recursion under a renamed def",
  "def a(n):\n    return n if n < 2 else n * a(n - 1)\n",
  "def b(k):\n    return k if k < 2 else k * b(k - 1)\n", True),
 ("different helper still different",
  "def a(xs):\n    return find_max(xs)\n", "def b(xs):\n    return pick_max(xs)\n", False),
 ("global is not a binding",
  "def a(xs):\n    global counter\n    counter += 1\n    return counter\n",
  "def b(xs):\n    global counter\n    counter += 1\n    return counter\n", True),
]
for label, l, r, want in cases:
    got = fp(build(l)) == fp(build(r))
    print(("OK  " if got == want else "BAD "), label, "->", got, "want", want)
