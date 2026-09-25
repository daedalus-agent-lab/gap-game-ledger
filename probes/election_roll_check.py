#!/usr/bin/env python3
"""Recompute a published election tally from the published ballot roll.

An election result is a claim the board prints, and the ballots behind it are a
claim the board also prints. The two can be checked against each other by anyone
with the roll and the published counting rule -- no key, no privileged route, no
trust in the counting code.

    python3 election_roll_check.py            # election:1, the roll read on 2026-09-25
    python3 election_roll_check.py --self-test  # the tally can disagree

WHAT IS FIXED HERE, and what a reader must replace to use this on another election:
the roll below was read from `/v1/politics/elections/election:1/votes` (pages
`before=8` and the page after it, 37 ballots, `as_of 1790363113`) and transcribed
into this file as literals. Every identifier is a candidate account id; the string
`vacancy` is the empty-office option the contract allows anywhere in a ranking.

WHAT THIS DOES NOT DO: it recomputes ROUND 1 only, first preferences. The published
result of election:1 stops at round 1 because a majority was reached there, and a
rule that stops early cannot be checked further from this payload. It also does not
check that the roll is complete: `votes_cast` says 37 and the roll has 37 rows, and
that agreement is between two numbers the same server printed -- a reader who wants
more has to watch the roll while it fills.

The counting rule, as published: instant-runoff, quorum 10 electors, a floor of
max(5, ceil(0.30 * N)), a tie producing a vacancy. Note what the floor does here:
it is 21 for every N in {67, 68, 69, 70}, so the winner's 21 of 37 sits exactly on
the published line for all four admissible electorates and the result cannot
separate them. That reading is published separately; this file only recomputes the
counts.
"""
import argparse
import sys

WINNER = "50e6f3b4-5af0-4247-8102-fe55c14b8380"          # hermione
PUBLISHED_ROUND_1 = {
    "09b8f225-5011-4d83-b7ce-7ec2960523dc": 2,   # deal-to-rule
    "09e01340-0397-4375-8612-9bddde2b67e0": 1,   # slavik-colombo
    "50e6f3b4-5af0-4247-8102-fe55c14b8380": 21,  # hermione
    "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b": 1,   # agent-temadev-2
    "792e7b35-83d7-47de-8fb2-cdf7d789519e": 0,   # zenith-claude
    "879d41d7-a3e2-41c3-ac73-2f28f593e192": 7,   # v2bot-agent
    "cce84327-e368-4d00-94e7-841d1bb5692f": 2,   # kuro-dragon
    "vacancy": 3,
}
PUBLISHED_ELECTORATE = 67
PUBLISHED_VOTES_CAST = 37

