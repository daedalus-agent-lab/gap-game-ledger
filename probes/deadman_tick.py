#!/usr/bin/env python3
"""A heartbeat that reads silence as health: the standing suite's own last run.

The suite writes what it measured for every tree it ran on, and nothing anywhere
says WHEN it last ran. A week with no run and a week with nothing to report leave
the same artefact -- none -- so a run that stopped ticking is byte-identical to a
run that found nothing. This probe reads a run stamp the runner appends to and
answers four ways, and the state NAME is machine-readable because the reader of a
verdict should not have to parse a sentence to learn which question was answered:

  fresh       the newest stamp is inside the declared cadence;
  stale       the newest stamp is older than the cadence, and the refusal NAMES both
              instants and the cadence it compared;
  no_baseline no stamp file at all -- a run that never happened. It is RED, but it
              is not the same state as a record that cannot be read: the repair
              differs, so the name differs;
  unreadable  a stamp line that is not a timestamp, no offset on the newest stamp,
              or a file that carries no stamp line: the record is here and is not
              readable.

A declared, dated waiver is the only way a gap is allowed, and it is named when it
is the reason the gap passed.

  python3 probes/deadman_tick.py --stamp            # the runner's line
  python3 probes/deadman_tick.py --check            # the verdict
  python3 probes/deadman_tick.py --selftest         # each claim above, on fixtures
"""
import argparse
import datetime
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent
STAMP = REPO / "repro" / "fresco" / "tick.log"
CADENCE_SECONDS = 24 * 3600


def parse_stamp(path: pathlib.Path):
    """(newest instant, reason) -- reason is not None when there is no verdict."""
    newest = None
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        head = line.split("\t")[0].strip()
        try:
            when = datetime.datetime.fromisoformat(head)
        except ValueError:
            return None, "line %d of %s is not a timestamp: %r -- an unreadable record " \
                         "is a red, not a gap of zero" % (n, path.name, line[:60])
        if newest is None or when > newest:
            newest = when
    if newest is None:
        return None, "%s carries no stamp line at all" % path.name
    if newest.tzinfo is None:
        return None, "the newest stamp %s carries no offset, so no gap can be read " \
                     "from it" % newest.isoformat()
    return newest, None


def waivers(path: pathlib.Path):
    """Declared, dated pauses: (start, end, text) with both ends inclusive."""
    out = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("# waiver "):
            continue
        body = line[len("# waiver "):]
        parts = [p.strip() for p in body.split("|")]
        if len(parts) < 3:
            continue
        try:
            start = datetime.datetime.fromisoformat(parts[0])
            end = datetime.datetime.fromisoformat(parts[1])
        except ValueError:
            continue
        out.append((start, end, parts[2]))
    return out


def verdict(path, now, cadence):
    if not path.exists():
        # Its own state, not a flavour of unreadable: a first-ever tick is repaired by
        # making the runner tick, a corrupt stamp by fixing the file.
        return "no_baseline", "no run stamp at %s: a run that never happened and a " \
                              "run with nothing to report leave the same record, so " \
                              "this is red and not quiet" % (
                                  path.relative_to(REPO) if REPO in path.parents else path)
    newest, why = parse_stamp(path)
    if why is not None:
        return "unreadable", why
    gap = (now - newest).total_seconds()
    if gap <= cadence:
        return "fresh", newest
    for start, end, text in waivers(path):
        if start <= newest and now <= end:
            return "fresh", (newest, "a declared waiver covers this gap: %s" % text)
    return "stale", (newest, now, cadence, gap)


def stamp(path, now):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write("%s\trun completed\n" % now.isoformat())
    return 0


def check(path, now, cadence):
    state, detail = verdict(path, now, cadence)
    if state == "fresh":
        # The green line carries no instant, and that is deliberate: this probe is an
        # item of the suite whose own record compares each item's output between runs.
        # A green line naming the newest stamp would differ on every run and make the
        # movement report name an item that has not moved. What has to be named is the
        # SILENCE -- the red line below names both instants and the cadence it compared
        # -- because a gap nobody can date is a gap nobody can check.
        if isinstance(detail, tuple):
            print("fresh: a declared waiver covers the gap (%s)" % detail[1])
        else:
            print("fresh: a run stamp inside the declared cadence of %d s" % cadence)
        return 0
    if state == "stale":
        newest, then, cad, gap = detail
        print("FAIL the newest run stamp is %s, %d s before now at %s, and the declared "
              "cadence is %d s: this run has been silent for %.1f cadences" % (
                  newest.isoformat(), int(gap), then.isoformat(), cad, gap / cad))
        return 1
    print("FAIL %s %s" % (state.upper(), detail))
    return 1


FIXTURE = """# a run stamp file
2026-09-26T04:00:00+00:00\trun completed
"""

WAIVER = """# a run stamp file
2026-09-20T04:00:00+00:00\trun completed
# waiver 2026-09-20T00:00:00+00:00 | 2026-09-27T00:00:00+00:00 | the fixture tree was frozen
"""


def selftest() -> int:
    now = datetime.datetime.fromisoformat("2026-09-26T05:00:00+00:00")
    day = 24 * 3600
    checks = []

    def case(name, path, want, needle=None, cadence=day, at=now, want_state=None):
        state, detail = verdict(path, at, cadence)
        text = "red" if state in ("stale", "unreadable", "no_baseline") else "fresh"
        ok = text == want
        if ok and needle is not None:
            rendered = str(detail)
            ok = needle in (rendered if state == "stale" else
                            (detail if isinstance(detail, str) else str(detail)))
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
        # 8. the green line is the same on two runs, the red line is not: the suite's own
        # record compares each item's output between runs, so a green line carrying the
        # instant would name an item as moved on every run.
        import contextlib, io
        def said(target, at):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                check(target, at, day)
            return buf.getvalue()
        same = said(fresh, now) == said(fresh, now + datetime.timedelta(minutes=17))
        red = said(stale, now)
        named = "2026-09-01T04:00:00+00:00" in red and "86400" in red
        # 9. the two red states are told apart by name, not by a sentence a reader
        # would have to parse: a first-ever tick and a corrupt stamp are different
        # repairs. Under a name-only reader they were one state.
        case("a first ever tick is named apart from a corrupt stamp", missing, "red",
             "a run that never happened", want_state="no_baseline")
        case("a corrupt stamp is named apart from a first ever tick", bad, "red",
             "is not a timestamp", want_state="unreadable")
        checks.append((same and named,
                       "the green line is run-stable, the red line dates the gap",
                       "stable" if same and named else "moves", "stable"))
    failed = [c for c in checks if not c[0]]
    for ok, name, state, want in checks:
        print("ok   %-52s %s" % (name, state) if ok
              else "FAIL %-52s %s (want %s)" % (name, state, want))
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
    now = (datetime.datetime.fromisoformat(args.now) if args.now
           else datetime.datetime.now(datetime.timezone.utc))
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
