#!/usr/bin/env python3
"""Two vote-maturation clocks: one a field with no sentence, one a sentence with no field.

`GET /v1/meatproxy/capabilities` answers `publication.standard.settlement_seconds`
(43200 live) -- an integer whose schema node carries no description at all.
`GET /v1/me` answers `voting.reputation`, whose meaning is stated in prose only:
"Votes >=48h old, current active peers >=7days old, ..." (172800 seconds, a number
the document never writes as digits).

So the pair of windows is visible only to a reader who reads fields AND sentences.
A reader who greps the document for a number finds the meatproxy clock's name and
no value; a reader who greps it for "48 hours" finds the /v1/me clock's meaning and
no field. Both clocks are real and they are four times apart.

This probe reads the document as both kinds of reader and requires that each clock
be found in exactly one of the two forms:

  C1 the numeric clock is declared as a field and carries no sentence
  C2 neither window is written as a literal number in the document
  C3 the other clock is stated as a duration in a sentence, and parses to 172800
  C4 the /v1/me tree carries exactly one maturation clock; every other duration
     there is an account-age gate with a reason (an unexplained duration fails)
  C5 the two windows differ (with --live, the live number is the first of them)
  C6 the live payload's two names for the meatproxy window agree

`--selftest` mutates the document (and the live payload) in eight ways and requires
every mutation to be refused. A clause nothing can break is a sentence.

Usage:
  python3 probes/two_clocks_contract.py --spec ../spec/openapi-1.17.3.json \
      --live probes/meatproxy_capabilities_20260926T0110Z.json --check
  python3 probes/two_clocks_contract.py --spec ../spec/openapi-1.17.3.json --selftest
"""

import argparse
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SPEC = HERE.parent.parent / "spec" / "openapi-1.17.3.json"

ME_SIDE = "/v1/me"
FIELD = "settlement_seconds"
FIELD_OWNER = "MeatproxyPermissions"
SENTENCE_OWNER = "VotingAllowance"
SENTENCE_FIELD = "reputation"
EXPECTED_SENTENCE_SECONDS = 172800          # 48 hours, the /v1/me clock
NOT_WRITTEN = ("43200", "172800")           # neither window as digits

# A duration in prose: "48 hours", "48h", ">=7days", "no 48-hour vote delay".
DURATION = re.compile(r"(\d+)\s*(?:-\s*)?(hours?|h|days?|d|minutes?|min)\b", re.I)
UNIT_SECONDS = {"h": 3600, "hour": 3600, "hours": 3600,
                "d": 86400, "day": 86400, "days": 86400,
                "min": 60, "minute": 60, "minutes": 60}

# Every duration reachable from the /v1/me response that is NOT the maturation
# clock, with the reason it is not. An unexplained duration fails C4.
AGE_GATES = {
    "/v1/me/pinning": "veteran qualification gate: age >=72 hours, karma, peers",
    "/v1/me/pinning/eligible_at": "the instant of that age gate, not a vote clock",
    "/v1/me/voting/can_downvote": "the same 72-hour age gate, one field further",
    "/v1/me/voting/mature_negative_peers": "peer age >=7days; the field says so",
    "/v1/me/voting/recovery_balance": "peer age >=7days at cast, no vote delay",
    "/v1/me/posting_quota/standing": "enum prose quoting the 72-hour gate",
}
# The single maturation clock on the /v1/me side.
MATURATION_FIELD = "/v1/me/voting/" + SENTENCE_FIELD


def deref(spec, node, depth=0):
    schemas = spec["components"]["schemas"]
    while isinstance(node, dict) and "$ref" in node and depth < 12:
        node = schemas[node["$ref"].split("/")[-1]]
        depth += 1
    return node


def me_schema(spec):
    node = spec["paths"][ME_SIDE]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    return deref(spec, node)


def walk_durations(spec, node, path="", out=None, depth=0):
    """Every node reachable from the /v1/me 200 schema that states a duration."""
    if out is None:
        out = []
    if depth > 8:
        return out
    node = deref(spec, node)
    if not isinstance(node, dict):
        return out
    for key, raw in (node.get("properties") or {}).items():
        child = deref(spec, raw)
        here = path + "/" + key
        text = " ".join(str(child.get(k, "")) for k in ("description", "title"))
        found = [m.group(0).strip() for m in DURATION.finditer(text)]
        if found:
            out.append({"path": here, "seconds": duration_seconds(text),
                        "forms": found, "description": child.get("description", "")})
        walk_durations(spec, child, here, out, depth + 1)
    if node.get("items"):
        walk_durations(spec, deref(spec, node["items"]), path + "[]", out, depth + 1)
    return out


def duration_seconds(text):
    """The largest duration phrase in `text`, in seconds (0 if none)."""
    best = 0
    for m in DURATION.finditer(text):
        unit = m.group(2).lower()
        best = max(best, int(m.group(1)) * UNIT_SECONDS[unit])
    return best


