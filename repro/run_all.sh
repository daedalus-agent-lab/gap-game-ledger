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
REQUIRE=""; NET=0; SELFTEST=0; STABLE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --net) NET=1 ;;
    --stable) STABLE=1 ;;
    --expect) REQUIRE="${2:-}"; shift ;;
    --self-test) SELFTEST=1 ;;
  esac
  shift
done

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

if [ "$SELFTEST" = 1 ]; then
  # Two commands, both exit 0, answering different things. An exit code cannot
  # separate them; the digest of what they said can.
  a='rule reads 3 runs'; b='rule reads 4 runs'
  da="$(printf '%s' "$a" | sha16)"; db="$(printf '%s' "$b" | sha16)"
  echo "same exit status (0):  A '$a' -> $da   B '$b' -> $db"
  [ "$da" = "$db" ] && { echo "self-test FAILED: a behaviour change the suite cannot see"; exit 1; }
  echo "self-test: the two runs are separated by the digest and by nothing else"
  exit 0
fi

fails=0; rows=""

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
  local log="/tmp/run_all.$$.log"
  if "$@" > "$log" 2>&1; then st=0; else st=1; fi
  local n; n="$(declared_lines < "$log")"
  norm="$(normalise < "$log")"
  local d; d="$(printf '%s' "$norm" | sha16)"
  local sd; sd="$(printf '%s' "$norm" | sort | sha16)"
  local last; last="$(tail -1 "$log" | cut -c1-46)"

  if [ "$STABLE" = 1 ]; then
    local log2="/tmp/run_all.$$.log2"
    "$@" > "$log2" 2>&1 || true
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
      rows="${rows}${name}|2|${d}|${n}|${sd}
"
      return
    fi
    if ! diff "$log" "$log2" | grep -E '^[<>]' | grep -qvE '\bkey [0-9a-f]{16}\b'; then
      :   # every raw difference sits on the declared field
    else
      printf 'FAIL %-34s differs outside the declared field\n' "$name"
      diff "$log" "$log2" | grep -E '^[<>]' | grep -vE '\bkey [0-9a-f]{16}\b' | sed -n '1,8p' | sed 's/^/       /'
      fails=$((fails + 1)); rm -f "$log" "$log2"
      rows="${rows}${name}|2|${d}|${n}
"
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

  if [ $st = 0 ]; then
    printf 'ok   %-34s out=%s set=%s norm=%d  %s\n' "$name" "$d" "$sd" "$n" "$last"
  else
    printf 'FAIL %-34s out=%s set=%s norm=%d\n' "$name" "$d" "$sd" "$n"; sed -n '1,12p' "$log" | sed 's/^/       /'
    fails=$((fails + 1))
  fi
  rows="${rows}${name}|${st}|${d}|${n}|${sd}
"
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
run "repro MANIFEST.sha256"       bash -c 'cd "$1" || exit 1; if [ ! -f MANIFEST.sha256 ]; then
                                    echo "no checksum file in this layout ($1): nothing was compared, so this item is not a check"
                                    echo "point the run at the mirror, e.g. REPRO_WS=<clone>/repro REPRO_LEDGER=<clone>"
                                    exit 1; fi
                                    sha256sum -c --quiet MANIFEST.sha256' _ "$WS"

run "resume_cursor.py"            python3 "$WS/resume_cursor.py"
run "probe_receipts.py"           python3 "$WS/fresco/review_fixtures/probe_receipts.py"
run "probe_regime_v3.py"          python3 "$WS/fresco/review_fixtures/probe_regime_v3.py"
run "band_profile.py"             env UV_CACHE_DIR="$UV_CACHE_DIR" uv run --with pillow \
                                    python "$WS/fresco/band_profile.py" --self-test
run "ledger check.py"             python3 "$LEDGER/check.py"
run "ledger verify_claims.py"     python3 "$LEDGER/verify_claims.py"
run "provenance.py --selftest"    python3 "$LEDGER/provenance.py" --selftest
run "policy mutations --check"    python3 "$LEDGER/probes/policy_mutations.py" --check
run "wire instrument --check"     python3 "$LEDGER/probes/wire_instrument.py" --check
run "segment equivalence"         python3 "$LEDGER/probes/segment_equivalence.py" --check
# The census of fields a consumer cannot fail on, in the standing set because it
# is the check that found the record's own answer column unread: a one-off run
# would have to be remembered, and this class is found by recurrence or not at all.
run "blind columns"               python3 "$LEDGER/probes/blind_columns.py" --check
# The client that refuses the coding is not installed here, so the verdict is
# driven from BOTH rows in-process: an expectation that holds only in the world
# this machine happens to be in is a claim about the machine, not about the record.
run "control worlds"              python3 "$LEDGER/probes/control_worlds.py" --check
if [ "$NET" = 1 ]; then
  run "attest_rings.py --net"     python3 "$WS/fresco/attest/attest_rings.py"
  run "ladder_rungs.py --net"     python3 "$LEDGER/probes/ladder_rungs.py" --check
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
skipped="$(printf '%s' "$rows" | awk -F'|' '$2 != 0 {print $1}' | tr '\n' ' ')"
[ -n "$skipped" ] && printf '%-39s %s\n' "not measured (still in the digest)" "$skipped"

# The aggregate says that something answers differently; it does not say what.
# Compare with the run recorded beside this tree and name the items that moved,
# so a digest that drifts for a reason other than a code change points at the
# item instead of at the whole suite.
reg="$WS/fresco/regression.json"
newreg="$(mktemp)"
cat > "$newreg" <<EOF
{"aggregate": "$aggregate", "net": $NET, "normalised_field": "minted stream keys of the form 'key <16 hex>'", "digests": "out = the item's normalised output in order; set = the same lines sorted", "items": $(printf '%s' "$rows" | python3 -c '
import sys, json
out = []
for line in sys.stdin.read().splitlines():
    if not line: continue
    name, st, d, n, sd = line.rsplit("|", 4)
    out.append({"name": name, "exit": int(st), "out": d, "set": sd,
                "normalised": int(n)})
print(json.dumps(out))')}
EOF
if [ -f "$reg" ]; then
  python3 - "$reg" "$newreg" <<'PY'
import json, sys
prev, new = (json.load(open(p)) for p in sys.argv[1:3])
a = {i["name"]: (i["exit"], i["out"], i.get("set"), i["normalised"]) for i in prev.get("items", [])}
b = {i["name"]: (i["exit"], i["out"], i.get("set"), i["normalised"]) for i in new["items"]}
moved = [n for n in b if n in a and a[n] != b[n]]
gone = [n for n in a if n not in b]
fresh = [n for n in b if n not in a]
if moved:
    print("moved since the last recorded run on this tree:")
    for n in moved:
        print(f"    {n}: exit {a[n][0]}->{b[n][0]}  out {a[n][1]}->{b[n][1]}  "
              f"set {a[n][2]}->{b[n][2]}  norm {a[n][3]}->{b[n][3]}")
if gone or fresh:
    print(f"items added {fresh or 'none'}, removed {gone or 'none'}")
if not (moved or gone or fresh):
    print("no item moved since the last recorded run on this tree")
PY
fi
mv "$newreg" "$reg"
echo
if [ -n "$REQUIRE" ] && [ "$aggregate" != "$REQUIRE" ]; then
  echo "digest MISMATCH: expected $REQUIRE, got $aggregate - something answers differently than when $REQUIRE was published"
  exit 2
fi
if [ "$fails" = 0 ]; then echo "all items pass"; else echo "$fails item(s) failed"; fi
exit $((fails > 0))
