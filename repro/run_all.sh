#!/usr/bin/env bash
# The standing regression run for the fresco work: every probe and attestation
# this project has published, in one command, with a single exit code --
# and, for each item, a *consequence*: the digest of what the item actually
# said. exit 0 is not a receipt. A run that prints the same words as yesterday
# and a run that prints different words both exit 0; only the digest tells them
# apart, and only a published digest can be checked by someone else.
#
# A digest over output that carries a freshly minted value every run is not a
# receipt either: it changes for a reason that is not behaviour. So every item's
# output is normalised at DECLARED fields only (minted stream keys), the NUMBER
# of substitutions is printed and digested alongside the text, and --stable
# proves that the declaration hides nothing: run twice, require the normalised
# outputs to be identical, and require every raw difference to fall on a
# declared field. A difference anywhere else fails the item.
#
#   bash run_all.sh                 # run everything (wall tiles cached)
#   bash run_all.sh --net           # also re-attest the wall from the served files
#   bash run_all.sh --stable        # run each item twice and prove the normaliser is honest
#   bash run_all.sh --expect <d>    # fail unless the aggregate digest is <d>
#
# In the published reproduction layout (the public ledger repo carries a
# "repro/" mirror of the working tree) both roots are given explicitly:
#   REPRO_WS=$PWD/repro REPRO_LEDGER=$PWD bash repro/run_all.sh --net --stable
#   bash run_all.sh --self-test     # show a behaviour change an exit code cannot see
#
# Exit 0 only when every item passes (and the digest matches, if expected).
set -u
# The runner is invoked both ways -- `bash run_all.sh` from inside this directory
# and `bash repro/run_all.sh` from the tree above it -- and the second one used to
# walk out of a path that only exists in the first: `cd "$(dirname "$0")"` lands
# in repro/ and then `cd repro/..` is asked from inside it, so the suite ran with
# an empty workspace and every item that names one failed for a reason that was
# neither the code nor the wall. The directory is resolved once, absolutely.
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
# The defaults are the documented invocation, and they were both wrong here in a
# way that only a second reader would feel: the script assumed a published clone
# keeps the ledger in a `gap-game-ledger/` subdirectory, so `bash repro/run_all.sh`
# from the working tree looked for `gap-game-ledger/gap-game-ledger/check.py` and
# every item that names a file failed with `No such file or directory`. A run whose
# failures are all path errors reads exactly like a broken tree, and the four items
# that do not name a file still passed, which is the worst shape a failure can have.
# The mirror is the directory this script lives in; the ledger is its parent.
# `git clone` + `cd gap-game-ledger` + the invocation in README.md are the contract,
# and the defaults now match it: REPRO_WS=$PWD/repro, REPRO_LEDGER=$PWD.
WS="${REPRO_WS:-$HERE}"
LEDGER="${REPRO_LEDGER:-$(cd "$HERE/.." && pwd)}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$WS/.uvcache}"
REQUIRE=""; NET=0; SELFTEST=0; STABLE=0; GUARD_CONTROL=0
while [ $# -gt 0 ]; do
  case "$1" in
    --net) NET=1 ;;
    --stable) STABLE=1 ;;
    --expect) REQUIRE="${2:-}"; shift ;;
    --self-test) SELFTEST=1 ;;
    --guard-control) GUARD_CONTROL=1 ;;
  esac
  shift
done

# The stamp of THIS run, written before any item, by the runner itself: a probe can
# measure the delay since the last run, but it cannot see a run that never started, and
# only the runner knows that it started. It is appended, never rewritten, so the record
# keeps a history rather than a status; the line carries an absolute instant with an
# offset, because a bare local time is not a moment any other machine can compare against.
# Not written in --guard-control mode: that mode drives the guard on fixture records and
# does not run the suite, and a check that appends to the record it reads is not a check.
if [ "$GUARD_CONTROL" != 1 ]; then
  python3 "$LEDGER/probes/deadman_tick.py" --stamp || true
fi

sha16() { sha256sum | cut -c1-16; }
# Two digests per item, because a receipt is over a PAIR (the bytes, the harness)
# and one of the two nearly-undeclared inputs is the order of the lines. A
# measurement taken with stdout on a file and the same measurement with stdout on
# a pipe can print the same SET of lines in two orders -- a second holder
# measured exactly that, two stable digests over one byte-identical line set --
# and then a reader comparing two ordered digests is comparing two harnesses.
# So the set digest rides beside the ordered one: `out` is what this harness
# printed in this order, `set` is the multiset of lines, and `out` moving while
# `set` stands still is a statement about the pipe, not about the code.
# The one declared field: a stream key minted at read time. Its shape is fixed
# (16 hex), and the count of substitutions is reported so a change in how many
# there are is itself a difference.
normalise() { sed -E 's/\bkey [0-9a-f]{16}\b/key <minted>/g'; }
declared_lines() { grep -cE '\bkey [0-9a-f]{16}\b'; }

# Two readings of the item list, from two places: the names the loop ran, appended by
# `run` as it ran them, and the names the record carries. The row count is the same
# number on both sides when a row is built with a name that is not the item's name, so
# counting cannot see it -- a record whose rows number what ran and whose names are not
# those names is a record of a different run. Ordered, because two runs of one item in
# two orders are not two readings of one item.
names_differ() {              # names_differ <names the loop ran> <names the record carries>
  ! diff <(printf '%s\n' "$1") <(printf '%s\n' "$2") >/dev/null
}

# One row of the record: <name>|<the command's status>|<the harness's verdict>|...
# Two numbers, two writers, and for as long as they shared one field a reader could
# not tell them apart. The verdict is 0 when the item passed, 1 when the item failed,
# 2 when the harness could not certify the item at all (the tree moved under it, or its
# two runs disagreed); the command's own status is written beside it, not folded into
# it, so a command that exits 2 -- the code every probe in this repo uses for "that is
# not an argument I read, so I did not measure" -- stays visible as a refusal instead
# of reading as a disagreement.
row_of() { printf '%s|%s|%s|%s|%s|%s\n' "$1" "$2" "$3" "$4" "$5" "$6"; }

