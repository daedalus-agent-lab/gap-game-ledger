#!/usr/bin/env python3
"""A module that relocates the process, and every relative path in it afterwards.

`check.py` used to read its own inputs by a relative name -- `Path("fragments.py")` --
and paid for that with a module-level `os.chdir(HERE)`. The two lines were one decision,
and the price was paid by the CALLER: importing the guard moved the process to the
ledger's root, so a caller working in its own directory found every relative path it
named afterwards aimed at the ledger's files instead.

This was not reasoned about; it was done to a live checkout. A reproduction script
chdir'd into a temporary directory, wrote `fragments.py` there as a fixture, imported
`check.py` to call `duplicate_declarations`, and found the fixture's two lines appended
to this repository's real `fragments.py`. The reading it had taken -- "the guard is
silent on the `.update` form" -- was then taken on a file the script itself had just
written, and the same run's `git status` showed the damage.

The repair is in the tree: the chdir is gone and the read is anchored on the file
(`HERE / "fragments.py"`). A probe that required the DEFECT to be present would go red
the moment the defect was repaired -- which is what this one did, and why it prints the
two worlds instead of asserting the one it was written in.

WHAT THIS MEASURES

  * two worlds, built from THIS tree's checker bytes rather than read off them: the
    written world is the checker with an import-time `os.chdir(HERE)` line after its
    directory line, the repaired world is the same bytes without it;
  * in each world, a child whose cwd is its own directory imports a copy of the checker
    and then names `fragments.py` relatively: where does the process stand afterwards,
    which file did the relative read return, and which file did the write that follows
    land in? (`root/fragments.py` and `caller/fragments.py` end in a marker line, so
    "which file" is a reading and not an inference from paths.)
  * the live reading: the same measurement on the shipped `check.py`, and the count of
    module-level `os.chdir` calls in it -- read from the source, not remembered. The
    live command exits non-zero when the shipped checker MOVES the process, which is the
    defect; a repaired tree is green.

EVERYTHING IS DONE IN A COPY: each world is a temporary "fake repo" carrying the
checker, a `fragments.py` and a `catches.json`, and a separate caller directory. This
probe never writes into the checkout it is run from -- the fixture that reported this
defect did, and that is the whole point of it.

    python3 cwd_repointing.py            # the live reading: what the shipped guard does
    python3 cwd_repointing.py --selftest # both worlds, measured in copies
"""
import argparse
import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CHECK = ROOT / "check.py"

MARK_MODULE = "# MODULE-SIDE"
MARK_CALLER = "# CALLER-SIDE"

CHILD = r'''
import json, os, sys
from pathlib import Path

root, caller = Path(sys.argv[1]), Path(sys.argv[2])
os.chdir(caller)
before = str(Path.cwd())
sys.path.insert(0, str(root))
said = ""
try:
    import check  # noqa: F401  -- the import is the thing under measurement
except Exception as exc:
    said = type(exc).__name__ + ": " + str(exc)
after = str(Path.cwd())
read = Path("fragments.py").read_text(encoding="utf-8").strip().splitlines()[-1]
Path("fragments.py").write_text("WROTE-BY-THE-CALLER\n", encoding="utf-8")
print(json.dumps({"before": before, "after": after, "said": said, "read": read}))
'''


def without_line(text: str, target: str) -> str:
    return "".join(l for l in text.splitlines(True) if l.strip() != target)


def with_line_after(text: str, anchor: str, target: str) -> str:
    """The same text, with `target` on its own line after the line carrying `anchor`."""
    out = []
    for line in text.splitlines(True):
        out.append(line)
        if line.strip() == anchor:
            out.append(target + "\n")
    return "".join(out)


def two_worlds() -> tuple:
    """The written and repaired checkers, built from this tree's own bytes.

    The tree may stand in either world, so neither is copied from it: the written world
    is the shipped bytes with the chdir line put back, the repaired world the shipped
    bytes with any such line removed. Both anchors are required, and the two texts are
    required to differ -- otherwise there is nothing here to read.
    """
    source = CHECK.read_text(encoding="utf-8")
    target = "os.chdir(HERE)"
    anchor = "HERE = Path(__file__).resolve().parent"
    if anchor not in source:
        raise SystemExit("REFUSED: the checker names no directory line to build on")
    present = target in [l.strip() for l in source.splitlines()]
    written = source if present else with_line_after(source, anchor, target)
    repaired = without_line(source, target)
    if written == repaired:
        raise SystemExit("REFUSED: the two worlds are one text")
    return written, repaired


def build_world(base: Path, check_source: str, fragments_source: str) -> Path:
    """A copy of the world: the checker, its inputs, and a caller with its own file."""
    root = base / "root"
    caller = base / "caller"
    root.mkdir()
    caller.mkdir()
    (root / "check.py").write_text(check_source, encoding="utf-8")
    (root / "fragments.py").write_text(fragments_source + MARK_MODULE + "\n",
                                       encoding="utf-8")
    shutil.copy2(ROOT / "catches.json", root / "catches.json")
    (caller / "fragments.py").write_text("NAMESPACES = {}\n" + MARK_CALLER + "\n",
                                         encoding="utf-8")
    return root


def run_child(base: Path, root: Path) -> dict:
    script = base / "child.py"
    script.write_text(CHILD, encoding="utf-8")
    out = subprocess.run([sys.executable, str(script), str(root), str(base / "caller")],
                         capture_output=True, text=True, cwd=str(base))
    if out.returncode != 0:
        raise SystemExit("the child did not finish: %s%s" % (out.stdout, out.stderr))
    return json.loads(out.stdout.strip().splitlines()[-1])


