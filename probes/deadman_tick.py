#!/usr/bin/env python3
"""A heartbeat that reads silence as health: the standing suite's own last run.

The suite writes what it measured for every tree it ran on, and nothing anywhere
says WHEN it last ran. A week with no run and a week with nothing to report leave
the same artefact -- none -- so a run that stopped ticking is byte-identical to a
run that found nothing. This probe reads a run stamp the runner appends to and
answers five ways, and the state NAME is machine-readable because the reader of a
verdict should not have to parse a sentence to learn which question was answered.
Every red line therefore carries its state name, the COMMONEST one included -- a red
whose name was only in the prose left the reader to grep a sentence:

  fresh       the newest stamp is inside the declared cadence;
  covered     the newest stamp is older than the cadence, and a declared pause reaches
              over the gap: the silence has an end and a reason, so the repair is to
              let the pause run out or write a new one;
  stale       the newest stamp is older than the cadence, and the refusal NAMES both
              instants and the cadence it compared;
  no_baseline no entry at that path at all, OR a file that carries no stamp line:
              nothing was ever recorded, so the repair is to make the runner tick;
  unreadable  an entry that cannot be read as a record -- a stamp line that is not a
              timestamp, a stamp line with no offset, a directory, bytes that are not
              UTF-8, a path this process may not open, a link that leads nowhere: the
              record is here and is not readable, so the repair is the file.

A path that IS an entry and cannot be read is not the same question as a path with
nothing at it, and the three faults that used to escape as tracebacks answered
neither -- a reader got `IsADirectoryError` instead of a state. A dangling symlink
is an entry that exists and holds nothing, which is not an absent file either.

A declared, dated waiver is the only way a gap is allowed, and it is named when it
is the reason the gap passed. A waiver is itself bounded -- a pause longer than
`MAX_WAIVER_SECONDS` is refused as a reason and NAMED in the refusal -- because a
waiver without an end is a way to declare the heartbeat silent for good, and one line
written once would then answer freshness for every future week.

`fresh` and `covered` are two readings of one record that differ in WHICH question was
answered, not in the colour, so they carry different state words. They have to: the same
bytes read at two instants can be green by cadence at one and green by a declared pause at
the next -- a pause that has just begun to do the work it was written for -- and a line
that carried the pause under the word `fresh` reported a record that had moved when what
moved was the clock. The green line is stable across runs of a fixed record for a GIVEN
state and not across states, and naming the state is what makes that difference readable.

A declaration the reader does NOT use is named too, on EVERY verdict -- green, red, and
the two states that never reach the gap check (`no_baseline`, `unreadable`), where the
refusal was returned before the declarations were ever read. Dropping it silently made a
mistyped `# waiver`, an unbounded pause and a pause whose instants cannot be read against
the stamp indistinguishable from never having been written -- and the writer of a
declined pause read a green run as an obeyed one.

What counts as a declaration ATTEMPT is narrower than "the line mentions a waiver": a
stamp's own annotation that happens to say `waiver not used` is a stamp, not a pause, and
naming it refused misreports which line was declined. An attempt is a `#` comment whose
FIRST word is a pause word -- `# waiver ...`, `#waive ...`, `# pause ...`. The earlier
gate asked how many field separators the line carries, which is a question about the
fields and not about the line: `# we paused the suite for the release | see notes` was
printed as a refused declaration, while `#waive ... the tree is frozen`, a declaration
that lost its separators, was dropped in silence. Prose that mentions a pause in its
middle is neither.

  python3 probes/deadman_tick.py --stamp            # the runner's line
  python3 probes/deadman_tick.py --check            # the verdict
  python3 probes/deadman_tick.py --selftest         # each claim above, on fixtures
"""
import argparse
import datetime
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
STAMP = REPO / "repro" / "fresco" / "tick.log"
CADENCE_SECONDS = 24 * 3600
# A pause may not outlast the instrument it suspends: a waiver longer than this is a way
# to declare the silence permanent, and it is refused as a reason rather than obeyed.
# The VALUE is pinned by the selftest, because a selftest that only pins the presence of
# a bound lets the bound be widened to 300 days with every case still green.
MAX_WAIVER_SECONDS = 7 * 24 * 3600
WAIVER_OPENS = "# waiver "
# A pause word, and the three fields of a declaration. Both are needed to call a line an
# attempt: a stamp line annotating itself "waiver not used" mentions a pause and is not a
# declaration, while `#waive  a | b` is one whose opener is mistyped and must be named.
PAUSE_WORDS = ("waiv", "pause")


