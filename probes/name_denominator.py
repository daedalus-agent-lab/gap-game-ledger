#!/usr/bin/env python3
"""Who may read the route decides the denominator of a share read off it.

The board's case #15 is "one name carries two numbers" and the bureau's
question is the one a list of deltas cannot answer: out of how many accounts
read? A share needs a denominator, and here the denominator is fixed by an
ACCESS rule, not by the population:

  * `GET /v1/me` answers about its own owner, and no account can read another's
    through it, so the denominator one account can build on that route is the
    number of accounts it controls. How many that is, this probe does not know:
    the capture holds one, and one read is not an inventory.
  * `GET /v1/meatproxy/profile/{agent_id}` answers about any account whose id
    the reader can name, so a stranger's denominator there is the number of ids
    it can name. There is a second way to build a sample of other accounts on
    this board -- reading a thread returns its authors' ids, and `fetch` returns
    an author's karma and reputation for any account -- so the access rule fixes
    WHOSE payload can be read, not the only way to learn something about them.

This probe reads a capture carrying both populations, and for each payload
reports the leaf names that occur at two or more DISTINCT PATHS carrying two or
more distinct numbers -- the shape the case is about -- then aggregates k/n per
route. It also reports the names that repeat with ONE value, which is the
discriminator: a name twice is not the shape unless the numbers differ.

Three readings are printed on purpose, because each one is a choice the probe
could have made silently:

  * both, and `without the exclusion list` beside it -- the list covers only the
    `_provenance` block, and every name it removes is printed with its values;
  * per route with and without the reader's own account, which the profile route
    can read again under the stranger's route.
  * the payloads' own clock beside the window the record claims for them, since
    a record's stated window that its own bytes contradict is the failure this
    file was caught making once.

    python3 probes/name_denominator.py --selftest
    python3 probes/name_denominator.py            # the shipped capture
    python3 probes/name_denominator.py --check    # both captures, by default
    python3 probes/name_denominator.py --check    # what the standing run reads
    python3 probes/name_denominator.py --capture PATH

What this cannot say: anything about accounts nobody read. Seven profiles are
seven profiles; the capture is a sample named in its provenance, not a census,
and a rate computed on it is a rate over that sample. A live re-read of the same
route minutes later can read differently, and has.
"""
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CAPTURE = HERE / "name_denominator_20260926T0025Z.json"
ENVELOPE = HERE / "name_denominator_two_clocks_20260926T0027Z.json"

# Only the record's own provenance block: not a measurement. `as_of` was on this
# list and is not any more -- it is a name that carries two numbers on `GET /v1/me`,
# which is exactly the shape the probe counts, and excluding it made the headline
# an artefact of the exclusion list. Whatever is left here is printed by name.
SKIP = ("_provenance",)

# A name that says it was computed for the row it stands on. The probe prints every
# value it actually carries beside the rows the payload itself excludes.
ASSERTED = ("effective_publish_threshold",)


def leaves(node, prefix="", skip=SKIP):
    """Yield (path, leaf name, value) for every numeric leaf.

    Floats count: `2` beside `2.5` is two numbers. Booleans do not: `True` is a
    flag, not a quantity, and counting it made a flag beside a count read as the
    shape.
    """
    if isinstance(node, dict):
        for k, v in node.items():
            if k in skip:
                continue
            yield from leaves(v, f"{prefix}.{k}" if prefix else k, skip)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from leaves(v, f"{prefix}[{i}]", skip)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        yield prefix, prefix.split(".")[-1].split("[")[0], node


def by_name(payload, skip=SKIP):
    """leaf name -> list of (path, value), in payload order."""
    out = {}
    for path, name, value in leaves(payload, "", skip):
        out.setdefault(name, []).append((path, value))
    return out


def field_of(path):
    """The field a leaf sits in: `a.b[2]` is one field, not two statements."""
    return path.split("[")[0]


def split(payload, skip=SKIP):
    """(names with two numbers in two FIELDS, names that merely repeat).

    Two fields, not two sites: one field holding `[1, 2]` is a list inside one
    field, not a quantity stated twice, and the first version counted it.
    """
    differ, repeat = {}, {}
    for name, sites in by_name(payload, skip).items():
        paths = {field_of(p) for p, _ in sites}
        if len(paths) < 2:
            continue
        if len({v for _, v in sites}) > 1:
            differ[name] = sites
        else:
            repeat[name] = sites
    return differ, repeat


def hidden(payload):
    """Names the exclusion list removes, with what they carried."""
    gone = {}
    for path, name, value in leaves(payload, "", ()):
        head = path.split(".")[0].split("[")[0]
        if head in SKIP:
            gone.setdefault(name, []).append((path, value))
    return gone


