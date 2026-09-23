#!/usr/bin/env python3
"""Export the ledger's class entries without class names, for a blind second reader.

The ledger's new/repeat labels were all assigned by one classifier. This script
exports only what a reader needs to group the entries by shape: the docstring's
claim, what the code does, and the probe with its promised and actual value.
Class names, first_seen, repeats and aliases are dropped, and ids are shuffled
with a fixed seed so the order carries no signal.

Usage:
    python3 export_blind.py            # writes blind_classes.json
    python3 export_blind.py --out X    # writes elsewhere
"""

import argparse
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20260923


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="blind_classes.json")
    args = ap.parse_args()

    data = json.loads((HERE / "catches.json").read_text(encoding="utf-8"))
    items = []
    for entry in data["entries"]:
        items.append(
            {
                "promise": entry.get("promise", ""),
                "fact": entry.get("fact", ""),
                "probe": entry.get("probe", ""),
                "expected": entry.get("expected", ""),
                "observed": entry.get("observed", ""),
                "lang": entry.get("lang", "python"),
            }
        )
    rng = random.Random(SEED)
    order = list(range(len(items)))
    rng.shuffle(order)
    out = {
        "task": "group by shape of lie",
        "note": (
            "No class names, no author, no order signal. Each item is one "
            "docstring claim vs what the code does. Group items whose lie is "
            "the same shape."
        ),
        "seed": SEED,
        "count": len(items),
        "items": [dict(items[i], id=f"i{i:03d}") for i in order],
    }
    (HERE / args.out).write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {args.out}: {len(items)} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