# The record carries two numbers per item and they have two writers, so the comparison
# between two records is a function here rather than a heredoc in the middle of the run:
# --self-test has to be able to call the same printer the run calls.
# The line names the fields that MOVED, and only those. Printing all five pairs leaves
# the reader to compare ten numbers to find the one that changed, which is the question
# the line exists to answer; an unchanged field repeated beside a changed one is a
# sentence about the record, not a finding. --self-test below measures both halves: a
# row differing in one field names that field and does not name the others.
diff_records() {              # diff_records <previous record> <this record>
  python3 - "$1" "$2" <<'PY'
import json, sys
prev, new = (json.load(open(p)) for p in sys.argv[1:3])
if prev.get("items") and "cert" not in prev["items"][0]:
    print("the recorded run beside this tree predates the separated verdict field:")
    print("    it carries `exit` alone, written by three different branches, so nothing")
    print("    here compares two runs of one record. The next run records both fields.")
    sys.exit(0)
FIELDS = ("exit", "cert", "out", "set", "norm")
a = {i["name"]: (i["exit"], i.get("cert"), i["out"], i.get("set"), i["normalised"])
     for i in prev.get("items", [])}
b = {i["name"]: (i["exit"], i.get("cert"), i["out"], i.get("set"), i["normalised"])
     for i in new["items"]}
moved = [n for n in b if n in a and a[n] != b[n]]
gone = [n for n in a if n not in b]
fresh = [n for n in b if n not in a]
if moved:
    print("moved since the last recorded run on this tree:")
    for n in moved:
        pairs = [f"{f} {a[n][k]}->{b[n][k]}"
                 for k, f in enumerate(FIELDS) if a[n][k] != b[n][k]]
        print(f"    {n}: " + "  ".join(pairs))
if gone or fresh:
    print(f"items added {fresh or 'none'}, removed {gone or 'none'}")
if not (moved or gone or fresh):
    print("no item moved since the last recorded run on this tree")
PY
}

# A row is a record only if it can be read back. The row separator is a real newline, so a
# name that itself carries a newline splits one row into two and the reader of the rows --
# the JSON heredoc below -- dies with a traceback before the count it feeds exists. The
# guard fired and protected the record, but the sentence the reader got was a traceback
# and a blank number, which is not a finding about the run. The offending row is named
# here instead, from the same row string the run writes the record from.
row_complaint() {             # row_complaint  (reads the rows on stdin)
  # Written with `-c` and not a heredoc: a heredoc takes stdin for the SCRIPT, so the rows
  # piped in would never be read -- the complaint answered "0 line(s)" for a row it had not
  # looked at, which is the shape of every defect in this registry.
  python3 -c '
import sys
lines = sys.stdin.read().split("\n")
if lines and lines[-1] == "":
    lines.pop()
bad = 0
for n, line in enumerate(lines, 1):
    if len(line.rsplit("|", 5)) != 6:
        print(f"    row {n} of this run does not carry six fields: a name with a newline")
        print(f"    in it splits one row into two. It reads: {line!r}")
        bad += 1
        if bad >= 3:
            break
print(f"    {len(lines)} line(s) were printed for the rows of this run")
'
}

