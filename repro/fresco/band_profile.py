#!/usr/bin/env python3
"""A seam is a band, not a border: the multi-inset profile of a pair of edges.

Why this exists
---------------
The wall's published rule samples runs *at* the border, so every number it
publishes about a seam is a number about one row of pixels. A metric that samples
only the boundary is one witness about the rim, published as a claim about the
band: two tiles can agree exactly on the border row and diverge immediately
inside it, and the border scalar will report a clean seam. The fix is not a
stricter threshold but a different shape of result - a profile over insets:

    {k: distances at inset k, offset_at_k, worst_abs, origin_left, origin_right,
     digest_per_side}

so that a reader sees where inside the band the two pictures part.

This module renders each tile ALONE (never both in one frame - that measures the
layout) and emits that record. It also builds the synthetic falsifier: a pair
that is byte-identical on the border row and divided by 200 at inset 7, where the
border-only verdict is PASS and the profile's is FAIL.

Run:  uv run --with pillow python band_profile.py            (fixtures + real pairs)
      uv run --with pillow python band_profile.py --self-test
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHROME = ["chromium", "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars"]
SIDES = ("north", "south", "west", "east")


def render(svg_bytes: bytes, size: int = 300, background=(0, 0, 0)) -> list[list[tuple[int, int, int]]]:
    """One tile alone, in its own frame, at 1:1. Never two tiles in one frame.

    Transparency is composited on `background` and the count of transparent pixels
    is returned with the rows, because a tile whose background is not its own ink
    renders as the page behind it and a number read off that is a number about the
    page.
    """
    b64 = base64.b64encode(svg_bytes).decode()
    html = (f"<html><body style='margin:0;background:rgb({background[0]},{background[1]},"
            f"{background[2]})'>"
            f"<img src='data:image/svg+xml;base64,{b64}' width={size} height={size}>"
            f"</body></html>")
    tag = hashlib.sha1(svg_bytes).hexdigest()[:10]
    h, png = HERE / f".profile_{tag}.html", HERE / f".profile_{tag}.png"
    h.write_text(html)
    subprocess.run(CHROME + [f"--screenshot={png}", f"--window-size={size},{size}",
                             "file://" + str(h)], check=True, capture_output=True)
    from PIL import Image
    im = Image.open(png).convert("RGB")
    rows = [[im.getpixel((x, y)) for x in range(size)] for y in range(size)]
    h.unlink()
    png.unlink()
    return rows


def walk(rows, side: str, inset: int) -> list[tuple[int, int, int]]:
    """The line of pixels at `inset` from `side`, walked as a reader at that seam sees it.

    Both edges of a seam are walked in the same direction along the shared line and
    inward in the same sense, so index i is the same position for both tiles.
    """
    n = len(rows)
    if side == "north":
        return list(rows[inset])[:n]
    if side == "south":
        return list(rows[n - 1 - inset])[:n]
    if side == "west":
        return [rows[i][inset] for i in range(n)]
    if side == "east":
        return [rows[i][n - 1 - inset] for i in range(n)]
    raise ValueError(f"side must be one of {SIDES}, got {side!r}")


def dist(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b)) ** 0.5


def line_distance(left, right, max_offset: int = 30) -> dict:
    """Worst and mean distance, and the offset that best aligns the two lines."""
    best = None
    for off in range(-max_offset, max_offset + 1):
        pairs = [(left[i], right[i - off]) for i in range(max(len(left), 0))
                 if 0 <= i - off < len(right)]
        if not pairs:
            continue
        worst = max(dist(a, b) for a, b in pairs)
        mean = sum(dist(a, b) for a, b in pairs) / len(pairs)
        key = (round(mean, 6), abs(off))
        if best is None or key < best[0]:
            best = (key, off, worst, mean)
    _, off, worst, mean = best
    return {"offset": off, "worst": worst, "mean": mean}


def profile(a_bytes: bytes, a_side: str, b_bytes: bytes, b_side: str,
            kmax: int = 14, tol: float = 70.0) -> dict:
    """The multi-inset record for one pair of edges."""
    a, b = render(a_bytes), render(b_bytes)
    return profile_rows(a, b, a_side, b_side, kmax, tol,
                        sha_a=hashlib.sha256(a_bytes).hexdigest()[:16],
                        sha_b=hashlib.sha256(b_bytes).hexdigest()[:16])


def profile_rows(a, b, a_side: str, b_side: str, kmax: int = 14, tol: float = 70.0,
                 sha_a: str = "-", sha_b: str = "-") -> dict:
    """The multi-inset record for two rendered tiles."""
    insets = {}
    for k in range(kmax + 1):
        la, lb = walk(a, a_side, k), walk(b, b_side, k)
        d = line_distance(la, lb)
        insets[k] = {"offset_at_k": d["offset"], "worst": round(d["worst"], 2),
                     "mean": round(d["mean"], 2)}
    border_worst = insets[0]["worst"]
    band_worst = max(v["worst"] for v in insets.values())
    worst_k = max(insets, key=lambda k: insets[k]["worst"])
    la, lb = walk(a, a_side, 0), walk(b, b_side, 0)
    fits_digest = lambda line: hashlib.sha256(
        bytes(v for px in line for v in px)).hexdigest()[:16]
    record = {
        "a": {"side": a_side, "digest_border": fits_digest(la),
              "origin_left": la[0], "origin_right": la[-1],
              "sha256": sha_a},
        "b": {"side": b_side, "digest_border": fits_digest(lb),
              "origin_left": lb[0], "origin_right": lb[-1],
              "sha256": sha_b},
        "kmax": kmax, "tolerance": tol,
        "insets": {str(k): v for k, v in insets.items()},
        "border_worst": border_worst,
        "band_worst": band_worst,
        "band_worst_at_k": worst_k,
        "border_only_verdict": "PASS" if border_worst <= tol else "FAIL",
        "profile_verdict": "PASS" if band_worst <= tol else "FAIL",
        "band_diverges_where_the_border_agrees": border_worst <= tol < band_worst,
    }
    return record


# ---------------------------------------------------------------- the falsifier

def falsifier_pair(size: int = 300, mid: int = 7, step: int = 200) -> tuple[bytes, bytes]:
    """Two tiles equal on the border row and divided by `step` at inset `mid`.

    A is flat `#101020`; B is the same, except its rows at inset >= mid carry
    `#101020 + step` in the red channel. Nothing about the border row differs.
    """
    def svg(shift: bool) -> bytes:
        r = (16 + (step if shift else 0))
        body = (f"<rect x='0' y='0' width='{size}' height='{mid}' fill='#101020'/>"
                f"<rect x='0' y='{mid}' width='{size}' height='{size - mid}' fill='#{r:02x}1020'/>")
        return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{size}' height='{size}' "
                f"viewBox='0 0 {size} {size}'>{body}</svg>").encode()
    return svg(False), svg(True)


def self_test() -> int:
    bad = []

    def check(name, cond, detail=""):
        print(("ok   " if cond else "FAIL ") + name + ("" if cond else f"  {detail}"))
        if not cond:
            bad.append(name)

    a, b = falsifier_pair()
    ra, rb = render(a), render(b)
    la, lb = walk(ra, "north", 0), walk(rb, "north", 0)
    check("the falsifier pair is identical on the border row",
          la == lb, f"{la[0]} vs {lb[0]}")
    rec = profile(a, "north", b, "north")
    check("border-only verdict says PASS", rec["border_only_verdict"] == "PASS", rec["border_worst"])
    check("the profile says FAIL", rec["profile_verdict"] == "FAIL", rec["band_worst"])
    check("the profile names the inset where they part",
          rec["band_worst_at_k"] == 7 and rec["band_worst"] >= 199,
          (rec["band_worst_at_k"], rec["band_worst"]))
    check("the record carries both origins and both digests",
          all(rec[s][k] is not None for s in ("a", "b")
              for k in ("origin_left", "origin_right", "digest_border")))
    # a pair that agrees everywhere must pass both
    same = profile(a, "north", a, "north")
    check("a pair with nothing to see passes both verdicts",
          same["border_only_verdict"] == "PASS" and same["profile_verdict"] == "PASS")
    # the walk is index-aligned across a shared seam: my north index i touches their
    # south index i, and both are walked in the same direction along the line
    rows = render(a)
    check("the walks are index-aligned along a shared seam",
          all((walk(rows, side, 0)[i] == rows[row][i])
              for side, row in (("north", 0), ("south", 299))
              for i in (0, 150, 299)))
    check("a tile against itself reads offset 0 at every inset",
          all(line_distance(walk(rows, "east", k), walk(rows, "east", k))["offset"] == 0
              for k in range(3)))
    print(f"\n{7 - len(bad)} of 7 checks pass")
    return 1 if bad else 0


def report_pairs() -> int:
    pairs = [
        ("40146 west against 12216 east (the wall records met 3)",
         HERE / "attest/tile_40146.svg", "west", HERE / "attest/tile_12216.svg", "east"),
        ("54908 south against 12216 north (the wall records met 1, offset 0)",
         HERE / "attest/tile_54908.svg", "south", HERE / "attest/tile_12216.svg", "north"),
        ("40146 north against an empty cell (no seam record exists)",
         HERE / "attest/tile_40146.svg", "north", None, None),
    ]
    out = {}
    for label, a, aside, b, bside in pairs:
        if b is None:
            rows = render(a.read_bytes())
            insets = {k: round(max(dist(x, walk(rows, aside, 0)[i])
                                   for i, x in enumerate(walk(rows, aside, k))), 2)
                      for k in range(15)}
            worst_k = max(insets, key=lambda k: insets[k])
            print(f"{label}\n  band self-spread (inset vs its own border): "
                  f"worst {insets[worst_k]:.2f} at k={worst_k}; over 70: "
                  f"{[k for k, v in insets.items() if v > 70]}")
            out[label] = {"insets": insets, "worst_at_k": worst_k}
            continue
        rec = profile(a.read_bytes(), aside, b.read_bytes(), bside)
        out[label] = rec
        print(f"{label}\n  border-only {rec['border_only_verdict']} (worst "
              f"{rec['border_worst']:.2f}); profile {rec['profile_verdict']} "
              f"(worst {rec['band_worst']:.2f} at k={rec['band_worst_at_k']}); "
              f"origins {rec['a']['origin_left']}/{rec['a']['origin_right']} vs "
              f"{rec['b']['origin_left']}/{rec['b']['origin_right']}; "
              f"digests {rec['a']['digest_border']}/{rec['b']['digest_border']}")
    bad = [k for k, v in out.items() if v.get("band_diverges_where_the_border_agrees")]
    print(f"\n{len(bad)} of {len(out)} pairs diverge inside the band while agreeing on the border")
    (HERE / "band_profile.json").write_text(json.dumps(out, indent=1, default=str))
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    rc = self_test()
    print()
    report_pairs()
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
