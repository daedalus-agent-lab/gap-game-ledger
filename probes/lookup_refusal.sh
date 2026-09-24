#!/bin/sh
# hermione's claim, run by a stranger -- via curl, because the edge refuses
# non-browser clients outright (403, error_code 1010, browser_signature_banned).
# The five reasons: absent header, 14, 15, 16-with-invalid-character, 129.
# No credential is used or needed; the probes are deliberately invalid strings.
URL='https://getpostingboard.dev/v1/me/publications/lookup'
hdr() {
  printf '  %-12s ' "$1"
  if [ "$1" = absent ]; then
    curl -sS -o /tmp/b.$$ -w '%{http_code} %{size_download} ' \
      -H 'Accept: application/json' -H 'X-Agent-Protocol: getpostingboard/1' "$URL"
  else
    curl -sS -o /tmp/b.$$ -w '%{http_code} %{size_download} ' \
      -H 'Accept: application/json' -H 'X-Agent-Protocol: getpostingboard/1' \
      -H "Authorization: Bearer $2" "$URL"
  fi
  printf '%s B sha16 ' "$(wc -c < /tmp/b.$$ | tr -d ' ')"
  sha256sum /tmp/b.$$ | cut -c1-16
  cmp -s /tmp/b.$$ /tmp/first.$$ 2>/dev/null || cp /tmp/b.$$ /tmp/first.$$.new 2>/dev/null
  [ -f /tmp/first.$$ ] || cp /tmp/b.$$ /tmp/first.$$
  cp /tmp/b.$$ /tmp/last.$$
}
echo "claim: 400, 223 B / 221 chars, sha16 c3811cbe9f9565c3"
rm -f /tmp/first.$$ /tmp/last.$$
hdr absent
hdr 14 "$(printf 'a%.0s' $(seq 1 14))"
hdr 15 "$(printf 'a%.0s' $(seq 1 15))"
hdr 16-bad-char "$(printf 'a%.0s' $(seq 1 15))!"
hdr 129 "$(printf 'a%.0s' $(seq 1 129))"
echo
echo "first body vs last body identical: $(cmp -s /tmp/first.$$ /tmp/last.$$ && echo yes || echo no)"
echo "--- first body ---"
cat /tmp/first.$$
echo
echo "--- last body ---"
cat /tmp/last.$$
