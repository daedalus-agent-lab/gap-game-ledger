#!/usr/bin/env python3
"""Which names does an answer carry that the contract's schema does not declare?

    python3 declared_names.py <capture.json> --route "/v1/me" --key block
    python3 declared_names.py --selftest
    python3 declared_names.py <capture.json> --route "/v1/me" --key block --check

The contract is the published OpenAPI document (`--spec`, default: a copy beside
this repository's root, else ../spec/openapi-1.17.3.json). A route whose 200 answer
is described by no JSON schema is reported as UNDESCRIBED, not as a match: a
comparison in which one side is empty is silence, and this probe exits non-zero on
silence under `--check` rather than printing a number.

Only TOP-LEVEL names are compared. A name nested inside an object the schema does
declare is that object's business; counting it would invent a missing declaration
out of a nesting depth, which is the unit error this probe exists to avoid --
selftest case (c) plants exactly that.

The capture must name its own route in `_provenance.route`; a capture whose route
differs from `--route` is refused, because a body read from one route compared
against another route's schema is two objects wearing one name.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DEFAULT_SPECS = (
    ROOT / "spec" / "openapi-1.17.3.json",
    ROOT.parent / "spec" / "openapi-1.17.3.json",
)


def load_spec(path):
    return json.loads(Path(path).read_text())


def find_spec(explicit=None):
    if explicit:
        return Path(explicit)
    for c in DEFAULT_SPECS:
        if c.exists():
            return c
    return None


def resolve(spec, schema):
    """Follow $ref chains to the object that carries `properties`. Depth 8 is a
    guard against a cycle in the document, not a guess about nesting."""
    seen = 0
    while isinstance(schema, dict) and "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            return {}
        node = spec
        for part in ref[2:].split("/"):
            node = node.get(part, {})
            if not isinstance(node, dict):
                return {}
        schema = node
        seen += 1
        if seen > 8:
            return {}
    return schema if isinstance(schema, dict) else {}


def descend(spec, schema, parts):
    """Walk a dotted path of property names into a declared schema, resolving
    $refs at every step. A path the schema does not carry returns None, which is
    a refusal, not an empty set: a block compared against a schema that has no
    line for it is silence."""
    node = resolve(spec, schema)
    for part in parts:
        props = node.get("properties")
        if not isinstance(props, dict) or part not in props:
            return None
        node = resolve(spec, props[part])
    return node


def declared_top_level(spec, route, method="get"):
    op = (spec.get("paths") or {}).get(route, {})
    if not isinstance(op, dict) or method not in op:
        return None
    answer = (op[method].get("responses") or {}).get("200") or {}
    schema = ((answer.get("content") or {}).get("application/json") or {}).get("schema") or {}
    if not schema:
        return set()
    schema = resolve(spec, schema)
    props = schema.get("properties")
    return set(props) if isinstance(props, dict) else None


def carried_top_level(body, drop=("_provenance",)):
    if not isinstance(body, dict):
        return set()
    return {k for k in body if k not in drop}


def compare(spec, route, body, method="get", drop=("_provenance",), at=()):
    decl = declared_top_level(spec, route, method)
    carried = carried_top_level(body, drop)
    if decl is None:
        return {"route": route, "state": "NO SUCH ROUTE", "declared": None, "carried": carried}
    if not decl:
        return {"route": route, "state": "UNDESCRIBED", "declared": set(), "carried": carried}
    node = None
    if at:
        op = (spec.get("paths") or {}).get(route, {}).get(method, {})
        answer = (op.get("responses") or {}).get("200") or {}
        schema = ((answer.get("content") or {}).get("application/json") or {}).get("schema") or {}
        node = descend(spec, schema, tuple(at))
        if node is None:
            return {"route": route, "state": "NO SUCH FIELD", "declared": None, "carried": carried}
        props = node.get("properties")
        decl = set(props) if isinstance(props, dict) else set()
        if not decl:
            return {"route": route, "state": "UNDESCRIBED", "declared": set(), "carried": carried}
    return {
        "route": route,
        "state": "compared",
        "declared": decl,
        "carried": carried,
        "carried_not_declared": sorted(carried - decl),
        "declared_not_carried": sorted(decl - carried),
    }


def report(rows, out=sys.stdout):
    bad = 0
    for r in rows:
        out.write("%s  %s\n" % (r["route"], r["state"]))
        if r["state"] != "compared":
            out.write("   declared: none   carried: %d\n" % len(r["carried"]))
            bad += 1
            continue
        out.write("   declared %d  carried %d\n" % (len(r["declared"]), len(r["carried"])))
        out.write("   carried, not declared : %s\n" % (", ".join(r["carried_not_declared"]) or "-"))
        out.write("   declared, not carried : %s\n" % (", ".join(r["declared_not_carried"]) or "-"))
    return bad


def fixture():
    """Two routes, one described and one that answers with no schema, plus the
    nesting case: a declared property whose own keys must not be counted."""
    def answer(schema):
        return {"get": {"responses": {"200": {"content": {"application/json": {"schema": schema}}}}}}

    spec = {
        "paths": {
            "/shown": answer({"type": "object", "properties": {
                "karma": {"type": "integer"},
                "voting": {"$ref": "#/components/schemas/V"},
                "gone": {"type": "integer"}}}),
            "/undescribed": answer({}),
        },
        "components": {"schemas": {
            "V": {"type": "object", "properties": {"remaining": {"type": "integer"}}}}},
    }
    shown = {"karma": 1, "voting": {"remaining": 2, "inner_only": 3}, "extra": 4}
    undescribed = {"anything": 1}
    return spec, shown, undescribed


def selftest(out=sys.stdout):
    spec, shown, undescribed = fixture()
    checks = []

    r = compare(spec, "/shown", shown)
    checks.append(("a name the schema lacks is reported",
                   r["carried_not_declared"] == ["extra"]))
    checks.append(("a declared name the answer omits is reported",
                   r["declared_not_carried"] == ["gone"]))
    checks.append(("a nested name is not counted at the top level",
                   "inner_only" not in r["carried_not_declared"] and "remaining" not in r["carried"]))

    r2 = compare(spec, "/shown", dict(shown, karma=1))
    checks.append(("dropping _provenance changes nothing when it is absent",
                   r2["carried_not_declared"] == ["extra"]))

    r3 = compare(spec, "/undescribed", undescribed)
    checks.append(("an answer with no declared schema is UNDESCRIBED, not a match",
                   r3["state"] == "UNDESCRIBED"))

    r4 = compare(spec, "/nowhere", undescribed)
    checks.append(("a route the contract does not carry is refused",
                   r4["state"] == "NO SUCH ROUTE"))

    bad = report([r3, r4], out)
    checks.append(("--check would refuse both silences", bad == 2))

    r5 = compare({"paths": {"/shown": {"get": {"responses": {"200": {"content": {
        "application/json": {"schema": {"type": "object", "properties": {}}}}}}}}}},
        "/shown", shown)
    checks.append(("a schema with an empty property dict is UNDESCRIBED",
                   r5["state"] == "UNDESCRIBED"))

    r6 = compare(spec, "/shown", {"remaining": 2, "inner_only": 3}, at=("voting",))
    checks.append(("a path into the schema compares the block the path names",
                   r6["state"] == "compared" and r6["carried_not_declared"] == ["inner_only"]
                   and r6["declared"] == {"remaining"}))

    r7 = compare(spec, "/shown", {"remaining": 2}, at=("absent",))
    checks.append(("a path the schema does not carry is refused, not compared against nothing",
                   r7["state"] == "NO SUCH FIELD"))

    checks.append(("a route named with its method is the same route",
                   same_route("GET /v1/me", "/v1/me")))
    checks.append(("two different routes are not the same route",
                   not same_route("GET /v1/me", "/v1/me/politics")))

    fails = [n for n, ok in checks if not ok]
    for n, ok in checks:
        out.write("%s %s\n" % ("ok  " if ok else "FAIL", n))
    out.write("%d checks, %d failed\n" % (len(checks), len(fails)))
    return 1 if fails else 0


def same_route(a, b):
    """A capture's provenance names its route the way a reader writes it, often
    with the method in front. The method is not part of the path."""
    def norm(s):
        parts = (s or "").split()
        return parts[-1] if parts else ""
    return norm(a) == norm(b)


def main(argv):
    if "--selftest" in argv:
        return selftest()
    spec_path = None
    if "--spec" in argv:
        spec_path = argv[argv.index("--spec") + 1]
    path = find_spec(spec_path)
    if path is None or not path.exists():
        sys.stderr.write("no OpenAPI document at %s (pass --spec)\n" % path)
        return 2
    if "--route" not in argv:
        sys.stderr.write("--route is required: a capture compared against the wrong route is two objects wearing one name\n")
        return 2
    route = argv[argv.index("--route") + 1]
    key = argv[argv.index("--key") + 1] if "--key" in argv else None
    at = tuple(argv[argv.index("--at") + 1].split(".")) if "--at" in argv and argv[argv.index("--at") + 1] else ()
    foreign = "--foreign-block" in argv
    files = [a for a in argv[1:] if a.endswith(".json") and a != spec_path]
    if not files:
        sys.stderr.write("no capture given\n")
        return 2
    spec = load_spec(path)
    routes = []
    problems = []
    for f in files:
        doc = json.loads(Path(f).read_text())
        prov = doc.get("_provenance") or {}
        claimed = prov.get("route")
        body = doc
        for part in (key.split(".") if key else []):
            body = body.get(part) if isinstance(body, dict) else None
        if body is None and key:
            problems.append("%s carries no %r block" % (f, key))
            continue
        if claimed and not same_route(claimed, route) and not foreign:
            problems.append("%s names its route %r, not %r (pass --foreign-block if this block belongs to another route's answer)" % (Path(f).name, claimed, route))
            continue
        r = compare(spec, route, body, at=at)
        r["file"] = Path(f).name
        routes.append(r)
    bad = report(routes)
    for p in problems:
        sys.stdout.write("problem: %s\n" % p)
    if "--check" in argv and (bad or problems):
        sys.stdout.write("CHECK=1\n")
        return 1
    if "--check" in argv:
        sys.stdout.write("CHECK=0\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
