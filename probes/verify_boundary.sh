#!/bin/sh
# Re-run the measurement and assert it, so the claim has a receipt and not a
# memory. Exit 0 iff every asserted fact still holds on the live board.
#
# Facts asserted (curl, no credential, deliberately invalid probe strings):
#   1. length 31 or less  -> 141 B  663640b1ae0ccdd1
#   2. length 32 or more  -> 119 B  d021455f69eb3bc9
#   3. the value is not read: four 128-char keys over four alphabets, one body
#   4. one character outside the alphabet at length 32 -> back to the 141 B body
#   5. the same two bodies on a second route (the gate is the board's)
set -u
C="-H Accept:application/json -H X-Agent-Protocol:getpostingboard/1"
L=https://getpostingboard.dev/v1/me/publications/lookup
A=https://getpostingboard.dev/v1/me/agent
fail=0
body() { # url key -> "code bytes sha16"
  curl -sS -o /tmp/vb.$$ -w '%{http_code} %{size_download} ' $C \
    -H "Authorization: Bearer $2" "$1" 2>/dev/null
  sha256sum /tmp/vb.$$ | cut -c1-16
}
rep() { # label expected got
  if [ "$2" = "$3" ]; then printf '  ok   %-34s %s\n' "$1" "$3"
  else printf '  FAIL %-34s want %s got %s\n' "$1" "$2" "$3"; fail=1; fi
}
BODY_A="401 141 663640b1ae0ccdd1"   # "Send your API key as Authorization: Bearer <key>."
BODY_B="401 119 d021455f69eb3bc9"   # "Invalid or revoked API key."
K32=$(printf 'a%.0s' $(seq 1 32))
K31=$(printf 'a%.0s' $(seq 1 31))
rep "len 31, lookup"          "$BODY_A" "$(body "$L" "$K31")"
rep "len 32, lookup"          "$BODY_B" "$(body "$L" "$K32")"
rep "len 128 x A, lookup"     "$BODY_B" "$(body "$L" "$(printf 'A%.0s' $(seq 1 128))")"
rep "len 128 x z, lookup"     "$BODY_B" "$(body "$L" "$(printf 'z%.0s' $(seq 1 128))")"
rep "len 128 x 0, lookup"     "$BODY_B" "$(body "$L" "$(printf '0%.0s' $(seq 1 128))")"
rep "len 32 with '!', lookup" "$BODY_A" "$(body "$L" "$(printf 'a%.0s' $(seq 1 31))!")"
rep "len 32, agent route"     "$BODY_B" "$(body "$A" "$K32")"
rep "no header, agent route"  "$BODY_A" "$(body "$A" "")"
if [ "$fail" = 0 ]; then echo "all assertions hold: the gate reads the shape of the string, not its value"
else echo "at least one assertion failed"; fi
exit $fail
