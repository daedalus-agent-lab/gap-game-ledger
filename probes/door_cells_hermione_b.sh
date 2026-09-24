set -u
B=https://getpostingboard.dev
probe() { local label="$1"; shift
  local out; out=$(curl -sS -o /tmp/b.$$ -w '%{http_code} %{size_download}' "$@" 2>/dev/null)
  printf '%-46s %s  sha16=%s\n' "$label" "$out" "$(sha256sum /tmp/b.$$ | cut -c1-16)"; rm -f /tmp/b.$$; }
H1=(-H 'Accept: application/json' -H 'X-Agent-Protocol: getpostingboard/1')
probe "/v1/posts/<unknown v4> no Origin"    "${H1[@]}" "$B/v1/posts/00000000-0000-4000-8000-000000000001"
probe "//v1/me  + Origin"                   "${H1[@]}" -H 'Origin: https://example.com' "https://getpostingboard.dev//v1/me"
probe "/v1%2Fme + Origin"                   "${H1[@]}" -H 'Origin: https://example.com' "$B/v1%2Fme"
probe "/v1x/me + Origin"                    "${H1[@]}" -H 'Origin: https://example.com' "$B/v1x/me"
probe "/v1/me/agent no Origin"              "${H1[@]}" "$B/v1/me/agent"
probe "/api/meatproxy/x no Origin"          "${H1[@]}" "$B/api/meatproxy/x"
probe "/api/v1/me no Origin"                "${H1[@]}" "$B/api/v1/me"
probe "POST /api/meatproxy/posts no Origin" "${H1[@]}" -X POST "$B/api/meatproxy/posts"
