"""Positive control: if the erasure goes back to one flat set of bound names,
the new scoping rows must fail."""
import importlib, importlib.util, sys, os
sys.path.insert(0, os.getcwd())
from pathlib import Path
spec = importlib.util.spec_from_file_location("chk", Path(".").resolve() / "check.py")
chk = importlib.util.module_from_spec(spec); spec.loader.exec_module(chk)
real = chk.scope_bindings
def flat(node):
    scopes, external = real(node)
    merged = set().union(*scopes.values()) if scopes else set()
    return {k: merged for k in scopes}, set()      # one flat set, the old behaviour
chk.scope_bindings = flat
import verify_claims
verify_claims_r = None
# run the row directly
ok, msg = verify_claims.r_attribute_pair(Path("."))
print("with one flat set of bound names:", ok, "|", msg)
