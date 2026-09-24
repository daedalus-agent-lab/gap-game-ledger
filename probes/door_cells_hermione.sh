set -u
B=https://getpostingboard.dev
probe() {  # label, curl args...
  local label="$1"; shift
  local out; out=$(curl -sS -o /tmp/body.$$ -w '%{http_code} %{size_download}' "$@" 2>/dev/null)
  printf '%-42s %s  sha16=%s\n' "$label" "$out" "$(sha256sum /tmp/body.$$ | cut -c1-16)"
  rm -f /tmp/body.$$
}
H1=(-H 'Accept: application/json' -H 'X-Agent-Protocol: getpostingboard/1')
probe "/v1/me  (baseline)"                 "${H1[@]}" "$B/v1/me"
probe "/v1/me + Origin"                    "${H1[@]}" -H 'Origin: https://example.com' "$B/v1/me"
probe "/v1//me  + Origin"                  "${H1[@]}" -H 'Origin: https://example.com' "$B/v1//me"
probe "/v1/me  + S-F-Storage-Access:active" "${H1[@]}" -H 'Sec-Fetch-Storage-Access: active' "$B/v1/me"
probe "/v1/me  + Accept: text/html;q=0"    -H 'Accept: text/html;q=0' -H 'X-Agent-Protocol: getpostingboard/1' "$B/v1/me"
probe "/v1/me  + Accept: TEXT/HTML"        -H 'Accept: TEXT/HTML' -H 'X-Agent-Protocol: getpostingboard/1' "$B/v1/me"
probe "/v1/posts/<unknown v4> + Origin"    "${H1[@]}" -H 'Origin: https://example.com' "$B/v1/posts/00000000-0000-4000-8000-000000000001"
