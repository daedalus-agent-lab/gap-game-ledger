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

So the exit code could not tell two worlds apart: 1/1 either way. On a machine
with the refusing client the first cause MASKS the second -- both branches die at
the same `int("")` -- so the two are one observation there and two only where the
client is permissive. The second cause was reached by mending the first.

The worlds are DRIVEN, not described. Where the client is permissive its row is
substituted for the refusing one at the single place the two worlds differ: what
`one()` returns for the gzip cell. Where the client refuses natively there is
nothing to substitute and the real row IS the refusing world. The first check
therefore asks WHICH WORLD WAS ENTERED, not BY WHICH PATH -- the earlier form of
this probe asked the second question, so on a natively-refusing machine it
reported "a world was never entered" about the machine that was in it, and the
probe took 1 or 0 depending on the installed client: the class it exists to catch,
one floor up. A substitution is weaker than the real thing and is named as one: it
exercises the verdict, not the client.

The refusing row carries exit 61, which is the client's own exit for an
unsolicited transfer coding -- read off a third holder's live measurement on curl
8.18.0, and reproduced by her on this probe's subject.

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
    """What curl 8.18.0 leaves of this row: no answer, and exit 61."""
    return {**row, "status": None, "size": None, "curl_rc": 61,
            "digest": "e3b0c44298fc1c14"}


def drive(mod, tamper: bool):
    """`--check` against a copy of the record, with the gzip row refused.

    Returns (exit code, sizes substituted, the rows the client itself produced).
    The third element is what makes the difference between "this machine is in the
    accepting world and we moved it" and "this machine is in the refusing world
    already" -- two different paths to the same experiment.
    """
    real = mod.one
    seen: list = []
    swapped: list = []

    def fake(path, headers, base=""):
        row = real(path, headers, base)
        if row.get("transfer_encoding") == "gzip":
            seen.append({"curl_rc": row["curl_rc"], "size": row["size"]})
            if row["curl_rc"] == 0:
                swapped.append(row["size"])
                return refusing_row(row)
        return row

    # The world is made OUTSIDE the tree. It used to be made inside it, and the
    # cleanup below runs in a `finally` -- which a killed run never reaches, so a
    # world stayed behind and the blind-columns census reported it, correctly, as
    # a record with rows that nothing reads. A probe that litters the tree it is
    # audited by fails a later run for a reason that has nothing to do with what
    # it measured. The table is passed by path, so the tree it sits in is free.
    work = pathlib.Path(tempfile.mkdtemp(prefix="worlds-"))
    try:
        table = work / "ladder_rungs.json"
        shutil.copy(ROOT / "probes" / "ladder_rungs.json", table)
        if tamper:
            rec = json.loads(table.read_text())
            rec["cells"][0]["got"] = [599, 999999, "deadbeefdeadbeef"]
            table.write_text(json.dumps(rec))
        mod.one = fake
        rc = mod.main(["--check"], table_path=str(table), quiet=True)
        return rc, list(swapped), list(seen)
    finally:
        mod.one = real
        shutil.rmtree(work, ignore_errors=True)


def world_of(seen: list) -> tuple[str, str]:
    """Which world this machine is in natively, and the row that says so."""
    if not seen:
        return "unreached", "the client was never asked for a gzip answer"
    row = seen[0]
    if row["curl_rc"] != 0:
        return "refusing", f"curl exit {row['curl_rc']}, size {row['size']!r}"
    return "accepting", f"curl exit 0, size {row['size']!r}"


def run_world(mod, mode: str, tamper: bool):
    """One run of the ladder's `--check` with the CLIENT forced into `mode`.

    `mode` is what the installed curl does, before this probe touches anything:
    "native" is whatever is installed, "refusing" writes the row 8.18.0 leaves
    behind, "accepting" writes the one 8.5.0 leaves. Only the gzip cell is
    touched. Forcing is a substitution and is named as one -- but it is the only
    way to judge a world this machine is not in, and a probe that judges only its
    own world is the thing under test.
    """
    real = mod.one

    def client(path, headers, base=""):
        row = real(path, headers, base)
        if row.get("transfer_encoding") == "gzip":
            if mode == "refusing" and row["curl_rc"] == 0:
                return refusing_row(row)
            if mode == "accepting" and row["curl_rc"] != 0:
                return {**row, "status": 200, "size": 29, "curl_rc": 0,
                        "digest": "e3b0c44298fc1c14"}
        return row

    mod.one = client
    try:
        return drive(mod, tamper)
    finally:
        mod.one = real


def check(verbose: bool = True) -> int:
    mod = load()
    checks = []
    for mode in ("native", "refusing", "accepting"):
        clean, swapped_clean, seen_clean = run_world(mod, mode, tamper=False)
        tampered, _, _ = run_world(mod, mode, tamper=True)
        world, evidence = world_of(seen_clean)
        # The experiment has been run if the gzip row was refused either way: by
        # our substitution (an accepting client) or by the client itself (a
        # refusing one). Asking for a non-empty `swapped` alone was the defect --
        # it reported "no world was entered" on the machine that is in one.
        entered = bool(swapped_clean) or world == "refusing"
        label = "installed client" if mode == "native" else f"client forced {mode}"
        checks.append((f"{label}: a refusing world was entered ({world})",
                       entered and world != "unreached",
                       f"{evidence}; rows substituted by the probe: {swapped_clean}"))
        checks.append((f"{label}: clean exits 0, tampered exits 1",
                       (clean, tampered) == (0, 1),
                       f"clean {clean} vs tampered {tampered}; before this was pinned "
                       "the old tree gave 1 and 1 -- the same code for opposite claims"))
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
