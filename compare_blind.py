#!/usr/bin/env python3
"""Compare the blind second grouping against this ledger's own classes.

Reconstructs the id -> class mapping with the same seed export_blind.py used,
then reports every pair the second reader merged but this ledger keeps apart,
and vice versa (which cannot happen for class entries, but is checked anyway).

Usage:
    python3 compare_blind.py
"""

import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20260923


def id_map() -> dict:
    data = json.loads((HERE / "catches.json").read_text(encoding="utf-8"))
    order = list(range(len(data["entries"])))
    random.Random(SEED).shuffle(order)
    return {f"i{i:03d}": data["entries"][i]["class"] for i in order}


def main() -> int:
    mine = id_map()
    blind = json.loads((HERE / "blind_grouping.json").read_text(encoding="utf-8"))
    groups = blind["groups"]

    seen = set()
    for g in groups:
        for i in g["ids"]:
            assert i in mine, f"unknown id {i}"
            assert i not in seen, f"{i} grouped twice"
            seen.add(i)
    assert len(seen) == len(mine), f"{len(seen)} of {len(mine)} grouped"

    merged_pairs = 0
    by_its_group = 0
    for g in groups:
        ids = g["ids"]
        if len(ids) < 2:
            continue
        by_its_group += 1
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                merged_pairs += 1

    print(f"reader groups           {len(groups)} (multi-item {by_its_group})")
    print(f"items                   {len(seen)}")
    print(f"reader merge pairs      {merged_pairs}")
    print(f"ledger classes          {len(mine)}")
    print()
    print("--- pairs the reader merged, ledger keeps apart ---")
    for g in groups:
        if len(g["ids"]) < 2:
            continue
        names = [f"{i}={mine[i]}" for i in g["ids"]]
        print(f"[{g['label']}]")
        for n in names:
            print(f"    {n}")
    unsure = blind.get("unclear") or []
    print()
    print(f"reader's own unsure pairs: {len(unsure)}")
    for u in unsure:
        print(f"    {u['ids']}: {u['why'][:110]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
