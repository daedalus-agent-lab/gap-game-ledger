import importlib.util, linecache, textwrap, sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
HERE = Path(".").resolve()
spec = importlib.util.spec_from_file_location("chk", HERE / "check.py")
chk = importlib.util.module_from_spec(spec); spec.loader.exec_module(chk)
fp = chk.fingerprint
c = [0]
def build(src):
    c[0] += 1
    s = textwrap.dedent(src).strip() + "\n"
    name = f"<s{c[0]}>"
    linecache.cache[name] = (len(s), None, s.splitlines(True), name)
    ns = {}
    exec(compile(s, name, "exec"), ns)
    return ns[s.split("(")[0].split()[-1]]

A = "def a(xs):\n    def inner():\n        helper = 1\n        return helper\n    return helper(xs)\n"
B = "def b(xs):\n    def inner():\n        step = 1\n        return step\n    return helper(xs)\n"
C = "def c(xs):\n    def inner():\n        return helper()\n    return inner(xs)\n"
D = "def d(xs):\n    def inner():\n        step = 1\n        return step\n    return inner(xs)\n"
print("A vs B (a local in a nested scope named like an outer free name):", fp(build(A)) == fp(build(B)))
print("C vs D (control: no collision):", fp(build(C)) == fp(build(D)))
print("--- A dump ---"); print(fp(build(A))[:400])
print("--- B dump ---"); print(fp(build(B))[:400])