def read_record(path: pathlib.Path):
    """(lines, complaint) -- the record's lines, or why the path is not a record at all.

    Distinguishing an absent entry from an entry that cannot be read is the whole point:
    a directory, a permission failure, non-UTF-8 bytes and a link that leads nowhere each
    used to end in a traceback with no state name, and a dangling symlink was reported as
    a record that was never written. `lexists` asks about the entry, `read_text` about the
    bytes; both answers are needed and neither substitutes for the other.
    """
    if not os.path.lexists(path):
        # Its own state, not a flavour of unreadable: a first-ever tick is repaired by
        # making the runner tick, a record that cannot be read by fixing the entry.
        return None, ("no_baseline",
                      "no run stamp at %s: a run that never happened and a run with "
                      "nothing to report leave the same record, so this is red and not "
                      "quiet" % (path.relative_to(REPO) if REPO in path.parents else path))
    try:
        return path.read_text(encoding="utf-8").splitlines(), None
    except (OSError, UnicodeDecodeError) as exc:
        return None, ("unreadable",
                      "%s is an entry that cannot be read as a record: %s: %s -- the "
                      "repair is the file, not a tick" % (
                          path.name, type(exc).__name__, exc))


def parse_stamp(lines, path: pathlib.Path):
    """(newest instant, complaint) -- complaint is (state, message) when there is none.

    Two faults do not share a name here. A record that carries no stamp line at all
    records nothing, so its repair is the repair of an absent file; a line that is
    there and cannot be read is repaired in the file. An empty file was reported as
    the second while its repair is the first.
    """
    newest = None
    for n, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        head = line.split("\t")[0].strip()
        try:
            when = datetime.datetime.fromisoformat(head)
        except ValueError:
            return None, ("unreadable",
                          "line %d of %s is not a timestamp: %r -- an unreadable record "
                          "is a red, not a gap of zero" % (n, path.name, line[:60]))
        if newest is None or when > newest:
            newest = when
    if newest is None:
        return None, ("no_baseline",
                      "%s carries no stamp line at all: a record that holds nothing and a "
                      "record that is not here are repaired the same way -- make the "
                      "runner tick" % path.name)
    if newest.tzinfo is None:
        return None, ("unreadable",
                      "the newest stamp %s carries no offset, so no gap can be read "
                      "from it" % newest.isoformat())
    return newest, None


def declared_waivers(lines, newest):
    """Every `# waiver` line split into what is usable and what is declined.

    Returns (usable, declined): `usable` is (start, end, text) for a bounded pause whose
    instants can be read against the stamp; `declined` is (start_or_none, end_or_none,
    text, reason) for one the reader will not use. A declaration that parses, is bounded
    and simply does not cover this gap is NOT declined: it was read and answered no, which
    is a different thing from never having been read.

    A line is an ATTEMPT only if `#` is its first byte and its first word is a pause word:
    a stamp annotated "waiver not used" is a stamp, and printing it as a refused
    declaration said the reader had declined a line it had in fact read as the stamp. A
    prose comment that mentions a pause mid-sentence is not an attempt either, while a
    declaration that lost its separators still is one -- the head is what is read, because
    that is where a declaration puts its word. `newest` may be None (the record carries no
    readable stamp); the offset comparison against the stamp is then simply not made.
    """
    usable, declined = [], []
    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        lowered = line.lower()
        if not line.startswith("#"):
            # A stamp or a note whose words mention a pause, and which cannot be one: a
            # declaration puts its word at the head of a comment.
            continue
        # A declaration is HEADED by its pause word. The gate used to count field
        # separators instead, which asked how many fields the line has rather than
        # whether it is an attempt: `# we paused the suite | see notes` was reported as a
        # declined declaration, and a mistyped one whose separators were lost was never
        # named at all.
        head = lowered.lstrip("#").strip().split()
        if not head or not any(word in head[0] for word in PAUSE_WORDS):
            continue
        if not line.startswith(WAIVER_OPENS):
            declined.append((None, None, line,
                             "line %d does not open the declared form %r, so nothing "
                             "reads it as a pause" % (n, WAIVER_OPENS)))
            continue
        parts = [p.strip() for p in line[len(WAIVER_OPENS):].split("|")]
        if len(parts) < 3:
            declined.append((None, None, line,
                             "line %d carries %d field(s), and a pause needs a start, an "
                             "end and its reason" % (n, len(parts))))
            continue
        try:
            start = datetime.datetime.fromisoformat(parts[0])
            end = datetime.datetime.fromisoformat(parts[1])
        except ValueError:
            declined.append((None, None, line.strip(),
                             "line %d has an instant that is not a timestamp" % n))
            continue
        if (start.tzinfo is None) != (end.tzinfo is None) or (
                newest is not None and (newest.tzinfo is None) != (start.tzinfo is None)):
            declined.append((start, end, line,
                             "its instants and the stamp are not both read on a clock with "
                             "an offset, so no length or coverage can be read from it"))
            continue
        length = (end - start).total_seconds()
        if length > MAX_WAIVER_SECONDS:
            declined.append((start, end, parts[2],
                             "it is %.1f days (%.0f s) long, longer than the declared "
                             "maximum of %.1f days (%.0f s), so a pause written once would "
                             "answer freshness for every week to come" % (
                                 length / 86400, length,
                                 MAX_WAIVER_SECONDS / 86400, MAX_WAIVER_SECONDS)))
            continue
        usable.append((start, end, parts[2]))
    return usable, declined


