#!/usr/bin/env python3
"""Measure the instrument: break each rule of the fingerprint policy, and see who notices.

"Every rule of the policy has a control pair that fails when the rule is broken"
is a sentence until every rule is actually broken. A second holder attacked that
claim on copies of this tree and broke six rules -- two dynamic readers, the
import rule, the dunder rule, the dead-store pass's notion of a read, and the
class-body scope -- with `check.py` still printing `fingerprint control ok` and
`verify_claims.py` still at 24/24. The table of pairs counted *labels*, two of
its labels guarded one rule, and no pair exercised the parameter it claimed.

This probe applies each mutation in `fragments.POLICY_MUTATIONS` to `check.py` in
memory, fingerprints every fragment named in the control table under the mutated
policy, and reports:

  * for a guarded rule: whether any fingerprint MOVED (a mutation that changes
    no fingerprint is not guarding anything) and whether `check.py`'s own control
    fails naming that rule's pair. If it does not, the rule is unguarded whatever
    the table says.
  * for a declared rule (`fragments.RULES_WITHOUT_A_PAIR`): whether the control
    *passes* -- that is the blind spot, measured rather than asserted -- and
    whether the acceptance row the declaration points at fails on a copy carrying
    the same break. A pointer to a row nobody runs is not coverage.
  * whether every rule in `fragments.POLICY_RULES` is either guarded or declared.
    A rule in neither is the silent case: nobody counted it.

Exit 0 prints one line per mutation and a summary; any drift exits 1.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fragments as F  # noqa: E402


def load_check(source: str) -> dict:
    """Execute a (possibly mutated) copy of check.py in its own namespace."""
    path = ROOT / "check.py"
    ns = {"__name__": "check_under_mutation", "__file__": str(path)}
    exec(compile(source, str(path), "exec"), ns)
    return ns


def fingerprints(ns: dict, names) -> dict:
    out = {}
    for name in names:
        try:
            out[name] = ns["fingerprint"](getattr(F, name))
        except Exception as exc:
            out[name] = f"<{type(exc).__name__}: {exc}>"
    return out


def pair_verdict(fps: dict, left: str, right: str) -> bool:
    """Do the two fragments answer `yes, one piece of logic` under these prints?"""
    return fps[left] == fps[right]


def own_axis_flip(base_fps, mutated_fps, left, right, rule) -> tuple[bool, str]:
    """Does THIS pair's own verdict move when THIS rule is broken?

    A pair is a control of its rule only if the two members differ along that one
    axis and nothing else. If the verdict is already fixed by some other
    difference -- two different source names, two fragments that both raise
    before the rule is ever consulted -- then the correct and the incorrect
    implementation of the rule print the same verdict, and the pair is a label
    standing where a guard is claimed. Counting pairs is not counting controls;
    this returns what the pair itself does under the break, not what some other
    fragment in the table does.
    """
    before = pair_verdict(base_fps, left, right)
    after = pair_verdict(mutated_fps, left, right)
    return (before != after,
            f"{'same' if before else 'different'} -> {'same' if after else 'different'}")


def names_in_the_table() -> list:
    seen = []
    for left, right, _same, _rule in F.CONTROL_PAIRS:
        for name in (left, right):
            if name not in seen:
                seen.append(name)
    return seen


def pair_names_for(rule: str) -> list:
    return [f"{l}/{r}" for l, r, _s, rid in F.CONTROL_PAIRS if rid == rule]


def declared_row(rule: str):
    for rid, row in F.RULES_WITHOUT_A_PAIR:
        if rid == rule:
            return row
    return None


def check_declared_row(row: str, old: str, new: str) -> tuple[bool, str]:
    """Run the named acceptance row on a copy whose check.py carries the break."""
    import verify_claims as V
    found = None
    for _label, fn in V.CASES:
        if fn.__name__ == row:
            found = fn
    if found is None:
        return False, f"no acceptance row defined under {row!r}"
    tree = V.copy_ledger(f"policy-mutation-{row}")
    src = (tree / "check.py").read_text(encoding="utf-8")
    if src.count(old) != 1:
        return False, f"the break is not where the row's copy can take it ({src.count(old)} hits)"
    (tree / "check.py").write_text(src.replace(old, new, 1), encoding="utf-8")
    ok, detail = found(tree)
    return (not ok), f"row {row} {'fails' if not ok else 'stays green'} on the copy ({detail})"


def control_table() -> str:
    """The control table as data, so a reader can play it by hand.

    A reader who will not run my script still needs the table in a form they can
    work: rule id, the two fragments, the verdict the policy answers, the verdict
    the broken policy answers, and the break that was applied. Table and caveats
    in one place, because the three caveats below are what make the rows
    portable -- which holder took them, with what the measurement was asked of,
    and the exact command that produced them.
    """
    import hashlib
    import time

    base = load_check((ROOT / "check.py").read_text(encoding="utf-8"))
    table = names_in_the_table()
    baseline = fingerprints(base, table)
    src = (ROOT / "check.py").read_text(encoding="utf-8")
    policy = hashlib.sha256(src.encode()).hexdigest()[:16]

    by_rule: dict[str, list] = {}
    for rule, old, new in F.POLICY_MUTATIONS:
        if src.count(old) != 1:
            continue
        by_rule.setdefault(rule, []).append((old, new,
            fingerprints(load_check(src.replace(old, new, 1)), table)))

    out = ["# The fingerprint policy's control table, as data",
           "",
           f"as_of {int(time.time())}  policy sha256[:16] {policy}",
           "holder: this container, no credentials, no network -- every row is",
           "  measured in memory, so a row is a property of the code and not of a host",
           "command: python3 probes/policy_mutations.py --table",
           "verdict under the broken policy: `yes` = one fingerprint, `no` = two",
           "",
           "| rule | left | right | policy says | broken says | break that moves it |",
           "|---|---|---|---|---|---|"]
    for rid, text in F.POLICY_RULES:
        for left, right, same, rule in F.CONTROL_PAIRS:
            if rule != rid:
                continue
            a = "yes" if baseline[left] == baseline[right] else "no"
            runs = by_rule.get(rid, [])
            b, brk = "?", "no mutation for this rule"
            for old, new, fps in runs:
                if (fps[left] == fps[right]) != (baseline[left] == baseline[right]):
                    b = "yes" if fps[left] == fps[right] else "no"
                    brk = "`" + old.strip().splitlines()[0][:60] + "`"
                    break
            out.append(f"| {rid} | `{left}` | `{right}` | {a} | {b} | {brk} |")
    out += ["",
            "caveats, and what each of them is not:",
            "  * authority: these are readings by THIS container. Signed by nobody;",
            "    verify by re-running the command, not by trusting the file.",
            "  * what was measured: the fingerprint policy IN THE TREE, taken from",
            "    check.py's own bytes at the sha above. A row does not describe any",
            "    other build, and the sha is what a second holder compares first.",
            "  * a row's break: exactly one textual substitution in check.py, named",
            "    in the last column. A break that does not compile is not a",
            "    measurement, and `--check` reports it rather than skipping it."]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 on drift (the default)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--table", action="store_true",
                    help="print the control table as data, with its caveats")
    args = ap.parse_args()

    rules = {rid: text for rid, text in F.POLICY_RULES}
    guarded_rules = {rid for _l, _r, _s, rid in F.CONTROL_PAIRS}
    declared_rules = {rid for rid, _row in F.RULES_WITHOUT_A_PAIR}
    if args.list:
        for rid, text in F.POLICY_RULES:
            where = "pair" if rid in guarded_rules else (
                declared_row(rid) if rid in declared_rules else "NOTHING")
            print(f"{rid}  {where:<18s} {text}")
        return 0

    if args.table:
        print(control_table())
        return 0

    base = load_check((ROOT / "check.py").read_text(encoding="utf-8"))
    table = names_in_the_table()
    baseline = fingerprints(base, table)

    problems, lines = [], []
    by_rule: dict[str, list] = {}
    for rule, old, new in F.POLICY_MUTATIONS:
        src = (ROOT / "check.py").read_text(encoding="utf-8")
        hits = src.count(old)
        if hits != 1:
            problems.append(f"{rule}: the mutation text occurs {hits} times, not once: {old!r}")
            continue
        mutated = load_check(src.replace(old, new, 1))
        by_rule.setdefault(rule, []).append(fingerprints(mutated, table))
        moved = [n for n in table if fingerprints(mutated, [n])[n] != baseline[n]]
        ok, detail = mutated["fingerprint_control"]()
        pair = pair_names_for(rule)
        if rule in guarded_rules:
            if not moved:
                problems.append(f"{rule}: guarded, but the mutation moves no fingerprint "
                                f"of the {len(table)} in the table -- the pair is not "
                                "guarding this rule")
                continue
            named = [p for p in pair
                     if p.split("/")[0] in detail or p.split("/")[1] in detail]
            if ok:
                problems.append(f"{rule}: control still passes with the rule broken "
                                f"(pairs {', '.join(pair)})")
            elif not named:
                problems.append(f"{rule}: control fails but names none of {pair}: {detail}")
            else:
                lines.append(f"ok   {rule}  control FAILS on {', '.join(named)}"
                             f"  (moved {len(moved)}/{len(table)} fp)")
        elif rule in declared_rules:
            row = declared_row(rule)
            if row is None:
                problems.append(f"{rule}: broken, declared without a row")
            elif not ok:
                problems.append(f"{rule}: declared as a blind spot but the control FAILS: {detail}")
            else:
                caught, note = check_declared_row(row, old, new)
                if caught:
                    lines.append(f"ok   {rule}  blind spot measured: control passes, "
                                 f"moved {len(moved)}/{len(table)} fp, {note}")
                else:
                    problems.append(f"{rule}: declared row does not notice the break: {note}")
        else:
            problems.append(f"{rule}: a mutation for a rule that is in neither table")

    for rid, text in F.POLICY_RULES:
        if rid not in guarded_rules and rid not in declared_rules:
            problems.append(f"{rid}: a rule of the policy with no pair and no declaration: {text}")
    for rid in guarded_rules | declared_rules:
        if rid not in rules:
            problems.append(f"{rid}: guarded or declared, but not a rule of the policy")

    # The pairs' own axis. A pair whose verdict is fixed by a difference the rule
    # never touches sits in the table as a guard and measures nothing.
    for left, right, _same, rid in F.CONTROL_PAIRS:
        runs = by_rule.get(rid, [])
        if not runs:
            problems.append(f"pair {left}/{right} ({rid}): the rule has no mutation, "
                            "so whether the pair controls anything is unmeasured")
            continue
        flips = [own_axis_flip(baseline, m, left, right, rid) for m in runs]
        if not any(f for f, _ in flips):
            problems.append(
                f"pair {left}/{right} ({rid}): the pair's own verdict does not move when "
                f"the rule is broken ({'; '.join(d for _f, d in flips)}) -- the verdict is "
                "fixed by a difference the rule never touches, so the pair is a label, "
                "not a control")
        else:
            lines.append(f"ok   {left}/{right} ({rid})  own verdict flips: "
                         f"{next(d for f, d in flips if f)}  ({len(runs)} mutation(s))")

    for line in lines:
        print(line)
    print(f"rules {len(rules)}  guarded {len(guarded_rules)}  declared {len(declared_rules)}  "
          f"mutations {len(F.POLICY_MUTATIONS)}  mutations for unrecognised rules "
          f"{sum(1 for m in F.POLICY_MUTATIONS if m[0] not in rules)}")
    if problems:
        for p in problems:
            print(f"DRIFT {p}")
        return 1
    print(f"ok   every rule either fails the control when broken ({len(guarded_rules)}) "
          f"or is a declared blind spot whose row notices ({len(declared_rules)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
