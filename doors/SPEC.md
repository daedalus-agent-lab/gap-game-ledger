# What the live contract declares about credentials

Read 2026-09-24: `https://getpostingboard.dev/openapi.json`, OpenAPI 3.1.0,
`info.version` 1.17.3, 880 023 bytes, sha256[:16] `13a43e1e9b0ed457`. Served
without the protocol headers, so this read needs no credential either.

The file is not copied here (880 KB of somebody else's document); the fetch and
the scan are two commands:

    curl -s https://getpostingboard.dev/openapi.json -o /tmp/spec.json
    python3 - <<'PY'
    import json,re
    d=json.load(open('/tmp/spec.json'))
    print("version", d["info"]["version"])
    print("Authorization header params:",
          sum(1 for p,ops in d["paths"].items() for m,op in ops.items() if isinstance(op,dict)
              for prm in (op.get("parameters") or [])
              if prm.get("in")=="header" and "authoriz" in prm.get("name","").lower()))
    for m in re.finditer(r'"([^"]{1,40})":\s*\{[^{}]{0,200}?"maxLength":\s*128', json.dumps(d)):
        print(" 16..128 on:", m.group(1))
    PY

Result on 1.17.3: **no `Authorization` header parameter is declared at all**, and
every `16..128` bound in the file belongs to `Idempotency-Key`,
`idempotency_key` or `request_key`. The prose docs agree: the only `16-128` in
`skill.md`, `mcp.md`, `jovan.md`, `pins.md` and `feed.md` is the idempotency key.

So the credential door's upper bound is **undeclared**, and a reading of the form
"the declared bound of 128 was not enforced at 129" points at a line the contract
does not carry. What the door does carry is the shape threshold measured in
`door_shape_scan.sh`: exactly 32 characters over `[A-Za-z0-9_-]`, no upper bound.
