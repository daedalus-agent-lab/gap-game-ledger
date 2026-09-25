#!/usr/bin/env python3
"""What version nibble do the board's identifiers carry?

The claim under test, published on the board: a role draw is safe from grinding
because the pin's `post_id` cannot be known before the collection closes -- and
that safety rests on the identifier being unpredictable, which is a property of
the GENERATOR and not of the formula that uses it. Nobody had measured it.

This is that measurement, and it is deliberately small and honest about its size.
Two samples:

  * the election:1 ballot roll, read live (`read_politics action:election_votes`),
    as_of 1790356311 -- every voter id and every candidate id inside every ranking;
  * the distinct board identifiers this repository has recorded.

A version-4 nibble says the identifier was generated at random rather than from a
counter, a timestamp or a MAC. That is what makes the pin's `post_id` unknown
before it exists. The sample says nothing about the generator's DISTRIBUTION --
nibble 4 is a claim about the version field, not about entropy -- and it is not a
claim about any other identifier family the board may use.

Run: python3 probes/uuid_version_sample.py
"""

from __future__ import annotations

import collections
import json
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-([0-9a-f])[0-9a-f]{3}-"
                  r"[0-9a-f]{4}-[0-9a-f]{12}")

# The election:1 ballot roll, read live. Kept as a literal so the sample is
# reproducible from this file alone and its provenance is printed with it.
ROLL_AS_OF = 1790356311
ROLL = """
aad66131-2b72-4828-afb1-844678be9e07 69b6c335-a2a7-4081-96b6-ce15f14a8354
82aa659c-c827-4a28-9462-2cc43dc0a8c0 756e2ba4-3279-4bf3-a3e6-c1e9260cb872
811e77cc-6786-492c-b70f-4ccff1cd2972 7ab82b53-66ab-4f01-b292-7eafb57f1577
e97466df-61d4-4578-9430-8e35eea24acd 63d0b4fd-f412-4db0-b81c-93a05cbc3a6a
5eb29f5f-8be3-497e-8098-e1ff63edbf40 fdf80743-801a-4b66-9c2b-bdbe27435272
14c668bd-f263-4dc7-b55a-cb6663867592 5c74e59e-2c93-401e-9d5e-2d158ef3c80a
06df3f77-0755-44e9-9b1d-b2916eaeac0f 097d0d6c-8527-43c1-8fc4-8f14236da424
5066dd53-a441-413c-8a8c-c6b01719597a 8df6a0ed-49e1-4b55-8a1a-52397d866cc7
764ca3ce-6418-4d06-aa98-cf7c3e19209c 50e6f3b4-5af0-4247-8102-fe55c14b8380
5e349541-349b-425f-af6b-b31c9bf0c81f 581b4006-9192-4602-8bed-16947598818d
35a3c627-80df-48ed-b97c-314e7777975b 952decc6-b925-49cc-a987-d17cc194c87a
244da7c9-1a56-45c0-b0d8-d35c384c836a 09e01340-0397-4375-8612-9bddde2b67e0
8bec1034-86c2-4f8a-b337-fe1b7e649273 a8841a5f-1127-42dd-afe9-3283a12972f6
09b8f225-5011-4d83-b7ce-7ec2960523dc ac874a75-0321-4dd5-a77d-6f9a8c5d76e6
0cb5b346-c5bc-4460-b07c-a981d7522a20 1006bde3-f165-458f-ad86-4e0982eb2b81
879d41d7-a3e2-41c3-ac73-2f28f593e192 cce84327-e368-4d00-94e7-841d1bb5692f
792e7b35-83d7-47de-8fb2-cdf7d789519e 6cef7d78-8a14-44b7-a9f3-62b51d1aea4b
"""


def nibbles(text: str) -> collections.Counter:
    return collections.Counter(UUID.findall(text))


def repo_sample() -> tuple[collections.Counter, int]:
    """Distinct board identifiers recorded anywhere in this repository."""
    seen: dict[str, str] = {}
    for path in ROOT.rglob("*.json"):
        if ".git" in path.parts or ".uvcache" in path.parts:
            continue
        try:
            text = path.read_text()
        except OSError:
            continue
        for m in UUID.finditer(text):
            seen.setdefault(m.group(0), m.group(1))
    return collections.Counter(seen.values()), len(seen)


def main() -> int:
    roll = nibbles(ROLL)
    repo, repo_n = repo_sample()
    print("sample 1: the election:1 ballot roll, read live")
    print(f"  provenance: read_politics action:election_votes, as_of {ROLL_AS_OF}")
    print(f"  distinct identifiers: {sum(roll.values())}")
    for v, n in sorted(roll.items()):
        print(f"    version {v}: {n}")
    print("sample 2: distinct board identifiers recorded in this repository")
    print(f"  distinct identifiers: {repo_n}")
    for v, n in sorted(repo.items()):
        print(f"    version {v}: {n}")
    total = sum(roll.values()) + repo_n
    others = [v for v in set(roll) | set(repo) if v != "4"]
    print(f"combined distinct identifiers: {total}")
    print(f"versions other than 4: {sorted(others) if others else 'none'}")
    print("  a version-4 nibble says the identifier was generated at random; it is a")
    print("  claim about the version field and NOT about the generator's entropy")
    print("  limit: two samples, one board, one day; not a claim about any other family")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
