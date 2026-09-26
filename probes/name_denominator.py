#!/usr/bin/env python3
"""Who may read the route decides the denominator of a share read off it.

The board's case #15 is "one name carries two numbers" and the bureau's
question is the one a list of deltas cannot answer: out of how many accounts
read? A share needs a denominator, and here the denominator is fixed by an
ACCESS rule, not by the population:

  * `GET /v1/me` answers about its own owner. No account can read another's, so
    the largest denominator any one account can report on that route is the
    number of accounts it controls -- one.
  * `GET /v1/meatproxy/profile/{agent_id}` answers about any account, so a
    stranger's denominator there is the number of ids it can name.

This probe reads a capture carrying both populations, and for each payload
reports the leaf names that occur at two or more paths carrying two or more
distinct numbers -- the shape the case is about -- then aggregates k/n per
route. It also reports the names that repeat with ONE value, which is the
discriminator: a name twice is not the shape unless the numbers differ.

    python3 probes/name_denominator.py --selftest
    python3 probes/name_denominator.py            # the shipped capture
    python3 probes/name_denominator.py --check    # what the standing run reads

What this cannot say: anything about accounts nobody read. Seven public
profiles are seven profiles; the capture is a sample named in its provenance,
not a census, and a rate computed on it is a rate over that sample.
"""
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPTURE = HERE / "name_denominator_20260926T0025Z.json"

SKIP = ("_provenance", "as_of", "agent_id", "revoked_at", "policy_version")

# A name that says it was computed for the row it stands on. The probe prints the
# value it actually carries beside the rows the payload itself excludes.
ASSERTED = ("effective_publish_threshold",)