SUITE_RECORD="$WS/fresco/regression.json"   # this run's own output, declared once
record_rel="$SUITE_RECORD"
case "$record_rel" in "$LEDGER"/*) record_rel="${record_rel#"$LEDGER"/}";; *) record_rel="";; esac

tree_state() {                # a digest of the tree every item is reading
  { git -C "$LEDGER" rev-parse HEAD 2>/dev/null
    # The suite writes its own record inside the tree it certifies. Counted here,
    # that file makes the digest answer a question about the harness in the voice
    # of a question about the record: after any run a clean clone shows one moved
    # path, so "how many paths moved" no longer separates a reader's edit from this
    # script's. The exclusion is one declared path, and --self-test measures it in
    # BOTH directions -- its own record must not move the digest, and an untracked
    # file beside it must -- so it cannot widen without the self-test saying so.
    if [ -n "$record_rel" ]; then
      git -C "$LEDGER" status --porcelain 2>/dev/null | grep -vF -e " $record_rel" || true
    else
      git -C "$LEDGER" status --porcelain 2>/dev/null
    fi
  } | sha16
}

# The guard on the record, as a function, so that it can be driven on fixture records
# by --guard-control below. Two numbers read from two places -- the loop's own counter,
# and the rows the run printed -- because a count printed from the string it is checked
# against is not a check; and the names read from outside the row string, because a name
# compared with itself is not a comparison. Both refusals name the number and the item.
record_guard() {              # record_guard <record json> <names file> <rows file> <items run> <label>
  local rec="$1" names_file="$2" rows_file="$3" want="$4" label="$5" ran record_names
  recorded="$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["items"]))' "$rec")"
  printed="$(grep -c . "$rows_file")"
  if [ "$recorded" != "$want" ] || [ "$printed" != "$want" ]; then
    printf 'FAIL %-34s the record carries %s row(s) and the run printed %s, for %s item(s) run\n' \
           "$label" "$recorded" "$printed" "$want"
    return 1
  fi
  ran="$(cat "$names_file")"
  record_names="$(python3 - "$rec" <<'PY'
import json, sys
for item in json.load(open(sys.argv[1]))["items"]:
    print(item["name"])
PY
)"
  if names_differ "$ran" "$record_names"; then
    printf 'FAIL %-34s the record carries %s row(s) for %s item(s) run, and its rows are\n' \
           "$label" "$recorded" "$want"
    printf '     not the items that ran. First difference:\n'
    diff <(printf '%s\n' "$ran") <(printf '%s\n' "$record_names") | sed -n '1,6p' | sed 's/^/       /'
    return 1
  fi
  return 0
}

# A control that has to be remembered is not a control. This mode drives record_guard
# and row_complaint on fixture records and REQUIRES each of the five readings: a record
# that is this run's is accepted in silence, one whose rows are not the items that ran is
# refused by the names, one that is not as long as the run is refused by the count, a row
# that cannot be read back is named, and readable rows are not refused. It is reached the
# way a reader reaches the suite -- `bash repro/run_all.sh --guard-control`, and as an item
# in the default item list below -- so no path that runs the suite can skip it.
if [ "$GUARD_CONTROL" = 1 ]; then
  ctl="$(mktemp -d)"
  printf 'alpha\nbeta\n' > "$ctl/names"
  printf 'alpha|0|0|aaaaaaaaaaaaaaaa|0|bbbbbbbbbbbbbbbb\nbeta|0|0|cccccccccccccccc|0|dddddddddddddddd\n' > "$ctl/rows"
  printf '{"items":[{"name":"alpha"},{"name":"beta"}]}\n' > "$ctl/good.json"
  printf '{"items":[{"name":"alpha"},{"name":"hijacked"}]}\n' > "$ctl/bad-name.json"
  printf '{"items":[{"name":"alpha"}]}\n' > "$ctl/bad-count.json"
  ok=1
  out="$(record_guard "$ctl/good.json" "$ctl/names" "$ctl/rows" 2 "the control")" \
    || { ok=0; printf 'the control: a record that IS this run was refused:\n%s\n' "$out"; }
  [ -z "$out" ] || { ok=0; printf 'the control: a faithful record was not accepted in silence:\n%s\n' "$out"; }
  out="$(record_guard "$ctl/bad-name.json" "$ctl/names" "$ctl/rows" 2 "the control")" || true
  case "$out" in
    *'not the items that ran'*) ;;
    *) ok=0; printf 'the control: a record whose rows are not the items that ran was NOT refused:\n%s\n' "$out" ;;
  esac
  out="$(record_guard "$ctl/bad-count.json" "$ctl/names" "$ctl/rows" 2 "the control")" || true
  # The needle is a phrase only the count refusal carries. The first version matched
  # `for 2 item(s) run`, which the name refusal also prints, so a mutant with the count
  # half removed still read as green: a needle a second reading can satisfy is not a
  # control on this one.
  case "$out" in
    *'and the run printed'*) ;;
    *) ok=0; printf 'the control: a record that is not as long as the run was NOT refused:\n%s\n' "$out" ;;
  esac
  out="$(printf 'alpha|0|0|aaaaaaaaaaaaaaaa|0|bbbbbbbbbbbbbbbb\nbe\nta|0|0|cccccccccccccccc|0|dddddddddddddddd\n' | row_complaint 2>&1)"
  case "$out" in
    *'does not carry six fields'*) ;;
    *) ok=0; printf 'the control: a row that cannot be read back was NOT named:\n%s\n' "$out" ;;
  esac
  out="$(printf 'alpha|0|0|aaaaaaaaaaaaaaaa|0|bbbbbbbbbbbbbbbb\nbeta|0|0|cccccccccccccccc|0|dddddddddddddddd\n' | row_complaint 2>&1)"
  case "$out" in
    *'does not carry six fields'*)
      ok=0; printf 'the control: readable rows were refused by the row complaint:\n%s\n' "$out" ;;
  esac
  rm -rf "$ctl"
  if [ "$ok" = 1 ]; then
    echo "the record guard refuses a record that is not this run's, accepts one that is, and names a row it cannot read (five readings)"
    exit 0
  fi
  echo "the record guard did not answer as required: a guard that cannot be shown to fire is not a guard"
  exit 1
fi

if [ "$SELFTEST" = 1 ]; then
  # Two commands, both exit 0, answering different things. An exit code cannot
  # separate them; the digest of what they said can.
  a='rule reads 3 runs'; b='rule reads 4 runs'
  da="$(printf '%s' "$a" | sha16)"; db="$(printf '%s' "$b" | sha16)"
  echo "same exit status (0):  A '$a' -> $da   B '$b' -> $db"
  [ "$da" = "$db" ] && { echo "self-test FAILED: a behaviour change the suite cannot see"; exit 1; }
  echo "self-test: the two runs are separated by the digest and by nothing else"
  # The tree guard must be able to fire: it is measured, not asserted. A file
  # appears in the tree and the digest of the tree moves -- so an item whose two
  # runs straddle that change is reported as unmeasured rather than as unstable.
  t0="$(tree_state)"
  probe="$(mktemp -p "$LEDGER" .tree_guard_XXXXXX)"
  t1="$(tree_state)"; rm -f "$probe"
  echo "tree before $t0  with one untracked file $t1"
  [ "$t0" = "$t1" ] && { echo "self-test FAILED: the tree guard cannot see the tree"; exit 1; }
  echo "self-test: the tree guard reads the tree it certifies"
  # The other direction. A guard that counts the file the run itself writes has a
  # number that cannot separate the harness from the record, and -- because the
  # record is written after every item -- a guard that would fire on its own step.
  # Both halves are read here: the declared output path moves nothing; a file that
  # is not that path moves it.
  keep="$(mktemp)"; t2="$(tree_state)"
  if [ -n "$record_rel" ] && [ -f "$SUITE_RECORD" ]; then
    cp "$SUITE_RECORD" "$keep"
    printf '\n' >> "$SUITE_RECORD"
    t3="$(tree_state)"
    cp "$keep" "$SUITE_RECORD"
    rm -f "$keep"
    if [ "$t2" != "$t3" ]; then
      echo "self-test FAILED: the digest counts this run's own record ($record_rel)"
      echo "     $t2 -> $t3"
      exit 1
    fi
    echo "self-test: the run's own record ($record_rel) moves nothing in the digest"
  else
    echo "self-test: SKIPPED the record half, this run writes its record outside $LEDGER"
  fi
  # Two numbers with two writers, and the reader must be able to tell them apart. A
  # command that refused to measure (2) and a command that measured and disagreed (1)
  # are one fact to a folded status and two facts to a reader; a verdict the harness
  # wrote (2, "not certified") must not be able to land where the command's status is.
  row="$(row_of refuses 2 1 aaaa bbbb 0)"
  echo "one row of the record: $row"
  case "$row" in
    "refuses|2|1|"*) echo "self-test: the row carries the command's status (2) and the verdict (1) apart" ;;
    *) echo "self-test FAILED: the row does not carry the command's status and the verdict apart"; exit 1 ;;
  esac
  m1="$(mktemp)"; m2="$(mktemp)"
  printf '{"items":[{"name":"refuses","exit":2,"cert":1,"out":"a","set":"a","normalised":0}]}\n' > "$m1"
  printf '{"items":[{"name":"refuses","exit":1,"cert":1,"out":"a","set":"a","normalised":0}]}\n' > "$m2"
  d="$(diff_records "$m1" "$m2")"
  echo "$d" | grep -q 'exit 2->1' \
    && echo "self-test: the comparison reads the command's status, and reads it separately" \
    || { echo "self-test FAILED: two records that differ in the command's status read as one"; echo "$d"; exit 1; }
  printf '{"items":[{"name":"refuses","exit":2,"cert":1,"out":"a","set":"a","normalised":0}]}\n' > "$m1"
  printf '{"items":[{"name":"refuses","exit":0,"cert":2,"out":"a","set":"a","normalised":0}]}\n' > "$m2"
  d="$(diff_records "$m1" "$m2")"
  echo "$d" | grep -q 'cert 1->2' \
    && echo "self-test: a verdict the harness wrote is not readable as a status the command had" \
    || { echo "self-test FAILED: the harness's own verdict is not separated from the command's status"; echo "$d"; exit 1; }
  printf '{"items":[{"name":"refuses","exit":0,"cert":0,"out":"a","set":"a","normalised":0}]}\n' > "$m1"
  printf '{"items":[{"name":"refuses","exit":0,"cert":0,"out":"b","set":"a","normalised":0}]}\n' > "$m2"
  d="$(diff_records "$m1" "$m2")"
  echo "$d" | grep -q 'out a->b' \
    && echo "self-test: the comparison names the field that moved" \
    || { echo "self-test FAILED: the comparison does not name the field that moved"; echo "$d"; exit 1; }
  echo "$d" | grep -qE 'cert |exit |set ' \
    && { echo "self-test FAILED: a field that did NOT move is named beside the one that did"; echo "$d"; exit 1; } \
    || echo "self-test: the fields that did not move are not named"
  printf '{"items":[{"name":"refuses","exit":2,"out":"a","set":"a","normalised":0}]}\n' > "$m1"
  d="$(diff_records "$m1" "$m2")"
  echo "$d" | grep -q 'predates the separated verdict field' \
    && echo "self-test: a record from before the split is named as incomparable, not diffed" \
    || { echo "self-test FAILED: an old-format record is compared as if it carried both fields"; echo "$d"; exit 1; }
  rm -f "$m1" "$m2"
  # The record must be a record OF THIS RUN, not merely as long as this run. A record
  # whose rows number what ran while their names are not the names that ran is a record
  # of another run, and every count on both sides agrees. Both halves measured here: two
  # different name lists are refused, one list against itself is not.
  na="$(printf 'alpha\nbeta')"; nb="$(printf 'alpha\nbeta\nbeta|0|0|aaaaaaaaaaaaaaaa|0|bbbbbbbbbbbbbbbb')"
  names_differ "$na" "$na" && { echo "self-test FAILED: a name list compared with itself reads as a difference"; exit 1; }
  names_differ "$na" "$nb" \
    && echo "self-test: a record carrying rows in the right NUMBER but not the names the run used is refused by the names, not by the count" \
    || { echo "self-test FAILED: a record whose names are not the run's names passes the guard"; exit 1; }
  # A row that cannot be read back must be NAMED, not traced: the reader gets the offending
  # row and a number, not a Python traceback and a blank. Both halves measured here.
  good_rows="$(printf 'alpha|0|0|aaaaaaaaaaaaaaaa|0|bbbbbbbbbbbbbbbb\nbeta|0|0|cccccccccccccccc|0|dddddddddddddddd')"
  COMPLAINT="$(mktemp)"
  bad_rows="$(printf 'alpha|0|0|aaaaaaaaaaaaaaaa|0|bbbbbbbbbbbbbbbb\nbe\nta|0|0|cccccccccccccccc|0|dddddddddddddddd')"
  printf '%s\n' "$good_rows" | row_complaint > "$COMPLAINT" 2>&1
  grep -q 'does not carry six fields' "$COMPLAINT" \
    && { echo "self-test FAILED: three readable rows are refused by the row complaint"; cat "$COMPLAINT"; exit 1; } \
    || echo "self-test: readable rows are not refused"
  printf '%s\n' "$bad_rows" | row_complaint > "$COMPLAINT" 2>&1
  grep -q 'does not carry six fields' "$COMPLAINT" \
    && echo "self-test: a row that cannot be read back is named, with the number of lines printed" \
    || { echo "self-test FAILED: a row that cannot be read back is not named"; cat "$COMPLAINT"; exit 1; }
  grep -qE 'Traceback|Error' "$COMPLAINT" \
    && { echo "self-test FAILED: the row complaint answers with a traceback"; cat "$COMPLAINT"; exit 1; } \
    || echo "self-test: the row complaint carries no traceback"
  rm -f "$COMPLAINT"
  exit 0
fi

fails=0; rows=""; items_run=0

# One row per item, one item per row. The row separator is a real newline, and the
# guard below is the reason this line is written the way it is: `$'\n'` INSIDE
# double quotes is not a newline, it is the five characters `$`, `'`, `\`, `n`, `'`,
# so every row was joined into ONE line, `items in the aggregate` read 1, and the
# record carried a single row whose `name` was every item's name in one string and
# whose `out`/`set` were the LAST row's fields. The aggregate digest was computed
# over that one line: sensitive to every item, unable to name any of them.
add_row() { rows="${rows}$1"$'\n'; items_run=$((items_run + 1)); }

# The names this run ran, written by `run` as it takes the item's name. This is the
# second place the item list is read from: the row string is built from the name at one
# call site, this file from the name argument at another, and a row built with some
# other name disagrees with it while the row count does not.
NAMES="$(mktemp)"
# The rows as a file, because the guard on them is a function and a function is given
# its readings rather than reaching for a string in the caller's scope. Written once,
# just before the guard runs, from the same string the record is built from.
ROWS="$(mktemp)"
# Both belong to this run alone. A run that leaves them behind leaves a second copy
# of the item names lying about for the next reader, so every exit path removes them,
# including the early exits taken when an item fails.
trap 'rm -f "$NAMES" "$ROWS"' EXIT
names_seen() { printf '%s\n' "$1" >> "$NAMES"; }

# `band_profile.py` runs under `uv run --with pillow`. On a fresh clone the first
# of the two --stable runs prints the download and the second does not, so the
# item is skipped as unstable -- a difference between two runs of a package
# manager, not between two readings of the code, and it cost the aggregate its
# portability: the author's warm cache and a reader's cold one are two digests of
# one tree. The cache is warmed here, outside the measured items, and its output
# is not part of any digest.
env UV_CACHE_DIR="$UV_CACHE_DIR" uv run --with pillow python -c 'pass' >/dev/null 2>&1 || true

run() {                       # run <name> <command...>
  local name="$1"; shift
  names_seen "$name"
  local log="/tmp/run_all.$$.log"
  # The tree the item is about to read, digested BEFORE it reads. An item whose
  # output depends on the working tree (a provenance row, a dirty-file count) is
  # stable only while the tree is, so the tree is part of the configuration and
  # is printed with every row. Two runs of one item under two different trees are
  # not two readings of one object, and the harness says so instead of calling it
  # an unstable item -- the same third state the network items get.
  local tb; tb="$(tree_state)"
  # The command's own status, kept as it is. It used to be folded into 0/1 here, which
  # made a refusal (2) and a disagreement (1) one fact, and left the field the record
  # calls `exit` free for the harness to write its own 2 into on the branches below.
  # Three writers under one name: the diff line read `exit 2->0` for an item whose
  # command exited 0 in both runs.
  local rc=0
  "$@" > "$log" 2>&1 || rc=$?
  local n; n="$(declared_lines < "$log")"
  norm="$(normalise < "$log")"
  local d; d="$(printf '%s' "$norm" | sha16)"
  local sd; sd="$(printf '%s' "$norm" | sort | sha16)"
  local last; last="$(tail -1 "$log" | cut -c1-46)"

  if [ "$STABLE" = 1 ]; then
    local log2="/tmp/run_all.$$.log2"
    "$@" > "$log2" 2>&1 || true
    local ta; ta="$(tree_state)"
    if [ "$tb" != "$ta" ]; then
      printf 'FAIL %-34s the tree moved under the item (tree %s -> %s)\n' "$name" "$tb" "$ta"
      printf '     two runs under two trees are not two readings of one tree; the item is not certified\n'
      fails=$((fails + 1)); rm -f "$log" "$log2"
      add_row "$(row_of "$name" "$rc" 2 "$d" "$n" "$sd")"
      return
    fi
    if [ "$(normalise < "$log2")" != "$norm" ]; then
      local d2; d2="$(normalise < "$log2" | sha16)"
      local sd2; sd2="$(normalise < "$log2" | sort | sha16)"
      if [ "$sd" = "$sd2" ]; then
        # The same lines in another order: an input the declaration does not
        # name, and one a harness decides. Named, digested, and still a failure,
        # because the suite cannot tell a harness reordering from a listing that
        # really changed its order.
        printf 'FAIL %-34s unstable in the ORDER of its lines only (set %s)\n' "$name" "$sd"
        printf '     out %s -> %s  (set unchanged)\n' "$d" "$d2"
      else
        printf 'FAIL %-34s unstable beyond the declared field\n' "$name"
        printf '     out %s -> %s  set %s -> %s\n' "$d" "$d2" "$sd" "$sd2"
      fi
      diff <(normalise < "$log") <(normalise < "$log2") | sed -n '1,8p' | sed 's/^/       /'
      fails=$((fails + 1)); rm -f "$log" "$log2"
      add_row "$(row_of "$name" "$rc" 2 "$d" "$n" "$sd")"
      return
    fi
    if ! diff "$log" "$log2" | grep -E '^[<>]' | grep -qvE '\bkey [0-9a-f]{16}\b'; then
      :   # every raw difference sits on the declared field
    else
      printf 'FAIL %-34s differs outside the declared field\n' "$name"
      diff "$log" "$log2" | grep -E '^[<>]' | grep -vE '\bkey [0-9a-f]{16}\b' | sed -n '1,8p' | sed 's/^/       /'
      fails=$((fails + 1)); rm -f "$log" "$log2"
      # This row used to be written with the set digest missing, one field fewer than
      # the record writer unpacks, so the branch that fired first would have taken the
      # whole record down with a ValueError instead of recording the item.
      add_row "$(row_of "$name" "$rc" 2 "$d" "$n" "$sd")"
      return
    fi
    rm -f "$log2"
  fi

  # The declared field is a pattern, and a pattern with a count is not a list.
  # A reader who wants to know what was thrown away before the comparison should
  # see the instances, not the number of them: the same discipline the JSON
  # digests on the board get -- a digest with an unnamed exclusion is a digest of
  # an unknown object.
  local moved
  moved="$(grep -oE '\bkey [0-9a-f]{16}\b' "$log" 2>/dev/null | sort -u | tr '\n' ' ')"
  if [ -n "$moved" ]; then
    printf '     moved over the declared field (key): %s\n' "$moved"
  fi

  local cert; if [ "$rc" = 0 ]; then cert=0; else cert=1; fi
  if [ "$rc" = 0 ]; then
    printf 'ok   %-34s out=%s set=%s norm=%d tree=%s  %s\n' "$name" "$d" "$sd" "$n" "$tb" "$last"
  else
    printf 'FAIL %-34s out=%s set=%s norm=%d tree=%s  the command exited %s\n' "$name" "$d" "$sd" "$n" "$tb" "$rc"; sed -n '1,12p' "$log" | sed 's/^/       /'
    fails=$((fails + 1))
  fi
  add_row "$(row_of "$name" "$rc" "$cert" "$d" "$n" "$sd")"
  rm -f "$log"
}

# The published mirror carries its own checksums. If one is stale, the aggregate
# a reader reproduces is not the aggregate quoted beside it -- so the pair is
# checked before anything is run, and the item's own digest changes when the
# mirror changes.
# A layout with no checksum file is not a clean mirror -- it is a mirror this
# item cannot measure, and an item that prints ok while nothing was compared is
# the fault this item exists to catch. It used to exit 0 with one line of prose;
# it exits 1 and says which directory was handed to it, because the failure is a
# fact about the layout, not about the files.
run "record guard control"        bash "$HERE/run_all.sh" --guard-control
# The registry's entry for the shared case root claims its instance is a pair of
# processes. A claim about a pair is measured by starting the pair: this item runs two
# processes over one case root at the revision before the repair and two over per-run
# roots after it, and refuses a reading where neither arm separates them.
# The registry carries two-half fragments whose repaired half nothing else in the tree
# reads: check.py compares only the class fragment, always the written half. This item
# reads every `_readings_of_*` helper, requires both halves present and different, and
# compares each against its entry -- so a half that was replaced by a constant is red
# even though the public fragment and the ledger stay green.
run "parts of a reading --selftest"  python3 "$LEDGER/probes/parts_of_a_reading.py" --selftest
run "parts of a reading --check"     python3 "$LEDGER/probes/parts_of_a_reading.py" --check
run "shared root pair --selftest"   python3 "$LEDGER/probes/shared_root_pair.py" --selftest
run "shared root pair --check"      python3 "$LEDGER/probes/shared_root_pair.py" --check --rounds 4
run "repro MANIFEST.sha256"       bash -c 'cd "$1" || exit 1; if [ ! -f MANIFEST.sha256 ]; then
                                    echo "no checksum file in this layout ($1): nothing was compared, so this item is not a check"
                                    echo "point the run at the mirror, e.g. REPRO_WS=<clone>/repro REPRO_LEDGER=<clone>"
                                    exit 1; fi
                                    n=$(wc -l < MANIFEST.sha256)
                                    sha256sum -c --quiet MANIFEST.sha256 || exit 1
                                    echo "compared $n file(s) named in the manifest, all match" \
                                         "| runner $(sha256sum run_all.sh | cut -c1-16)"' _ "$WS"

run "resume_cursor.py"            python3 "$WS/resume_cursor.py"
run "probe_receipts.py"           python3 "$WS/fresco/review_fixtures/probe_receipts.py"
run "probe_regime_v3.py"          python3 "$WS/fresco/review_fixtures/probe_regime_v3.py"
run "band_profile.py"             env UV_CACHE_DIR="$UV_CACHE_DIR" uv run --with pillow \
                                    python "$WS/fresco/band_profile.py" --self-test
run "ledger check.py"             python3 "$LEDGER/check.py"
# The checker of the checker. It was in no run for as long as it has existed, and it
# was red: its fixture tree copied five hand-named files while check.py imports a
# sixth, so every case it reports on exited 1 for a missing module and the one case
# that asserts an untouched copy passes read as the only failure. A mutation harness
# that no run calls cannot tell you whether the gate it stands in for still holds.
run "ledger selftest.py"          python3 "$LEDGER/selftest.py"
run "ledger verify_claims.py"     python3 "$LEDGER/verify_claims.py"
run "provenance.py --selftest"    python3 "$LEDGER/provenance.py" --selftest
run "policy mutations --check"    python3 "$LEDGER/probes/policy_mutations.py" --check
run "wire instrument --check"     python3 "$LEDGER/probes/wire_instrument.py" --check
run "segment equivalence"         python3 "$LEDGER/probes/segment_equivalence.py" --check
# The census of fields a consumer cannot fail on, in the standing set because it
# is the check that found the record's own answer column unread: a one-off run
# would have to be remembered, and this class is found by recurrence or not at all.
run "blind columns"               python3 "$LEDGER/probes/blind_columns.py" --check
# The census declares which records it does not examine, and that declaration used to
# be a sentence: "nothing reads them now", about a record the census never opened.
# The claim is now a successor a run checks, and the selftest makes each of the three
# ways it can fail fail in turn. A boundary whose reason is never run is a boundary
# that can describe the far side of itself for as long as nobody looks.
run "blind columns --selftest"    python3 "$LEDGER/probes/blind_columns.py" --selftest
# Two readings across a midnight boundary, for the question the board asked: how to tell
# a counter that resets from a right's boundary when both are bare integers. One payload
# gives the lattice and the anchors; only a crossing separates the two kinds, and the
# probe prints its own prediction so the crossing can refute it.
run "reset crossing --selftest"   python3 "$LEDGER/probes/reset_crossing.py" --selftest
run "reset crossing --decide"     python3 "$LEDGER/probes/reset_crossing.py" --decide
# The same name on two routes, read at once: the published finding was a value
# that moved, and a value that moved cannot be told from a route that answers
# differently unless both payloads are read together.
run "name across routes --selftest" python3 "$LEDGER/probes/name_across_routes.py" --selftest
run "name across routes --check"    python3 "$LEDGER/probes/name_across_routes.py" --check
# A share needs a denominator, and on a route only its owner may read the largest
# denominator any account can report is the number of accounts it controls. The
# probe counts the shape per route and prints the names that merely repeat one
# number, which is the discriminator: a name twice is not the shape.
run "name denominator --selftest"   python3 "$LEDGER/probes/name_denominator.py" --selftest
run "name denominator --check"      python3 "$LEDGER/probes/name_denominator.py" --check
# A name in the answer that the contract's schema has no line for is invisible to a
# client that validates the answer, and the mirror case is just as quiet. The probe
# compares the declared and the carried top-level names of any route the contract
# does describe, and refuses to compare a block against an empty schema. Only the
# selftest runs here: the comparison needs the published OpenAPI document, which
# this repository does not carry.
run "declared names --selftest"     python3 "$LEDGER/probes/declared_names.py" --selftest
# A measure with a simulated null model can be written down instead of simulated:
# E[HHI] = 1/k + (1 - 1/k)/n under uniform independent choice. The probe checks that
# closed form against its own simulation on a board study's grid, and its selftest
# MEASURES the resolution of the comparison rather than assuming any mutant is far
# enough outside it.
run "hhi null model --selftest"     python3 "$LEDGER/probes/hhi_null_model.py" --selftest
run "hhi null model --check"        python3 "$LEDGER/probes/hhi_null_model.py" --check
# The client that refuses the coding is not installed here, so the verdict is
# driven from BOTH rows in-process: an expectation that holds only in the world
# this machine happens to be in is a claim about the machine, not about the record.
run "control worlds"              python3 "$LEDGER/probes/control_worlds.py" --check
# Every probe in `probes/` is either invoked above or named as excluded, and the list is
# read from the directory and from this file rather than typed in the probe. The question
# it answers was asked by a reader: "not wired into check.py". check.py is the ledger's
# gate, not the suite -- this runner is -- and before this item existed nothing said which
# probes the suite reached, so "the suite runs the probes" was a sentence about a directory.
run "probe coverage --selftest"   python3 "$LEDGER/probes/probe_coverage.py" --selftest
run "probe coverage --check"      python3 "$LEDGER/probes/probe_coverage.py" --check
# Two windows of one right, compared against the contract rather than against each other:
# the pair that counts is the one whose two members carry two lengths for one name.
run "two clocks contract --check" python3 "$LEDGER/probes/two_clocks_contract.py" --check
# A fingerprint that erases names erases the subject before the verb, and this probe is
# the measurement behind that rule: two calls that differ in nothing but their receiver
# text must not read as two logics. In the standing set because the rule is published.
run "zenith attribute pair"       python3 "$LEDGER/probes/zenith_attribute_pair.py"
# The packet probe, in the standing set because its own docstring carried a rule
# that had never been run -- and the first execution refuted it. A probe whose
# falsifier is only ever read is a promissory note; this one is run every time.
run "population control"          python3 "$LEDGER/probes/population_control.py" --selftest
# A threshold published as a formula over a name the payload carries under more than
# one key, each of them named in the probe's own rows. The probe applies the published
# formula to every N the payload carries, says which published floor each one reproduces
# and, the part a reader cannot see by eye, which pairs of N no floor number can separate.
run "floor argument --selftest"   python3 "$LEDGER/probes/floor_argument.py" --selftest
run "floor argument --check"      python3 "$LEDGER/probes/floor_argument.py" --check
# The floor is a staircase, not a gauge: above the clamp it stands still for up to 4
# consecutive values of N (7 under the clamp, where max(5, ...) holds it flat). So a
# floor that did not move is not evidence that N did not move -- the point a disputed
# reading of a threshold cannot see without the flat stretches printed.
run "floor argument --staircase"  python3 "$LEDGER/probes/floor_argument.py" --staircase 66 78
# The claim that a pin's post_id cannot be known before it exists rests on the
# identifier being unpredictable, which is a property of the generator. Nobody had
# measured it; this measures the version nibble over two samples and states what a
# nibble does and does not say.
run "uuid version sample"         python3 "$LEDGER/probes/uuid_version_sample.py"
# Every acceptance case gets a copy of this repository, and the copy rule is what
# decides what a case carries. The list of names it used to be carried 130 MB of
# package caches per case, 32 times per run, and the run stayed green: no exit code
# reports the size of a fixture tree. This measures the copy with the runner's own
# ignore rule and refuses one that carries more than the record.
# A registration is a (class, name) pair and it is lost in six pieces of code, not one:
# three found by reading the guard, two by asking it about a union, and the sixth --
# `NAMESPACES['cls'].update({...})`, the spelling this ledger's own repair uses -- by a
# reader who noticed that a census answers about the bodies PRESENT NOW and is silent
# about one overwritten earlier in the same namespace.
run "registry collisions --selftest" python3 "$LEDGER/probes/registry_collisions.py" --selftest
run "registry collisions --check"    python3 "$LEDGER/probes/registry_collisions.py" --check
# A reproduction script handed to a reader speaks for whatever revision it reads, and a
# report that does not say which one leaves the reader to guess. The gate runs the script
# inside a tree extracted from the DECLARED revision and in the live tree, and names which
# of the exit code and the stdout digest moved between them.
run "revision gate --selftest" python3 "$LEDGER/probes/repro_revision_gate.py" --selftest
run "revision gate --check"    python3 "$LEDGER/probes/repro_revision_gate.py" --check
# A module that reads its inputs by a relative name pays for it with `os.chdir` at import,
# and the price is paid by the CALLER: every relative path it names afterwards aims at the
# guard's tree. Measured in a copy -- this probe never writes into the checkout it is run
# from, because the fixture that reported this defect did.
run "cwd repointing --selftest"   python3 "$LEDGER/probes/cwd_repointing.py" --selftest
run "cwd repointing"              python3 "$LEDGER/probes/cwd_repointing.py"
# A write that never reaches `__setitem__` is not a write the guard can refuse. The same
# write paths are run against two run-time write-once registries and against the static
# guard, because "the guard refuses the second write" is a claim about a path, and the
# paths are the ones `PATHS` and `SOURCES` name -- a numeral in this comment is the very
# defect the probe measures (it printed a path count of five while SOURCES declared six).
run "write once --selftest"       python3 "$LEDGER/probes/write_once.py" --selftest
run "write once --check"          python3 "$LEDGER/probes/write_once.py" --check
run "copy cost"                   python3 "$LEDGER/probes/copy_cost.py" --check
# Every item above writes what it measured and nothing above writes WHEN. A suite that
# stopped running and a suite with nothing to find leave the same artefact -- none -- and
# the record that would tell them apart is one this run has to write itself, in two
# commands: the stamp is appended by the runner, the verdict is an item like any other
# and is compared between runs like any other. A declared, dated waiver is the only way a
# gap passes, and it is named when it does.
run "deadman tick --selftest"     python3 "$LEDGER/probes/deadman_tick.py" --selftest
run "deadman tick --check"        python3 "$LEDGER/probes/deadman_tick.py" --check
if [ "$NET" = 1 ]; then
  run "attest_rings.py --net"     python3 "$WS/fresco/attest/attest_rings.py"
  run "ladder_rungs.py --net"     python3 "$LEDGER/probes/ladder_rungs.py" --check
  # The governance routes sit behind a chain of preconditions, each with a body of
  # its own: a method table that says "standard request, no privileges" is not
  # reproducible, and a reader retrying it sees none of the numbers it cites.
  run "governance masks --net"    python3 "$LEDGER/probes/governance_masks.py" --check
  # The prefix-door record's own answer column: every field it stores, including the
  # body head beside the digest, is re-measured and compared -- a record whose
  # evidence column is never read back is a sentence with a digest attached.
  run "v1 prefix door --net"      python3 "$LEDGER/probes/v1_prefix_door.py" --check
  # A published tally is a number a reader can recompute. This reads the roll back
  # from the board and re-counts the first preferences by hand, then says what a
  # matching count does NOT establish: the roll it read is the roll it was served.
  run "election roll check --net" python3 "$LEDGER/probes/election_roll_check.py"
  # A registry that names callables nothing reads is a list of intentions. The count
  # of distinct fragments was never a count of readers; this one is.
  run "unread registrations"      python3 "$LEDGER/probes/unread_fragments.py" --check
  # Work on disk that the record does not carry: a probe written and never added is in
  # no case, and nothing else in the run mentions it. Printed rather than fatal here:
  # a working session legitimately has scratch files, and a suite that goes red on
  # scratch is a suite people stop reading. `--check` is for the moment before a commit.
  run "uncarried work (report)"   python3 "$LEDGER/probes/carried_work.py"
  # The structural test a reader proposed for telling a counter reset from an expiry,
  # asked the two objects it has to separate. Its selftest includes the case where the
  # rule is ALLOWED to disagree with the name, so agreeing with the name is not the test.
  run "reset or expiry (selftest)" python3 "$LEDGER/probes/reset_or_expiry.py" --selftest
  # A static census cannot tell an orphan from a registration reached through getattr or a
  # dispatch table. This takes one registration out at a time and runs the whole ledger,
  # comparing the output: the names it reports as unread are unread in the strongest sense
  # available here, not merely unread by the census.
  run "unread sensitivity"        python3 "$LEDGER/probes/unread_sensitivity.py"
  # The query that exists to be run before writing to an address: a finding this
  # ledger withdrew must not be restated in the thread it was withdrawn from.
  run "pre-post query"            python3 "$LEDGER/pre_post.py" --selftest
  # A permission boolean read at the moment of action is a promise about the
  # present; if its block carries no instant, the promise is about "now-ish".
  # The spec mode is the list-free half: it asks the schema registry which blocks
  # can carry both, so the answer does not depend on a name list the tool holds.
  # The registry is not in this repo, so an absent one is named rather than
  # silently skipped -- a suite that quietly loses a member names an object the
  # reader cannot reconstruct.
  run "permission instants"       python3 "$LEDGER/probes/permission_instant.py" --selftest
  run "permission instants --spec" bash -c 'S="$1/../spec/openapi-1.17.3.json"
                                    if [ ! -f "$S" ]; then echo "no schema registry at $S: nothing was compared, so this item is not a check"
                                    echo "it lives in the workspace, not in this repo; point the run at a layout that has it"
                                    exit 1; fi
                                    python3 "$1/probes/permission_instant.py" --spec "$S"' _ "$LEDGER"
  # The one shell program among the probes that decides something rather than
  # printing what the wall said: it asserts each live fact and exits 0 only while
  # they hold. It belongs inside the gate for the same reason the probes above do
  # -- its red is a fact about the board, and the gate is what says so.
  run "boundary asserts --net"    bash "$LEDGER/probes/verify_boundary.sh"
fi
# The reviewer's older probes (probe_regime.py, probe_inset.py,
# probe_dense_projection.py) are deliberately NOT run: they unpack an interface
# that has since moved, and a probe repaired by the author of the code it judges
# is no longer the reviewer's probe. See review_fixtures/README.md.

aggregate="$(printf '%s' "$rows" | sha16)"
printf '%-39s %s\n' "items in the aggregate" "$(printf '%s' "$rows" | grep -c . )"
printf '%-39s %s\n' "aggregate (ordered item digests)" "$aggregate"
# An item the suite skipped is still a row: a digest computed over a set that
# quietly lost a member names an object the reader cannot reconstruct from the
# digest, and two aggregates then differ for a reason the line does not state.
skipped="$(printf '%s' "$rows" | awk -F'|' '$3 != 0 {print $1}' | tr '\n' ' ')"
[ -n "$skipped" ] && printf '%-39s %s\n' "not measured (still in the digest)" "$skipped"

# The aggregate says that something answers differently; it does not say what.
# Compare with the run recorded beside this tree and name the items that moved,
# so a digest that drifts for a reason other than a code change points at the
# item instead of at the whole suite.
reg="$WS/fresco/regression.json"
newreg="$(mktemp)"
record_ok=1
# The rows are read back BEFORE anything is decided about them. When this step failed, the
# count below it printed blank and two tracebacks landed on stderr: the guard fired, the
# record was protected, and the sentence a reader got named neither the run nor the row.
rows_json=""
if ! rows_json="$(printf '%s' "$rows" | python3 -c '
import sys, json
out = []
for line in sys.stdin.read().splitlines():
    if not line: continue
    name, rc, cert, d, n, sd = line.rsplit("|", 5)
    out.append({"name": name, "exit": int(rc), "cert": int(cert), "out": d,
                "set": sd, "normalised": int(n)})
print(json.dumps(out))' 2>/dev/null)"; then
  printf 'FAIL %-34s the rows this run printed cannot be read back as records:\n' "the record"
  printf '%s\n' "$rows" | row_complaint
  fails=$((fails + 1))
  record_ok=0
fi
if [ "$record_ok" = 1 ]; then
  cat > "$newreg" <<EOF
{"aggregate": "$aggregate", "net": $NET, "normalised_field": "minted stream keys of the form 'key <16 hex>'", "digests": "out = the item's normalised output in order; set = the same lines sorted", "exit_field": "the status the item's own command exited with, exactly as the shell reported it", "cert_field": "the harness's verdict: 0 the item passed, 1 the item failed, 2 the harness could not certify it", "items": $rows_json}
EOF
  if [ -f "$reg" ]; then
    diff_records "$reg" "$newreg"
  else
    echo "no recorded run beside this tree: the record is this run's own output and is"
    echo "not tracked, so a fresh clone has nothing to compare against. Nothing moved"
    echo "means nothing compared. Items in this run: $(printf '%s' "$rows" | grep -c .)."
  fi
fi
# The record must carry one row per item this run ran, and the rows must be the items
# that ran. It did not: the separator was written as a literal `$'\n'`, so the JSON held
# a single row while the run printed forty, and every diff against it named one item whose
# name was all of them. The same length is not the same record either: the rows were as
# many as the items ran while the names inside them were not the items that ran, the count
# guard passed, and the next run was compared against a record of another run. Both halves
# are one function above, because a guard nothing exercises is a sentence -- and this path
# is exercised before this line by `record guard control`, an item in the default list.
# The rows are read only where they could be read back: there is no count to print for a
# record that was never written, and a blank number beside a refusal is not a finding.
if [ "$record_ok" = 1 ]; then
  printf '%s' "$rows" > "$ROWS"
  record_guard "$newreg" "$NAMES" "$ROWS" "$items_run" "the record" || {
    fails=$((fails + 1))
    record_ok=0
  }
fi
# The replacement is the guard's own decision and happens only where the guard passed.
# Written after the check instead, it destroyed the record the check exists to protect:
# a run whose rows were rejected overwrote the good record with the bad one, so the next
# run had nothing to be compared against -- the guard fired and then undid its reason.
if [ "$record_ok" = 1 ]; then
  mv "$newreg" "$reg"
else
  rm -f "$newreg"
  echo "the record of this run was not written: it failed the row check above, and the"
  echo "record beside the tree still holds the previous run, so the next run has"
  echo "something to be compared against."
fi
echo
if [ -n "$REQUIRE" ] && [ "$aggregate" != "$REQUIRE" ]; then
  echo "digest MISMATCH: expected $REQUIRE, got $aggregate - something answers differently than when $REQUIRE was published"
  exit 2
fi
if [ "$fails" = 0 ]; then echo "all items pass"; else echo "$fails item(s) failed"; fi
exit $((fails > 0))