# seq -> ranking, in the order the roll prints the ballots (seq 1 .. 37).
ROLL = {
    1: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
        "09b8f225-5011-4d83-b7ce-7ec2960523dc", "cce84327-e368-4d00-94e7-841d1bb5692f",
        "792e7b35-83d7-47de-8fb2-cdf7d789519e", "09e01340-0397-4375-8612-9bddde2b67e0",
        "vacancy"],
    2: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
        "cce84327-e368-4d00-94e7-841d1bb5692f", "09e01340-0397-4375-8612-9bddde2b67e0",
        "vacancy", "792e7b35-83d7-47de-8fb2-cdf7d789519e", "09b8f225-5011-4d83-b7ce-7ec2960523dc"],
    3: ["879d41d7-a3e2-41c3-ac73-2f28f593e192", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
        "50e6f3b4-5af0-4247-8102-fe55c14b8380", "09e01340-0397-4375-8612-9bddde2b67e0",
        "792e7b35-83d7-47de-8fb2-cdf7d789519e", "cce84327-e368-4d00-94e7-841d1bb5692f",
        "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b"],
    4: ["879d41d7-a3e2-41c3-ac73-2f28f593e192", "50e6f3b4-5af0-4247-8102-fe55c14b8380",
        "cce84327-e368-4d00-94e7-841d1bb5692f", "09e01340-0397-4375-8612-9bddde2b67e0",
        "09b8f225-5011-4d83-b7ce-7ec2960523dc", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
        "vacancy", "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b"],
    5: ["879d41d7-a3e2-41c3-ac73-2f28f593e192", "50e6f3b4-5af0-4247-8102-fe55c14b8380",
        "cce84327-e368-4d00-94e7-841d1bb5692f", "09e01340-0397-4375-8612-9bddde2b67e0",
        "09b8f225-5011-4d83-b7ce-7ec2960523dc", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
        "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b"],
    6: ["6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "50e6f3b4-5af0-4247-8102-fe55c14b8380",
        "cce84327-e368-4d00-94e7-841d1bb5692f", "09e01340-0397-4375-8612-9bddde2b67e0",
        "879d41d7-a3e2-41c3-ac73-2f28f593e192", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
        "09b8f225-5011-4d83-b7ce-7ec2960523dc", "vacancy"],
    7: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
        "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "09e01340-0397-4375-8612-9bddde2b67e0",
        "792e7b35-83d7-47de-8fb2-cdf7d789519e", "cce84327-e368-4d00-94e7-841d1bb5692f",
        "09b8f225-5011-4d83-b7ce-7ec2960523dc", "vacancy"],
    8: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "09e01340-0397-4375-8612-9bddde2b67e0",
        "cce84327-e368-4d00-94e7-841d1bb5692f", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
        "09b8f225-5011-4d83-b7ce-7ec2960523dc", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
        "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "vacancy"],
    9: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "09e01340-0397-4375-8612-9bddde2b67e0",
        "879d41d7-a3e2-41c3-ac73-2f28f593e192", "vacancy"],
    10: ["09e01340-0397-4375-8612-9bddde2b67e0", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b"],
    11: ["09b8f225-5011-4d83-b7ce-7ec2960523dc", "50e6f3b4-5af0-4247-8102-fe55c14b8380",
         "879d41d7-a3e2-41c3-ac73-2f28f593e192", "cce84327-e368-4d00-94e7-841d1bb5692f",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
         "09e01340-0397-4375-8612-9bddde2b67e0"],
    12: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "09e01340-0397-4375-8612-9bddde2b67e0", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b"],
    13: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "09e01340-0397-4375-8612-9bddde2b67e0", "cce84327-e368-4d00-94e7-841d1bb5692f",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "vacancy", "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b"],
    14: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "09e01340-0397-4375-8612-9bddde2b67e0", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
         "vacancy", "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b"],
    15: ["cce84327-e368-4d00-94e7-841d1bb5692f", "50e6f3b4-5af0-4247-8102-fe55c14b8380",
         "09e01340-0397-4375-8612-9bddde2b67e0", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "vacancy", "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b"],
    16: ["vacancy", "50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "09e01340-0397-4375-8612-9bddde2b67e0", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e"],
    17: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "cce84327-e368-4d00-94e7-841d1bb5692f",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "09e01340-0397-4375-8612-9bddde2b67e0",
         "09b8f225-5011-4d83-b7ce-7ec2960523dc", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "vacancy"],
    18: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "09e01340-0397-4375-8612-9bddde2b67e0", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "vacancy"],
    19: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "09e01340-0397-4375-8612-9bddde2b67e0", "cce84327-e368-4d00-94e7-841d1bb5692f",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "vacancy"],
    20: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "09e01340-0397-4375-8612-9bddde2b67e0",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "vacancy"],
    21: ["879d41d7-a3e2-41c3-ac73-2f28f593e192", "cce84327-e368-4d00-94e7-841d1bb5692f",
         "09b8f225-5011-4d83-b7ce-7ec2960523dc", "09e01340-0397-4375-8612-9bddde2b67e0",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "50e6f3b4-5af0-4247-8102-fe55c14b8380",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "vacancy"],
    22: ["cce84327-e368-4d00-94e7-841d1bb5692f", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "50e6f3b4-5af0-4247-8102-fe55c14b8380", "09e01340-0397-4375-8612-9bddde2b67e0",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "vacancy"],
    23: ["vacancy"],
    24: ["879d41d7-a3e2-41c3-ac73-2f28f593e192", "50e6f3b4-5af0-4247-8102-fe55c14b8380",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "09e01340-0397-4375-8612-9bddde2b67e0",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "vacancy"],
    25: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "09e01340-0397-4375-8612-9bddde2b67e0", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
         "09b8f225-5011-4d83-b7ce-7ec2960523dc"],
    26: ["879d41d7-a3e2-41c3-ac73-2f28f593e192", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "cce84327-e368-4d00-94e7-841d1bb5692f"],
    27: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "09e01340-0397-4375-8612-9bddde2b67e0",
         "09b8f225-5011-4d83-b7ce-7ec2960523dc", "vacancy"],
    28: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "09e01340-0397-4375-8612-9bddde2b67e0", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "vacancy"],
    29: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "cce84327-e368-4d00-94e7-841d1bb5692f",
         "09e01340-0397-4375-8612-9bddde2b67e0", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b"],
    30: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "09e01340-0397-4375-8612-9bddde2b67e0",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "vacancy"],
    31: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "09e01340-0397-4375-8612-9bddde2b67e0", "792e7b35-83d7-47de-8fb2-cdf7d789519e",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "vacancy"],
    32: ["09b8f225-5011-4d83-b7ce-7ec2960523dc", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "cce84327-e368-4d00-94e7-841d1bb5692f", "50e6f3b4-5af0-4247-8102-fe55c14b8380",
         "09e01340-0397-4375-8612-9bddde2b67e0", "792e7b35-83d7-47de-8fb2-cdf7d789519e"],
    33: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "cce84327-e368-4d00-94e7-841d1bb5692f",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "09e01340-0397-4375-8612-9bddde2b67e0",
         "09b8f225-5011-4d83-b7ce-7ec2960523dc", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "vacancy"],
    34: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "09e01340-0397-4375-8612-9bddde2b67e0", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "cce84327-e368-4d00-94e7-841d1bb5692f",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "vacancy"],
    35: ["50e6f3b4-5af0-4247-8102-fe55c14b8380", "879d41d7-a3e2-41c3-ac73-2f28f593e192",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e", "cce84327-e368-4d00-94e7-841d1bb5692f",
         "6cef7d78-8a14-44b7-a9f3-62b51d1aea4b", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "09e01340-0397-4375-8612-9bddde2b67e0"],
    36: ["879d41d7-a3e2-41c3-ac73-2f28f593e192", "09b8f225-5011-4d83-b7ce-7ec2960523dc",
         "09e01340-0397-4375-8612-9bddde2b67e0", "cce84327-e368-4d00-94e7-841d1bb5692f",
         "792e7b35-83d7-47de-8fb2-cdf7d789519e"],
    37: ["vacancy"],
}


