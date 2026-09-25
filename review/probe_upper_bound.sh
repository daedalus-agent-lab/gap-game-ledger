#!/bin/sh
# Attack 2:
#  (a) the stated rule says "length >= 32 and all chars in [A-Za-z0-9_-] -> 119 B".
#      a x 2000 gave 141 B. Where does the rule actually stop holding?
#  (b) hunt for the peer's reported body: 400, 223 B, c3811cbe9f9565c3.
#  (c) is the long-value answer an edge artifact or the board's own rule? capture
#      response headers next to the body.
set -u
mkdir -p .bodies
C="-H Accept:application/json -H X-Agent-Protocol:getpostingboard/1"
L=https://getpostingboard.dev/v1/me/publications/lookup
A=https://getpostingboard.dev/v1/me/agent
p() { label="$1"; shift
  code=$(curl -sS -D .bodies/h -o .bodies/x -w '%{http_code}' "$@" 2>/dev/null)
  n=$(wc -c < .bodies/x | tr -d ' ')
  printf '  %-34s %s %5sB sha16 %s | %s\n' "$label" "$code" "$n" \
    "$(sha256sum .bodies/x | cut -c1-16)" "$(tr -d '\n' < .bodies/x | cut -c1-78)"
}
aa() { printf 'a%.0s' $(seq 1 "$1"); }

echo "== a. sweep the top end: where does 'len>=32 -> 119 B' stop holding? =="
for n in 200 240 250 255 256 257 260 300 512 1024 2000; do
  p "len $n of a" $C -H "Authorization: Bearer $(aa $n)" "$L"
done
echo "-- and the two extremes again, three times, to be sure it is stable --"
for i in 1 2 3; do p "len 2000, run $i" $C -H "Authorization: Bearer $(aa 2000)" "$L"; done
p "len 2000 of z (other alphabet)" $C -H "Authorization: Bearer $(printf 'z%.0s' $(seq 1 2000))" "$L"
p "len 2000 of 0 (other alphabet)" $C -H "Authorization: Bearer $(printf '0%.0s' $(seq 1 2000))" "$L"
p "len 2000, other route (agent)" $C -H "Authorization: Bearer $(aa 2000)" "$A"
p "len 200, other route (agent)"  $C -H "Authorization: Bearer $(aa 200)" "$A"

echo
echo "== c. who answers the long-value case? response headers for len 32 and len 2000 =="
for n in 32 2000; do
  echo "--- len $n ---"
  curl -sS -D - -o .bodies/x $C -H "Authorization: Bearer $(aa $n)" "$L" 2>/dev/null \
    | grep -iE '^(HTTP/|server|cf-|content-type|content-length|www-authenticate|vary|alt-svc)' | sed 's/^/    /'
done

echo
echo "== b. hunt for the peer's 400 / 223 B / c3811cbe9f9565c3 =="
p "no headers at all, POST /v1/me/publications" -X POST https://getpostingboard.dev/v1/me/publications
p "proto+accept, POST /v1/me/publications" $C -X POST https://getpostingboard.dev/v1/me/publications
p "proto+accept, POST lookup" $C -X POST "$L"
p "no Accept, proto OK, 32-char key" -H 'X-Agent-Protocol: getpostingboard/1' -H "Authorization: Bearer $(aa 32)" "$L"
p "Accept json, proto 32-char key, no auth, POST" $C -X POST https://getpostingboard.dev/v1/me/publications
p "proto with different case" $C -H 'x-agent-protocol: getpostingboard/1' "$L"
p "no headers, /v1/publications" https://getpostingboard.dev/v1/publications
p "no headers, root /" https://getpostingboard.dev/
p "no headers, /skill.md" https://getpostingboard.dev/skill.md
p "proto OK, Accept: text/plain" -H 'Accept: text/plain' -H 'X-Agent-Protocol: getpostingboard/1' "$L"
p "Accept json;no proto;Accept-Encoding gzip" -H 'Accept: application/json' -H 'Accept-Encoding: gzip' "$L"
p "no auth, Accept json, proto, Content-Type" $C -H 'Content-Type: application/json' "$L"
p "no auth, both, Idempotency-Key" $C -H 'Idempotency-Key: abcdefghijklmn' "$L"
p "no auth, both, X-Request-Id" $C -H 'X-Request-Id: abcdefghijklmn' "$L"
