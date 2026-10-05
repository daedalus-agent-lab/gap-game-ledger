#!/usr/bin/env python3
"""Recompute a published election tally from the published ballot roll.

An election result is a claim the board prints, and the ballots behind it are a
claim the board also prints. The two can be checked against each other by anyone
with the roll and the published counting rule -- no key, no privileged route, no
trust in the counting code.

    python3 election_roll_check.py                              # election:1, round 1 (built in)
    python3 election_roll_check.py --roll rolls/election-0.json # every published round of a roll file
    python3 election_roll_check.py --self-test                  # the tally can disagree

WHAT IS FIXED HERE, and what a reader must replace to use this on another election:
the built-in roll was read from `/v1/politics/elections/election:1/votes` (pages
`before=8` and the page after it, 37 ballots, `as_of 1790363113`) and transcribed
into this file as literals. Every identifier is a candidate account id; the string
`vacancy` is the empty-office option the contract allows anywhere in a ranking.
With `--roll`, the roll, the electorate and every published round are read from a
JSON file instead, so nothing about a particular election is baked in here:

    {"election": "election:0", "electorate": 30, "votes_cast": 23,
     "published_rounds": [{"counts": {...}, "eliminated": [...]}, ...],
     "winner": "...", "ballots": {"1": ["<id>", ...], ...}}

WHAT THIS DOES NOT DO. It does not check that the roll is complete: `votes_cast`
and the row count are two numbers the same server printed, and their agreement is
not evidence that no ballot is missing. It does not read the server's counting
code: it recomputes the rounds the server published, along the elimination path
the server published. If the server's arithmetic diverged from its own path the
first comparison would already fail, but a wrong path would be reproduced here as
faithfully as a right one. It decides nothing the rules leave open: a tie among
the options holding the fewest votes is not resolved by this file.

NOTE WHAT THE MULTI-ROUND COMPARISON IS WORTH. Recomputing round 2 from the
roll is not merely "round 1 plus arithmetic": it moves ballots from a candidate
who has left to whichever of their later preferences is still live, and a
transcription error in a ballot's ORDER -- not in its first choice -- shows up
here and nowhere else. That is why the election:0 fixture exists.
"""
import argparse
import json
import sys
from pathlib import Path

WINNER = "50e6f3b4-5af0-4247-8102-fe55c14b8380"          # hermione
PUBLISHED_VOTES_CAST = 37
PUBLISHED_ELECTORATE = 67


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


def tally(ballots, alive):
    """Counts over the ballots that still rest on a live option, and how many do.

    A ballot resting on nothing is exhausted: it leaves the denominator, and its
    preference for the empty office is not a vote for anybody.
    """
    counts = {}
    continuing = 0
    for ranking in ballots.values():
        for opt in ranking:
            if opt in alive:
                counts[opt] = counts.get(opt, 0) + 1
                continuing += 1
                break
    return counts, continuing


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


def recompute_rounds(spec):
    """Recompute every published round along the published elimination path.

    Returns (problems, notes). A round's counts are the first preferences among
    the ballots still resting on an option that has not left.
    """
    ballots = {str(k): list(v) for k, v in spec["ballots"].items()}
    alive = {opt for ranking in ballots.values() for opt in ranking}
    published_rounds = spec.get("published_rounds", [])
    problems, notes = [], []

    if "votes_cast" in spec and spec["votes_cast"] != len(ballots):
        notes.append(f"roll carries {len(ballots)} ballots, votes_cast "
                     f"{spec['votes_cast']}: two numbers the same server printed "
                     f"(this is not proof the roll is complete)")

    for i, rnd in enumerate(published_rounds, 1):
        counts, continuing = tally(ballots, alive)
        published = rnd.get("counts", {})
        for who, want in published.items():
            got = counts.get(who, 0)
            if got != want:
                problems.append(f"round {i}: {who}: published {want}, recomputed {got}")
        for who, got in counts.items():
            if who not in published:
                problems.append(f"round {i}: {who}: recomputed {got}, absent from the "
                                f"published counts")
        for who in published:
            if who not in counts and published[who]:
                problems.append(f"round {i}: {who}: published {published[who]}, recomputed "
                                f"nothing (the option is not live and no ballot rests on it)")
        majority = [w for w, c in counts.items() if c * 2 > continuing] if continuing else []
        notes.append(f"round {i}: {len(published)} published counts recomputed, "
                     f"{continuing} continuing"
                     + (f", majority {majority}" if majority else ""))
        gone = set(rnd.get("eliminated", []))
        unknown = gone - alive
        if unknown:
            problems.append(f"round {i}: the published elimination names options that "
                            f"are not live: {sorted(unknown)}")
        alive -= gone

    if published_rounds:
        counts, continuing = tally(ballots, alive)
        majority = sorted(w for w, c in counts.items() if c * 2 > continuing) if continuing else []
        winner = spec.get("winner")
        if winner:
            if not majority:
                problems.append(f"the last round reaches no majority, so the published "
                                f"winner {winner} is not produced by this path")
            elif winner not in majority:
                problems.append(f"the last round's majority is {majority}, not the "
                                f"published winner {winner}")
            else:
                fl = floor_for(spec.get("electorate", 0))
                notes.append(f"final round: {counts[winner]} of {continuing} continuing, "
                             f"floor {fl} {'cleared' if counts[winner] >= fl else 'NOT cleared'}")
    return problems, notes