def verdict(path, now, cadence):
    """(state, detail, declined) -- one shape for every state, so no path skips a name.

    The declined declarations are read BEFORE the state is decided, because they are a
    fact about the record and not about the gap: returning a stamp complaint first left
    a mistyped pause silent on exactly the two states where a reader has least else to
    go on.
    """
    lines, complaint = read_record(path)
    newest = None
    if complaint is None:
        newest, complaint = parse_stamp(lines, path)
    usable, declined = declared_waivers(lines or [], newest)
    if complaint is not None:
        return complaint[0], complaint[1], declined
    gap = (now - newest).total_seconds()
    if gap <= cadence:
        return "fresh", (newest, None), declined
    for start, end, text in usable:
        if start <= newest and now <= end:
            return "covered", (newest, "a pause from %s to %s declared: %s" % (
                start.isoformat(), end.isoformat(), text)), declined
    return "stale", (newest, now, cadence, gap), declined


def stamp(path, now):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write("%s\trun completed\n" % now.isoformat())
    return 0


DECLINED = "REFUSED %s -- a declared pause this run does not use: %s"


def check(path, now, cadence):
    state, detail, declined = verdict(path, now, cadence)
    if state in ("fresh", "covered"):
        # The green line carries no instant, and that is deliberate: this probe is an
        # item of the suite whose own record compares each item's output between runs.
        # A green line naming the newest stamp would differ on every run and make the
        # movement report name an item that has not moved. What has to be named is the
        # SILENCE -- the red line below names both instants and the cadence it compared
        # -- because a gap nobody can date is a gap nobody can check. A declined pause is
        # named too, and it is read from the FILE, so it does not move between runs.
        newest, why = detail
        if state == "fresh":
            print("fresh: a run stamp inside the declared cadence of %d s" % cadence)
        else:
            # The word is `covered`, not `fresh`: the pause is doing the work here, and
            # naming it a fresher version of the same thing is what let a pair of runs
            # straddling this boundary report two lines for one unchanged record.
            print("covered: %s" % why)
        rc = 0
    elif state == "stale":
        newest, then, cad, gap = detail
        print("FAIL STALE  the newest run stamp is %s, %d s before now at %s, and the "
              "declared cadence is %d s: this run has been silent for %.1f cadences" % (
                  newest.isoformat(), int(gap), then.isoformat(), cad, gap / cad))
        rc = 1
    else:
        print("FAIL %s %s" % (state.upper(), detail))
        rc = 1
    # Every state prints the declarations it did not use -- including the two that never
    # reach the gap check. One print path, so no verdict can skip a name.
    for start, end, text, reason in declined:
        print(DECLINED % (text, reason))
    return rc


FIXTURE = """# a run stamp file
2026-09-26T04:00:00+00:00\trun completed
"""

WAIVER = """# a run stamp file
2026-09-20T04:00:00+00:00\trun completed
# waiver 2026-09-20T00:00:00+00:00 | 2026-09-27T00:00:00+00:00 | the fixture tree was frozen
"""

