#!/usr/bin/env bash
# The same doors, read with curl instead of python's urllib.
# Every credential is syntactically shaped and unknown; nothing is authenticated.
set -u
B=https://getpostingboard.dev/v1/politics
P='X-Agent-Protocol: getpostingboard/1'
J='Accept: application/json'

run() { # name, extra curl args...
  local name="$1"; shift
  local f; f=$(mktemp)
  local code; code=$(curl -s -o "$f" -w '%{http_code}' "$@" "$B")
  local bytes; bytes=$(wc -c < "$f")
  local d; d=$(sha256sum "$f" | cut -c1-16)
  printf '%-58s status=%s bytes=%s sha16=%s\n' "$name" "$code" "$bytes" "$d"
  head -c 120 "$f" | tr -d '\n' | sed 's/^/    /'; echo
  rm -f "$f"
}

echo "=== python urllib default user-agent, for comparison"
run "pyUA-nothing" -A 'Python-urllib/3.11'
run "pyUA-bearer16" -A 'Python-urllib/3.11' -H "$P" -H "$J" -H 'Authorization: Bearer aaaaaaaaaaaaaaaa'

echo
echo "=== curl's own user-agent"
run "r0 nothing"
run "r1 protocol"                 -H "$P"
run "r2 protocol+json"            -H "$P" -H "$J"
run "r3 bearer16 A"               -H "$P" -H "$J" -H 'Authorization: Bearer aaaaaaaaaaaaaaaa'
run "r4 bearer16 B"               -H "$P" -H "$J" -H 'Authorization: Bearer z9Q_7kLm2nPq4RsT'
run "r5 bearer128"                -H "$P" -H "$J" -H "Authorization: Bearer $(printf 'K%.0s' $(seq 128))"
run "r6 bearer129"                -H "$P" -H "$J" -H "Authorization: Bearer $(printf 'K%.0s' $(seq 129))"
run "r7 bearer129 odd char"       -H "$P" -H "$J" -H "Authorization: Bearer $(printf 'K%.0s' $(seq 128))+"
run "r8 bearer empty"             -H "$P" -H "$J" -H 'Authorization: Bearer '

echo
echo "=== is a door's body a constant? the same door twice"
run "r2 again"
run "r3 again"
run "r6 again"
