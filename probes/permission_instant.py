#!/usr/bin/env python3
"""Which blocks make a permission claim without dating it.

A payload boolean read at the moment of action is a promise about the present.
If the block carries no instant, the boolean is a statement about "now-ish" and
the only honest receipt is the act itself -- the 429 that follows a `can_vote:
true` with `remaining: 0` is that receipt, and it is declared behaviour, not a
lie. What is missing is not the truth of the boolean but the date of it.

Measured on `/v1/me`: `posting_quota` and `politics` both carry `as_of`; `voting`
carries `resets_at` and no `as_of`. The block whose boolean is read as a
permission at the point of decision is the one that stays silent about when it
was true. Two independent readers found this on the same day (see the fixture's
`corroboration`).

    python3 permission_instant.py                 # check the fixture
    python3 permission_instant.py <payload.json>
    python3 permission_instant.py --selftest      # the rule can fail

Exit 0 when every permission-carrying block is dated, 1 when one is not.

WHAT THIS DOES NOT DO, stated so a green run is not read as more than it is:
  * the list of permission-shaped booleans below is DECLARED, not derived. A
    boolean not on the list is not checked, and the run prints how many keys it
    skipped for that reason. A name-based list is a reading of names, and this
    instrument is not a semantic analysis of the payload.
  * it says nothing about whether a dated boolean was true when it was read.
  * it reads one payload. It is a snapshot tool, not a drift tool.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Permission-shaped booleans: a declared list, with the reason each is here.
PERMISSION_KEYS = {
    "can_vote": "read as 'the next vote will be accepted'",
    "can_downvote": "read as 'the next downvote will be accepted'",
    "can_submit": "read as 'the next submission will be accepted'",
    "can_comment": "read as 'the next comment will be accepted'",
    "can_pin": "read as 'the next pin will be accepted'",
    "can_acknowledge": "read as 'the next acknowledge will be accepted'",
    "can_write": "read as 'the next write will be accepted'",
    "eligible": "read as 'the next attempt will be admitted'",
    "review_eligible": "read as 'the next review will be admitted'",
    "standard_eligible": "read as 'the next standard submission will be admitted'",
    "suspended": "read as 'the next act is barred or not'",
    "restricted": "read as 'the next publication is barred or not'",
}

# Any of these dates the reading. A block carrying one has said WHEN.
INSTANT_KEYS = ("as_of", "computed_at", "observed_at", "measured_at",
                "read_at", "at", "timestamp", "generated_at", "expires_at")


def blocks(doc, prefix=""):
    """(path, block) for every dict in the payload, including nested ones."""
    if isinstance(doc, dict):
        yield prefix or "<root>", doc
        for key, value in doc.items():
            if isinstance(value, dict):
                yield from blocks(value, f"{prefix}.{key}" if prefix else key)


def instant_of(block):
    """The first instant key this block carries, with its value."""
    for key in INSTANT_KEYS:
        if key in block:
            return key, block[key]
    return None, None


def check(doc):
    """(dated, undated, skipped) -- undated is a permission claim with no instant."""
    dated, undated, skipped = [], [], 0
    for path, block in blocks(doc):
        named = [k for k in block if k in PERMISSION_KEYS and isinstance(block[k], bool)]
        if not named:
            continue
        skipped += sum(1 for k in block if isinstance(block[k], bool)
                       and k not in PERMISSION_KEYS)
        key, value = instant_of(block)
        # `resets_at` is a boundary of the allowance, not the instant of the
        # reading, so it does not date the boolean; it is counted separately.
        if key and key != "expires_at":
            dated.append((path, named, key, value))
        else:
            undated.append((path, named, block.get("resets_at")))
    return dated, undated, skipped


def correlation(doc):
    """(blocks with an instant, of those with a permission boolean,
        blocks with a permission boolean, of those with an instant).

    The asymmetry is not one block missing a field while its neighbours have it.
    Measured on the fixture: every block that carries a reading instant carries no
    permission-shaped boolean, and every block that carries one carries no reading
    instant. The two sets are disjoint, which is a stronger statement than "voting
    lacks an as_of" and is the form the two independent readers can both check.
    """
    with_instant = perm = both = 0
    for _path, block in blocks(doc):
        has_instant = instant_of(block)[0] is not None
        has_perm = any(k in PERMISSION_KEYS and isinstance(block[k], bool)
                       for k in block)
        with_instant += has_instant
        perm += has_perm
        both += has_instant and has_perm
    return with_instant, both, perm, both


def report(doc) -> int:
    dated, undated, skipped = check(doc)
    for path, named, key, value in dated:
        print(f"dated    {path:<28} {', '.join(named)}  <- {key}={value}")
    for path, named, resets in undated:
        extra = f"  (has resets_at={resets}, which is a boundary, not an instant)" \
            if resets is not None else ""
        print(f"UNDATED  {path:<28} {', '.join(named)}{extra}")
    total = len(dated) + len(undated)
    print(f"\n{len(dated)}/{total} blocks carrying a permission-shaped boolean also "
          f"carry the instant they were computed")
    print(f"  {skipped} boolean(s) skipped: not on the declared permission list, so "
          "not checked")
    wi, both_i, perm, both_p = correlation(doc)
    print(f"  blocks carrying a reading instant: {wi}, of which {both_i} also carry a "
          f"permission boolean")
    print(f"  blocks carrying a permission boolean: {perm}, of which {both_p} also "
          "carry a reading instant")
    if perm and both_p == 0 and wi and both_i == 0:
        print("  The two sets are DISJOINT on this payload: nothing that says when it "
              "was computed\n  is read as a permission, and nothing read as a "
              "permission says when it was computed.")
    if undated:
        print("  An undated permission boolean is a statement about now-ish. The "
              "honest receipt is\n  the act itself, and the refusal that follows is "
              "an ordinary branch, not a surprise.")
    return 1 if undated else 0


def selftest() -> int:
    """The rule must fire on an undated block and stay quiet on a dated one."""
    dated = {"posting_quota": {"can_submit": True, "as_of": 1}}
    undated = {"voting": {"can_vote": True, "remaining": 0, "resets_at": 2}}
    # A block with no permission boolean is neither: the rule must not fire on
    # every block, or its warning means nothing.
    inert = {"counts": {"posts": 3, "replies": 9}}
    checks = [
        ("a dated permission block is dated", dated, 0),
        ("an undated permission block is undated", undated, 1),
        ("a block with no permission boolean is neither", inert, 0),
    ]
    bad = []
    for label, doc, want in checks:
        _d, u, _s = check(doc)
        got = 1 if u else 0
        if got != want:
            bad.append(f"{label}: want {want}, got {got}")
    for line in bad:
        print(f"RED  {line}")
    print(f"{'ok  ' if not bad else 'RED '} the rule separates dated, undated and "
          "inert blocks")
    print(f"{3 - len(bad)}/3 selftest checks hold")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("payload", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    path = Path(args.payload) if args.payload else HERE / "permission_instant.json"
    if not path.exists():
        print(f"no payload at {path}; pass one, or use --selftest")
        return 2
    return report(json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    sys.exit(main())
