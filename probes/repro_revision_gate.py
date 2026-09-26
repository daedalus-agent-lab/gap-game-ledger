#!/usr/bin/env python3
"""Does a reproduction script's exit code still mean what the report said it meant?

A report hands a reader a script and, usually, a claim about which revision the script
speaks for. If the report says "the tree as it stands" while the script reads an archive
frozen when the report was written, then the script's exit code is a reading of revision
R1 and the report is a sentence about revision R2, and nothing in either says which.

This gate takes the two revisions apart and reports on both, side by side:

  * the script is run inside a tree extracted from the DECLARED revision
    (`git archive <rev>` into a fresh temporary directory), and
  * the same script is run in the LIVE tree, as the reader's rerun would run it;

and it compares the two runs on the two things a caller can act on: the exit code, and
the sha256 of standard output. `divergence` names which of the two moved -- `("exit",)`,
`("stdout",)`, both, or `()` for a report whose repro reproduces the same thing on both
trees. A third column says whether the SCRIPT'S OWN BYTES differ between the revisions,
because a divergence caused by the instrument's being edited is a different finding from
one caused by the tree it measures.

The gate does not read the report and does not know what the report claimed: it takes the
revision as a caller's input, so the caller must have read the claim. Passing the live
revision is not a no-op -- it is the measurement that says the script is stable under its
own rerun, which is what makes the declared-revision run interpretable.

    python3 repro_revision_gate.py                       # the gate, measured on a fixture
    python3 repro_revision_gate.py --selftest            # the gate's own cases
    python3 repro_revision_gate.py --check               # fail unless they all hold
    python3 repro_revision_gate.py --repo DIR --rev REV --script NAME.sh

WHAT THIS DOES NOT DO, named rather than hidden:
  * It compares exit codes and stdout digests. A script that writes its finding into a
    FILE, or into stderr only, is compared on the two channels named here and no others;
    a report whose repro differs only in a file it leaves behind is not caught.
  * A script that changes the tree it is run in is run in the extracted copy first and in
    the live tree afterwards; the live run is therefore the one that carries that cost,
    and the gate does not restore what it changes.
  * A divergence in stdout can come from anything nondeterministic in the environment --
    a timestamp, a path, a hash of a temporary name. `divergence` reports that stdout
    moved; it does not say why, and a reader who needs a cause must read both outputs.
  * Timeouts are reported as their own value (`"timeout"`), never folded into an exit
    code: a script killed by the gate is not a script that exited non-zero.
"""
import argparse
import hashlib
import os
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TIMEOUT = 120


def _extract(repo: Path, rev: str, dest: Path) -> None:
    """Write the tree at `rev` into `dest`, from the repository's own record."""
    archive = dest / "_tree.tar"
    with open(archive, "wb") as fh:
        done = subprocess.run(["git", "-C", str(repo), "archive", "--format=tar", rev],
                              stdout=fh, stderr=subprocess.PIPE, check=False)
    if done.returncode != 0:
        raise RuntimeError("git archive %s failed: %s"
                           % (rev, done.stderr.decode("utf-8", "replace").strip()))
    with tarfile.open(archive) as tar:
        tar.extractall(dest, filter="data")
    archive.unlink()


def _interpreter(script: Path) -> list[str]:
    if script.suffix == ".py":
        return [sys.executable]
    if script.suffix in (".sh", ""):
        return ["bash"]
    return ["bash"]


def run_one(cwd: Path, script: str, timeout: int = TIMEOUT) -> dict:
    """Run one script in one directory and keep what a caller can act on."""
    path = cwd / script
    if not path.exists():
        return {"exit": "missing", "stdout_sha256": None}
    done = subprocess.run(_interpreter(path) + [str(path)], cwd=str(cwd),
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=None if timeout is None else timeout, check=False)
    return {"exit": done.returncode,
            "stdout_sha256": hashlib.sha256(done.stdout).hexdigest()}


def gate(repo: Path, rev: str, script: str, timeout: int = TIMEOUT) -> dict:
    """The declared revision's reading, the live tree's reading, and what moved."""
    repo = Path(repo).resolve()
    live = run_one(repo, script, timeout)
    with tempfile.TemporaryDirectory(prefix="rev-gate-") as tmp:
        tmpdir = Path(tmp)
        _extract(repo, rev, tmpdir)
        declared = run_one(tmpdir, script, timeout)
    differs = subprocess.run(["git", "-C", str(repo), "diff", "--quiet", rev, "--", script],
                             check=False).returncode != 0
    divergence = []
    if declared["exit"] != live["exit"]:
        divergence.append("exit")
    if declared["stdout_sha256"] != live["stdout_sha256"]:
        divergence.append("stdout")
    return {"script": script,
            "declared_revision": rev,
            "script_bytes_differ": differs,
            "declared_revision_exit": declared["exit"],
            "live_tree_exit": live["exit"],
            "declared_revision_stdout": declared["stdout_sha256"],
            "live_tree_stdout": live["stdout_sha256"],
            "divergence": tuple(divergence)}


# --------------------------------------------------------------------------------------
# The fixture. A three-commit repository built here, so the gate has a subject whose right
# answers are known: a script that flips its exit code, a script that keeps its exit code
# and changes only what it prints, and a subject the two scripts read.
FIXTURE_FILES = {
    "subject.txt": ("a\n", "b\n", "b\n"),
    "flips.sh": ("echo reading >/dev/null\nexit 0\n", "echo reading >/dev/null\nexit 1\n",
                 "echo reading >/dev/null\nexit 1\n"),
    "quiet.sh": ("exit 0\n", "exit 0\n", "exit 0\n"),
    "silent.sh": ("exit 0\n", "exit 0\n", "exit 0\n"),
}
FIXTURE_PRINTS = {
    "quiet.sh": ("echo \"$1\"\n", "echo \"one\"\n", "echo \"two\"\n"),
}