NOUN = re.compile(r"\b(votes?|reputation|peers?|accounts?)\b", re.I)


def clock_phrases(text):
    """Duration phrases in prose, each tagged by the noun its clause is about.

    "Votes >=48h old, current active peers >=7days old" carries two durations and
    one noun each: the vote clock and a peer-age gate. Taking the largest phrase
    would read the peer gate as the clock, which is the mistake this function is
    here to make impossible.
    """
    rows = []
    for clause in re.split(r"[.;]", text):
        nouns_in_clause = NOUN.findall(clause)
        for m in DURATION.finditer(clause):
            before = NOUN.findall(clause[:m.start()])
            noun = (before[-1] if before else (nouns_in_clause[-1] if nouns_in_clause else "")).lower()
            rows.append({"noun": noun, "phrase": m.group(0).strip(),
                         "seconds": int(m.group(1)) * UNIT_SECONDS[m.group(2).lower()],
                         "clause": clause.strip()[:70]})
    return rows


def settlement_node(spec):
    return (spec["components"]["schemas"].get(FIELD_OWNER, {}).get("properties") or {}).get(FIELD)


def sentence_node(spec):
    return (spec["components"]["schemas"].get(SENTENCE_OWNER, {}).get("properties") or {}).get(SENTENCE_FIELD)


def live_window(live):
    """The meatproxy window as the live payload states it: two names, one number."""
    if not live:
        return None
    publication = (live.get("publication") or {})
    standard = (publication.get("standard") or {})
    limits = (live.get("limits") or {})
    named = {"publication.standard." + FIELD: standard.get(FIELD)}
    camel = "settlementSeconds"
    if camel in limits:
        named["limits." + camel] = limits.get(camel)
    return named


def report(spec, live=None):
    node = settlement_node(spec) or {}
    sent = sentence_node(spec) or {}
    rows = {
        "numeric_field": {
            "declared_at": "components.schemas.%s.properties.%s" % (FIELD_OWNER, FIELD),
            "type": node.get("type"),
            "has_description": "description" in node,
            "live_value": (live_window(live) or {}).get("publication.standard." + FIELD),
        },
        "prose_clock": {
            "declared_at": "components.schemas.%s.properties.%s.description" % (SENTENCE_OWNER, SENTENCE_FIELD),
            "phrases": clock_phrases(sent.get("description", "")),
            "has_numeric_field": "const" in sent or "maximum" in sent,
        },
        "live_names_for_the_numeric_clock": live_window(live),
        "durations_in_the_me_tree": walk_durations(spec, me_schema(spec), ME_SIDE),
        "literals_in_the_document": {n: (n in json.dumps(spec)) for n in NOT_WRITTEN},
    }
    return rows


def check(spec, live=None, ages=AGE_GATES):
    """Every clause as (name, ok, detail). `ages` is the reason list for the
    durations that are account-age gates rather than vote clocks."""
    raw = json.dumps(spec)
    node = settlement_node(spec)
    sentence = (sentence_node(spec) or {}).get("description", "")
    durations = walk_durations(spec, me_schema(spec), ME_SIDE)
    gates = [r for r in durations if r["path"] in ages]
    unexplained = [r["path"] for r in durations if r["path"] not in ages
                   and r["path"] != MATURATION_FIELD]
    maturation = [r for r in durations if r["path"] == MATURATION_FIELD]
    sentences = clock_phrases(sentence)
    vote_clocks = [p for p in sentences if p["noun"].startswith("vote")]
    peer_gates = [p for p in sentences if p["noun"].startswith("peer")]
    sentence_seconds = vote_clocks[0]["seconds"] if len(vote_clocks) == 1 else 0
    named = live_window(live) or {}
    window = named.get("publication.standard." + FIELD)

    clauses = []
    clauses.append((
        "numeric_clock_is_a_field_without_a_sentence",
        isinstance(node, dict) and node.get("type") == "integer" and "description" not in node,
        "settlement_seconds: type=%r has_description=%r" % (
            (node or {}).get("type"), isinstance(node, dict) and "description" in node)))
    clauses.append((
        "no_window_is_written_as_a_number",
        all(n not in raw for n in NOT_WRITTEN),
        "literals found: %s" % [n for n in NOT_WRITTEN if n in raw]))
    clauses.append((
        "the_other_clock_is_a_sentence",
        len(vote_clocks) == 1 and sentence_seconds == EXPECTED_SENTENCE_SECONDS
        and peer_gates and all(p["seconds"] != EXPECTED_SENTENCE_SECONDS for p in peer_gates),
        "vote-clause clock=%s peer-age clauses=%s" % (
            [p["phrase"] + " in " + p["clause"] for p in vote_clocks],
            [p["phrase"] for p in peer_gates])))
    clauses.append((
        "one_maturation_clock_in_the_me_tree",
        len(maturation) == 1 and not unexplained,
        "maturation=%s unexplained=%s age_gate_rows=%d" % (
            [r["path"] for r in maturation], unexplained, len(gates))))
    clauses.append((
        "the_two_windows_differ",
        window is None or (sentence_seconds and window != sentence_seconds),
        "meatproxy=%r /v1/me=%d" % (window, sentence_seconds)))
    named = named or {}
    if named:
        clauses.append((
            "the_live_names_agree",
            len(set(named.values())) == 1 and isinstance(list(named.values())[0], int),
            json.dumps(named)))
    return clauses


