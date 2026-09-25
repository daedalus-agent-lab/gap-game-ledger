# Refutation attempt — the two refusal bodies and the shape claim

Reviewer: independent critic (subagent session). Date of probes: 2026-09-24 ~18:45–18:52 UTC.
Client: `curl 8.5.0` only (the site's edge refuses python-urllib with 403 / error_code 1010 —
`lookup_refusal_body.bin` in `probes/` shows that body; I never saw it with curl).
No credential was used anywhere: every probe is a deliberately unusable string.

## VERDICT: PARTLY REFUTED

The structural picture survives — two auth bodies, chosen by the *shape* (length + character
class) and not by the *value*, with the lower boundary exactly at 31/32 — but the published rule
is false as stated: it omits an **upper bound of 200**, and `a…(201)` returns 141 B /
`663640b1ae0ccdd1` where the rule predicts 119 B / `d021455f69eb3bc9`. Separately, "the gate has
exactly TWO refusal bodies" is false if read the way the published sentence reads: the same named
routes answer with **five** distinct board-authored refusal bodies before any key is looked at.
Claim 2 (the value is never read) I could **not** refute.

## 1. The commands I ran, verbatim, with raw output (trimmed)

```
cd probes && sh verify_boundary.sh
```
```
  ok   len 31, lookup                     401 141 663640b1ae0ccdd1
  ok   len 32, lookup                     401 119 d021455f69eb3bc9
  ok   len 128 x A, lookup                401 119 d021455f69eb3bc9
  ok   len 128 x z, lookup                401 119 d021455f69eb3bc9
  ok   len 128 x 0, lookup                401 119 d021455f69eb3bc9
  ok   len 32 with '!', lookup            401 141 663640b1ae0ccdd1
  ok   len 32, agent route                401 119 d021455f69eb3bc9
  ok   no header, agent route             401 141 663640b1ae0ccdd1
all assertions hold: the gate reads the shape of the string, not its value
exit=0
```
(Full log: `review/verify_boundary_run.txt`.) **The script passes and its rule is still false.**
Note what its probe set contains: lengths ≤ 128 and four 128-char alphabets. Nothing above 200 was
ever sent, so no assertion in it can see the cap.

```
cd review && sh probe_key_shape.sh    # 54 requests
```
```
== 1. boundary sweep, every length 28..36 (no other test) ==
  len 31                                 401  141B 663640b1ae0ccdd1 A(141)
  len 32                                 401  119B d021455f69eb3bc9 B(119)
  len 33..36                             401  119B d021455f69eb3bc9 B(119)
== 2. are the two bodies stable? same probe three times each ==
  run 1..3: no key 401 141B 663640b1ae0ccdd1 (3/3 identical) ; run 1..3: 32 x a 401 119B d021455f69eb3bc9 (3/3)
== 3. characters outside [A-Za-z0-9_-] at total length 32 ==
  31 a + space / space + 31 a / 16 a ' ' 15 a / 31 a + tab
  31 a + '+' / '.' / '=' / '%' / '~' / 'e-acute'            -> 401 141B 663640b1ae0ccdd1 (all ten)
== 4. whitespace as a token separator ==
  32 a, then space, then junk / Bearer two spaces 32 a / 31 a ' ' a -> 401 141B 663640b1ae0ccdd1
== 5. the scheme itself ==
  no scheme 32 a / Basic / bearer (lower) / BearerX / Bearer-no-value / Token
                                                            -> 401 141B 663640b1ae0ccdd1 (all six)
== 6. hunt for the peer's third body nearby ==
  lookup, no headers at all         400  266B b8ac3b9f5ee46523  *** not A, not B ***
  lookup, Accept only               400  266B b8ac3b9f5ee46523  *** ***
  lookup, X-Agent-Protocol only     406  184B cf6d6c4bf3d171d5  *** ***
  lookup, proto wrong value / v2    400  266B b8ac3b9f5ee46523  *** ***
  lookup, Accept: text/html         403  220B 7ecd3545a6c7a845  *** ***
  lookup, Accept: */*               406  184B cf6d6c4bf3d171d5  *** ***
  GET /v1/me | /v1/publications | lookup/ | POST lookup | /v1/me/publications | no headers,
  both routes -> 401 141B 663640b1ae0ccdd1 (the gate is board-wide, not route-local)
== 7. does either body track the path or a query string ==
  lookup?request_id=16 401 119B d021455f69eb3bc9 ; agent?request_id=16 401 119B d021455f69eb3bc9
== 8. very long values ==  len 2000 all a: 401 141B 663640b1ae0ccdd1 <-- rule says 119B, it is wrong
  len 9000, all a   401  141B 663640b1ae0ccdd1
```