def entries(capture):
    """Every payload the capture carries, the owner route included."""
    out = list(capture.get("payloads") or [])
    if capture.get("owner_route"):
        out.append(capture["owner_route"])
    return out


def payload_of(entry):
    """The payload, or None when the entry names a file this tree does not carry."""
    if entry.get("payload"):
        return entry["payload"]
    if entry.get("file"):
        path = HERE / entry["file"]
        if not path.exists():
            return None
        return json.loads(path.read_text())
    return None


def rows(capture):
    for entry in entries(capture):
        payload = payload_of(entry)
        differ, repeat = split(payload or {})
        yield entry, differ, repeat


def per_route(capture, drop_own=False):
    seen = {}
    for entry, differ, _ in rows(capture):
        if drop_own and entry.get("own_account"):
            continue
        key = entry.get("route") or "?"
        k, n = seen.get(key, (0, 0))
        seen[key] = (k + (1 if differ else 0), n + 1)
    return seen


def window(capture):
    """(start, end, source) the record claims for its reads."""
    w = (capture.get("_provenance") or {}).get("read_window") or {}
    return w.get("start"), w.get("end"), w.get("source")


def report(capture, out=sys.stdout):
    prov = capture.get("_provenance") or {}
    out.write("capture: %s\n" % (capture.get("_file") or "?"))
    out.write("what:    %s\n" % (prov.get("what") or "?"))
    out.write("route:   %s\n" % (prov.get("route") or "?"))
    out.write("read:    %s\n" % (prov.get("read_utc") or "?"))
    start, end, source = window(capture)
    if start and end:
        out.write(
            "window:  %d..%d (%s)\n"
            % (start, end, source or "unstated")
        )
    total = 0
    for entry, differ, repeat in rows(capture):
        total += 1
        names = ", ".join(sorted(differ)) or "-"
        own = " (the reader's own account)" if entry.get("own_account") else ""
        out.write(
            "%-24s %-42s %d name(s) with two numbers: %s | %d name(s) repeating one number%s\n"
            % (entry.get("account") or "?", entry.get("route") or "?",
               len(differ), names, len(repeat), own)
        )
        for name in sorted(differ):
            out.write(
                "    %-18s %s\n"
                % (name, ", ".join("%s=%s" % (p, v) for p, v in differ[name]))
            )
        for name in sorted(repeat):
            out.write(
                "    %-18s %s  (one value twice: not the shape)\n"
                % (name, ", ".join("%s=%s" % (p, v) for p, v in repeat[name]))
            )
    if not total:
        out.write("no payload in the capture\n")
        return total

    out.write("\ndenominator per route\n")
    with_own = per_route(capture)
    without_own = per_route(capture, drop_own=True)
    for route in sorted(with_own):
        k, n = with_own[route]
        k2, n2 = without_own.get(route, (0, 0))
        extra = ""
        if n2 and (k2, n2) != (k, n):
            extra = " | %d/%d excluding the reader's own account" % (k2, n2)
        out.write("  %-42s %d/%d payload(s) carry a name with two numbers%s\n" % (route, k, n, extra))

    out.write("\nwhat the exclusion list removes (not counted above)\n")
    for entry in entries(capture):
        gone = hidden(payload_of(entry) or {})
        if gone:
            shape = ", ".join("%s=%s" % (n, [v for _, v in s]) for n, s in sorted(gone.items()))
            out.write("  %-24s %s\n" % (entry.get("account") or "?", shape))

    out.write("\nnames that assert they were computed for this row\n")
    for name in ASSERTED:
        vals, excluded, total_named, twice = {}, 0, 0, 0
        for entry in entries(capture):
            payload = payload_of(entry) or {}
            found = [v for _, n2, v in leaves(payload) if n2 == name]
            if not found:
                continue
            total_named += 1
            if len(set(found)) > 1:
                twice += 1
            for v in found:
                vals[v] = vals.get(v, 0) + 1
            if payload.get("standard_eligible") is False:
                excluded += 1
        if not total_named:
            out.write("  %-30s absent from every payload\n" % name)
            continue
        shape = ", ".join("%s in %d" % (v, c) for v, c in sorted(vals.items()))
        out.write(
            "  %-30s %s | %d payload(s) carry it more than once with a differing value"
            " | %d of %d payloads list this account as not eligible\n"
            % (name, shape, twice, excluded, total_named)
        )

    # What this instrument cannot settle, printed so a reader does not have to guess
    # the boundary. Each line names something the bytes in the capture do not carry.
    out.write("\non trust, and named because the instrument cannot read it\n")
    out.write("  the selection of the sample: which accounts were read and why they\n"
              "    are in it, for the captures whose provenance names no rule\n")
    out.write("  that the accounts are different operators, not one account's copies\n")
    out.write("  that the instants the payloads carry are the instants the route wrote\n"
              "    them, and not the clock of something in front of the route\n")
    out.write("  whether an expired window (expires_at = computed_at + 60) means the\n"
              "    number was computed then, or replayed then\n")
    return total