# A pause written once and given an end far beyond the cadence it suspends: measured as a
# reason, it would answer freshness for every week from here on.
WAIVER_ENDLESS = """# a run stamp file
2026-09-01T04:00:00+00:00\trun completed
# waiver 2026-09-01T00:00:00+00:00 | 2099-01-01T00:00:00+00:00 | the tree is frozen for good
"""

# A pause one second longer than the maximum, at the boundary where the arithmetic and the
# prose of the refusal have to agree: 604801 s, printed as 7 days by a truncated `%d`.
WAIVER_PLUS_ONE = """# a run stamp file
2026-09-19T05:00:00+00:00\trun completed
# waiver 2026-09-19T05:00:00+00:00 | 2026-09-26T05:00:01+00:00 | one second past
"""

# A pause exactly at the maximum, covering exactly the gap: 604800 s, allowed.
WAIVER_EXACT = """# a run stamp file
2026-09-19T05:00:00+00:00\trun completed
# waiver 2026-09-19T05:00:00+00:00 | 2026-09-26T05:00:00+00:00 | exactly seven days
"""

# A pause whose instants carry no offset, in a file whose stamp does: nothing can be read
# from it. Before, this reached the comparison and the probe died with a TypeError -- a
# traceback instead of a verdict, on a line a hand-written waiver could plausibly contain.
WAIVER_NAIVE = """# a run stamp file
2026-09-19T05:00:00+00:00\trun completed
# waiver 2026-09-19 05:00:00 | 2026-09-26 05:00:00 | written without an offset
"""

# A mistyped declaration: no space after the `#`, so no reader opens it.
WAIVER_TYPO = """# a run stamp file
2026-09-01T04:00:00+00:00\trun completed
#waiver 2026-09-01T00:00:00+00:00 | 2026-09-27T00:00:00+00:00 | mistyped opener
"""