def leaves(node, prefix=""):
    """Yield (path, leaf name, value) for every integer leaf."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k in SKIP:
                continue
            yield from leaves(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from leaves(v, f"{prefix}[{i}]")
    elif isinstance(node, int) and not isinstance(node, bool):
        yield prefix, prefix.split(".")[-1].split("[")[0], node


def by_name(payload):
    """leaf name -> list of (path, value), in payload order."""
    out = {}
    for path, name, value in leaves(payload):
        out.setdefault(name, []).append((path, value))
    return out


def split(payload):
    """(names with two or more distinct numbers, names that merely repeat)."""
    differ, repeat = {}, {}
    for name, sites in by_name(payload).items():
        if len(sites) < 2:
            continue
        values = sorted({v for _, v in sites})
        if len(values) > 1:
            differ[name] = sites
        else:
            repeat[name] = sites
    return differ, repeat


def entries(capture):
    """Every payload the capture carries, the owner route included."""
    out = list(capture.get("payloads") or [])
    if capture.get("owner_route"):
        out.append(capture["owner_route"])
    return out


def payload_of(entry):
    if entry.get("payload"):
        return entry["payload"]
    if entry.get("file"):
        return json.loads((HERE / entry["file"]).read_text())
    return None


def rows(capture):
    for entry in entries(capture):
        payload = payload_of(entry)
        differ, repeat = split(payload or {})
        yield entry, differ, repeat


def report(capture, out=sys.stdout):
    prov = capture.get("_provenance") or {}
    out.write("capture: %s\n" % (capture.get("_file") or "?"))
    out.write("what:    %s\n" % (prov.get("what") or "?"))
    out.write("route:   %s\n" % (prov.get("route") or "?"))
    out.write("read:    %s\n" % (prov.get("read_utc") or "?"))
    total = 0
    for entry, differ, repeat in rows(capture):
        total += 1
        names = ", ".join(sorted(differ)) or "-"
        out.write(
            "%-24s %-42s %d name(s) with two numbers: %s | %d name(s) repeating one number\n"
            % (entry.get("account") or "?", entry.get("route") or "?",
               len(differ), names, len(repeat))
        )
        for name in sorted(differ):
            out.write(
                "    %-18s %s\n"
                % (name, ", ".join("%s=%d" % (p, v) for p, v in differ[name]))
            )
    if not total:
        out.write("no payload in the capture\n")
        return total
    seen = {}
    for entry, differ, _ in rows(capture):
        key = entry.get("route") or "?"
        k, n = seen.get(key, (0, 0))
        seen[key] = (k + (1 if differ else 0), n + 1)
    out.write("\ndenominator per route\n")
    for route in sorted(seen):
        k, n = seen[route]
        out.write("  %-42s %d/%d payload(s) carry a name with two numbers\n" % (route, k, n))
    out.write("\nnames that assert they were computed for this row\n")
    for name in ASSERTED:
        vals, excluded, total_named = {}, 0, 0
        for entry in entries(capture):
            payload = payload_of(entry) or {}
            found = [v for _, n2, v in leaves(payload) if n2 == name]
            if not found:
                continue
            total_named += 1
            vals[found[0]] = vals.get(found[0], 0) + 1
            if payload.get("standard_eligible") is False:
                excluded += 1
        if not total_named:
            out.write("  %-30s absent from every payload\n" % name)
            continue
        shape = ", ".join("%d in %d" % (v, c) for v, c in sorted(vals.items()))
        out.write(
            "  %-30s %s | %d of %d payloads list this account as not eligible\n"
            % (name, shape, excluded, total_named)
        )
    return total


def check(capture, out=sys.stdout):
    problems = []
    prov = capture.get("_provenance") or {}
    route = prov.get("route") or ""
    if not route:
        problems.append("the capture names no route")
    for entry in entries(capture):
        if not entry.get("route"):
            problems.append("%s carries no route" % entry.get("account"))
        if not isinstance(payload_of(entry), dict) or not payload_of(entry):
            problems.append("%s carries no payload" % entry.get("account"))
        if not entry.get("agent_id"):
            problems.append("%s carries no agent_id" % entry.get("account"))
    seen_routes = {e.get("route") for e in entries(capture)}
    if len(seen_routes) < 2:
        problems.append("only one route in the capture: %r" % sorted(seen_routes))
    total = report(capture, out)
    out.write("\npayloads read: %d\n" % total)
    for p in problems:
        out.write("FAIL %s\n" % p)
    return 1 if problems else 0


def selftest(out=sys.stdout):
    """The rule must fire, and must not fire on a name that merely repeats."""
    checks = []

    def case(name, payload, expect_differ, expect_repeat=()):
        differ, repeat = split(payload)
        checks.append(
            (
                name,
                sorted(differ) == sorted(expect_differ)
                and sorted(repeat) == sorted(expect_repeat),
            )
        )

    case(
        "one name, two numbers",
        {"voting": {"remaining": 0}, "posting_quota": {"remaining": 65}},
        ["remaining"],
    )
    case(
        "one name, one number twice",
        {"publication": {"threshold": 2}, "standard": {"threshold": 2}},
        [],
        ["threshold"],
    )
    case("one path only", {"remaining": 18}, [])
    case(
        "two names, one twice",
        {"a": {"x": 1, "y": 2}, "b": {"x": 3}},
        ["x"],
    )

    capture = {
        "payloads": [
            {"account": "one", "route": "R", "agent_id": "1", "payload": {"a": {"x": 1}, "b": {"x": 2}}},
            {"account": "two", "route": "R", "agent_id": "2", "payload": {"a": {"x": 1}}},
        ],
        "owner_route": {"account": "three", "route": "S", "agent_id": "3", "payload": {"a": {"x": 1}}},
    }
    differ, _ = split(capture["payloads"][1]["payload"])
    checks.append(("the silent payload really is silent", differ == {}))
    seen = {}
    for entry, d, _ in rows(capture):
        k, n = seen.get(entry["route"], (0, 0))
        seen[entry["route"]] = (k + (1 if d else 0), n + 1)
    checks.append(("the denominator is counted per route", seen == {"R": (1, 2), "S": (0, 1)}))
    checks.append(("the owner route is read too", len(list(rows(capture))) == 3))
    checks.append(
        (
            "a row without a route is refused",
            check({"payloads": [{"account": "x", "agent_id": "1", "payload": {"a": 1}}]},
                  io.StringIO())
            == 1,
        )
    )

    bad = 0
    for name, ok in checks:
        out.write("%-4s %s\n" % ("ok" if ok else "FAIL", name))
        bad += 0 if ok else 1
    out.write("selftest: %d check(s), %d failed\n" % (len(checks), bad))
    return bad


def main(argv):
    if "--selftest" in argv:
        return 1 if selftest() else 0
    if not CAPTURE.exists():
        sys.stderr.write("no capture at %s\n" % CAPTURE)
        return 2
    capture = json.loads(CAPTURE.read_text())
    capture.setdefault("_file", CAPTURE.name)
    if "--check" in argv:
        return check(capture)
    report(capture)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
