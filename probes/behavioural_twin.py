#!/usr/bin/env python3
"""Behavioural twins: two class fragments that agree on EVERY input, not on one.

`check.class_collisions` answers with the FINGERPRINT, so it refuses a second NAME
for one logic and never a second SPELLING of it (measured: a behaviour-preserving
rewrite of a class fragment registers as a new class). Equivalence of programs is
not decidable, so no fix closes that. What a bounded probe can do is turn
"silently accepted as a new class" into "accepted, with a named twin to look at".

Not a refusal. Two fragments that agree on a fixed input set are not equivalent,
and the tool says only what it measured: they have not been told apart on this set.

Two rules keep it from reporting every boolean-returning pair as a twin, which the
first version did:

  1. agree on EVERY input of the set, not on one;
  2. the agreed outputs must not be constant -- two fragments that both answer
     `False` to everything are not twins, they are both uninformative here.

    python3 probes/behavioural_twin.py --out /somewhere/else.json
"""
from __future__ import annotations

import argparse
import inspect
import json
import pathlib
import signal
import sys

HERE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
from fragments import NAMESPACES  # noqa: E402

# Values a fragment realistically accepts. Deliberately heterogeneous: the point is
# to reach both the ordinary path and the one the lie lives on.
POOL = [0, 1, -1, 2, "", "ab", "abc", [], [1], [1, 2, 3], {}, {1: 2}, (),
        (1, 2), True, None]
INPUTS_PER_ARITY = 10


class Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise Timeout()


def safe_call(fn, args, seconds: int):
    """Call with a wall-clock bound; a hang and a raise are both results."""
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(seconds)
    try:
        return True, fn(*args)
    except Timeout:
        return False, "Z_TIMEOUT"
    except BaseException as exc:  # noqa: BLE001 -- a raise is an observation
        return False, "E_" + type(exc).__name__
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def arity(fn):
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return None
    n = 0
    for p in sig.parameters.values():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            return None
        if p.default is p.empty:
            n += 1
    return n


def inputs_for(n: int):
    out = []
    for i in range(min(INPUTS_PER_ARITY, len(POOL))):
        out.append(tuple(POOL[(i + j) % len(POOL)] for j in range(n)))
    return out


def vector(fn, n, seconds):
    """The outputs of one fragment over the whole input set.

    Stops at the first timeout: a fragment that cannot answer inside the bound is
    unmeasurable, and paying the bound for each of the other nine inputs buys
    nothing. It is counted, not silently dropped.
    """
    out = []
    for args in inputs_for(n):
        ok, got = safe_call(fn, args, seconds)
        out.append((ok, got))
        if not ok and got == "Z_TIMEOUT":
            return tuple(out), True
    return tuple(out), False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=int, default=2)
    ap.add_argument("--out", default=str(HERE / "twin_candidates.json"),
                    help="point this outside the tree when the tree is the one "
                         "being read, so a scan leaves no file in the record")
    args = ap.parse_args()

    data = check.load()
    subjects = []
    for e in data["entries"]:
        if e.get("lang") != "python" or e.get("executable") is False:
            continue
        prim = check.primary(e)
        ns = NAMESPACES.get(e["class"], {})
        if not prim or prim not in ns:
            continue
        try:
            if check.literal(e["expected"]) == check.literal(e["observed"]):
                continue  # not a divergence; nothing to reproduce
        except Exception:
            continue
        n = arity(ns[prim])
        if n is None:
            continue
        subjects.append({"cls": e["class"], "prim": prim, "fn": ns[prim], "n": n})

    by_arity: dict[int, list] = {}
    for s in subjects:
        by_arity.setdefault(s["n"], []).append(s)
    print(f"subjects with a runnable primary, a real divergence and a fixed arity: "
          f"{len(subjects)}")
    for n in sorted(by_arity):
        print(f"  arity {n}: {len(by_arity[n])} classes")
    # Print what was fed, not only that they agreed. A fragment pair can agree on
    # every input of this pool and differ on the next string a reader hands it
    # (`capitalize_first('AB cd') = 'Ab cd'` against `title_case('AB cd') = 'Ab Cd'`,
    # while every string in the pool is lowercase). Agreement is a sentence about
    # the pool, so the pool has to be in the output beside it.
    print(f"input pool ({len(POOL)} values, {INPUTS_PER_ARITY} tuples per arity): "
          f"{POOL!r}")

    # One vector per subject: the fragment's outputs over the whole input set.
    print("computing one output vector per subject ...", flush=True)
    unmeasurable = []
    for k, s in enumerate(subjects, 1):
        s["vec"], s["timed_out"] = vector(s["fn"], s["n"], args.seconds)
        if s["timed_out"]:
            unmeasurable.append(s["cls"])
        # repr, because a fragment may answer with a list; the question is only
        # whether the answers ever differ from each other.
        s["constant"] = len({repr(v) for v in s["vec"]}) == 1
        if k % 25 == 0 or k == len(subjects):
            print(f"  vectors: {k}/{len(subjects)}, "
                  f"{len(unmeasurable)} unmeasurable so far", flush=True)
    print(f"unmeasurable (a fragment that did not answer inside the bound): "
          f"{len(unmeasurable)}")
    for c in unmeasurable:
        print(f"  NOT MEASURED {c}")

    # A fragment that takes no arguments cannot be told apart by an input set:
    # there is one input, so "agrees on every input" is "agrees once". Those
    # classes are excluded and COUNTED, not silently dropped.
    single_input = [s["cls"] for s in subjects if s["n"] == 0]
    if single_input:
        print(f"NOT COMPARABLE on an input set (arity 0, one input only, so no "
              f"discrimination is possible): {len(single_input)} classes")

    pairs = twins = 0
    for n, group in sorted(by_arity.items()):
        if n == 0:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]
                if a.get("timed_out") or b.get("timed_out"):
                    continue
                pairs += 1
                if a["vec"] != b["vec"]:
                    continue
                if a["constant"]:
                    continue  # both answer the same thing to everything; no signal
                twins += 1
                print(f"  TWIN arity {n}: {a['cls']}\n"
                      f"             ~ {b['cls']}\n"
                      f"      agree on all {len(a['vec'])} inputs; e.g. "
                      f"{inputs_for(n)[0]!r} -> {a['vec'][0]!r}", flush=True)
    print(f"pairs compared within an arity: {pairs}")
    print(f"twin candidates (agree on every input, non-constant): {twins}")
    print(f"classes NOT comparable this way (arity 0): {len(single_input)}")
    print(f"classes unmeasurable (timeout): {len(unmeasurable)}")

    pathlib.Path(args.out).write_text(json.dumps(
        {"subjects": len(subjects),
         "pairs_compared": pairs,
         "input_set_size": INPUTS_PER_ARITY,
         "twins": twins,
         "not_comparable_arity0": len(single_input),
         "unmeasurable": len(unmeasurable),
         "input_pool": [repr(v) for v in POOL],
         "note": "agreement on a fixed input set is not equivalence; this is a "
                 "candidate list for a reader, not a refusal. Classes whose primary "
                 "takes no arguments are excluded: with one input, agreement once "
                 "is not evidence of anything. A candidate agrees on the POOL "
                 "above and nothing more -- read the pool before reading a "
                 "candidate as a twin"},
        ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