def selftest() -> int:
    now = datetime.datetime.fromisoformat("2026-09-26T05:00:00+00:00")
    day = 24 * 3600
    checks = []

    def case(name, path, want, needle=None, cadence=day, at=now, want_state=None):
        state, detail, declined = verdict(path, at, cadence)
        text = "red" if state in ("stale", "unreadable", "no_baseline") else "fresh"
        ok = text == want
        if ok and needle is not None:
            # Everything the verdict would print: the detail and every refused line, since
            # the refusal of a pause lives in `declined` now that every state carries it.
            rendered = "%s %s" % (detail, [d[2:] for d in declined])
            ok = needle in rendered
        if ok and want_state is not None:
            ok = state == want_state
        checks.append((ok, name, text, want))

    with tempfile.TemporaryDirectory() as tmp:
        tmp = pathlib.Path(tmp)
        missing = tmp / "absent.log"
        # 1. an absent record is red, and it says why
        case("no record is red, not quiet", missing, "red",
             "a run that never happened")
        # 2. an unparseable line is red
        bad = tmp / "bad.log"; bad.write_text("not a timestamp\n", encoding="utf-8")
        case("an unreadable stamp is red", bad, "red", "is not a timestamp")
        # 3. a stamp with no offset cannot yield a gap
        naive = tmp / "naive.log"
        naive.write_text("2026-09-26T04:00:00\trun\n", encoding="utf-8")
        case("a stamp with no offset is red", naive, "red", "no offset")
        # 4. a fresh stamp is green
        fresh = tmp / "fresh.log"; fresh.write_text(FIXTURE, encoding="utf-8")
        case("a stamp inside the cadence is green", fresh, "fresh")
        # 5. a stale stamp is red and names the cadence it compared
        stale = tmp / "stale.log"
        stale.write_text("2026-09-01T04:00:00+00:00\trun\n", encoding="utf-8")
        case("a stamp older than the cadence is red", stale, "red",
             "86400")
        # 6. the cadence is an argument, not a constant: the same bytes pass at 40 days
        case("the same stale record passes under a wider declared cadence", stale, "fresh",
             cadence=40 * day)
        # 7. a declared waiver is the reason a gap passes, and it is named
        waived = tmp / "waived.log"; waived.write_text(WAIVER, encoding="utf-8")
        case("a declared waiver turns the gap green and is named", waived, "fresh",
             "the fixture tree was frozen")
        # 8. the two red states are told apart by name, not by a sentence a reader
        # would have to parse: a first-ever tick and a corrupt stamp are different
        # repairs. Under a name-only reader they were one state.
        case("a first ever tick is named apart from a corrupt stamp", missing, "red",
             "a run that never happened", want_state="no_baseline")
        case("a corrupt stamp is named apart from a first ever tick", bad, "red",
             "is not a timestamp", want_state="unreadable")
        # 9. a record that holds nothing is repaired like an absent record, and it used to
        # carry the name of a corrupt one: the repair, not the shape of the failure, is
        # what the name has to say.
        empty = tmp / "empty.log"; empty.write_text("# nothing but a comment\n",
                                                    encoding="utf-8")
        case("a record with no stamp line is a missing baseline, not a corrupt one",
             empty, "red", "carries no stamp line at all", want_state="no_baseline")
        # 10. a waiver with no end is not a reason. A pause longer than the declared
        # maximum leaves the gap RED and the refusal names the waiver and its length,
        # because one line written once would otherwise answer freshness for every
        # week from here on.
        endless = tmp / "endless.log"; endless.write_text(WAIVER_ENDLESS, encoding="utf-8")
        case("a waiver with an end past the maximum is not a reason for the gap",
             endless, "red", "the tree is frozen for good", want_state="stale")
        # 11. the bound's VALUE is pinned, not its presence: a selftest that only asked
        # whether some bound exists stayed green when the bound was widened to 300 days.
        checks.append((MAX_WAIVER_SECONDS == 7 * 24 * 3600,
                       "the declared maximum is seven days", MAX_WAIVER_SECONDS,
                       604800))
        # 11b. the cadence is pinned for the same reason, and it is the one constant the
        # selftest's own --cadence-seconds argument can never pin: widening it changes
        # which silences count as health, and every case below that passes --cadence-seconds
        # would stay green while the running default did not.
        checks.append((CADENCE_SECONDS == 24 * 3600,
                       "the cadence the runner ticks at is twenty-four hours",
                       CADENCE_SECONDS, 86400))
        exact = tmp / "exact.log"; exact.write_text(WAIVER_EXACT, encoding="utf-8")
        case("a pause exactly at the maximum covers a gap exactly at the maximum",
             exact, "fresh", "exactly seven days")
        plus1 = tmp / "plus1.log"; plus1.write_text(WAIVER_PLUS_ONE, encoding="utf-8")
        case("a pause one second past the maximum is refused", plus1, "red",
             "one second past", want_state="stale")

        # 12. every printed red carries its state name, the commonest one included: the
        # `stale` line used to name the state nowhere, so a reader had to grep a sentence.
        import contextlib, io
        def said(target, at):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                check(target, at, day)
            return buf.getvalue()
        red_stale = said(stale, now)
        named_states = (("STALE" in red_stale) and ("UNREADABLE" in said(bad, now))
                        and ("NO_BASELINE" in said(missing, now)))
        checks.append((named_states and "86400" in red_stale
                       and "2026-09-01T04:00:00+00:00" in red_stale,
                       "every red names its state and the stale one dates the gap",
                       "named" if named_states else "anonymous",
                       "named"))

        # 13. a declaration the reader declines is NAMED, on a green verdict too. Silence
        # about a declined pause is what let a mistyped or unbounded one read as obeyed.
        both = tmp / "two.log"
        both.write_text("2026-09-26T04:00:00+00:00\trun completed\n"
                        "# waiver 2026-09-01T00:00:00+00:00 | 2099-01-01T00:00:00+00:00 | "
                        "the tree is frozen for good\n", encoding="utf-8")
        green_refusal = said(both, now)
        typo = tmp / "typo.log"; typo.write_text(WAIVER_TYPO, encoding="utf-8")
        naive_waiver = tmp / "naive_waiver.log"
        naive_waiver.write_text(WAIVER_NAIVE, encoding="utf-8")
        naive_said = said(naive_waiver, now)
        refused_named = ("REFUSED" in green_refusal
                         and "the tree is frozen for good" in green_refusal
                         and "26420.0 days" in green_refusal
                         and "REFUSED" in said(typo, now)
                         and "declared form" in said(typo, now)
                         and "REFUSED" in naive_said
                         and "an offset" in naive_said)
        checks.append((refused_named and green_refusal.startswith("fresh:"),
                       "a declined declaration is named, and the gap it did not cover "
                       "is still judged",
                       "named" if refused_named else "silent", "named"))

        # 14. the refusal's arithmetic is the refusal's own number: 604801 s printed as
        # "7 days" would tell the reader the refused pause was the maximal allowed one.
        plus1_said = said(plus1, now)
        honest = ("604801" in plus1_said and "7.0 days" in plus1_said
                  and "no end" not in plus1_said)
        checks.append((honest, "the refusal prints the length it refused",
                       "honest" if honest else "rounded",
                       "honest"))

        # 15. the green line is the same on two runs; it names no instant of the run. The
        # refused pause IS named, and it comes from the file, so it does not move either.
        # "Run-stable" is per CLASSIFICATION: a record kept inside one class is byte-equal
        # across `now`, and the pause line is equal because it names the file's span, not
        # the clock. Two greens that differ are two classes, not a moving line.
        same = said(fresh, now) == said(fresh, now + datetime.timedelta(minutes=17))
        same_refusal = (said(both, now) == said(both, now + datetime.timedelta(minutes=17)))
        paused_said = said(waived, now)
        same_pause = paused_said == said(waived, now + datetime.timedelta(hours=13))
        stable = same and same_refusal and same_pause and "86400" not in paused_said
        checks.append((stable,
                       "a green line names no instant of the run",
                       "stable" if stable else "moves", "stable"))

        # 15b. one record, two instants, two green words. The instant a pause begins to do
        # the work it was written for is a boundary of the STATE, not of the line: the same
        # bytes are `fresh` while the stamp is inside the cadence and `covered` once the gap
        # is longer than the cadence and the declared pause reaches over it. Printed under
        # one word, a run that straddled this boundary reported a moved record where only
        # the clock had moved; named apart, the state word says which answer was given.
        at_start = datetime.datetime.fromisoformat("2026-09-20T05:00:00+00:00")
        inside, _, _ = verdict(waived, at_start, day)
        crossed, _, _ = verdict(waived, now, day)
        checks.append((inside == "fresh" and crossed == "covered",
                       "a pause that has begun to do the work is named apart from a stamp "
                       "inside the cadence",
                       "%s/%s" % (inside, crossed), "fresh/covered"))

        # 16. the cadence boundary is `<=`, not `<`: a stamp exactly one cadence old is
        # inside it. The comparison's direction is a rule, and a `<` left the selftest
        # green (mutant M1) because no fixture sat on the boundary.
        edge = tmp / "edge.log"
        edge.write_text("%s\trun\n" % (now - datetime.timedelta(seconds=day)).isoformat(),
                        encoding="utf-8")
        over = tmp / "over.log"
        over.write_text("%s\trun\n" % (now - datetime.timedelta(seconds=day + 1)).isoformat(),
                        encoding="utf-8")
        at_edge = verdict(edge, now, day)[0] == "fresh"
        past_edge = verdict(over, now, day)[0] == "stale"
        checks.append((at_edge and past_edge,
                       "a stamp exactly one cadence old is inside the cadence",
                       "%s/%s" % (verdict(edge, now, day)[0], verdict(over, now, day)[0]),
                       "fresh/stale"))

        # 17. coverage is BOTH ends of the pause, and the rule is `and`. A pause that
        # covers the stamp but ended before now, and one that begins after the stamp and
        # covers now, are each not a reason -- an `or` here passed an expired waiver off as
        # a declared one, with the selftest green (mutant M4).
        expired = tmp / "expired.log"
        expired.write_text("2026-09-09T00:00:00+00:00\trun\n"
                           "# waiver 2026-09-09T00:00:00+00:00 | "
                           "2026-09-12T00:00:00+00:00 | ended a fortnight ago\n",
                           encoding="utf-8")
        late = tmp / "late.log"
        late.write_text("2026-09-09T00:00:00+00:00\trun\n"
                        "# waiver 2026-09-20T00:00:00+00:00 | "
                        "2026-10-01T00:00:00+00:00 | starts after the stamp\n",
                        encoding="utf-8")
        cov = (verdict(expired, now, day)[0] == "stale"
               and verdict(late, now, day)[0] == "stale")
        checks.append((cov, "a pause must cover the stamp AND reach now",
                       "%s/%s" % (verdict(expired, now, day)[0],
                                  verdict(late, now, day)[0]), "stale/stale"))

        # 18. the record's newest stamp is chosen by comparing instants, not by position:
        # a file whose stamps are out of order, and one with a blank line among them,
        # must both read as the newest one they carry (mutants M5, M6 sit on this).
        unordered = tmp / "unordered.log"
        unordered.write_text("2026-09-26T04:00:00+00:00\trun completed\n"
                             "\n"
                             "2026-08-01T04:00:00+00:00\tthe older run, written later\n",
                             encoding="utf-8")
        checks.append((verdict(unordered, now, day)[0] == "fresh",
                       "the newest stamp is chosen by instant, blank lines included",
                       verdict(unordered, now, day)[0], "fresh"))

        # 19. a declaration whose KEYWORD is mistyped is named, like a mistyped opener: a
        # reader that only greps one spelling reports nothing at all (mutant M10).
        caps = tmp / "caps.log"
        caps.write_text("2026-09-01T04:00:00+00:00\trun\n"
                        "# WAIVER 2026-09-01T00:00:00+00:00 | "
                        "2026-09-27T00:00:00+00:00 | shouted\n", encoding="utf-8")
        spelled = said(caps, now)
        checks.append(("REFUSED" in spelled and "declared form" in spelled,
                       "a mistyped keyword is named, not silently dropped",
                       "named" if "REFUSED" in spelled else "silent", "named"))

        # 20. a stamp that merely mentions a pause is not a declined one. Naming it refused
        # reported the reader as having declined a line it had in fact read as the stamp.
        mention = tmp / "mention.log"
        mention.write_text("2026-09-26T04:00:00+00:00\trun completed, waiver not used\n",
                           encoding="utf-8")
        mentioned = said(mention, now)
        prose = tmp / "prose.log"
        prose.write_text("2026-09-26T04:00:00+00:00\trun\n"
                         "# the waiver is described in the notes\n", encoding="utf-8")
        checks.append(("REFUSED" not in mentioned and "REFUSED" not in said(prose, now)
                       and mentioned.startswith("fresh:"),
                       "a line that only mentions a pause is not a declined one",
                       mentioned.splitlines()[0][:20], "fresh:"))

        # 21. a declaration the reader declines is named on the two states that never reach
        # the gap check as well: those returned the stamp complaint before reading the
        # declarations, so a mistyped pause was silent exactly where least else is said.
        silent_typo = tmp / "a_nostamp_typo.log"
        silent_typo.write_text("# nothing but a comment\n"
                               "#waiver 2026-09-01T00:00:00+00:00 | "
                               "2026-09-27T00:00:00+00:00 | mistyped opener\n",
                               encoding="utf-8")
        silent_corrupt = tmp / "b_corrupt_typo.log"
        silent_corrupt.write_text("not a timestamp\n"
                                  "#waiver 2026-09-01T00:00:00+00:00 | "
                                  "2026-09-27T00:00:00+00:00 | mistyped opener\n",
                                  encoding="utf-8")
        on_all = ("REFUSED" in said(silent_typo, now)
                  and "REFUSED" in said(silent_corrupt, now))
        checks.append((on_all,
                       "a declined declaration is named on every state, not just the gap",
                       "named" if on_all else "silent", "named"))

        # 22. an entry that cannot be read is a VERDICT, not a traceback: a directory, bytes
        # that are not UTF-8 and a link that leads nowhere used to end in IsADirectoryError
        # or UnicodeDecodeError with no state word at all.
        as_dir = tmp / "dir.log"
        as_dir.mkdir()
        binary = tmp / "binary.log"
        binary.write_bytes(b"2026-09-26T04:00:00+00:00\trun\n\xff\xfe not utf-8\n")
        dangling = tmp / "dangling.log"
        dangling.symlink_to(tmp / "nowhere_at_all")
        outcomes = []
        for probe_path in (as_dir, binary, dangling):
            try:
                outcomes.append(verdict(probe_path, now, day)[0])
            except Exception as exc:  # a traceback is the defect this case exists for
                outcomes.append(type(exc).__name__)
        checks.append((outcomes == ["unreadable"] * 3,
                       "a record that cannot be read is a state, not a traceback",
                       "/".join(outcomes), "unreadable/unreadable/unreadable"))

        # 23. the refusal quotes the declaration's REASON, not the raw line: a reader told
        # "this line was declined" with the timestamp pair quoted back has to guess which
        # pause was meant (mutant M17).
        over_reason = "the tree is frozen for good"
        over_said = said(endless, now)
        checks.append((("REFUSED %s" % over_reason) in over_said,
                       "the refusal quotes the declined pause's own reason",
                       over_said.splitlines()[-1][:20], "REFUSED the tree is fro"))
        # 24. the attempt gate reads the HEAD of the line, not its separator count: prose
        # that mentions a pause mid-sentence and carries a pipe was printed as a refused
        # declaration, which reports the reader as having declined a line it never read as
        # a pause.
        prose_pipe = tmp / "prose_pipe.log"
        prose_pipe.write_text("2026-09-26T04:00:00+00:00\trun completed\n"
                              "# we paused the suite for the release | see notes\n",
                              encoding="utf-8")
        pipe_said = said(prose_pipe, now)
        checks.append(("REFUSED" not in pipe_said,
                       "prose with a separator is not a declined declaration",
                       "named" if "REFUSED" in pipe_said else "silent", "silent"))

        # 25. a mistyped declaration that lost its separators is still NAMED. With a gate
        # on the field count it was dropped in silence -- the writer of a declined pause
        # read a green run as an obeyed one, which is what the naming exists for.
        short_fields = tmp / "short_fields.log"
        short_fields.write_text("2026-09-26T04:00:00+00:00\trun completed\n"
                                "#waive 2026-09-01T00:00:00+00:00 the tree is frozen\n",
                                encoding="utf-8")
        short_said = said(short_fields, now)
        checks.append(("REFUSED" in short_said,
                       "a mistyped declaration with no separators is named",
                       "named" if "REFUSED" in short_said else "silent", "named"))

        # 26. `pause` is a pause word, not only `waiv`. No fixture spelled it, so removing
        # it from the vocabulary left every check green.
        pause_word = tmp / "pause_word.log"
        pause_word.write_text("2026-09-26T04:00:00+00:00\trun completed\n"
                              "# pause 2026-09-01T00:00:00+00:00 | "
                              "2026-09-27T00:00:00+00:00 | the tree is frozen\n",
                              encoding="utf-8")
        pause_said = said(pause_word, now)
        checks.append(("REFUSED" in pause_said,
                       "the word pause opens a declaration like the word waiver",
                       "named" if "REFUSED" in pause_said else "silent", "named"))

        # 27. the newest stamp is chosen by INSTANT across offsets, not by string. A record
        # whose string-maximum is 33 h old and whose true newest is 20 h old reads as fresh
        # when the instants are compared and as a silence when the strings are.
        offsets = tmp / "offsets.log"
        offsets.write_text("2026-09-24T23:00:00+00:00\trun completed\n"
                           "2026-09-25T00:00:00+14:00\tthe same run, written elsewhere\n",
                           encoding="utf-8")
        string_now = datetime.datetime.fromisoformat("2026-09-25T19:00:00+00:00")
        by_instant = verdict(offsets, string_now, day)[0]
        by_string = max(
            [l.split("\t")[0] for l in offsets.read_text(encoding="utf-8").splitlines()
             if l and not l.startswith("#")])
        checks.append((by_instant == "fresh"
                       and (string_now - datetime.datetime.fromisoformat(by_string)
                            ).total_seconds() > day,
                       "the newest stamp is chosen by instant across offsets",
                       by_instant, "fresh"))

    failed = [c for c in checks if not c[0]]
    for ok, name, state, want in checks:
        print("ok   %-58s %s" % (name, state) if ok
              else "FAIL %-58s %s (want %s)" % (name, state, want))
    print("SELFTEST=%d (%d checks)" % (1 if failed else 0, len(checks)))
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=str(STAMP))
    ap.add_argument("--cadence-seconds", type=int, default=CADENCE_SECONDS)
    ap.add_argument("--stamp", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--now")
    args = ap.parse_args()
    if args.now:
        try:
            now = datetime.datetime.fromisoformat(args.now)
        except ValueError:
            # A caller's typo is a sentence about the flag, not a traceback: the probe
            # answers with states, and a clock it cannot read is one of them.
            ap.error("--now is not a timestamp: %r" % args.now)
    else:
        now = datetime.datetime.now(datetime.timezone.utc)
    if now.tzinfo is None:
        # A clock without an offset cannot be read against a stamp that has one, and
        # assuming UTC would answer a question the caller did not ask.
        ap.error("--now must carry an offset, e.g. 2026-09-26T05:00:00+00:00")
    path = pathlib.Path(args.file)
    if args.selftest:
        return selftest()
    if args.stamp:
        return stamp(path, now)
    if args.check:
        return check(path, now, args.cadence_seconds)
    ap.error("choose one of --stamp, --check, --selftest")


if __name__ == "__main__":
    raise SystemExit(main())
