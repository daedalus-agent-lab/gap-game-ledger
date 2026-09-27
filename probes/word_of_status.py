#!/usr/bin/env python3
"""A status read from the wrong word.

`$?` reports the exit status of the most recently executed pipeline.  That is
not always the pipeline the text beside the `$?` names:

  in_word       echo "$(basename x.y) rc=$?"
                the word's own command substitution ran last, so `$?` is
                `basename`'s status while the line reads as the command's

  after_sub     out=$(f | head -1); echo "rc=$?"
                the previous statement launched the substitution and the
                pipeline inside it ran last, so `$?` is `head`'s status

A substitution written to the left of the read does not always RUN before it,
so the shape of the word is not the verdict:

  behind_a_branch  f; printf 'g=%s\n' "${v:+$(g)}$?"
                the parameter expansion decides whether `$(g)` runs at all; with
                `v` unset the branch is skipped, nothing is spawned, and the read
                is honest.  Whether the branch is taken depends on the value of
                `v` WHEN THE LINE RUNS, so a static reader cannot decide it and
                must say UNKNOWN rather than taint or clean.

  behind_arithmetic  f; printf 'a=%s\n' "$(( 1 ? 0 : $(h) ))$?"
                the ternary chooses a VALUE, not whether to expand: `$(h)` runs
                even in the branch that is not taken, so the read is never honest
                whatever the condition says.  Sits with the unconditional case.

Measured on GNU bash 5.2.21(1)-release with `f() { return 7; }`, `g() { printf x.y; return 3; }`,
`h() { printf 5; return 3; }`:
  f; printf 'plain=%s\n' "$?"                       -> plain=7
  f; printf 'in_word=%s\n' "$(basename x.y) rc=$?"  -> in_word=x.y rc=0
  out=$(f | head -1); printf 'pipeline=%s\n' "$?"   -> pipeline=0
  f; s=$?; printf 'saved=%s\n' "$s"                 -> saved=7
  unset v; f; printf 'g=%s\n' "${v:+$(g)}$?"        -> g=7     (branch skipped)
  v=set;   f; printf 'g=%s\n' "${v:+$(g)}$?"        -> g=x.y3  (branch taken)
  f; printf 'a=%s\n' "$(( 1 ? 0 : $(h) ))$?"        -> a=03    (expansion ran)

Usage:
  word_of_status.py --check [--root DIR]
  word_of_status.py --selftest
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

IN_WORD = "FAIL[STATUS-INSIDE-WORD]"
AFTER_SUB = "FAIL[STATUS-AFTER-SUBSTITUTION]"
BEHIND_ARITHMETIC = "FAIL[STATUS-BEHIND-ARITHMETIC]"
BEHIND_A_BRANCH = "UNKNOWN[STATUS-BEHIND-A-BRANCH]"
PARAM_GUARD = re.compile(r"\$\{[A-Za-z_][A-Za-z0-9_]*:[-+=?]")
SHELL_SUFFIXES = (".sh", ".bash")
SKIP_PARTS = {".git", "__pycache__", "verify", "node_modules", ".uvcache"}


def _spans(text: str):
    """Yield (kind, start, end) for quoted runs and substitutions, outermost first.

    kind is "quote", "sub" or "backtick".  Nesting is walked so that a `;` or a
    `|` inside `$(...)` is not read as a statement boundary.
    """
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "'":
            end = text.find("'", i + 1)
            end = n if end == -1 else end + 1
            yield "quote", i, end
            i = end
            continue
        if ch == '"':
            depth, j = 1, i + 1
            while j < n:
                if text[j] == "\\":
                    j += 2
                    continue
                if text[j] == '"' and depth == 1:
                    break
                if text.startswith("$(", j):
                    sub = _match_sub(text, j)
                    j = sub[1]
                    continue
                if text[j] == "`":
                    end = text.find("`", j + 1)
                    j = n if end == -1 else end + 1
                    continue
                j += 1
            end = min(j + 1, n)
            yield "quote", i, end
            i = end
            continue
        if text.startswith("$(", i):
            start, end = _match_sub(text, i)
            yield "sub", start, end
            i = end
            continue
        if ch == "`":
            end = text.find("`", i + 1)
            end = n if end == -1 else end + 1
            yield "backtick", i, end
            i = end
            continue
        if ch == "{":
            yield "brace", i, _match_brace(text, i)
            i = _match_brace(text, i)
            continue
        i += 1


def _match_sub(text: str, at: int):
    """The (start, end) of the `$(...)` that opens at `at`, end exclusive."""
    depth, i = 0, at + 1
    while i < len(text):
        ch = text[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return at, i + 1
        elif ch == "'":
            end = text.find("'", i + 1)
            i = len(text) if end == -1 else end
        i += 1
    return at, len(text)


def _match_brace(text: str, at: int):
    depth, i = 0, at
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(text)


def _blank(text: str, spans) -> str:
    out = list(text)
    for _kind, start, end in spans:
        for i in range(start, min(end, len(out))):
            out[i] = "\0"
    return "".join(out)


def _masked(text: str) -> str:
    """`text` with quoted runs and substitutions blanked, for boundary decisions."""
    return _blank(text, _spans(text))


def all_subs(text: str):
    """Every `$(...)` or `` `...` `` span in text, quotes or not."""
    found, i = [], 0
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text.startswith("$(", i):
            start, end = _match_sub(text, i)
            found.append((start, end))
            i = end
            continue
        if text[i] == "`":
            end = text.find("`", i + 1)
            end = len(text) if end == -1 else end + 1
            found.append((i, end))
            i = end
            continue
        i += 1
    return found


def _match_arith(text: str, at: int):
    """The (start, end) of the `$(( ... ))` that opens at `at`, end exclusive."""
    depth, i = 2, at + 2
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "'":
            end = text.find("'", i + 1)
            i = len(text) if end == -1 else end
            continue
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return at, i + 1
        i += 1
    return at, len(text)


def _arith_spans(text: str):
    """Every `$(( ... ))` span in text."""
    found, i = [], 0
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text.startswith("$((", i):
            start, end = _match_arith(text, i)
            found.append((start, end))
            i = end
            continue
        i += 1
    return found


def _brace_spans(text: str):
    """Every `${ ... }` span in text."""
    found, i = [], 0
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text.startswith("${", i):
            end = _match_brace(text, i + 1)
            found.append((i, end))
            i = end
            continue
        i += 1
    return found


def _left_kind(statement: str, start: int, end: int) -> str:
    """How the substitution at (start, end) came to run, as the read's left neighbour.

    "arithmetic"   it stands inside `$(( ... ))`: the branch chooses a value, not
                   whether the expansion happens, so it always runs.
    "guarded"      it stands in the word of a `${name:op...}` expansion whose other
                   arm needs no expansion at all, so whether it runs is a fact about
                   the values at run time, not about the text.
    "unconditional" anything else: a plain `$(...)` to the left always runs first.
    """
    for a0, a1 in _arith_spans(statement):
        if a0 <= start and end <= a1:
            return "arithmetic"
    for b0, b1 in _brace_spans(statement):
        if b0 <= start < b1 and PARAM_GUARD.match(statement[b0:b1]):
            return "guarded"
    return "unconditional"


def _single_quoted_spans(text: str):
    i = 0
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "'":
            end = text.find("'", i + 1)
            end = len(text) if end == -1 else end + 1
            yield i, end
            i = end
            continue
        i += 1


def statements(text: str):
    """Yield (line, offset, statement) honouring quotes and `$(...)` nesting."""
    for lineno, raw in enumerate(text.splitlines(), 1):
        masked = _masked(raw)
        start = 0
        for m in re.finditer(r"[;&|]{1,2}", masked):
            chunk = raw[start:m.start()]
            if chunk.strip():
                yield lineno, start, chunk
            start = m.end()
        chunk = raw[start:]
        if chunk.strip():
            yield lineno, start, chunk


def _launched_a_compound(statement: str) -> bool:
    """Did running this statement end with something other than its own command?"""
    if all_subs(statement):
        return True
    return "|" in _blank(statement, _spans(statement))


def _masked_quotes(text: str) -> str:
    return _blank(text, ((k, s, e) for k, s, e in _spans(text) if k == "quote"))


def word_span(statement: str, at: int):
    """The (start, end) of the shell word the index `at` stands in."""
    masked = _masked_quotes(statement)
    start = at
    while start > 0 and not masked[start - 1].isspace():
        start -= 1
    end = at
    while end < len(masked) and not masked[end].isspace():
        end += 1
    return start, end


def readings(text: str):
    """The two halves: every `$?` written, and those whose word spawned its last command."""
    written, wrong, unread = [], [], []
    prev_compound = False
    for lineno, offset, statement in statements(text):
        subs = all_subs(statement)
        singles = list(_single_quoted_spans(statement))
        for m in re.finditer(r"\$\?", statement):
            at = m.start()
            if any(s < at < e for s, e in singles):
                continue  # a literal `$?` in single quotes is not a read at all
            where = offset + at
            w0, w1 = word_span(statement, at)
            word = statement[w0:w1]
            inside = any(s <= at < e for s, e in subs)
            left = [_left_kind(statement, s, e) for s, e in subs if w0 <= s and e <= at]
            reason = ("arithmetic" if "arithmetic" in left else
                      "unconditional" if "unconditional" in left else
                      "guarded" if left else None)
            if inside:
                shape = "inside_a_substitution"
            elif reason in {"arithmetic", "unconditional"}:
                shape = "in_word"
            elif reason == "guarded":
                shape = "behind_a_branch"
            elif prev_compound:
                shape = "after_substitution"
            else:
                shape = "statement"
            row = {"line": lineno, "at": where, "shape": shape,
                   "reason": reason, "text": word.strip()}
            written.append(row)
            if shape in {"in_word", "after_substitution"}:
                wrong.append(row)
            elif shape == "behind_a_branch":
                unread.append(row)
        prev_compound = _launched_a_compound(statement)
    return {"as_written": written, "as_repaired": wrong, "unread": unread}


def id_of(row) -> str:
    """The id that names this row's own reason, not the shape of its word."""
    if row["shape"] == "in_word":
        return BEHIND_ARITHMETIC if row.get("reason") == "arithmetic" else IN_WORD
    if row["shape"] == "behind_a_branch":
        return BEHIND_A_BRANCH
    return AFTER_SUB


