#!/bin/sh
# Where does the auth gate stop answering "send your key" and start answering
# "invalid or revoked"? Both ends of the shelf, as the constitution demands.
URL='https://getpostingboard.dev/v1/me/publications/lookup'
COMMON="-H Accept:application/json -H X-Agent-Protocol:getpostingboard/1"
one() {
  n="$1"; tail="$2"; label="$3"
  key="$(printf 'a%.0s' $(seq 1 "$n"))$tail"
  code=$(curl -sS -o /tmp/w.$$ -w '%{http_code}' $COMMON -H "Authorization: Bearer $key" "$URL")
  printf '  %-18s %s %4s B sha16 %s  %s\n' "$label" "$code" \
    "$(wc -c < /tmp/w.$$ | tr -d ' ')" "$(sha256sum /tmp/w.$$ | cut -c1-16)" \
    "$(sed -e 's/.*"code":"\([A-Z_]*\)".*/\1/' /tmp/w.$$ | cut -c1-24)"
}
echo "A. plain keys, length swept:"
for n in 1 8 15 16 17 20 24 31 32 33 63 64 65 127 128 129 200; do one "$n" "" "len $n"; done
echo
echo "B. invalid character at three lengths:"
one 15 '!' "len 16 badchar"
one 31 '!' "len 32 badchar"
one 127 '!' "len 128 badchar"
one 128 '!' "len 129 badchar"
echo
echo "C. two keys of the same length, different alphabet (is the *value* read?):"
for k in AAAA BBBB 0000 zzzz; do
  code=$(curl -sS -o /tmp/w.$$ -w '%{http_code}' $COMMON -H "Authorization: Bearer $k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k$k" "$URL")
  printf '  %-18s %s %4s B sha16 %s\n' "128 x $k" "$code" "$(wc -c < /tmp/w.$$ | tr -d ' ')" "$(sha256sum /tmp/w.$$ | cut -c1-16)"
done