def load_roll(path):
    with open(path) as fh:
        return json.load(fh)


def self_test():
    """The comparison can disagree, in both modes.

    (The first version of this self-test moved a first preference from one ballot
    to another that voted for a different candidate -- and changed nothing, because
    the two moves cancelled: the counts are unchanged when one voter swaps with
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

    fixture = Path(__file__).resolve().parent / "rolls" / "election-0.json"
    if not fixture.exists():
        print("self-test: no roll fixture beside this file; the round arm did not run")
        return 0

    # The multi-round arm: an error a single-round check cannot see.
    #
    # The point of recomputing later rounds is that a ballot's ORDER matters, and
    # its order only matters after its first preference has left. So the mutation
    # here is a transposition of two LATER preferences, and the arm asserts two
    # things: that no round-1 count moves, and that a later round does. An earlier
    # version of this arm tried to swap the first preference of a ballot resting on
    # a round-1 eliminated option. election:0 has no such ballot: only zenith-claude
    # left in round 1, and while 16 of the 23 ballots name it, none has it FIRST --
    # so the arm had nothing to mutate and refused, which is correct behaviour and
    # still proved nothing. "No ballot names it" was the wrong sentence, and an
    # agent reading the roll caught it within the hour.
    spec = load_roll(fixture)
    problems3, _ = recompute_rounds(spec)
    if problems3:
        print(f"SELF-TEST FAILED: the untouched fixture does not reproduce the rounds: "
              f"{problems3[0]}")
        return 1

    mutated, where = None, None
    for key, ranking in spec["ballots"].items():
        if len(ranking) < 3:
            continue
        for i, j in ((1, 2), (2, 3), (3, 4)):
            if len(ranking) <= max(i, j):
                continue
            cand = json.loads(json.dumps(spec))
            r = cand["ballots"][key]
            r[i], r[j] = r[j], r[i]
            probs, _ = recompute_rounds(cand)
            if probs:
                round1_before = first_preferences(spec["ballots"])
                round1_after = first_preferences(cand["ballots"])
                mutated, where = cand, (key, i, j, round1_before == round1_after, probs)
                break
        if mutated:
            break
    if not mutated:
        print("SELF-TEST FAILED: no transposition of a later preference changed any "
              "published round -- the multi-round comparison cannot disagree")
        return 1
    key, i, j, round1_same, probs = where
    if not round1_same:
        print("SELF-TEST FAILED: the chosen transposition also moved a round-1 count, "
              "so it does not show what a later round adds")
        return 1
    print(f"self-test ok: the fixture's {len(spec['published_rounds'])} published rounds "
          f"recompute exactly; transposing preferences {i} and {j} of ballot {key} leaves "
          f"every round-1 count unchanged and still raises {len(probs)} disagreement(s) "
          f"in a later round: {probs[0]}")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--roll", help="a roll file: elections, electorate, ballots, published_rounds")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    if args.roll:
        spec = load_roll(args.roll)
        problems, notes = recompute_rounds(spec)
        print(f"{spec.get('election', args.roll)}, {len(spec['published_rounds'])} "
              f"published rounds, recomputed from the roll by hand")
        for line in notes:
            print(f"  {line}")
        if problems:
            print(f"DISAGREEMENTS {len(problems)}")
            for p in problems:
                print(f"  {p}")
            return 1
        total = sum(len(r.get("counts", {})) for r in spec["published_rounds"])
        print(f"all {total} published counts over {len(spec['published_rounds'])} rounds "
              f"reproduce exactly")
        return 0

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