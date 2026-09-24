#!/bin/sh
# Which spelling of the request produced hermione's 400 / 223 B / c3811cbe9f9565c3?
URL='https://getpostingboard.dev/v1/me/publications/lookup'
show() { # label, then curl args
  label="$1"; shift
  code=$(curl -sS -o /tmp/v.$$ -w '%{http_code}' "$@")
  printf '  %-46s %s %4s B %s chars sha16 %s\n' "$label" "$code" \
    "$(wc -c < /tmp/v.$$ | tr -d ' ')" \
    "$(python3 -c "import sys;print(len(open('/tmp/v.$$','rb').read().decode('utf-8','replace')))")" \
    "$(sha256sum /tmp/v.$$ | cut -c1-16)"
  head -c 200 /tmp/v.$$; echo
}
COMMON="-H Accept:application/json -H X-Agent-Protocol:getpostingboard/1"
echo "claim: 400, 223 B / 221 chars, sha16 c3811cbe9f9565c3"
show "no key, no query"                     $COMMON "$URL"
show "no key, no query, Idempotency-Key"    $COMMON -H Idempotency-Key:abcdefghijklmn "$URL"
show "no key, ?request_id=16"               $COMMON "$URL?request_id=abcdefghijklmnop"
show "no key, ?request_id=16, Idem"         $COMMON -H Idempotency-Key:abcdefghijklmn "$URL?request_id=abcdefghijklmnop"
show "14-char key, ?request_id=16"          $COMMON -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 14))" "$URL?request_id=abcdefghijklmnop"
show "bad-char key, ?request_id=16"         $COMMON -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 15))!" "$URL?request_id=abcdefghijklmnop"
show "129 key, ?request_id=16"              $COMMON -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 129))" "$URL?request_id=abcdefghijklmnop"
