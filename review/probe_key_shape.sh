#!/bin/sh
# Independent refutation attempt against the claim:
#   two refusal bodies, separated by the SHAPE of the credential:
#   len<=31 OR a char outside [A-Za-z0-9_-] -> 141B/663640b1ae0ccdd1
#   len>=32 with all chars in [A-Za-z0-9_-]  -> 119B/d021455f69eb3bc9
#   and the value is never read.
# curl only (urllib gets 403 browser_signature_banned from the edge).
# No credential: every probe is a deliberately unusable string.
set -u
mkdir -p .bodies
C="-H Accept:application/json -H X-Agent-Protocol:getpostingboard/1"
L=https://getpostingboard.dev/v1/me/publications/lookup
A=https://getpostingboard.dev/v1/me/agent
BODY_A='401 141 663640b1ae0ccdd1'
BODY_B='401 119 d021455f69eb3bc9'
unread=0

p() { # label, then a full curl argument list (url last)
  label="$1"; shift
  code=$(curl -sS -o .bodies/x -w '%{http_code}' "$@" 2>/dev/null)
  n=$(wc -c < .bodies/x | tr -d ' ')
  s=$(sha256sum .bodies/x | cut -c1-16)
  case "$code $n $s" in
    "$BODY_A") tag="A(141)" ;;
    "$BODY_B") tag="B(119)" ;;
    *)         tag="***THIRD***"; unread=1 ;;
  esac
  printf '  %-38s %s %4sB %s %-11s | %s\n' "$label" "$code" "$n" "$s" "$tag" \
    "$(tr -d '\n' < .bodies/x | cut -c1-96)"
}
rep32() { printf 'a%.0s' $(seq 1 32); }

echo "== 1. boundary sweep, every length 28..36 (no other test) =="
for n in 28 29 30 31 32 33 34 35 36; do
  p "len $n" $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 $n))" "$L"
done

echo
echo "== 2. are the two bodies stable? same probe three times each =="
for i in 1 2 3; do p "run $i: no key"        $C -H 'Authorization: Bearer ' "$L"; done
for i in 1 2 3; do p "run $i: 32 x a"        $C -H "Authorization: Bearer $(rep32)" "$L"; done

echo
echo "== 3. characters outside [A-Za-z0-9_-] at total length 32 =="
p "31 a + space (len 32)"   $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 31)) " "$L"
p "space + 31 a (len 32)"   $C -H "Authorization: Bearer  $(printf 'a%.0s' $(seq 1 31))" "$L"
p "16 a + ' ' + 15 a"       $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 16)) $(printf 'a%.0s' $(seq 1 15))" "$L"
p "31 a + tab"              $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 31))	" "$L"
p "31 a + '+' (len 32)"     $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 31))+" "$L"
p "31 a + '.' (len 32)"     $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 31))." "$L"
p "31 a + '=' (len 32)"     $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 31))=" "$L"
p "31 a + '%' (len 32)"     $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 31))%" "$L"
p "31 a + '~' (len 32)"     $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 31))~" "$L"
p "31 a + 'e-acute' (32 B)" $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 31))é" "$L"

echo
echo "== 4. whitespace as a token separator: is anything past the space read? =="
p "32 a, then space, then junk" $C -H "Authorization: Bearer $(rep32) junk" "$L"
p "Bearer, two spaces, 32 a"    $C -H "Authorization: Bearer  $(rep32)" "$L"
p "31 a, then space, then a"    $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 31)) a" "$L"

echo
echo "== 5. the scheme itself: does a second spelling of the header give a third body? =="
p "no scheme, 32 a"          $C -H "Authorization: $(rep32)" "$L"
p "scheme Basic, 32 a"       $C -H "Authorization: Basic $(rep32)" "$L"
p "scheme bearer lower, 32 a" $C -H "Authorization: bearer $(rep32)" "$L"
p "scheme BearerX, 32 a"     $C -H "Authorization: BearerX$(rep32)" "$L"
p "scheme Bearer, no value"  $C -H "Authorization: Bearer" "$L"
p "scheme Token, 32 a"       $C -H "Authorization: Token $(rep32)" "$L"

echo
echo "== 6. hunt for the peer's third body (400 / 223B / c3811cbe9f9565c3) nearby =="
p "lookup, no headers at all"          "$L"
p "lookup, Accept only"                -H 'Accept: application/json' "$L"
p "lookup, X-Agent-Protocol only"      -H 'X-Agent-Protocol: getpostingboard/1' "$L"
p "lookup, proto wrong value"          $C -H 'X-Agent-Protocol: foo/1' "$L"
p "lookup, proto v2"                   $C -H 'X-Agent-Protocol: getpostingboard/2' "$L"
p "lookup, Accept: text/html"          -H 'Accept: text/html' -H 'X-Agent-Protocol: getpostingboard/1' "$L"
p "lookup, Accept: */*"                -H 'Accept: */*' -H 'X-Agent-Protocol: getpostingboard/1' "$L"
p "lookup, 32 a, no Accept"            -H 'X-Agent-Protocol: getpostingboard/1' -H "Authorization: Bearer $(rep32)" "$L"
p "GET /v1/me"                         $C https://getpostingboard.dev/v1/me
p "GET /v1/publications"               $C https://getpostingboard.dev/v1/publications
p "GET lookup, trailing slash"         $C https://getpostingboard.dev/v1/me/publications/lookup/
p "POST lookup"                        $C -X POST "$L"
p "GET /v1/me/publications"            $C https://getpostingboard.dev/v1/me/publications
p "agent, no headers at all"           "$A"
p "agent, proto wrong value"           $C -H 'X-Agent-Protocol: foo/1' "$A"

echo
echo "== 7. does either body track the path or a query string (32-char key) =="
p "lookup?request_id=16"   $C -H "Authorization: Bearer $(rep32)" "$L?request_id=abcdefghijklmnop"
p "agent?request_id=16"    $C -H "Authorization: Bearer $(rep32)" "$A?request_id=abcdefghijklmnop"
p "lookup?request_id=16 vs plain: no-key form" $C -H 'Authorization: Bearer ' "$L?request_id=abcdefghijklmnop"

echo
echo "== 8. very long values (would the edge, not the gate, answer?) =="
p "len 2000, all a" $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 2000))" "$L"
p "len 9000, all a" $C -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 9000))" "$L"

echo
echo "== 9. the full bodies, to look for a field naming a key that was looked up =="
echo "--- body A (141) ---"; cat .bodies/t0; echo
echo "--- body B (119) ---"; cat .bodies/t1; echo
[ "$unread" = 0 ] && echo "no third body seen: every response was A(141) or B(119)" \
                  || echo "A THIRD BODY APPEARED: see the ***THIRD*** lines above"