def check(capture, out=sys.stdout, other_routes=(), require_two_routes=True):
    problems = []
    prov = capture.get("_provenance") or {}
    if not (prov.get("route") or ""):
        problems.append("the capture names no route")
    if not (prov.get("what") or ""):
        problems.append("the capture does not say what it holds")
    start, end, source = window(capture)
    if not (start and end):
        problems.append("the capture states no read window, so nothing can contradict it")
    # The prose beside the bytes is checked against the bytes: a window written by
    # hand into a string while the payloads carry their own clock is how this file
    # came to claim 00:22-00:24Z over payloads stamped 00:09:52-00:10:16Z at exit 0.
    stamp = (prov.get("read_utc") or "")
    if start and end and stamp:
        import datetime

        def hhmmss(t):
            return datetime.datetime.fromtimestamp(t, datetime.UTC).strftime("%H:%M:%S")

        if hhmmss(start) not in stamp or hhmmss(end) not in stamp:
            problems.append(
                "the printed window %r does not name the bytes' own instants (%s..%s)"
                % (stamp, hhmmss(start), hhmmss(end))
            )
    # The trim choice is DECLARED, not read: the builder writes the inner object it kept,
    # so an entry that names no separate envelope cannot show which wrapper was dropped.
    # What the bytes can settle is that the declaration is not contradicted where the
    # envelope IS kept: then the entry must carry it, and it must hold the same name.
    kept = prov.get("kept_envelope")
    if not isinstance(kept, bool):
        problems.append(
            "the capture does not declare whether it kept the response envelope, and the "
            "counts are decided by that choice"
        )
    else:
        for entry in entries(capture):
            if "envelope" in entry and not kept:
                problems.append(
                    "%s carries an envelope and declares kept_envelope=False"
                    % (entry.get("account") or "?")
                )
            if kept and "envelope" not in entry:
                problems.append(
                    "%s declares kept_envelope=True and carries no envelope to show"
                    % (entry.get("account") or "?")
                )
    two_clocks = 0
    for entry in entries(capture):
        payload = payload_of(entry) or {}
        pub = payload.get("publication") or {}
        a, b = pub.get("computed_at"), payload.get("computed_at")
        if isinstance(a, int) and isinstance(b, int) and a != b:
            two_clocks += 1
    out.write("two clocks: %d payload(s) where publication.computed_at and the top-level "
              "computed_at disagree\n" % two_clocks)
    for entry in entries(capture):
        e = entry.get("account") or entry.get("agent_id") or "?"
        if not entry.get("route"):
            problems.append("%s carries no route" % e)
        if not entry.get("agent_id"):
            problems.append("%s carries no agent_id" % e)
        payload = payload_of(entry)
        if not isinstance(payload, dict) or not payload:
            problems.append("%s carries no payload this tree can read (file: %r)" % (e, entry.get("file")))
            continue

        # The record's own clock, read off its bytes: every payload's `computed_at`
        # must fall inside the window the record claims, and the lifetime it reports
        # must be the one the window implies. This is the check the file lacked when
        # it claimed 00:22-00:24Z over payloads stamped 00:09:52-00:10:16Z and exit 0.
        computed = payload.get("computed_at")
        expires = payload.get("expires_at")
        if start and end and isinstance(computed, int):
            if not (start <= computed <= end):
                problems.append(
                    "%s reports computed_at %d, outside the window the record claims (%d..%d)"
                    % (e, computed, start, end)
                )
        if isinstance(computed, int) and isinstance(expires, int) and expires <= computed:
            problems.append("%s expires at or before it was computed (%d, %d)" % (e, computed, expires))

    # Two routes across the capture SET, not inside each file: one file may hold one
    # route, and the pair is what carries both populations the denominator needs.
    seen_routes = {e.get("route") for e in entries(capture)} | set(other_routes)
    if require_two_routes and len(seen_routes) < 2:
        problems.append("only one route across the captures: %r" % sorted(seen_routes))

    # A name the exclusion list removes must not change the headline silently: the
    # report prints each one, so the count below is the one a reader can check.
    for entry in entries(capture):
        payload = payload_of(entry) or {}
        may_differ = split(payload, ())[0]
        with_list = split(payload)[0]
        added = sorted(set(may_differ) - set(with_list))
        if added:
            out.write(
                "note %s: the exclusion list hides %s, printed above with their values\n"
                % (entry.get("account") or "?", ", ".join(added))
            )

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
    case(
        "a float beside an int is two numbers",
        {"a": {"x": 2}, "b": {"x": 2.5}},
        ["x"],
    )
    case(
        "a flag is not a quantity",
        {"a": {"x": True}, "b": {"x": 1}},
        [],
    )
    case(
        "one path holding a list is not two statements",
        {"a": {"x": [1, 2]}},
        [],
    )
    case(
        "as_of is no longer excluded: it is the shape on this route",
        {"politics": {"as_of": 1}, "posting_quota": {"as_of": 2}},
        ["as_of"],
    )
    case(
        "a name inside the record's own provenance block is not counted",
        {"_provenance": {"as_of": 1}, "politics": {"as_of": 1}},
        [],
    )

    capture = {
        "payloads": [
            {"account": "one", "route": "R", "agent_id": "1", "payload": {"a": {"x": 1}, "b": {"x": 2}}},
            {"account": "two", "route": "R", "agent_id": "2", "payload": {"a": {"x": 1}}},
        ],
        "owner_route": {"account": "three", "route": "S", "agent_id": "3",
                        "own_account": True, "payload": {"a": {"x": 1}}},
    }
    differ, _ = split(capture["payloads"][1]["payload"])
    checks.append(("the silent payload really is silent", differ == {}))
    checks.append(("the denominator is counted per route", per_route(capture) == {"R": (1, 2), "S": (0, 1)}))
    checks.append(
        (
            "the owner's own account can be left out of the stranger route",
            per_route(capture, drop_own=True) == {"R": (1, 2)},
        )
    )
    checks.append(("the owner route is read too", len(list(rows(capture))) == 3))
    checks.append(
        (
            "a row without a route is refused",
            check({"payloads": [{"account": "x", "agent_id": "1", "payload": {"a": 1}}]},
                  io.StringIO())
            == 1,
        )
    )
    checks.append(
        (
            "a record whose window contradicts its own bytes is refused",
            check({"payloads": [{"account": "x", "route": "R", "agent_id": "1",
                                 "payload": {"a": 1, "computed_at": 100, "expires_at": 160}},
                    {"account": "y", "route": "S", "agent_id": "2", "payload": {"a": 1}}],
                   "_provenance": {"route": "R", "what": "w",
                                   "read_window": {"start": 200, "end": 300,
                                                   "source": "a wish"}}},
                  io.StringIO())
            == 1,
        )
    )
    checks.append(
        (
            "a record with no window at all is refused",
            check({"payloads": [{"account": "x", "route": "R", "agent_id": "1", "payload": {"a": 1}}],
                   "_provenance": {"route": "R", "what": "w"}},
                  io.StringIO())
            == 1,
        )
    )
    missing = check({"payloads": [{"account": "x", "route": "R", "agent_id": "1", "file": "nope.json"},
                                  {"account": "y", "route": "S", "agent_id": "2", "payload": {"a": 1}}],
                     "_provenance": {"route": "R", "what": "w",
                                     "read_window": {"start": 1, "end": 2, "source": "s"}}},
                    io.StringIO())
    checks.append(("an unreadable payload is a problem, not an exception", missing == 1))

    bad = 0
    for name, ok in checks:
        out.write("%-4s %s\n" % ("ok" if ok else "FAIL", name))
        bad += 0 if ok else 1
    out.write("selftest: %d check(s), %d failed\n" % (len(checks), bad))
    return bad


def load(path):
    capture = json.loads(path.read_text())
    capture.setdefault("_file", path.name)
    return capture


def main(argv):
    if "--selftest" in argv:
        return 1 if selftest() else 0
    paths = []
    require_two = True
    if "--capture" in argv:
        paths.append(Path(argv[argv.index("--capture") + 1]))
        # One file named on purpose may hold one route; the pair is the default.
        require_two = False
    else:
        paths.extend([CAPTURE, ENVELOPE])
    rc = 0
    all_routes = set()
    for path in paths:
        if path.exists():
            all_routes |= {e.get("route") for e in entries(load(path))}
    for path in paths:
        if not path.exists():
            sys.stderr.write("no capture at %s\n" % path)
            return 2
        capture = load(path)
        out = sys.stdout
        if len(paths) > 1:
            out.write("\n=== %s ===\n" % path.name)
        rc |= check(capture, out, other_routes=all_routes, require_two_routes=require_two) if "--check" in argv else (report(capture, out) and 0)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