def build_fixture(dest: Path) -> list[str]:
    """Three commits; returns their ids oldest first."""
    def git(*argv: str) -> None:
        subprocess.run(["git", "-C", str(dest), *argv], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    dest.mkdir(parents=True, exist_ok=True)
    git("init", "-q")
    git("config", "user.email", "gate@example.invalid")
    git("config", "user.name", "gate")
    revs = []
    for i in range(3):
        for name, versions in FIXTURE_FILES.items():
            body = FIXTURE_PRINTS.get(name, (None, None, None))[i] or versions[i]
            (dest / name).write_text(body, encoding="utf-8")
            (dest / name).chmod((dest / name).stat().st_mode | stat.S_IXUSR)
        git("add", "-A")
        git("commit", "-q", "-m", "step %d" % i)
        revs.append(subprocess.run(["git", "-C", str(dest), "rev-parse", "HEAD"],
                                   check=True, stdout=subprocess.PIPE
                                   ).stdout.decode().strip())
    return revs


def selftest() -> tuple[list[str], int]:
    """Cases the gate's own answers must get right, each one a distinction it draws."""
    bad: list[str] = []
    checks = 0
    with tempfile.TemporaryDirectory(prefix="rev-gate-selftest-") as tmp:
        repo = Path(tmp) / "fx"
        first, second, third = build_fixture(repo)

        # The defect the gate exists for: the script's exit code means one thing on the
        # revision it was written against and the other thing on the tree as it stands.
        checks += 1
        g = gate(repo, first, "flips.sh")
        if g["divergence"] != ("exit",) or g["declared_revision_exit"] != 0 \
                or g["live_tree_exit"] != 1:
            bad.append("a script whose exit flipped between revisions read as %r" % (g,))
        checks += 1
        if not g["script_bytes_differ"]:
            bad.append("the gate did not notice the script's own bytes had moved")

        # The live revision as the declared one: no divergence, and the gate says so
        # rather than reporting a defect it would report for any script at all.
        checks += 1
        g = gate(repo, third, "flips.sh")
        if g["divergence"] != ():
            bad.append("the live revision read as a divergence: %r" % (g,))

        # A second revision behind, where the script's bytes are the same: the reading
        # moved, the instrument did not -- the two columns must not be one column.
        checks += 1
        g = gate(repo, second, "flips.sh")
        if g["script_bytes_differ"] or g["divergence"] != ():
            bad.append("an unchanged script one revision back read as %r" % (g,))

        # Exit code and stdout are compared as two things: a script that keeps its exit
        # code and changes only what it prints is a divergence the exit code alone hides.
        checks += 1
        g = gate(repo, first, "quiet.sh")
        if g["divergence"] != ("stdout",) or g["declared_revision_exit"] \
                != g["live_tree_exit"]:
            bad.append("a print-only change read as %r" % (g,))

        # And a script that is the same picture on both trees is reported as NO
        # divergence -- the case that makes a gate's silence mean something.
        checks += 1
        g = gate(repo, first, "silent.sh")
        if g["divergence"] != ():
            bad.append("an identical script and tree read as %r" % (g,))

        # A named-but-absent script is `missing`, not an exit code: a gate that folds
        # "there was nothing to run" into `1` invents a finding.
        checks += 1
        g = gate(repo, first, "never-written.sh")
        if g["divergence"] != () and "missing" not in (g["declared_revision_exit"],
                                                       g["live_tree_exit"]):
            bad.append("an absent script read as %r" % (g,))
        checks += 1
        if not str(g["declared_revision_exit"]).startswith("missing"):
            bad.append("an absent script did not report as missing: %r" % (g,))

        # An unknown revision must raise rather than be read as an empty tree.
        checks += 1
        try:
            gate(repo, "deadbeefdeadbeef", "flips.sh")
            bad.append("an unknown revision was accepted as a tree")
        except RuntimeError:
            pass
    return bad, checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="run the self-test and fail on any wrong answer")
    ap.add_argument("--repo")
    ap.add_argument("--rev")
    ap.add_argument("--script")
    args = ap.parse_args()

    if args.selftest or args.check:
        bad, checks = selftest()
        for line in bad:
            print("FAIL", line)
        print("SELFTEST=%d (%d checks)" % (1 if bad else 0, checks))
        return 1 if bad else 0

    if args.repo and args.rev and args.script:
        g = gate(Path(args.repo), args.rev, args.script)
        for key in ("script", "declared_revision", "script_bytes_differ",
                    "declared_revision_exit", "live_tree_exit", "divergence"):
            print("%-24s %r" % (key, g[key]))
        return 1 if g["divergence"] else 0

    bad, checks = selftest()
    for line in bad:
        print("FAIL", line)
    print("gate self-test      %d checks, %d failed" % (checks, len(bad)))

    with tempfile.TemporaryDirectory(prefix="rev-gate-main-") as tmp:
        repo = Path(tmp) / "fx"
        first, second, third = build_fixture(repo)
        for label, rev, script in [("stale revision", first, "flips.sh"),
                                   ("one revision back", second, "flips.sh"),
                                   ("declared = live", third, "flips.sh"),
                                   ("print-only change", first, "quiet.sh"),
                                   ("same picture both sides", first, "silent.sh")]:
            g = gate(repo, rev, script)
            print("%-24s %-12s exit %s -> %s  divergence %r  script bytes moved: %s"
                  % (label, script, g["declared_revision_exit"], g["live_tree_exit"],
                     g["divergence"], g["script_bytes_differ"]))

    print("CHECK=%d" % (1 if bad else 0))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
