#!/usr/bin/env python3
"""Does the ladder's `--check` separate a clean record from a tampered one on a
client that REFUSES the unsolicited transfer coding?

The question is not academic. curl 8.5.0 accepts `transfer-encoding: gzip` on an
answer and reports the coded bytes (29 for a 1024-byte entity); curl 8.18.0
refuses the same answer with exit 61 and reports nothing. The ladder's control
asks its own loopback listener for that row, so WHICH WORLD THE RUN IS IN depends
on the client installed -- and a verdict that flips with the client is not a
verdict about the record.

It flipped. On the tree before this probe existed, a run on the refusing client:

  - died inside its own control (`int("")` over the absent `%{size_download}`),
    so `--check` exited 1 both with and without a tampered record; and
  - even once that was mended, the gzip check asked for `exit 0 and 29 bytes`,
    which is a claim about the client rather than about the count, and moved the
    same way.

So the exit code could not tell two worlds apart: 1/1 either way. That is the
defect this probe pins, and it is pinned by DRIVING both worlds rather than by
describing one of them.

The refusing client is not installed everywhere, so its row is substituted at the
single place the two worlds differ: what `one()` returns for the gzip cell. Only
that row is replaced; every other call goes to the real path. A substitution is
weaker than the real thing and is named as one: it exercises the verdict and not
the client.

Run: python3 probes/control_worlds.py --check
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def load():
    spec = importlib.util.spec_from_file_location("ladder_rungs", HERE / "ladder_rungs.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["ladder_rungs"] = mod
    spec.loader.exec_module(mod)
    return mod


def refusing_row(row: dict) -> dict:
    """What curl 8.18.0 leaves of this row: no answer, and exit 61.

    61 is the client's own exit for an unsolicited transfer coding, read off the
    third holder's report of 8.18.0, not measured here. What is measured here is
    that the verdict does not depend on which of the two rows it is handed.
    """
    return {**row, "status": None, "size": None, "curl_rc": 61,
            "digest": "e3b0c44298fc1c14"}


def drive(mod, tamper: bool) -> tuple[int, list]:
    """`--check` against a copy of the record, with the gzip row refused."""
    real = mod.one
    swapped: list = []

    def fake(path, headers, base=""):
        row = real(path, headers, base)
        if row.get("transfer_encoding") == "gzip" and row["curl_rc"] == 0:
            swapped.append(row["size"])
            return refusing_row(row)
        return row

    work = pathlib.Path(tempfile.mkdtemp(prefix="worlds-", dir=ROOT))
    try:
        table = work / "ladder_rungs.json"
        shutil.copy(ROOT / "probes" / "ladder_rungs.json", table)
        if tamper:
            rec = json.loads(table.read_text())
            rec["cells"][0]["got"] = [599, 999999, "deadbeefdeadbeef"]
            table.write_text(json.dumps(rec))
        mod.one = fake
        rc = mod.main(["--check"], table_path=str(table), quiet=True)
        return rc, list(swapped)
    finally:
        mod.one = real
        shutil.rmtree(work, ignore_errors=True)


def check(verbose: bool = True) -> int:
    mod = load()
    clean, swapped_clean = drive(mod, tamper=False)
    tampered, swapped_tampered = drive(mod, tamper=True)

    checks = [
        ("the refusing client's row is the one actually driven",
         bool(swapped_clean) and bool(swapped_tampered),
         f"rows substituted: clean {swapped_clean}, tampered {swapped_tampered}; if this "
         "is empty the rest is a claim about a world that was never entered"),
        ("a clean record passes on the refusing client",
         clean == 0, f"exit {clean}"),
        ("a tampered record fails on the refusing client",
         tampered == 1, f"exit {tampered}"),
        ("the two worlds are separated, which the exit code alone did not do",
         (clean, tampered) == (0, 1),
         f"clean {clean} vs tampered {tampered}; before this was pinned the old tree "
         "gave 1 and 1 -- the same code for opposite claims"),
    ]
    bad = [f"{label}: {detail}" for label, ok, detail in checks if not ok]
    if verbose:
        for label, ok, detail in checks:
            print(f"{'ok ' if ok else 'MOVED'} {label}")
            print(f"     {detail}")
        print(f"\n{len(checks) - len(bad)}/{len(checks)} checks hold")
    for line in bad:
        print(f"MOVED  {line}")
    return 1 if bad else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="drive both worlds and judge")
    args = ap.parse_args(argv)
    if not args.check:
        print(__doc__)
        return 0
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