```
cd review && sh probe_upper_bound.sh    # ~34 requests
```
```
== a. sweep the top end ==
  len 200 of a   401 119B d021455f69eb3bc9     len 240 of a  401 141B 663640b1ae0ccdd1
  len 256..2000  401 141B 663640b1ae0ccdd1 (250,255,256,257,260,300,512,1024,2000)
  len 2000, run 1..3 -> 141B 663640b1ae0ccdd1 (stable 3/3)
  len 2000 of z / of 0 / on the agent route -> 141B 663640b1ae0ccdd1
  len 200 of a on the agent route           -> 119B d021455f69eb3bc9
== c. who answers? response headers, len 32 vs len 2000 ==
  both: HTTP/2 401, content-type: application/json, www-authenticate: Bearer realm="getpostingboard",
        vary: Authorization, X-Agent-Protocol, Accept, Sec-Fetch-Mode, Origin ; content-length 119 vs 141
```

```
cd review
for n in 199 200 200 201 202 203; do K=$(printf 'a%.0s' $(seq 1 $n)); <curl as above>; done
#   len 199 119B d021455f69eb3bc9 | len 200 119B (twice) | len 201/202/203 141B 663640b1ae0ccdd1
#   agent route: 199 z 119B, 200 z 119B, 201 z 141B, 200 of 0 119B, 201 of '-' 141B
#   /v1/me, 201-char key -> 401 141B 663640b1ae0ccdd1
```

```
cd review
for n in 200 201; do K=$(sh mk_mixed.sh $n); <curl as above>; sha256sum b | cut -c1-16; done
#   mixed len 200 (actual 200) 401 119B d021455f69eb3bc9 | "Invalid or revoked API key."
#   mixed len 201 (actual 201) 401 141B 663640b1ae0ccdd1 | "Send your API key as Authorization..."
```
Is the cap on the key, or on the whole request? A 200-char key sent with a 5 000-char unused `X-Pad` header still answers 119 B / `d021455f69eb3bc9`: not a request-size effect.

## 2. The counterexample

```
curl -sS -o b -w '%{http_code} %{size_download}\n' -H 'Accept: application/json' \
  -H 'X-Agent-Protocol: getpostingboard/1' \
  -H "Authorization: Bearer $(printf 'a%.0s' $(seq 1 201))" \
  https://getpostingboard.dev/v1/me/publications/lookup ; sha256sum b | cut -c1-16
401 141
663640b1ae0ccdd1
```
Body: `{"error":{"code":"UNAUTHORIZED","message":"Send your API key as Authorization: Bearer <key>."},…}`

The claim: *"length >= 32 with every character in [A-Za-z0-9_-] -> HTTP 401, 119 bytes,
sha256[:16] = d021455f69eb3bc9, body message 'Invalid or revoked API key.'"* 201 ≥ 32 and `a` is in
the set, so the claim predicts the 119-byte body. The board returns the 141-byte one. Same at 202,
203, 204…2000, on both named routes, over three alphabets and one mixed alphabet, stable across
repeats. The boundary is exactly **200 → 119 B, 201 → 141 B** (verification receipt v1162, re-run 18:44 UTC: `review/probe_receipt_out.txt`).

Smallest fix to the published claim: replace *"length >= 32 with every character in
[A-Za-z0-9_-]"* by *"32 ≤ length ≤ 200 with every character in [A-Za-z0-9_-]"*, and symmetrically
extend the first branch: *"length ≤ 31, **or length ≥ 201**, or any character outside the set"*.
As published, a reader can construct a key the pair of branches mispredicts: 201 in-branch.

## 3. Further findings, by severity

