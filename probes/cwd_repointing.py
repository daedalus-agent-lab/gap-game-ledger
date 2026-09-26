#!/usr/bin/env python3
"""A module that relocates the process, and every relative path in it afterwards.

`check.py` reads its own inputs by a relative name -- `Path("fragments.py")` -- and
pays for that with a module-level `os.chdir(HERE)`. The two lines are one decision,
and the price is paid by the CALLER: importing the guard moves the process to the
ledger's root, so a caller that was working in its own directory finds every relative
path it names afterwards aimed at the ledger's files instead.

This was not reasoned about; it was done to a live checkout. A reproduction script
chdir'd into a temporary directory, wrote `fragments.py` there as a fixture, imported
`check.py` to call `duplicate_declarations`, and found the fixture's two lines appended
to this repository's real `fragments.py`. The reading it had taken -- "the guard is
silent on the `.update` form" -- was then taken on a file the script itself had just
written, and the same run's `git status` showed the damage. The repair was `git checkout`
and a re-read; the tell is the line, and nothing in the guard's own output names it.

WHAT THIS MEASURES

  * the import itself: cwd before and after, in a child process, against a module that
    does not chdir (the control) and against `check.py`;
  * where a relative name lands afterwards: the caller's own `fragments.py`, or the
    module's? (the module's -- and the write that follows the read is the same write);
  * the repair: a caller that saves and restores cwd after the import keeps its own
    directory, and the same relative write then lands where the caller meant it;
  * the live reading: how many `os.chdir` calls the shipped `check.py` has at module
    level, so the count is read from the source and not remembered.

EVERYTHING IS DONE IN A COPY: the fixtures live in a temporary "fake repo" carrying a
minimal `check.py` and `fragments.py`, and in a separate caller directory. This probe
never writes into the checkout it is run from -- that is the whole point of it.

    python3 cwd_repointing.py            # the live reading: what the shipped guard does
    python3 cwd_repointing.py --selftest # the measurements, in copies
"""
import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CHECK = ROOT / "check.py"

CHILD = r'''
import json, os, sys
from pathlib import Path

fake_root, caller, restore = sys.argv[1], sys.argv[2], sys.argv[3] == "yes"
os.chdir(caller)
before = os.getcwd()
sys.path.insert(0, fake_root)
import check  # noqa: F401  -- the import is the thing under measurement
after = os.getcwd()
if restore:
    os.chdir(before)
seen = Path("fragments.py").read_text(encoding="utf-8").strip().splitlines()[-1]
Path("fragments.py").write_text("WROTE-BY-THE-CALLER\n", encoding="utf-8")
print(json.dumps({"before": before, "after": after, "seen": seen,
                  "restored": os.getcwd() == before}))
'''


def fake_repo(base: Path) -> Path:
    """A copy of the guard, small enough to make and safe to damage."""
    repo = base / "fake-repo"
    caller = base / "caller"
    repo.mkdir()
    caller.mkdir()
    shutil.copy2(CHECK, repo / "check.py")
    (repo / "fragments.py").write_text("NAMESPACES = {}\n\n# MODULE-SIDE\n", encoding="utf-8")
    (caller / "fragments.py").write_text("NAMESPACES = {}\n\n# CALLER-SIDE\n", encoding="utf-8")
    return repo


def run_child(base: Path, repo: Path, restore: bool) -> dict:
    script = base / "child.py"
    script.write_text(CHILD, encoding="utf-8")
    out = subprocess.run([sys.executable, str(script), str(repo), str(base / "caller"),
                          "yes" if restore else "no"],
                         capture_output=True, text=True, cwd=str(base))
    if out.returncode != 0:
        raise SystemExit("child failed: %s%s" % (out.stdout, out.stderr))
    return json.loads(out.stdout.strip().splitlines()[-1])


def module_level_chdirs(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines = []
    for node in tree.body:
        if (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Attribute)
                and node.value.func.attr == "chdir"):
            lines.append(node.lineno)
    return lines


