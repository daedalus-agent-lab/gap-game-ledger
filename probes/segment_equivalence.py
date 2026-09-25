"""Are two readings of a first segment two readings, or one function?

Two formulations of what the door does with a `#` before it takes the first
segment of a request target:

    F1  `#` ends the first segment where it stands; the segment is the bytes up
        to the first of `/`, `?`, `#` or the end of the target.
    F2  the fragment is cut off the target first -- everything from the `#` on is
        gone -- and the segment is taken from what is left.

The question was published as a limitation of the door instrument ("the mount
decision cannot separate those two"), and then as a pair of rows said to
separate them. Neither statement was earned: the second was false because a cut
is a TRUNCATION, not the removal of one character, and a truncation only ever
shortens the tail, which lies past the boundary the segment is taken at. This
probe settles it by search over every target up to a length, rather than by the
rows one happened to have: if no target parts them, they are one function and no
row can be found that does.

A disagreement is a target whose first segment differs between the two, so a
non-zero count is a witness and zero is the claim. The alphabet carries the
bytes that decide the question (`/`, `?`, `#`), the mount name and its letters
(`v`, `1`), and the two bytes already measured as ordinary inside a segment
(`;`) and as encoded (`%`).

Usage:
    python3 probes/segment_equivalence.py            # print the search
    python3 probes/segment_equivalence.py --check    # exit 1 if a target parts them
"""

from __future__ import annotations

import hashlib
import sys
from itertools import product

ALPHABET = "/?#v1;%"
MAX_LENGTH = 6
TARGETS = ["".join(t) for n in range(MAX_LENGTH + 1)
           for t in product(ALPHABET, repeat=n)]


def f1_hash_the_segment(target: str) -> str:
    """`#` ends the first segment where it stands."""
    body = target[1:] if target.startswith("/") else target
    for i, ch in enumerate(body):
        if ch in "/?#":
            return body[:i]
    return body


def f2_cut_the_fragment_first(target: str) -> str:
    """The fragment is cut off, then the segment is taken from what is left."""
    t = target.split("#", 1)[0]
    body = t[1:] if t.startswith("/") else t
    for i, ch in enumerate(body):
        if ch in "/?":
            return body[:i]
    return body


def main() -> int:
    check = "--check" in sys.argv
    part = [t for t in TARGETS if f1_hash_the_segment(t) != f2_cut_the_fragment_first(t)]
    print(f"{len(TARGETS)} targets over {ALPHABET!r} up to length {MAX_LENGTH}")
    print(f"{len(part)} target(s) part the two readings")
    for t in part[:10]:
        print(f"  {t!r}: F1 {f1_hash_the_segment(t)!r} "
              f"vs F2 {f2_cut_the_fragment_first(t)!r}")
    digest = hashlib.sha256("\n".join(TARGETS).encode()).hexdigest()[:16]
    print(f"target list sha16 {digest}  (the search, not the answer, is what moves)")
    if check and part:
        print("MOVED  the two readings are no longer one function")
        return 1
    if check and not part:
        print("the two readings take the same first segment from every target searched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