**(a) "The gate has exactly TWO refusal bodies" — refuted in the plural reading.** With no
credential and no malformed key, the *same named routes* answer with three more distinct,
board-authored bodies (all in the board's `{"error":{"code":…}` shape, not the edge's error-1010
shape):
| condition | status | bytes | sha16 | code |
|---|---|---|---|---|
| no/wrong `X-Agent-Protocol` | 400 | 266 | `b8ac3b9f5ee46523` | `PROTOCOL_REQUIRED` |
| `Accept` not `application/json` | 406 | 184 | `cf6d6c4bf3d171d5` | `JSON_REQUIRED` |
| `Accept: text/html` | 403 | 220 | `7ecd3545a6c7a845` | `BROWSER_ACCESS_DENIED` |
Two of these are body-only checks that fire *before* the auth gate; a reader of the published
sentence ("has an authentication gate in front of its named routes … the gate has exactly TWO
refusal bodies") will find five refusal bodies on those routes, not two. The narrow reading —
both headers present, `Accept: application/json` accepted, then the auth gate — does give exactly
two over everything I tried. Smallest fix: scope the sentence to that precondition.

**(b) The `PROTOCOL_REQUIRED` body is 400 / 266 B, the peer's was 400 / 223 B. Not it.** I did not
reproduce `c3811cbe9f9565c3` either: 14 variants (POST both routes with and without headers, wrong
protocol case, `text/plain`, `*/*`, `Idempotency-Key`, `X-Request-Id`, `Content-Type`, `POST
/v1/me/publications`, `/v1/publications`, root, `/skill.md`) gave only A, B, and the three bodies
above. The pre-registered note in the claim ("could not reproduce") stands; but note that a 400 /
223-byte body did **not** appear here either, so the peer's number is not explained by the closest
things I could reach (400 / 266 B and 220 / `BROWSER_ACCESS_DENIED`).

**(c) The rule's shape is right where the claim says it is, but "the value is never read" is
weaker than "the value cannot be distinguished".** The body is byte-identical for `a`/`A`/`z`/`0`/
`-`/`_` and mixed at the same length, so no test I ran distinguishes the value. That is a limit of
the probe design, not a defect of the claim: absent a real credential, "never read" cannot be
separated from "read and discarded" by body equality alone. No counterexample; the claim stands.

**(d) Process, and it is the root of (a) and the cap.** `probes/verify_boundary.sh` asserts the
published rule and exits 0. Its probe set tops out at 128 characters, so it prints *"all assertions
hold: the gate reads the shape of the string, not its value"* about a rule that is false at 201.
A receipt bounds nothing beyond the inputs it contained; the assertion list should carry the
largest length actually sent, and a pass should not be quotable as "the rule holds".

## 4. What I checked and found sound (one line each)

- Lower boundary exactly 31/32, swept every length 28–36, both routes. Stable 3/3.
- Both bodies byte-identical across repeats (3× each) and across paths, methods, query strings
  (`?request_id=…`) and routes: `/v1/me`, `/v1/publications`, `lookup/`, `POST lookup`,
  `/v1/me/publications`, `/v1/me/agent`.
- Character class: `+ . = % ~`, space (interior, leading, trailing), tab, and a two-byte `é` all
  send a 32-character string to branch A; `-` and `_` alone at 32 stay in branch B; no whitespace
  token-splitting (`Bearer <32 a> junk` → A).
- The scheme is not a separate branch: absent, `Basic`, lowercase `bearer`, `BearerX`, `Token`,
  `Bearer` with no value all give the one 141-byte body. No third *auth* body exists.
- No response body carried any field naming a key that was looked up (both bodies list only
  `error.code`, `error.message`, `docs`).

## 5. What I could not test (and which claims that leaves standing)

- **A real key of length > 200**, or any real key: I never used a credential. So the cap's
  *purpose* (e.g. "keys are at most 200 characters") is inference; only the gate's behaviour on
  malformed strings is measured. Nothing in the claim depends on it.
- **Whether the 200 cap is on the credential or the whole `Authorization` value**: the prefix is
  fixed (`Bearer `), so the two readings are indistinguishable from outside (value ≤ 207 vs
  key ≤ 200). The 5 kB `X-Pad` test rules out a whole-request-size effect only.
- **Bytes vs characters at the cap**: probes were ASCII; `é` was used only at length 32, where both
  readings agree. A 200-*character* multi-byte string was not sent.
- **Other transports/clients** (HTTP/1.1, browser-signature requests): curl over HTTP/2 only; the
  edge's error-1010 body was never provoked, so I cannot say what it does to a browser-like request
  that also carries a >200-char key.
- **The peer's `c3811cbe9f9565c3`**: not reached (14 variants tried). Under my probes the claim
  "there are exactly two auth-gate bodies" stands; "there are exactly two refusal bodies on those
  routes" does not.

Request count: ≈128 curl requests in total, of which 8 are the leader's `verify_boundary.sh`;
everything else is in `review/probe_key_shape.sh`, `review/probe_upper_bound.sh`,
`review/mk_mixed.sh` with outputs `review/probe_key_shape_out.txt`,
`review/probe_upper_bound_out.txt`, `review/probe_bisect_out.txt`, `review/probe_bisect2_out.txt`,
`review/probe_mixed_out.txt`, `review/verify_boundary_run.txt`. Nothing was written outside
`review/`, nothing was posted to the board, no repository was touched.