def selftest() -> int:
    bad = []
    checks = 0

    with tempfile.TemporaryDirectory(prefix="cwd-repoint-") as d:
        base = Path(d)
        repo = fake_repo(base)

        # The control: a module that does not chdir leaves the caller where it was.
        checks += 1
        ctrl = subprocess.run(
            [sys.executable, "-c",
             "import json, os; os.chdir(%r); import json; print(os.getcwd())" % str(base / "caller")],
            capture_output=True, text=True)
        if ctrl.stdout.strip() != str(base / "caller"):
            bad.append("the control module moved the process: %r" % ctrl.stdout.strip())

        # The import: the caller is relocated into the module's directory.
        checks += 1
        naive = run_child(base, repo, restore=False)
        if naive["after"] != str(repo):
            bad.append("importing the guard did not move the process to the module's root: %r"
                       % naive["after"])

        # And the relative name it reads afterwards is the MODULE's file, not the caller's.
        checks += 1
        if naive["seen"] != "# MODULE-SIDE":
            bad.append("the relative read after import did not land in the module's "
                       "directory: %r" % naive["seen"])

        # The write that follows lands there too -- the caller's own file is untouched.
        checks += 1
        caller_text = (base / "caller" / "fragments.py").read_text(encoding="utf-8")
        repo_text = (repo / "fragments.py").read_text(encoding="utf-8")
        if caller_text.strip().splitlines()[-1] != "# CALLER-SIDE":
            bad.append("the caller's own file was written by the naive import")
        if repo_text.strip() != "WROTE-BY-THE-CALLER":
            bad.append("the write did not land in the module's directory: %r" % repo_text)

        # The repair: save and restore cwd after the import; nothing moves.
        (repo / "fragments.py").write_text("NAMESPACES = {}\n\n# MODULE-SIDE\n", encoding="utf-8")
        (base / "caller" / "fragments.py").write_text("NAMESPACES = {}\n\n# CALLER-SIDE\n",
                                                      encoding="utf-8")
        checks += 1
        fixed = run_child(base, repo, restore=True)
        if not (fixed["after"] == str(repo) and fixed["restored"]
                and fixed["seen"] == "# CALLER-SIDE"):
            bad.append("the restored caller did not read its own file: %r" % fixed)
        checks += 1
        if (base / "caller" / "fragments.py").read_text(encoding="utf-8").strip() != "WROTE-BY-THE-CALLER":
            bad.append("the restored caller's write did not land in its own directory")
        if (repo / "fragments.py").read_text(encoding="utf-8").strip() != "NAMESPACES = {}\n\n# MODULE-SIDE":
            bad.append("the restored caller's write landed in the module's directory")

    # The live source: the count is read, not remembered.
    checks += 1
    live = module_level_chdirs(CHECK)
    print("live check.py: module-level chdir at line(s) %s" % (live,))
    if len(live) != 1:
        bad.append("the shipped guard has %d module-level chdir call(s), not one" % len(live))
    checks += 1
    if not any(s.startswith("os.chdir") for s in
               [l.strip() for l in CHECK.read_text(encoding="utf-8").splitlines()]):
        bad.append("no `os.chdir` line found in the guard's source")

    print("SELFTEST=%d (%d checks)" % (1 if bad else 0, checks))
    for b in bad:
        print("FAIL", b)
    return 1 if bad else 0


def live_reading() -> int:
    """Two runs of this line set are byte-identical: nothing here prints a temporary
    path. The runner's normaliser hides one declared field (a minted stream key) and a
    directory name is not it, so a probe that printed where its sandbox was fails its
    own stability check -- which is what this one did on its first run."""
    with tempfile.TemporaryDirectory(prefix="cwd-live-") as d:
        script = Path(d) / "live.py"
        script.write_text(
            "import json, os, sys\n"
            "os.chdir(%r)\n"
            "sys.path.insert(0, %r)\n" % (d, str(ROOT)) +
            "before = os.getcwd()\n"
            "import check\n"
            "print(json.dumps({'before': before, 'after': os.getcwd(),\n"
            "  'fragments_after_import': str(__import__('pathlib').Path('fragments.py').resolve())}))\n",
            encoding="utf-8")
        out = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        if out.returncode != 0:
            print(out.stdout + out.stderr)
            return 1
        r = json.loads(out.stdout.strip().splitlines()[-1])
    moved = r["before"] != r["after"]
    print("the import moved the process         : %s" % moved)
    print("the relative name afterwards resolves into this ledger : %s"
          % (Path(r["fragments_after_import"]).resolve() == (ROOT / "fragments.py").resolve()))
    print("the caller's own directory is left behind             : %s" % moved)
    print("live check.py: module-level chdir at line(s) %s" % (module_level_chdirs(CHECK),))
    print("CHECK=%d" % (0 if moved else 1))
    return 0 if moved else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    return selftest() if args.selftest else live_reading()


if __name__ == "__main__":
    sys.exit(main())
