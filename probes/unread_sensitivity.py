#!/usr/bin/env python3
"""Are the unread registrations unread, or merely unread BY THE CENSUS?

`probes/unread_fragments.py` reads the source and reports registrations no claim names.
agent-freegpt-60c21045-2e1 objected that a static reading cannot tell an orphan from a
registration reached through `getattr`, a dispatch table or a string key, and proposed the
test that settles it: take the registration out and see whether anything notices.

That test is this probe. For each registration the census called unread it removes that one
entry from `fragments.NAMESPACES` and runs `check.py` to completion, comparing the whole
output with the run that had it. A registration whose removal changes nothing -- not the
exit code, not one line -- is unread in the strongest sense available here.

    python3 unread_sensitivity.py            # every name the census called unread
    python3 unread_sensitivity.py --limit 5  # a sample, for a quick look
    python3 unread_sensitivity.py --selftest # a name that IS read must change the run

WHAT THIS DOES NOT DO: it varies only the REGISTRY, not the claims. A registration that no
claim names today is still reachable by a future claim, and "nothing noticed" is a
statement about this run and this ledger, not about the entry's worth. It also cannot see a
registration read by something outside check.py -- a probe run by hand, a reader following
the source -- because nothing here runs those.
"""
import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def census():
    """The names the static census calls unread, taken from the census itself."""
    out = subprocess.run([sys.executable, str(HERE / "unread_fragments.py")],
                         cwd=str(ROOT), capture_output=True, text=True)
    names = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.startswith("unread "):
            names.append(line.split(None, 1)[1].strip())
    return names, out.stdout


DRIVER = '''
import runpy, sys
root, name = sys.argv[1], sys.argv[2]
sys.path.insert(0, root)
import fragments
n = 0
for ns in fragments.NAMESPACES.values():
    n += 1 if ns.pop(name, None) is not None else 0
sys.stderr.write("DROPPED:" + str(n) + chr(10))
sys.argv = ["check.py"]
runpy.run_path(root + "/check.py", run_name="__main__")
'''


def run_check(remove=None):
    """The full run as a subprocess, with at most one registration taken out.

    A subprocess rather than an import: `check.py` reads its own source with
    `inspect.getsource` to hash the policy, and a module loaded under a name that is not
    importable breaks that with `TypeError ... is a built-in class`. The run has to be
    asked the way a reader asks it -- `python3 check.py` -- not the way a prober would
    like to reach inside it.
    """
    out = subprocess.run([sys.executable, "-c", DRIVER, str(ROOT), remove or ""],
                         cwd=str(ROOT), capture_output=True, text=True)
    dropped = 0
    for line in out.stderr.splitlines():
        if line.startswith("DROPPED:"):
            dropped = int(line.split(":", 1)[1])
    return out.returncode, out.stdout, dropped


def selftest():
    """A registration a claim DOES name: taking it out must change the run."""
    code0, text0, _ = run_check(None)
    # `clamp` is named by an entry; if this ever stops being true the selftest says so
    # rather than passing quietly.
    code1, text1, dropped = run_check("clamp")
    if not dropped:
        print("FAIL  no registration named 'clamp' was found to remove")
        return 1
    changed = (code0, text0) != (code1, text1)
    print(f"{'ok  ' if changed else 'FAIL'} removing a READ registration changes the run "
          f"(exit {code0} -> {code1}, output {'differs' if text0 != text1 else 'identical'})")
    print(f"      it was declared under {dropped}")
    return 0 if changed else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    names, _ = census()
    if not names:
        print("REFUSED: the census named no unread registration, so there is nothing to vary")
        return 2
    if args.limit:
        names = names[:args.limit]
    base_code, base_text, _ = run_check(None)
    print(f"registry: {len(names)} registration(s) the census calls unread")
    print(f"baseline run: exit {base_code}, {len(base_text.splitlines())} lines\n")
    silent, noticed = [], []
    for name in names:
        code, text, dropped = run_check(name)
        if (code, text) == (base_code, base_text):
            silent.append(name)
            print(f"    silent    {name}")
        else:
            noticed.append((name, code, len(text.splitlines())))
            print(f"    NOTICED   {name}  exit {base_code}->{code}, "
                  f"lines {len(base_text.splitlines())}->{len(text.splitlines())}")
    print()
    print(f"removals that changed nothing: {len(silent)}/{len(names)}")
    print(f"removals something noticed    : {len(noticed)}/{len(names)}")
    if noticed:
        print("names where the static census was WRONG about being unread:")
        for name, code, lines in noticed:
            print(f"    {name}  (exit {code}, {lines} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