def last_line(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip().splitlines()[-1]


def measure(base: Path, check_source: str, fragments_source: str) -> dict:
    """Where the process stands, what the relative read returned, where the write went."""
    root = build_world(base, check_source, fragments_source)
    caller = base / "caller"
    said = run_child(base, root)
    wrote = "neither"
    if last_line(caller / "fragments.py") == "WROTE-BY-THE-CALLER":
        wrote = "caller"
    elif last_line(root / "fragments.py") == "WROTE-BY-THE-CALLER":
        wrote = "module"
    return {
        "moved_into_the_module_directory":
            Path(said["after"]).resolve() == root.resolve(),
        "came_to_rest_in_the_caller_directory":
            Path(said["after"]).resolve() == caller.resolve(),
        "the_relative_read_returned_the_modules_file": said["read"] == MARK_MODULE,
        "the_relative_read_returned_the_callers_file": said["read"] == MARK_CALLER,
        "the_write_landed_in_the_module_directory": wrote == "module",
        "the_write_landed_in_the_callers_directory": wrote == "caller",
        "what_importing_the_copied_checker_said": said["said"],
    }


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
    written_src, repaired_src = two_worlds()

    # The two worlds must be two: a rebuilt "defect" that is not in the text would make
    # every reading below a reading of the repaired world under two names.
    checks += 1
    if written_src == repaired_src:
        bad.append("the written and repaired checkers are one text")
    checks += 1
    in_written = module_level_chdirs_text(written_src)
    in_repaired = module_level_chdirs_text(repaired_src)
    if len(in_written) != 1 or in_repaired:
        bad.append("the written world carries %d module-level chdir line(s) and the "
                   "repaired world %d: the reconstruction is not the repair"
                   % (len(in_written), len(in_repaired)))

    with tempfile.TemporaryDirectory(prefix="cwd-repoint-") as d:
        base = Path(d)
        defect_base, control_base = base / "defect", base / "control"
        defect_base.mkdir()
        control_base.mkdir()

        # The defect: the import moves the caller, and every relative name after it aims
        # at the module's directory -- the read AND the write that follows it.
        checks += 1
        defect = measure(defect_base, written_src, "NAMESPACES = {}\n")
        if defect["what_importing_the_copied_checker_said"]:
            bad.append("the fixture's import did not succeed, so nothing was measured: %r"
                       % defect["what_importing_the_copied_checker_said"])
        elif not (defect["moved_into_the_module_directory"]
                  and defect["the_relative_read_returned_the_modules_file"]
                  and defect["the_write_landed_in_the_module_directory"]):
            bad.append("the written world did not repoint its caller: %r" % defect)
        checks += 1
        if last_line(defect_base / "caller" / "fragments.py") != MARK_CALLER:
            bad.append("the caller's own file was written by the moving import")

        # The control, and the repair: the same measurement on a checker that does not
        # move the process. The caller keeps its directory, its read and its write.
        checks += 1
        control = measure(control_base, repaired_src, "NAMESPACES = {}\n")
        if control["what_importing_the_copied_checker_said"]:
            bad.append("the control's import did not succeed: %r"
                       % control["what_importing_the_copied_checker_said"])
        elif not (control["came_to_rest_in_the_caller_directory"]
                  and control["the_relative_read_returned_the_callers_file"]
                  and control["the_write_landed_in_the_callers_directory"]):
            bad.append("a checker without the chdir still repointed its caller: %r"
                       % control)
        checks += 1
        if last_line(control_base / "root" / "fragments.py") != MARK_MODULE:
            bad.append("the caller's write landed in the module's directory under the "
                       "repaired checker")

    # The live source: the count is read from the file, not remembered.
    checks += 1
    live = module_level_chdirs(CHECK)
    print("live check.py: module-level chdir at line(s) %s" % (live,))
    if len(live) > 1:
        bad.append("the shipped checker has %d module-level chdir calls" % len(live))

    print("SELFTEST=%d (%d checks)" % (1 if bad else 0, checks))
    for b in bad:
        print("FAIL", b)
    return 1 if bad else 0


def module_level_chdirs_text(text: str) -> list[int]:
    tree = ast.parse(text)
    return [n.lineno for n in tree.body
            if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Attribute)
            and n.value.func.attr == "chdir"]


def live_reading() -> int:
    """What the SHIPPED checker does to a caller, measured on a copy of it.

    Two runs of this line set are byte-identical: nothing here prints a temporary path,
    only booleans and a count. The runner's normaliser hides one declared field (a minted
    stream key) and a directory name is not it, so a probe that printed where its sandbox
    was fails its own stability check -- which is what this one did on its first run.

    The exit code is the defect's, not the reading's: a checker that moves its caller is
    what this reports as a failure.
    """
    source = CHECK.read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="cwd-live-") as d:
        base = Path(d)
        result = measure(base, source, (ROOT / "fragments.py").read_text(encoding="utf-8"))
    print("the import moved the process into the copied checker's directory : %s"
          % result["moved_into_the_module_directory"])
    print("the relative read afterwards returned the caller's own file     : %s"
          % result["the_relative_read_returned_the_callers_file"])
    print("the write afterwards landed in the caller's directory            : %s"
          % result["the_write_landed_in_the_callers_directory"])
    print("what importing the copied checker said                          : %r"
          % result["what_importing_the_copied_checker_said"])
    print("live check.py: module-level chdir at line(s) %s" % (module_level_chdirs(CHECK),))
    moved = result["moved_into_the_module_directory"]
    print("CHECK=%d" % (1 if moved else 0))
    return 1 if moved else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    return selftest() if args.selftest else live_reading()


if __name__ == "__main__":
    sys.exit(main())
