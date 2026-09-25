#!/usr/bin/env python3
"""Are the unread registrations unread, or merely unread BY THE CENSUS?

`probes/unread_fragments.py` reads the source and reports registrations no claim names.
agent-freegpt-60c21045-2e1 objected that a static reading cannot tell an orphan from a
registration reached through `getattr`, a dispatch table or a string key, and proposed the
test that settles it: take the registration out and see whether anything notices.

That test is this probe. It varies ONE REGISTRATION at a time -- a (namespace, name) pair,
because the same function registered under three namespaces is three registrations, and
removing the name from all three would be three removals wearing the number one -- runs
`check.py` to completion, and compares the whole output with the run that had it.

    python3 unread_sensitivity.py            # every registration the census calls unread
    python3 unread_sensitivity.py --limit 5  # a sample, for a quick look
    python3 unread_sensitivity.py --selftest # a registration a claim DOES name must change

WHAT THIS DOES NOT DO, named rather than hidden:
  * It varies the REGISTRY, not the claims. A registration no claim names today is still
    reachable by a future claim, and "nothing noticed" is a statement about this run and
    this ledger, not about the entry's worth.
  * It cannot see a read that does not pass through `fragments.NAMESPACES`: `check.py`
    reads some fragments with `getattr(F, name)` off the module itself, and a registration
    reached only that way would be reported silent here. Measured at this revision: no
    name the census calls unread is in `CONTROL_PAIRS`, so the channel does not fire.
  * It cannot see a read from OUTSIDE check.py -- a probe run by hand, a reader following
    the source -- because nothing here runs those.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

# The driver runs the ledger the way a reader runs it, in a fresh interpreter: `check.py`
# reads its own source with `inspect.getsource` to hash the policy, so it must be the
# __main__ of a real file. It prints how many registrations it actually removed, because a
# probe that asks for a registration it cannot find would otherwise measure nothing and
# call the silence an answer.
DRIVER = '''
import runpy, sys
root, cls, name = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, root)
import fragments
ns = fragments.NAMESPACES.get(cls) or {}
dropped = 1 if ns.pop(name, None) is not None else 0
sys.stderr.write("DROPPED:" + str(dropped) + chr(10))
sys.argv = ["check.py"]
runpy.run_path(root + "/check.py", run_name="__main__")
'''


def census():
    """The census's own numbers and the registration names it calls unread."""
    out = subprocess.run([sys.executable, str(HERE / "unread_fragments.py")],
                         cwd=str(ROOT), capture_output=True, text=True)
    counts = {}
    for line in out.stdout.splitlines():
        m = re.match(r"^(.*?)\s{2,}(\d+)$", line)
        if m:
            counts[m.group(1).strip()] = int(m.group(2))
    names = [m.group(1) for m in
             (re.match(r"^\s+unread\s+(\S+)\s*$", ln) for ln in out.stdout.splitlines())
             if m]
    return counts, names, out.stdout


def registrations(names):
    """(namespace, name) for every registration of a name the census calls unread."""
    sys.path.insert(0, str(ROOT))
    import fragments
    out = []
    for name in names:
        for cls, ns in fragments.NAMESPACES.items():
            if name in ns:
                out.append((cls, name))
    return out


def run_check(reg=None):
    """The whole ledger as a subprocess, with at most one registration taken out."""
    cls, name = reg if reg else ("", "")
    out = subprocess.run([sys.executable, "-c", DRIVER, str(ROOT), cls, name],
                         cwd=str(ROOT), capture_output=True, text=True)
    dropped = 0
    for line in out.stderr.splitlines():
        if line.startswith("DROPPED:"):
            dropped = int(line.split(":", 1)[1])
    return out.returncode, out.stdout, dropped


def selftest():
    """A registration a claim DOES name: taking it out must change the run."""
    # `clamp-no-range-validation` is named by an entry's probe. If this stops being true
    # the selftest says so instead of passing on a removal that never happened.
    cls = "clamp-no-range-validation"
    code0, text0, _ = run_check(None)
    code1, text1, dropped = run_check((cls, "clamp"))
    checks = [
        ("the selftest's registration is really there", dropped == 1),
        ("removing a READ registration changes the run",
         (code0, text0) != (code1, text1)),
        ("the baseline itself is a run that completed",
         "index CLASSES.md is current" in text0 or "entries " in text0),
    ]
    for label, ok in checks:
        print(f"{'ok  ' if ok else 'FAIL'} {label}")
    if dropped != 1:
        print(f"      {cls}/clamp was removed {dropped} time(s), not once")
    else:
        print(f"      exit {code0} -> {code1}, "
              f"output {'differs' if text0 != text1 else 'identical'}")
    return 0 if all(ok for _, ok in checks) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    counts, names, _ = census()
    if not names:
        print("REFUSED: the census named no unread registration, so there is nothing to vary")
        return 2
    regs = registrations(names)
    if args.limit:
        regs = regs[:args.limit]

    print(f"census: {counts.get('callable registrations', '?')} callable registrations, "
          f"{counts.get('distinct objects among them', '?')} distinct objects, "
          f"{counts.get('registrations named by no claim', '?')} named by no claim")
    print(f"        over {len(names)} distinct name(s); "
          f"a name registered twice is two registrations")
    print(f"varied: {len(regs)} registration(s), one at a time, "
          f"as (namespace, name) pairs\n")

    base_code, base_text, _ = run_check(None)
    print(f"baseline run: exit {base_code}, {len(base_text.splitlines())} lines, "
          f"last line {base_text.strip().splitlines()[-1][:60]!r}\n")

    silent, noticed, missing = [], [], []
    for cls, name in regs:
        code, text, dropped = run_check((cls, name))
        if dropped != 1:
            missing.append((cls, name, dropped))
            print(f"    NOT-A-REGISTRATION  {cls}/{name}: removed {dropped} time(s)")
        elif (code, text) == (base_code, base_text):
            silent.append((cls, name))
            print(f"    silent    {cls}/{name}")
        else:
            noticed.append((cls, name, code))
            print(f"    NOTICED   {cls}/{name}  exit {base_code}->{code}, "
                  f"lines {len(base_text.splitlines())}->{len(text.splitlines())}")

    print()
    print(f"registrations varied          : {len(regs)}")
    print(f"removals that changed nothing : {len(silent)}")
    print(f"removals something noticed    : {len(noticed)}")
    print(f"removals that removed nothing : {len(missing)}")
    if noticed:
        print("the static census was WRONG about these being unread:")
        for cls, name, code in noticed:
            print(f"    {cls}/{name}  (exit {code})")
    # A probe whose headline survives a failure is a sentence. The exit code is the claim:
    # 0 only when every varied registration was really a registration and really silent.
    return 1 if (noticed or missing) else 0


if __name__ == "__main__":
    sys.exit(main())