def verdicts(half):
    return [f"{id_of(r)} line {r['line']} col {r['at']}: {r['text']}" for r in half]


def scan(root: Path):
    files, found, unread = [], [], []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in SHELL_SUFFIXES:
            continue
        if SKIP_PARTS & set(path.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        rel = str(path.relative_to(root))
        files.append(rel)
        read = readings(text)
        for row in read["as_repaired"]:
            found.append((rel, row))
        for row in read["unread"]:
            unread.append((rel, row))
    return files, found, unread


FIXTURES = [
    ("plain", 'f() { return 7; }\nf\nprintf \'plain=%s\\n\' "$?"', "plain=7", None),
    ("in_word", 'f() { return 7; }\nf\nprintf \'in_word=%s\\n\' "$(basename x.y) rc=$?"',
     "in_word=x.y rc=0", IN_WORD),
    ("after_substitution", 'f() { return 7; }\nout=$(f | head -1)\nprintf \'pipeline=%s\\n\' "$?"',
     "pipeline=0", AFTER_SUB),
    ("saved", 'f() { return 7; }\nf\ns=$?\nprintf \'saved=%s\\n\' "$s"', "saved=7", None),
    # The order inside the word decides, so these three arms are the pair that
    # separates "the word contains a substitution" from "the read comes after it".
    # bash expands parameter expansions before command substitutions, so a `$?`
    # written to the LEFT of a substitution still reads the command before the
    # statement -- measured here, not reasoned from the manual.
    ("order", 'f() { return 7; }\nf\nprintf \'order=%s\\n\' "$? $(basename x.y)"',
     "order=7 x.y", None),
    ("before", 'f() { return 7; }\nf\nprintf \'before=%s\\n\' "$(basename x.y) $?"',
     "before=x.y 0", IN_WORD),
    ("inside", 'f() { return 7; }\nf\nprintf \'inside=%s\\n\' "$(printf \'%s\' "$?")"',
     "inside=7", None),
    # The three arms the static rule cannot decide from the word alone.  `g` prints
    # x.y and returns 3; the same bytes of word read 7 when the branch is skipped and
    # x.y3 when it is taken, so the honest verdict is UNKNOWN in both, and no verdict
    # at all about the branch from the text.  The arithmetic arm is the opposite: the
    # expansion happens either way, so it is refused for the same reason as `in_word`.
    ("behind_a_branch_skipped",
     'f() { return 7; }\ng() { printf x.y; return 3; }\nunset v\nf\n'
     'printf \'g=%s\\n\' "${v:+$(g)}$?"', "g=7", BEHIND_A_BRANCH),
    ("behind_a_branch_taken",
     'f() { return 7; }\ng() { printf x.y; return 3; }\nv=set\nf\n'
     'printf \'g=%s\\n\' "${v:+$(g)}$?"', "g=x.y3", BEHIND_A_BRANCH),
    ("behind_arithmetic",
     'f() { return 7; }\nh() { printf 5; return 3; }\nf\n'
     'printf \'a=%s\\n\' "$(( 1 ? 0 : $(h) ))$?"', "a=03", BEHIND_ARITHMETIC),
]


def selftest() -> int:
    bad = 0
    for entry in FIXTURES:
        name, script, expect_out, expect_id = entry[:4]
        allowed = entry[4] if len(entry) > 4 else ({expect_id} if expect_id else set())
        proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        said = proc.stdout.strip()
        read = readings(script)
        ids = [id_of(r) for r in read["as_repaired"]] + [id_of(r) for r in read["unread"]]
        print(f"{name}: bash said {said!r}; scanner said {ids}")
        if said != expect_out:
            print(f"FAIL arm {name}: bash printed {said!r}, the fixture claims {expect_out!r}")
            bad = 1
        if expect_id is None:
            if ids:
                print(f"FAIL arm {name}: the correct read was refused ({ids})")
                bad = 1
        elif expect_id not in ids:
            print(f"FAIL arm {name}: not refused ({expect_id} not in {ids})")
            bad = 1
        extra = set(ids) - set(allowed)
        if extra:
            print(f"FAIL arm {name}: a second verdict beside the one this arm tests: {sorted(extra)}")
            bad = 1
    return bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--root", default=".")
    args = ap.parse_args(argv)
    if args.selftest:
        rc = selftest()
        print(f"selftest rc {rc}")
        return rc
    if not args.check:
        ap.error("choose --check or --selftest")
    root = Path(args.root).resolve()
    files, found, unread = scan(root)
    total = 0
    for rel in files:
        total += len(readings((root / rel).read_text(encoding="utf-8"))["as_written"])
    print(f"shell files read {len(files)}")
    print(f"statuses read in this tree {total}")
    for name, row in found:
        print(f"{name}:{row['line']}: {id_of(row)} {row['text']}")
    for name, row in unread:
        print(f"{name}:{row['line']}: {id_of(row)} {row['text']}")
    print(f"statuses read from a word that spawned its own last command {len(found)}")
    print(f"statuses whose word may or may not have spawned one, and this text cannot say "
          f"which {len(unread)}")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
