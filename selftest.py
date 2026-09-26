#!/usr/bin/env python3
"""Prove the ledger's gate is live: a green run must mean something.

check.py exits 0 when every probe reproduces its recorded observation and
differs from its recorded expectation. A gate that never fails is decoration,
so this script copies the ledger to a scratch directory, breaks it on purpose
one way at a time, and asserts check.py notices each time.

    python3 selftest.py

Exit 0 means every mutation was caught and the untouched copy still passed.
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from verify_claims import ignore_for_the_record  # noqa: E402


def copy_the_ledger(tree: Path) -> None:
    """Copy this tree the way the case runner copies it: by the record, not by a list.

    Two repairs live here, both measured. The first was a hand list of five files used
    as the fallback where git cannot answer: it named five and `verify_claims.py` --
    imported by check.py halfway down its own length -- was the sixth, so in a tree
    exported without `.git` (`git archive HEAD | tar -x`) the case that asserts an
    untouched copy passes was RED. That is the very tree the revision gate tells a
    reader to build, so the red was in the recipe this ledger publishes. The second
    was the same list used the other way round: a name in the record and gone from
    disk raised FileNotFoundError out of `shutil.copy`, so a worktree with one deleted
    file produced a traceback instead of the sentence about what the copy lacks.

    `ignore_for_the_record` is the rule the case runner and `probes/copy_cost.py`
    already use -- the record is what git tracks, and where git cannot answer a small
    set of GENERATED names is excluded. A hand list here would be a third definition of
    the same rule, which is how the two failures above happened.
    """
    shutil.copytree(HERE, tree, ignore=ignore_for_the_record(HERE))


def modules_the_subject_imports() -> list:
    """What the copy must hold, read off the subject rather than listed by hand.

    A hand list asserts that the environment is complete and nothing checks the
    assertion; the failure that started this file was a copy missing one module, so
    every want-1 case read `ok` for a missing-import exit 1 and the single want-0 case
    read `FAIL`. The requirement is readable off the subject: every top-level import in
    `check.py` that names a `.py` file beside it must be resolvable where `check.py`
    runs. `copy_the_ledger` supplies what the copy has; this supplies what it needs; a
    requirement that is never tested against the thing that must satisfy it is a
    sentence, so `with_tree` tests them against each other before a case runs.
    """
    import ast

    needed = set()
    source = (HERE / "check.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            needed.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            needed.add(node.module.split(".")[0])
    beside = {path.stem: path.name for path in HERE.glob("*.py")}
    return sorted(beside[n] for n in needed & set(beside))


def run(tree: Path) -> int:
    return subprocess.run(
        [sys.executable, "check.py"], cwd=tree, capture_output=True, text=True
    )


class Result:
    """A run's exit code with the words it said kept beside it.

    A want-1 case that reads only the code accepts ANY red: a second fault that
    reddens every case at once flips them all green while the case under test is
    broken, which is the class `a-selftest-that-asserts-a-refusal-the-check-would-not-make`
    and was named on the board by a reader of this file. Each case therefore also
    carries a MARKER -- the name of the thing the case broke, as the run prints it --
    so the refusal argued for is the refusal observed. `__eq__` compares to the
    wanted code, which keeps the tuple shape of every case unchanged.
    """

    def __init__(self, rc: int, text: str = "") -> None:
        self.rc = rc
        self.text = text

    def __eq__(self, other) -> bool:
        return self.rc == other

    def __repr__(self) -> str:
        return f"exit {self.rc}"


COMPLAINT = re.compile(
    r"(?m)^(MISS|DUPE|HOLD|BADADDRESS|index|UNCITED|DECLINED|COUNT)"
)

LEDGER = json.loads((HERE / "catches.json").read_text(encoding="utf-8"))


def the_class_the_first_repeat_belongs_to() -> str:
    """The entry each repeat case mutates, read here so the marker names it."""
    for entry in LEDGER["entries"]:
        for rep in entry.get("repeats") or []:
            if isinstance(rep, dict):
                return entry["class"]
    raise AssertionError("no object-form repeat in the ledger to test with")


def catches_first_class() -> str:
    """The entry the class-probe case mutates: entries[0], named as the run prints it."""
    return LEDGER["entries"][0]["class"]


def the_first_class_with_an_address() -> str:
    """The entry each citation case mutates, read here so the marker names it."""
    for entry in LEDGER["entries"]:
        if entry.get("address"):
            return entry["class"]
    raise AssertionError("no entry carries an address to test with")


def the_first_repeat_with_an_address() -> str:
    """The repeat row each citation case mutates, named the way the run prints it."""
    for entry in LEDGER["entries"]:
        for rep in entry.get("repeats") or []:
            if isinstance(rep, dict) and rep.get("address") and rep.get("fn"):
                return f"{entry['class']}/{rep['id']}"
    raise AssertionError("no repeat carries both an address and a fragment")


def the_first_row_with_a_line_and_no_address() -> str:
    """The row the addressless-quote case mutates, named the way the run prints it.

    Two claims live on a cited row and the run uses the same name for the row whether
    the line sits on the entry or on one of its repeats: the complaint line is
    `BADADDRESS  <class>/<repeat id>`, so this returns exactly that.
    """
    for entry in LEDGER["entries"]:
        if entry.get("address_quote") and not entry.get("address"):
            return entry["class"]
        for rep in entry.get("repeats") or []:
            if (isinstance(rep, dict) and rep.get("address_quote")
                    and not rep.get("address")):
                return f"{entry['class']}/{rep['id']}"
    raise AssertionError("no row quotes a line with no address beside it")


MISSING_MODULE_CODE = 2  # no case may want this: the fixture refused before it ran


def with_tree(mutate, extra_module="", mutate_tree=None, drop=(), mutate_counts=None):
    """Copy the ledger, apply `mutate(catches)`, return check.py's exit code.

    `drop` leaves names out of the copy on purpose, so the case that says the copy must
    hold what the subject imports has a copy that does not.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tree = Path(tmp) / "ledger"
        copy_the_ledger(tree)
        for name in drop:
            (tree / name).unlink(missing_ok=True)
        copied = {p.relative_to(tree).as_posix() for p in tree.rglob("*") if p.is_file()}
        missing = [n for n in modules_the_subject_imports() if n not in copied]
        if missing:
            # Refuse to run the case, but say so instead of raising: an exception here
            # reached the caller as a traceback that named no case, and the value below
            # can never equal a wanted 0 or 1, so the refusal is reported as its own red
            # line. It is the same colour inversion either way -- with a module absent
            # every want-1 case exits 1 for that reason and reads `ok` -- and one case
            # exists to assert this refusal fires.
            print("     fixture refused: the copy lacks %r, which the subject imports"
                  % (missing,))
            return Result(MISSING_MODULE_CODE, "fixture refused")
        if extra_module:
            with (tree / "fragments.py").open("a", encoding="utf-8") as fh:
                fh.write(extra_module)
        catches = json.loads((tree / "catches.json").read_text(encoding="utf-8"))
        mutate(catches)
        (tree / "catches.json").write_text(
            json.dumps(catches, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if mutate_tree:
            mutate_tree(tree)
        if mutate_counts:
            counts = json.loads((tree / "counts.json").read_text(encoding="utf-8"))
            mutate_counts(counts)
            (tree / "counts.json").write_text(
                json.dumps(counts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        done = run(tree)
        return Result(done.returncode, done.stdout + done.stderr)


TWIN = '''

def clamp_twin(val, low, high):
    """A second name for the class clamp, with the same logic."""
    return min(max(val, low), high)


NAMESPACES["clamp-no-range-validation"]["clamp_twin"] = clamp_twin
'''

SECOND_CLASS = '''

NAMESPACES["clamp-second-name"] = {"clamp_twin": clamp_twin}
'''


def first_object_repeat(catches):
    for entry in catches["entries"]:
        for rep in entry.get("repeats") or []:
            if isinstance(rep, dict):
                return entry, rep
    raise AssertionError("no object-form repeat in the ledger to test with")


def main() -> int:
    cases = []

    cases.append(("untouched copy passes", with_tree(lambda c: None), 0))

    def flip_observed(catches):
        _, rep = first_object_repeat(catches)
        rep["observed"] = "999"

    cases.append(("a repeat's observed value is wrong", with_tree(flip_observed), 1,
                  the_class_the_first_repeat_belongs_to()))

    def same_as_expected(catches):
        _, rep = first_object_repeat(catches)
        rep["observed"] = rep["expected"]

    cases.append(("a repeat's expected == observed", with_tree(same_as_expected), 1,
                  the_class_the_first_repeat_belongs_to()))

    def drop_field(catches):
        _, rep = first_object_repeat(catches)
        del rep["promise"]

    cases.append(("a repeat is missing a field", with_tree(drop_field), 1,
                  the_class_the_first_repeat_belongs_to()))

    def same_as_class(catches):
        """Point a repeat at the class fragment itself: same bytes, no sighting.

        The repeat must carry the class's own probe, expected AND observed: that is
        what makes it the class probe rather than a second measurement. An earlier
        version substituted an expected of its own ("5"), so `same_measurement` was
        false, no refusal was due -- and the case read as passing only because the
        fixture tree was missing a module, so every case exited 1 for that reason.
        """
        import re

        for entry in catches["entries"]:
            for rep in entry.get("repeats") or []:
                if not isinstance(rep, dict) or not rep.get("fn"):
                    continue
                if str(entry["expected"]) == str(entry["observed"]):
                    continue
                rep["fn"] = re.findall(r"[A-Za-z_]\w*", entry["probe"])[0]
                rep["probe"] = entry["probe"]
                rep["expected"] = entry["expected"]
                rep["observed"] = entry["observed"]
                return
        raise AssertionError(
            "no entry with an object repeat and a divergent class probe to test with")

    cases.append(("a repeat points at the class fragment", with_tree(same_as_class), 1,
                  the_class_the_first_repeat_belongs_to()))

    def same_logic_other_name(catches):
        """A repeat whose fragment differs in name but not in logic.

        The twin is appended to the copied fragments.py, so the class gets a
        second name for its own bytes; the gate must refuse it.
        """
        for entry in catches["entries"]:
            if entry["class"] != "clamp-no-range-validation":
                continue
            for rep in entry.get("repeats") or []:
                if isinstance(rep, dict):
                    rep["fn"] = "clamp_twin"
                    rep["probe"] = "clamp_twin(5, 10, 0)"
                    rep["expected"] = "5"
                    rep["observed"] = "0"
                    return

    cases.append(
        (
            "a repeat whose fragment is the class logic",
            with_tree(same_logic_other_name, extra_module=TWIN),
            1,
            the_class_the_first_repeat_belongs_to(),
        )
    )

    def flip_class_probe(catches):
        catches["entries"][0]["observed"] = "999"

    cases.append(("a class probe's observed value is wrong", with_tree(flip_class_probe), 1,
                  catches_first_class()))

    def a_number_the_probe_no_longer_prints(counts):
        """The class this case exists for: a numeral typed beside a maybe-count.

        The entry types five numbers; the check reads them from the probe. A number that
        has drifted must be refused, or the sentence is a reading of nothing.
        """
        counts["rows"][0]["keys"]["namespaces"] = 999999

    cases.append(
        ("a counted numeral that no longer reads the same",
         with_tree(lambda c: None, mutate_counts=a_number_the_probe_no_longer_prints),
         1, "namespaces is typed as 999999")
    )

    def a_numeral_the_entry_types_that_no_probe_reads(dtree):
        """The clause this case exists for: a number typed in prose beside a counted one.

        `counts.json` is a second file, so it is also a second place a number can be
        typed by hand: before this case the reader compared the file with the probe and
        never with the sentence, and the ledger carried two entries whose prose numbers
        had drifted two and three digits behind the probes while the run stayed green.
        The copy's entry is rewritten to type 200000 where the file counts 186, and the
        index is regenerated so the numeral itself is the only complaint left.
        """
        spec = json.loads((dtree / "counts.json").read_text(encoding="utf-8"))
        row = next(r for r in spec["rows"]
                   if r["class"] == "a-class-registers-fragments-that-no-entry-reads")
        typed = row["keys"]["namespaces"]
        path = dtree / "catches.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["entries"]:
            if entry["class"] == "a-class-registers-fragments-that-no-entry-reads":
                entry["fact"] = entry["fact"].replace(
                    "%d namespaces" % typed, "200000 namespaces")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        fresh = subprocess.run([sys.executable, "check.py", "--index"], cwd=str(dtree),
                               capture_output=True, text=True)
        (dtree / "CLASSES.md").write_text(fresh.stdout, encoding="utf-8")

    cases.append(
        ("a numeral typed in the entry that no probe reads",
         with_tree(lambda c: None, mutate_tree=a_numeral_the_entry_types_that_no_probe_reads),
         1, "and the entry's own text does not type")
    )

    def a_numeral_that_stands_for_another_key(dtree):
        """The clause this case exists for: a number in the right entry, in the wrong slot.

        Between the entry and the probe stand two numbers -- the classes count and the
        registrations count -- and a reader that only asks whether the entry types the
        first anywhere accepts `registrations classes / classes registrations`, where each
        numeral is read off the other key's account. The numbers this copy types are the
        ones the probe counts; only their places are swapped, and the index is regenerated
        so the places are the only complaint left.
        """
        spec = json.loads((dtree / "counts.json").read_text(encoding="utf-8"))
        row = next(r for r in spec["rows"]
                   if r["class"] == "a-guard-that-reads-only-the-form-the-defect-was-reported-in")
        classes = row["keys"]["classes"]
        regs = row["keys"]["registrations"]
        path = dtree / "catches.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["entries"]:
            if entry["class"] == "a-guard-that-reads-only-the-form-the-defect-was-reported-in":
                entry["fact"] = entry["fact"].replace(
                    f"{classes} classes / {regs} registrations",
                    f"{regs} classes / {classes} registrations",
                )
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        fresh = subprocess.run([sys.executable, "check.py", "--index"], cwd=str(dtree),
                               capture_output=True, text=True)
        (dtree / "CLASSES.md").write_text(fresh.stdout, encoding="utf-8")

    cases.append(
        ("a counted numeral standing for the wrong key",
         with_tree(lambda c: None, mutate_tree=a_numeral_that_stands_for_another_key),
         1, "beside the words of")
    )

    def a_counted_row_that_names_no_number(counts):
        """The clause this case exists for: a row with nothing to read against.

        `counts.json` is a second place a number can be typed, and a row that names no
        number is green whatever the file and the probe say: the guard asks a question
        with no subject and reports no problem. Measured on a copy, a row with an empty
        `keys` was accepted before this clause existed.
        """
        counts["rows"][0]["keys"] = {}

    cases.append(
        ("a counts.json row that names no number",
         with_tree(lambda c: None, mutate_counts=a_counted_row_that_names_no_number),
         1, "carries nothing the probe or")
    )

    def a_row_for_a_class_the_ledger_lacks(counts):
        """The clause this case exists for: a row scoped to a universe nobody read.

        The file names the classes its numbers belong to, and nothing checked that those
        names are the ledger's own: a row for a class that does not exist was green, so
        the file could carry a reading of a sentence that is not here. The refusal names
        the class rather than pointing at an absent entry's wording.
        """
        counts["rows"].append({"class": "a-class-that-is-not-in-the-ledger",
                               "cmd": ["python3", "probes/unread_fragments.py"],
                               "keys": {"namespaces": 1}})

    cases.append(
        ("a counts.json row for a class the ledger lacks",
         with_tree(lambda c: None, mutate_counts=a_row_for_a_class_the_ledger_lacks),
         1, "the ledger has no entry of that name")
    )

    def a_full_stop_after_a_counted_numeral(dtree):
        """The clause this case exists for: punctuation read as a digit.

        The reader first took a `.` or a `,` after a number for the start of a longer
        number, so an honest entry was refused for the sentence's punctuation --
        `186. 301 callable registrations` printed "does not type 186". The entry here is
        honest in both halves and only the full stop differs; the index is regenerated so
        the place clause is the only thing that could complain.
        """
        counts = json.loads((dtree / "counts.json").read_text(encoding="utf-8"))
        row = next(r for r in counts["rows"]
                   if r["class"] == "a-guard-that-reads-only-the-form-the-defect-was-reported-in")
        classes = row["keys"]["classes"]
        path = dtree / "catches.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["entries"]:
            if entry["class"] == "a-guard-that-reads-only-the-form-the-defect-was-reported-in":
                entry["fact"] = entry["fact"].replace(f"{classes} classes",
                                                      f"{classes}. classes", 1)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
        fresh = subprocess.run([sys.executable, "check.py", "--index"], cwd=str(dtree),
                               capture_output=True, text=True)
        (dtree / "CLASSES.md").write_text(fresh.stdout, encoding="utf-8")

    cases.append(
        ("a counted numeral followed by a full stop",
         with_tree(lambda c: None, mutate_tree=a_full_stop_after_a_counted_numeral),
         0, "counted numerals")
    )

    def second_class_same_logic(catches):
        """Two class names for one shape: the ledger counts the same lie twice."""
        catches["entries"].append(
            {
                "class": "clamp-second-name",
                "promise": "clamped to the inclusive range",
                "fact": "no range validation",
                "probe": "clamp_twin(5, 10, 0)",
                "expected": "5",
                "observed": "0",
                "lang": "python",
            }
        )

    cases.append(
        (
            "a class is another class under a new name",
            with_tree(second_class_same_logic, extra_module=TWIN + SECOND_CLASS),
            1,
            "clamp-second-name",
        )
    )

    def unquoted_address(catches):
        """An address with no line from the message is a direction, not evidence."""
        for entry in catches["entries"]:
            if entry.get("address"):
                del entry["address_quote"]
                return

    cases.append(("an address with no line from the message", with_tree(unquoted_address), 1,
                  the_first_class_with_an_address()))

    def quote_is_prose(catches):
        """A line found in the message that is not a line of the fragment."""
        for entry in catches["entries"]:
            if entry.get("address"):
                entry["address_quote"] = "по словам автора, вот тот старый фрагмент"
                return

    cases.append(("a quote that is not a line of the fragment", with_tree(quote_is_prose), 1,
                  the_first_class_with_an_address()))

    def repeat_quote_from_another_fragment(catches):
        """A repeat's line is read against the fragment the REPEAT names.

        Seventeen repeats cite a message and quote a line, and the audit path never
        tested those lines -- it tested addressless rows instead -- while the report
        path tested them and nothing else. A repeat whose line belongs to another
        fragment's bytes sends a reader following `class -> fragment -> line` to the
        wrong fragment, and only one of the two modes said so.
        """
        for entry in catches["entries"]:
            for rep in entry.get("repeats") or []:
                if isinstance(rep, dict) and rep.get("address") and rep.get("fn"):
                    rep["address_quote"] = "    NOT A LINE OF THE FRAGMENT THIS REPEAT NAMES"
                    return
        raise AssertionError("no repeat carries both an address and a fragment")

    cases.append(
        ("a repeat's quote from another fragment",
         with_tree(repeat_quote_from_another_fragment), 1,
         the_first_repeat_with_an_address())
    )

    def a_foreign_line_where_no_address_stands(catches):
        """The clause this case exists for: a line's own claim, read wherever it stands.

        `citation_fields` tested a quoted line against the fragment the row names only
        inside the branch that carried an address, so a row quoting another fragment's
        bytes with no address kept the same claim unread: three rows in this ledger did
        and the run called them nothing. Here an addressless row's line is replaced by
        bytes its fragment does not contain, and the run must refuse it -- the address
        is a second claim about a message, never the condition for reading the first.
        """
        broken = False
        for entry in catches["entries"]:
            if entry.get("address_quote") and not entry.get("address"):
                entry["address_quote"] = "     NOT A LINE OF THE FRAGMENT THIS ROW NAMES"
                broken = True
                break
            for rep in entry.get("repeats") or []:
                if (isinstance(rep, dict) and rep.get("address_quote")
                        and not rep.get("address")):
                    rep["address_quote"] = "     NOT A LINE OF THE FRAGMENT THIS ROW NAMES"
                    broken = True
                    break
            if broken:
                break
        if not broken:
            raise AssertionError("no addressless row quotes a line to break")

    cases.append(
        ("an uncited line that is not a line of its fragment",
         with_tree(a_foreign_line_where_no_address_stands), 1,
         the_first_row_with_a_line_and_no_address())
    )

    def index_of_a_broken_ledger():
        """The complaint must not be written into the page the redirect produces.

        The check's own docstring says the remedy for a red ledger is
        `python3 check.py --index > CLASSES.md`, and three BADADDRESS complaints were
        written with a plain `print` while that paragraph stood above them: a copy
        with one broken quote put three lines of complaint into the generated page.
        Here the page is rendered from a broken copy and the complaint is looked for
        on both streams.
        """
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp) / "ledger"
            copy_the_ledger(tree)
            catches = json.loads((tree / "catches.json").read_text(encoding="utf-8"))
            broken = False
            for entry in catches["entries"]:
                if entry.get("address"):
                    entry["address_quote"] = "     NOT A LINE OF ANY FRAGMENT HERE"
                    broken = True
                    break
            if not broken:
                raise AssertionError("no entry carries an address to break")
            (tree / "catches.json").write_text(
                json.dumps(catches, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            out = subprocess.run([sys.executable, "check.py", "--index"], cwd=tree,
                                 capture_output=True, text=True)
            # At the START of a line: two entries describe this complaint inside their
            # own fact text, so a bare substring test reads a green page as polluted.
            complaint = re.compile(r"(?m)^BADADDRESS")
            clean = (not complaint.search(out.stdout) and bool(complaint.search(out.stderr))
                     and out.returncode == 1)
            if clean:
                return Result(out.returncode, out.stdout + out.stderr)
            return Result(MISSING_MODULE_CODE, "BADADDRESS " + out.stdout[:200])

    cases.append(
        ("the index of a broken ledger carries no complaint", index_of_a_broken_ledger(), 1,
         "BADADDRESS")
    )

    def stale_index(tree):
        """The published index no longer describes the ledger."""
        with (tree / "CLASSES.md").open("a", encoding="utf-8") as fh:
            fh.write("\n## `a-class-that-was-never-added`\n")

    cases.append(("a stale CLASSES.md", with_tree(lambda c: None, mutate_tree=stale_index), 1,
                  "index"))

    def copy_missing_what_the_subject_imports():
        """The requirement is tested against the copy instead of assumed to hold.

        The subject is asked what it imports, and one of those files is left out of the
        copy: the fixture must refuse to run, naming it. Without this, the same absence
        is reported as one red case and ten green ones, which is the colour inversion
        this file exists because of.
        """
        needed = modules_the_subject_imports()
        if not needed:
            raise AssertionError("the subject imports no module beside it: nothing to drop")
        return 1 if with_tree(lambda c: None, drop=[needed[0]]) == MISSING_MODULE_CODE else 0

    def a_row_that_names_no_file(tree):
        """One provenance row that declares itself checkable and names nothing.

        Nothing was digested for it, so the summary line must not count it among the
        rows this run read back. Before the repair the count was `rows - unproven`,
        and a row without a file was never unproven: the line read as a clean sweep
        over rows nobody had read.
        """
        path = tree / "label_recovery.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("rows") or []:
            if row.get("file") and row.get("file_checkable"):
                row.pop("file")
                break
        else:
            raise AssertionError("no provenance row names a checkable file to strip")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")

    cases.append(
        ("a provenance summary does not count a row it never digested",
         with_tree(lambda c: None, mutate_tree=a_row_that_names_no_file), 0,
         "name no file at all, so nothing was digested")
    )

    def a_row_whose_bytes_moved(tree):
        """The other end: a cited file whose bytes are not the ones recorded."""
        path = tree / "label_recovery.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for row in data.get("rows") or []:
            if row.get("file") and row.get("file_checkable"):
                target = tree / row["file"]
                target.write_bytes(target.read_bytes() + b"\n")
                break
        else:
            raise AssertionError("no provenance row names a checkable file to append to")

    cases.append(
        ("a provenance row whose bytes moved is not counted as digested",
         with_tree(lambda c: None, mutate_tree=a_row_whose_bytes_moved), 1,
         "cite bytes this repo does not carry")
    )

    cases.append(
        ("a copy missing what the subject imports", copy_missing_what_the_subject_imports(), 1)
    )

    bad = 0
    for case in cases:
        name, code, want = case[0], case[1], case[2]
        marker = case[3] if len(case) > 3 else None
        said = code.text if isinstance(code, Result) else ""
        named = marker is None or marker in said
        ok = (code == want) and named
        line = (f"{'ok  ' if ok else 'FAIL'} {name:<42} exit {code} (want {want})"
                + (f" [{marker}]" if marker else ""))
        if not ok:
            bad += 1
            if not named:
                line += f" -- and the run must name {marker!r}"
        print(line)
        if not ok:
            for other in [l for l in said.splitlines() if COMPLAINT.match(l)][:6]:
                print(f"     {other}")
    print(f"cases {len(cases)}  failed {bad}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
