#!/usr/bin/env bash
# A guard's reach is a claim about two trees: the one that carries the guard and the
# one that does not. This script builds both from the tree it is run in, breaks the
# run's record in the same way in each, runs the standing suite in each, and prints
# what each run left behind in repro/fresco/regression.json.
#
# The break is a row whose NAME is not the item's name: the run prints 44 rows under
# the names it used, and the record is built with one hijacked name. The row check
# exists to catch exactly that; the two arms differ only in whether the replacement of
# the record is gated on the check's verdict.
#
# usage: bash repro/record_guard_pair.sh [<tree>] [<seed record>]
#   <tree>          the checkout to clone from (default: the tree this script is in)
#   <seed record>   a record of a previous run of this tree, seeded into both arms so
#                   that each arm has something to be compared against and something
#                   to lose (default: <tree>/repro/fresco/regression.json)
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
TREE="${1:-$(cd "$HERE/.." && pwd)}"
SEED="${2:-$TREE/repro/fresco/regression.json}"
WORK="${WORK:-$(mktemp -d -t record-guard-pair-XXXXXX)}"

sha16() { sha256sum "$1" 2>/dev/null | cut -c1-16; }

if [ ! -f "$SEED" ]; then
  echo "no seed record at $SEED: an arm that starts without a record has nothing to lose"
  exit 2
fi
SEED_SHA="$(sha16 "$SEED")"

echo "tree      $TREE"
echo "seed      $SEED sha=$SEED_SHA"
echo "work      $WORK"

break_the_record() {                 # break_the_record <copy> <arm>
  python3 - "$1/repro/run_all.sh" "$2" <<'PY'
import pathlib, sys
path, arm = pathlib.Path(sys.argv[1]), sys.argv[2]
src = path.read_text()

# 1. an item name the record will not agree with (both arms)
hijack = "run \"$(printf '\\nhijacked|0|0|aaaaaaaaaaaaaaaa|0|bbbbbbbbbbbbbbbb')\""
old_item = 'run "repro MANIFEST.sha256"'
if old_item not in src:
    sys.exit("the item line is not in %s: this experiment measures the current runner" % path)
src = src.replace(old_item, hijack, 1)

# 2. in the ungated arm only: the record is replaced whatever the row check said
if arm == "ungated":
    gated = 'if [ "$record_ok" = 1 ]; then\n  mv "$newreg" "$reg"'
    if gated not in src:
        sys.exit("the gated replacement is not in %s: this experiment measures the current runner" % path)
    src = src.replace(gated, 'if true; then\n  mv "$newreg" "$reg"', 1)

path.write_text(src)
print("broke the record in %s (%s)" % (path, arm))
PY
}

for arm in gated ungated; do
  copy="$WORK/$arm"
  rm -rf "$copy"
  git clone -q --no-hardlinks "$TREE" "$copy" || cp -a "$TREE" "$copy"
  mkdir -p "$copy/repro/fresco"
  cp "$SEED" "$copy/repro/fresco/regression.json"
  break_the_record "$copy" "$arm" || exit 2
  ( cd "$copy" && bash repro/run_all.sh ) > "$WORK/$arm.log" 2>&1
  rc=$?

  rec="$copy/repro/fresco/regression.json"
  after_sha="$(sha16 "$rec")"
  items="$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))['items']))" "$rec" 2>/dev/null || echo "unreadable")"
  ok_rows="$(grep -c '^ok ' "$WORK/$arm.log")"
  guard="$(grep -m1 '^FAIL' "$WORK/$arm.log" || echo "(the run printed no FAIL line)")"
  if [ "$after_sha" = "$SEED_SHA" ]; then kept="yes"; else kept="no"; fi

  {
    echo "arm                  $arm"
    echo "  SUITE_RC           $rc"
    echo "  rows in the record $items"
    echo "  record sha         $after_sha (seed was $SEED_SHA)"
    echo "  the seed survived  $kept"
    echo "  ok rows            $ok_rows"
    echo "  guard said         $guard"
  } | tee "$WORK/$arm.summary"
done

echo "-----"
echo "gated   : the run refuses its record and the record beside the tree is untouched"
echo "ungated : the same refusal, and the record is replaced anyway"
echo "logs    : $WORK/gated.log $WORK/ungated.log"
echo "PAIR_DONE"
