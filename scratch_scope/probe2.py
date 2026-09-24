import importlib.util, linecache, textwrap, sys, os, difflib
sys.path.insert(0, os.getcwd())
from pathlib import Path
spec = importlib.util.spec_from_file_location("chk", Path(".").resolve() / "check.py")
chk = importlib.util.module_from_spec(spec); spec.loader.exec_module(chk)
fp = chk.fingerprint
c = [0]
def build(src):
    c[0] += 1
    s = textwrap.dedent(src).strip() + "\n"
    name = f"<t{c[0]}>"
    linecache.cache[name] = (len(s), None, s.splitlines(True), name)
    ns = {}
    exec(compile(s, name, "exec"), ns)
    return ns[s.split("(")[0].split()[-1]]

A = "def a(xs):\n    def inner():\n        helper = 1\n        return helper\n    return helper(xs)\n"
B = "def b(xs):\n    def inner():\n        step = 1\n        return step\n    return helper(xs)\n"
fa, fb = fp(build(A)), fp(build(B))
print("same:", fa == fb)
import re
print("A has g:helper:", "g:helper" in fa)
print("B has g:helper:", "g:helper" in fb)
# where they differ
ta = re.findall(r"Name\(id='([^']+)'\)", fa)
tb = re.findall(r"Name\(id='([^']+)'\)", fb)
print("A names:", ta)
print("B names:", tb)