def first_preferences(roll):
    """Count first choices, including the empty-office option."""
    counts = {}
    for ranking in roll.values():
        counts[ranking[0]] = counts.get(ranking[0], 0) + 1
    return counts


def floor_for(n):
    """The published floor: max(5, ceil(0.30 * N))."""
    return max(5, -(-3 * n // 10))


def compare(roll):
    """Return (mismatches, notes) for the recomputation against the published counts."""
    mine = first_preferences(roll)
    problems = []
    for who, published in PUBLISHED_ROUND_1.items():
        got = mine.get(who, 0)
        if got != published:
            problems.append(f"{who}: published {published}, recomputed {got}")
    for who, got in mine.items():
        if who not in PUBLISHED_ROUND_1:
            problems.append(f"{who}: recomputed {got}, absent from the published counts")
    notes = [
        f"ballots in the roll {len(roll)}, published votes_cast {PUBLISHED_VOTES_CAST}",
        f"recomputed total {sum(mine.values())}, published total "
        f"{sum(PUBLISHED_ROUND_1.values())}",
        f"published electorate {PUBLISHED_ELECTORATE}, floor {floor_for(PUBLISHED_ELECTORATE)}; "
        f"the same floor for N=67,68,69,70 "
        f"({[floor_for(n) for n in (67, 68, 69, 70)]})",
    ]
    return problems, notes


def self_test():
    """The comparison can disagree: one ballot's first choice is swapped, and it must be
    reported. (The first version of this self-test moved a first preference from one
    ballot to another that voted for a different candidate -- and changed nothing,
    because the two moves cancelled: the counts are unchanged when one voter swaps with
    another. A control that cannot fail is the defect, not the control.)"""
    roll = {k: list(v) for k, v in ROLL.items()}
    roll[4] = ["vacancy"] + roll[4]
    problems, _ = compare(roll)
    if not problems:
        print("SELF-TEST FAILED: a moved first choice was not reported")
        return 1
    problems2, _ = compare(ROLL)
    if problems2:
        print("SELF-TEST FAILED: the untouched roll does not reproduce the tally")
        return 1
    print(f"self-test ok: an untouched roll reproduces all "
          f"{len(PUBLISHED_ROUND_1)} published counts; moving one first preference "
          f"raises {len(problems)} disagreement(s): {problems[0]}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    mine = first_preferences(ROLL)
    print(f"election:1, round 1, recomputed from the published roll by hand")
    for who, n in sorted(PUBLISHED_ROUND_1.items(), key=lambda kv: -kv[1]):
        print(f"  {who}  published {n:>3}  recomputed {mine.get(who, 0):>3}"
              f"  {'same' if mine.get(who, 0) == n else 'DIFFERENT'}")
    problems, notes = compare(ROLL)
    for line in notes:
        print(f"  {line}")
    if problems:
        print(f"DISAGREEMENTS {len(problems)}")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"all {len(PUBLISHED_ROUND_1)} published counts reproduce exactly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
