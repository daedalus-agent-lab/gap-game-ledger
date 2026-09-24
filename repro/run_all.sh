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
cd "$(dirname "$0")"
WS="${REPRO_WS:-$(cd "$(dirname "$0")/.." && pwd)}"
LEDGER="${REPRO_LEDGER:-$WS/gap-game-ledger}"
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
  local last; last="$(tail -1 "$log" | cut -c1-46)"

  if [ "$STABLE" = 1 ]; then
    local log2="/tmp/run_all.$$.log2"
    "$@" > "$log2" 2>&1 || true
    if [ "$(normalise < "$log2")" != "$norm" ]; then
      printf 'FAIL %-34s unstable beyond the declared field\n' "$name"
      diff <(normalise < "$log") <(normalise < "$log2") | sed -n '1,8p' | sed 's/^/       /'
      fails=$((fails + 1)); rm -f "$log" "$log2"
      rows="${rows}${name}|2|${d}|${n}
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
    printf 'ok   %-34s out=%s norm=%d  %s\n' "$name" "$d" "$n" "$last"
  else
    printf 'FAIL %-34s out=%s norm=%d\n' "$name" "$d" "$n"; sed -n '1,12p' "$log" | sed 's/^/       /'
    fails=$((fails + 1))
  fi
  rows="${rows}${name}|${st}|${d}|${n}
"
  rm -f "$log"
}

# The published mirror carries its own checksums. If one is stale, the aggregate
# a reader reproduces is not the aggregate quoted beside it -- so the pair is
# checked before anything is run, and the item's own digest changes when the
# mirror changes.
run "repro MANIFEST.sha256"       bash -c 'cd "$1" || exit 1; if [ ! -f MANIFEST.sha256 ]; then
                                    echo "no checksum file in this layout"; exit 0; fi
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
{"aggregate": "$aggregate", "net": $NET, "normalised_field": "minted stream keys of the form 'key <16 hex>'", "items": $(printf '%s' "$rows" | python3 -c '
import sys, json
out = []
for line in sys.stdin.read().splitlines():
    if not line: continue
    name, st, d, n = line.rsplit("|", 3)
    out.append({"name": name, "exit": int(st), "out": d, "normalised": int(n)})
print(json.dumps(out))')}
EOF
if [ -f "$reg" ]; then
  python3 - "$reg" "$newreg" <<'PY'
import json, sys
prev, new = (json.load(open(p)) for p in sys.argv[1:3])
a = {i["name"]: (i["exit"], i["out"], i["normalised"]) for i in prev.get("items", [])}
b = {i["name"]: (i["exit"], i["out"], i["normalised"]) for i in new["items"]}
moved = [n for n in b if n in a and a[n] != b[n]]
gone = [n for n in a if n not in b]
fresh = [n for n in b if n not in a]
if moved:
    print("moved since the last recorded run on this tree:")
    for n in moved:
        print(f"    {n}: exit {a[n][0]}->{b[n][0]}  out {a[n][1]}->{b[n][1]}  norm {a[n][2]}->{b[n][2]}")
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
