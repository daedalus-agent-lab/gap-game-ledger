#!/usr/bin/env bash
# Where does the door stop saying "send your key" and start saying "invalid key"?
# All keys are synthetic and unknown; nothing is authenticated.
set -u
B=https://getpostingboard.dev/v1/politics
P='X-Agent-Protocol: getpostingboard/1'
J='Accept: application/json'

ask() { # label, key
  local label="$1" key="$2"
  local f; f=$(mktemp)
  local code; code=$(curl -s -o "$f" -w '%{http_code}' -H "$P" -H "$J" \
      -H "Authorization: Bearer $key" "$B")
  local bytes; bytes=$(wc -c < "$f")
  local d; d=$(sha256sum "$f" | cut -c1-16)
  local msg; msg=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["error"]["message"])' "$f" 2>/dev/null || cat "$f")
  printf '%-22s len=%-4s status=%s bytes=%-4s sha16=%s  %s\n' "$label" "${#key}" "$code" "$bytes" "$d" "$msg"
  rm -f "$f"
}

echo "=== length scan, key = 'K'*n"
for n in 1 8 15 16 20 24 32 40 48 56 60 62 63 64 65 66 68 72 96 127 128 129 200; do
  ask "K*$n" "$(printf 'K%.0s' $(seq "$n"))"
done

echo
echo "=== other shapes at the two sizes that differ"
ask "16 hex-like" "$(printf 'a%.0s' $(seq 16))"
ask "64 hex-like" "$(printf 'a%.0s' $(seq 64))"
ask "gpb_+60" "gpb_$(printf 'a%.0s' $(seq 60))"
ask "gpb_+12" "gpb_$(printf 'a%.0s' $(seq 12))"
ask "spaces x64" "$(printf ' %.0s' $(seq 64))"

echo
echo "=== stability: the same door three times each"
for rep in 1 2 3; do
  ask "r2 rep$rep (no key)" ""
  ask "r3 rep$rep (16)" "$(printf 'a%.0s' $(seq 16))"
  ask "r5 rep$rep (128)" "$(printf 'K%.0s' $(seq 128))"
done
