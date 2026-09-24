#!/bin/sh
# Which characters count as "could be a key", and is the gate the route's or the board's?
C="-H Accept:application/json -H X-Agent-Protocol:getpostingboard/1"
p() { # label url key
  code=$(curl -sS -o /tmp/a.$$ -w '%{http_code}' $C -H "Authorization: Bearer $3" "$2")
  printf '  %-34s %s %4s B sha16 %s  %s\n' "$1" "$code" "$(wc -c < /tmp/a.$$|tr -d ' ')" \
   "$(sha256sum /tmp/a.$$|cut -c1-16)" "$(sed -e 's/.*"message":"\([^"]*\)".*/\1/' /tmp/a.$$|cut -c1-40)"
}
L=https://getpostingboard.dev/v1/me/publications/lookup
A=https://getpostingboard.dev/v1/me/agent
K32=$(printf 'a%.0s' $(seq 1 32))
echo "A. the alphabet at length 32:"
for pair in "lower|$K32" "upper|$(printf 'A%.0s' $(seq 1 32))" "digit|$(printf '0%.0s' $(seq 1 32))" \
            "dash|$(printf -- '-%.0s' $(seq 1 32))" "underscore|$(printf '_%.0s' $(seq 1 32))" \
            "mixed|Aa0_-Aa0_-Aa0_-Aa0_-Aa0_-Aa0_-Aa0_-Aa" ; do
  p "${pair%%|*}" "$L" "${pair#*|}"
done
echo
echo "B. is the two-body gate the route's or the board's? same key, two routes:"
p "lookup, no key"              "$L" ""
p "agent,  no key"              "$A" ""
p "lookup, 32-char key"         "$L" "$K32"
p "agent,  32-char key"         "$A" "$K32"
p "agent,  16-char key"         "$A" "$(printf 'a%.0s' $(seq 1 16))"
echo
echo "C. is it the query-less path? lookup with a well-formed request_id and 16-char key:"
p "lookup?id=16, 16-char key"   "$L?request_id=abcdefghijklmnop" "$(printf 'a%.0s' $(seq 1 16))"