def selftest(spec, live=None):
    """Each mutation must be refused by the clause it targets.

    A mutation is refused vacuously if the baseline already fails, so the baseline
    is required to be green first and every mutation names the clause that must
    fire. Naming only 'something failed' would repeat the mistake this selftest
    exists to catch.
    """
    baseline = [c for c, good, _ in check(spec, live) if not good]
    if baseline:
        print("FAIL baseline is not green: %s" % baseline)
        return 1
    ok, why = [], []

    def mutate(name, fn, want_clause, ages=AGE_GATES):
        d = copy.deepcopy(spec)
        lv = copy.deepcopy(live)
        fn(d, lv)
        fired = [c for c, good, _ in check(d, lv, ages=ages) if not good]
        return name, want_clause, (want_clause in fired), fired

    mutations = []
    mutations.append(mutate("the field is given a description", lambda d, l: settlement_node(d).update(
        description="votes settle here"), "numeric_clock_is_a_field_without_a_sentence"))
    mutations.append(mutate("the field is made a string", lambda d, l: settlement_node(d).update(
        type="string"), "numeric_clock_is_a_field_without_a_sentence"))
    mutations.append(mutate("the field is deleted", lambda d, l: d["components"]["schemas"]
                            [FIELD_OWNER]["properties"].pop(FIELD),
                            "numeric_clock_is_a_field_without_a_sentence"))
    mutations.append(mutate("the sentence is rewritten to 24 hours", lambda d, l: sentence_node(d).update(
        description=sentence_node(d)["description"].replace("48h", "24h")),
        "the_other_clock_is_a_sentence"))
    mutations.append(mutate("the sentence is deleted", lambda d, l: sentence_node(d).pop("description"),
                            "the_other_clock_is_a_sentence"))
    mutations.append(mutate("the number is written into the document as a const",
                            lambda d, l: settlement_node(d).update(const=43200),
                            "no_window_is_written_as_a_number"))
    mutations.append(mutate("a second maturation clock is added to the /v1/me tree",
                            lambda d, l: d["components"]["schemas"]["VotingAllowance"]["properties"]
                            .update(settled_after_hours={"type": "integer", "description":
                                    "Reputation from a vote settles after 6 hours."}),
                            "one_maturation_clock_in_the_me_tree"))
    mutations.append(mutate("an age gate loses its reason",
                            lambda d, l: d,
                            "one_maturation_clock_in_the_me_tree",
                            ages={k: v for k, v in AGE_GATES.items()
                                  if k != "/v1/me/pinning/eligible_at"}))
    if live is not None:
        mutations.append(mutate("the live payload makes the two windows equal",
                                lambda d, l: l["publication"]["standard"].update(settlement_seconds=172800),
                                "the_two_windows_differ"))
        mutations.append(mutate("the live payload's two names disagree",
                                lambda d, l: l["limits"].update(settlementSeconds=86400),
                                "the_live_names_agree"))

    passed = 0
    for name, want, fired, fired_all in mutations:
        if fired:
            passed += 1
            print("ok  refused by %s: %s" % (want, name))
        else:
            print("FAIL accepted: %s (target %s; clauses that did fire: %s)" % (name, want, fired_all))
    print("selftest: %d check(s), %d failed" % (len(mutations), len(mutations) - passed))
    return 0 if passed == len(mutations) else 1


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", default=str(DEFAULT_SPEC))
    ap.add_argument("--live", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args(argv)

    spec_path = Path(args.spec)
    if not spec_path.exists():
        print("MISSING spec %s" % spec_path, file=sys.stderr)
        return 2
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    live = json.loads(Path(args.live).read_text(encoding="utf-8")) if args.live else None

    if args.selftest:
        return selftest(spec, live)

    if args.report or not args.check:
        print(json.dumps(report(spec, live), ensure_ascii=False, indent=1))

    if args.check:
        failed = 0
        for name, good, detail in check(spec, live):
            print("%s %s %s" % ("ok  " if good else "FAIL", name, detail))
            failed += 0 if good else 1
        print("%d clause(s), %d failed" % (len(check(spec, live)), failed))
        return 1 if failed else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
