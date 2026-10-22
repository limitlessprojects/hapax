#!/usr/bin/env python3
"""
hapax - every seed is a one-of-one poster.

Deterministic generative SVG posters from any phrase.
Pure Python standard library, zero dependencies.

    python hapax.py "a quiet machine"
    python hapax.py "a quiet machine" --style orbits --palette kiln
    python hapax.py "a quiet machine" --sheet 12

Same seed in, same poster out - byte for byte, forever.
(hapax legomenon: n. a word that occurs only once.)
"""

from __future__ import annotations

import argparse
import hashlib
import math
import os
import random
import re
import sys

__version__ = "1.0.0"

# ---------------------------------------------------------------------------
# seeding - domain-separated SHA-256 streams
# ---------------------------------------------------------------------------

def _digest(seed: str, domain: str) -> int:
    h = hashlib.sha256(seed.encode("utf-8") + b"\x1f" + domain.encode("utf-8")).digest()
    return int.from_bytes(h, "big")


def rng_for(seed: str, domain: str) -> random.Random:
    """A deterministic RNG stream. Different domains never correlate."""
    return random.Random(_digest(seed, domain))


def hash8(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]


def pick(rng: random.Random, seq):
    return seq[rng.randrange(len(seq))]


# ---------------------------------------------------------------------------
# palettes
# ---------------------------------------------------------------------------

PALETTES = {
    "argon": dict(
        bg="#141020", ink="#ece7f6",
        colors=["#8b5cf6", "#c4b5fd", "#5eead4", "#f0abfc", "#fda4af", "#a5b4fc"]),
    "kiln": dict(
        bg="#1c1410", ink="#f3e9dc",
        colors=["#e2725b", "#e8a87c", "#d9bf77", "#8a9a5b", "#c98d6b", "#f2d0a4"]),
    "tide": dict(
        bg="#0b1720", ink="#e4f0f2",
        colors=["#2ec4b6", "#4cc9f0", "#7fd8be", "#1b9aaa", "#b8e1e6", "#f4f1bb"]),
    "ember": dict(
        bg="#180d0a", ink="#f5e6da",
        colors=["#ff6b35", "#f7c59f", "#efefd0", "#d64550", "#ff9f1c", "#b8336a"]),
    "orchard": dict(
        bg="#101a12", ink="#eef3e2",
        colors=["#84cc16", "#bef264", "#fbbf24", "#34d399", "#a3e635", "#fcd34d"]),
    "monsoon": dict(
        bg="#0f1419", ink="#dce7ee",
        colors=["#6ea8c9", "#9db4c0", "#c9a86a", "#5c7d99", "#b7c9d3", "#e0a458"]),
    "candy": dict(
        bg="#fdf3f0", ink="#3a2430",
        colors=["#ff5d8f", "#ffb3c6", "#8bd3dd", "#f9f871", "#bb6bd9", "#ff9770"]),
    "noir": dict(
        bg="#0d0d0d", ink="#e8e6e1",
        colors=["#9a8c98", "#c9ada7", "#f2e9e4", "#4a4e69", "#b56576", "#6d597a"]),
    "paper": dict(
        bg="#f4efe6", ink="#2f2a26",
        colors=["#c14953", "#5b8266", "#37556c", "#d9a05b", "#8a6552", "#7d8ca3"]),
    "signal": dict(
        bg="#0a0a14", ink="#eef2ff",
        colors=["#ff3b30", "#00e5ff", "#ffe600", "#00d26a", "#ff2ec4", "#7c4dff"]),
    "moss": dict(
        bg="#131511", ink="#e9ece2",
        colors=["#6b8f71", "#a4c3a2", "#cfe1b9", "#ccd5ae", "#8a9a5b", "#d6d69b"]),
    "pastelex": dict(
        bg="#f2f0f7", ink="#33304a",
        colors=["#a594f9", "#f0c1e1", "#9ed2c6", "#f5d689", "#8ea7e9", "#e8a0bf"]),
}

# ---------------------------------------------------------------------------
# tiny SVG builder
# ---------------------------------------------------------------------------

def f(n) -> str:
    """Compact number formatting."""
    if isinstance(n, float):
        s = f"{n:.2f}".rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    return str(n)


def esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


class SVG:
    def __init__(self, w: float, h: float):
        self.w, self.h, self.p = w, h, []

    def rect(self, x, y, w, h, fill, opacity=None, rx=None, stroke=None, sw=None):
        a = []
        if opacity is not None: a.append(f'opacity="{f(opacity)}"')
        if rx: a.append(f'rx="{f(rx)}"')
        if stroke: a.append(f'stroke="{stroke}" stroke-width="{f(sw or 1)}"')
        extra = (" " + " ".join(a)) if a else ""
        self.p.append(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" fill="{fill}"{extra}/>')

    def circle(self, cx, cy, r, fill=None, stroke=None, sw=None, opacity=None, dash=None):
        a = []
        if fill is None and stroke is None: fill = "#000"
        a.append(f'fill="{fill}"' if fill else 'fill="none"')
        if stroke: a.append(f'stroke="{stroke}" stroke-width="{f(sw or 1)}"')
        if dash: a.append(f'stroke-dasharray="{dash}"')
        if opacity is not None: a.append(f'opacity="{f(opacity)}"')
        self.p.append(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" {" ".join(a)}/>')

    def line(self, x1, y1, x2, y2, stroke, sw=1.0, opacity=None, dash=None, cap=None):
        a = [f'stroke="{stroke}"', f'stroke-width="{f(sw)}"', 'fill="none"']
        if dash: a.append(f'stroke-dasharray="{dash}"')
        if cap: a.append(f'stroke-linecap="{cap}"')
        if opacity is not None: a.append(f'opacity="{f(opacity)}"')
        self.p.append(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" {" ".join(a)}/>')

    def path(self, d, fill="none", stroke=None, sw=None, opacity=None,
             dash=None, cap=None, join=None):
        a = [f'fill="{fill}"']
        if stroke:
            a.append(f'stroke="{stroke}"')
            a.append(f'stroke-width="{f(sw or 1)}"')
        if dash: a.append(f'stroke-dasharray="{dash}"')
        if cap: a.append(f'stroke-linecap="{cap}"')
        if join: a.append(f'stroke-linejoin="{join}"')
        if opacity is not None: a.append(f'opacity="{f(opacity)}"')
        self.p.append(f'<path d="{d}" {" ".join(a)}/>')

    def polyline(self, pts, stroke, sw=1.0, opacity=None, dash=None, cap="round"):
        d = "M" + " L".join(f"{round(x)} {round(y)}" for x, y in pts)
        self.path(d, stroke=stroke, sw=sw, opacity=opacity, dash=dash, cap=cap, join="round")

    def text(self, x, y, s, fill, size, opacity=None, family="monospace", anchor=None):
        a = f' text-anchor="{anchor}"' if anchor else ""
        op = f' opacity="{f(opacity)}"' if opacity is not None else ""
        self.p.append(
            f'<text x="{f(x)}" y="{f(y)}" font-family="{family}" '
            f'font-size="{f(size)}" fill="{fill}"{op}{a}>{esc(s)}</text>')

    def render(self, caption=None) -> str:
        head = (f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" '
                f'viewBox="0 0 {f(self.w)} {f(self.h)}" '
                f'width="{f(self.w)}" height="{f(self.h)}">\n')
        body = "\n".join(self.p)
        cap = f"\n{caption}\n" if caption else ""
        return head + body + cap + "</svg>\n"


# ---------------------------------------------------------------------------
# value-noise field (for flowfield)
# ---------------------------------------------------------------------------

def noise_field(R: random.Random, gw=7, gh=7):
    """Seeded value noise on a lattice, bilinear + smoothstep.
    Returns at(x, y) for x, y in [0, 1] -> value in [0, 1]."""
    lat = [[R.random() for _ in range(gw + 1)] for _ in range(gh + 1)]

    def smooth(t):
        return t * t * (3 - 2 * t)

    def at(x, y):
        x = min(max(x, 0.0), 0.9999)
        y = min(max(y, 0.0), 0.9999)
        fx, fy = x * gw, y * gh
        x0, y0 = int(fx), int(fy)
        tx, ty = smooth(fx - x0), smooth(fy - y0)
        v00, v10 = lat[y0][x0], lat[y0][x0 + 1]
        v01, v11 = lat[y0 + 1][x0], lat[y0 + 1][x0 + 1]
        top = v00 + (v10 - v00) * tx
        bot = v01 + (v11 - v01) * tx
        return top + (bot - top) * ty

    return at


# ---------------------------------------------------------------------------
# shared texture
# ---------------------------------------------------------------------------

def add_grain(svg: SVG, R: random.Random, ink: str, n=700):
    for _ in range(n):
        svg.circle(R.random() * svg.w, R.random() * svg.h,
                   0.4 + R.random() * 0.8, fill=ink,
                   opacity=0.02 + R.random() * 0.05)


def add_caption(svg: SVG, seed: str, style: str, pal: str, ink: str):
    h8 = hash8(seed)
    label = f'hapax - "{seed}" - {style}/{pal} - {h8}'
    size = max(11.0, svg.w * 0.011)
    svg.text(svg.w * 0.045, svg.h * 0.968, label, ink, size, opacity=0.55)


# ---------------------------------------------------------------------------
# style: flowfield
# ---------------------------------------------------------------------------

def style_flowfield(svg: SVG, R: random.Random, pal, W, H):
    field = noise_field(R, R.randint(5, 8), R.randint(5, 8))
    turn = R.uniform(1.2, 2.2) * math.pi
    # background wash
    for _ in range(R.randint(2, 4)):
        svg.circle(R.random() * W, R.random() * H, W * R.uniform(0.18, 0.45),
                   fill=pick(R, pal["colors"]), opacity=R.uniform(0.05, 0.12))
    n_lines = R.randint(430, 680)
    cols = pal["colors"]
    for i in range(n_lines):
        x = W * (0.03 + R.random() * 0.94)
        y = H * (0.03 + R.random() * 0.94)
        steps = R.randint(30, 62)
        step = W / R.uniform(110, 160)
        pts = [(x, y)]
        for _ in range(steps):
            a = field(x / W, y / H) * turn
            x += math.cos(a) * step
            y += math.sin(a) * step
            if not (-0.05 * W < x < 1.05 * W and -0.05 * H < y < 1.05 * H):
                break
            pts.append((x, y))
        if len(pts) < 8:
            continue
        c = cols[int((y / H) * len(cols)) % len(cols)]
        sw = R.uniform(0.5, 1.8)
        op = R.uniform(0.3, 0.75)
        svg.polyline(pts, c, sw=sw, opacity=op)
    # accents
    for _ in range(R.randint(3, 7)):
        x = W * (0.1 + R.random() * 0.8)
        y = H * (0.1 + R.random() * 0.8)
        pts = [(x, y)]
        a = R.random() * math.tau
        for _ in range(R.randint(30, 60)):
            a = field(x / W, y / H) * turn
            x += math.cos(a) * W / 130
            y += math.sin(a) * W / 130
            pts.append((x, y))
        svg.polyline(pts, pal["ink"], sw=R.uniform(2.2, 3.6), opacity=R.uniform(0.5, 0.85))


# ---------------------------------------------------------------------------
# style: orbits
# ---------------------------------------------------------------------------

def style_orbits(svg: SVG, R: random.Random, pal, W, H):
    cx = W * R.uniform(0.38, 0.62)
    cy = H * R.uniform(0.42, 0.58)
    rmax = min(W, H) * R.uniform(0.40, 0.46)
    n_rings = R.randint(20, 32)
    cols = pal["colors"]
    radii = []
    r = rmax * R.uniform(0.08, 0.16)
    for _ in range(n_rings):
        radii.append(r)
        r += rmax / n_rings * R.uniform(0.6, 1.6)
    for i, r in enumerate(radii):
        use_col = R.random() < 0.38
        col = pick(R, cols) if use_col else pal["ink"]
        op = R.uniform(0.22, 0.55) if not use_col else R.uniform(0.5, 0.85)
        sw = R.uniform(0.7, 1.7)
        if R.random() < 0.14:
            sw = R.uniform(2.4, 4.8)
            op = min(1.0, op + 0.25)
        dash = f"{f(R.uniform(2, 10))} {f(R.uniform(3, 12))}" if R.random() < 0.3 else None
        svg.circle(cx, cy, r, stroke=col, sw=sw, opacity=op, dash=dash)
    # arc highlights with round caps
    for _ in range(R.randint(4, 8)):
        r = pick(R, radii)
        a0 = R.random() * math.tau
        span = R.uniform(0.3, 1.6)
        a1 = a0 + span
        x0, y0 = cx + math.cos(a0) * r, cy + math.sin(a0) * r
        x1, y1 = cx + math.cos(a1) * r, cy + math.sin(a1) * r
        large = 1 if span > math.pi else 0
        d = (f"M {f(x0)} {f(y0)} A {f(r)} {f(r)} 0 {large} 1 {f(x1)} {f(y1)}")
        svg.path(d, stroke=pick(R, cols), sw=R.uniform(2.5, 6.0),
                 opacity=R.uniform(0.7, 1.0), cap="round")
    # planets
    for _ in range(R.randint(5, 8)):
        r = pick(R, radii)
        a = R.random() * math.tau
        px, py = cx + math.cos(a) * r, cy + math.sin(a) * r
        pr = R.uniform(3.0, 8.5)
        col = pick(R, cols)
        svg.circle(px, py, pr * 3.2, fill=col, opacity=0.16)
        svg.circle(px, py, pr, fill=col, opacity=0.95)
        if R.random() < 0.5:
            svg.circle(px, py, pr + R.uniform(3, 8), stroke=pal["ink"],
                       sw=0.7, opacity=0.6)
    svg.circle(cx, cy, 2.5, fill=pal["ink"], opacity=0.9)


# ---------------------------------------------------------------------------
# style: mosaic
# ---------------------------------------------------------------------------

def style_mosaic(svg: SVG, R: random.Random, pal, W, H):
    m = W * R.uniform(0.05, 0.08)
    gutter = W * R.uniform(0.004, 0.009)
    cols = pal["colors"]
    bg = pal["bg"]
    cells = []

    def split(x, y, w, h, depth):
        area_frac = (w * h) / (W * H)
        if depth >= 2 and (R.random() < 0.28 or area_frac < R.uniform(0.004, 0.02)
                           or depth > 7 or w < W * 0.06 or h < H * 0.05):
            cells.append((x, y, w, h))
            return
        vertical = w > h if abs(w - h) > W * 0.02 else R.random() < 0.5
        t = R.uniform(0.33, 0.67)
        if vertical:
            split(x, y, w * t - gutter / 2, h, depth + 1)
            split(x + w * t + gutter / 2, y, w * (1 - t) - gutter / 2, h, depth + 1)
        else:
            split(x, y, w, h * t - gutter / 2, depth + 1)
            split(x, y + h * t + gutter / 2, w, h * (1 - t) - gutter / 2, depth + 1)

    split(m, m, W - 2 * m, H - 2 * m, 0)
    for (x, y, w, h) in cells:
        roll = R.random()
        if roll < 0.55:
            col = pick(R, cols)
            op = R.uniform(0.75, 1.0)
        elif roll < 0.8:
            col = pal["ink"]
            op = R.uniform(0.12, 0.3)
        else:
            col = bg
            op = 1.0
        svg.rect(x, y, w, h, col, opacity=op)
        # interrupts
        if w > W * 0.06 and h > H * 0.06 and R.random() < 0.3:
            cc = pick(R, cols) if col != bg else pal["ink"]
            if R.random() < 0.5:
                svg.circle(x + w / 2, y + h / 2, min(w, h) * R.uniform(0.18, 0.34),
                           fill=cc, opacity=R.uniform(0.7, 1.0))
            else:
                svg.circle(x + w / 2, y + h / 2, min(w, h) * R.uniform(0.2, 0.38),
                           stroke=cc, sw=R.uniform(2, 5), opacity=0.9)
    svg.rect(m, m, W - 2 * m, H - 2 * m, "none", stroke=pal["ink"], sw=1.6, opacity=0.65)


# ---------------------------------------------------------------------------
# style: ribbons
# ---------------------------------------------------------------------------

def _edge(R, x0, y0, x1, y1, drift, segs):
    pts = [(x0, y0)]
    for i in range(1, segs):
        t = i / segs
        pts.append((x0 + (x1 - x0) * t,
                    y0 + (y1 - y0) * t + (R.random() - 0.5) * drift))
    pts.append((x1, y1))
    return pts


def _smooth_path(pts):
    d = f"M {f(pts[0][0])} {f(pts[0][1])}"
    for i in range(1, len(pts)):
        x0, y0 = pts[i - 1]
        x1, y1 = pts[i]
        mx = (x0 + x1) / 2
        d += f" Q {f(x0)} {f(y0)} {f(mx)} {f((y0 + y1) / 2)}"
    x1, y1 = pts[-1]
    d += f" T {f(x1)} {f(y1)}"
    return d


def style_ribbons(svg: SVG, R: random.Random, pal, W, H):
    # sun disc
    svg.circle(W * R.uniform(0.3, 0.7), H * R.uniform(0.2, 0.38),
               W * R.uniform(0.12, 0.22), fill=pick(R, pal["colors"]),
               opacity=R.uniform(0.25, 0.5))
    cols = pal["colors"]
    order = list(range(len(cols)))
    R.shuffle(order)
    n_bands = R.randint(9, 14)
    top = H * R.uniform(0.16, 0.24)
    bot = H * R.uniform(0.82, 0.9)
    band_h = (bot - top) / n_bands
    segs = R.randint(4, 7)
    drift = H * R.uniform(0.03, 0.09)
    y = top
    for i in range(n_bands):
        col = cols[order[i % len(order)]]
        top_pts = _edge(R, -W * 0.02, y, W * 1.02, y + R.uniform(-drift, drift), drift, segs)
        thick = band_h * R.uniform(0.55, 1.05)
        bot_pts = [(px, py + thick) for (px, py) in top_pts]
        d = _smooth_path(top_pts) + " L " + " L".join(
            f"{f(px)} {f(py)}" for px, py in reversed(bot_pts)) + " Z"
        svg.path(d, fill=col, opacity=R.uniform(0.85, 1.0))
        if R.random() < 0.5:
            hl = [(px, py + thick * R.uniform(0.25, 0.6)) for (px, py) in top_pts]
            svg.polyline(hl, pal["ink"], sw=R.uniform(0.8, 1.8),
                         opacity=R.uniform(0.25, 0.6))
        y += band_h


# ---------------------------------------------------------------------------
# style: constellation
# ---------------------------------------------------------------------------

def style_constellation(svg: SVG, R: random.Random, pal, W, H):
    # faint dot grid
    step = W / R.uniform(28, 42)
    gx = step
    while gx < W:
        gy = step
        while gy < H:
            svg.circle(gx, gy, 0.8, fill=pal["ink"], opacity=0.07)
            gy += step
        gx += step
    m = W * 0.05
    nodes = [(m + R.random() * (W - 2 * m), m + R.random() * (H - 2 * m))
             for _ in range(R.randint(95, 150))]
    cols = pal["colors"]
    # proximity edges
    maxd = W * R.uniform(0.11, 0.16)
    for i, (x, y) in enumerate(nodes):
        near = []
        for j, (x2, y2) in enumerate(nodes):
            if i == j:
                continue
            d = math.hypot(x - x2, y - y2)
            if d < maxd:
                near.append((d, j))
        near.sort()
        for _, j in near[:R.randint(1, 2)]:
            if j > i:
                svg.line(x, y, *nodes[j], pal["ink"], sw=0.8, opacity=0.22)
    for (x, y) in nodes:
        svg.circle(x, y, R.uniform(1.0, 2.4), fill=pal["ink"], opacity=R.uniform(0.45, 0.95))
    # stars
    stars = [(m + R.random() * (W - 2 * m), m + R.random() * (H - 2 * m))
             for _ in range(R.randint(7, 11))]
    for (x, y) in stars:
        col = pick(R, cols)
        r = R.uniform(3.0, 6.5)
        svg.circle(x, y, r * 5.2, fill=col, opacity=0.09)
        svg.circle(x, y, r * 2.6, fill=col, opacity=0.2)
        svg.circle(x, y, r, fill=col, opacity=1.0)
        arm = r * R.uniform(2.4, 3.6)
        svg.line(x - arm, y, x + arm, y, col, sw=0.8, opacity=0.7)
        svg.line(x, y - arm, x, y + arm, col, sw=0.8, opacity=0.7)
    # dashed route through a subset of stars
    route = stars[:]
    R.shuffle(route)
    route = route[:max(4, len(route) * 2 // 3)]
    svg.polyline(route, pal["ink"], sw=1.0, opacity=0.4,
                 dash=f"{f(W * 0.008)} {f(W * 0.01)}")


# ---------------------------------------------------------------------------

STYLES = {
    "flowfield": style_flowfield,
    "orbits": style_orbits,
    "mosaic": style_mosaic,
    "ribbons": style_ribbons,
    "constellation": style_constellation,
}

STYLE_NAMES = list(STYLES)
PALETTE_NAMES = list(PALETTES)


def build_poster(seed: str, style="auto", palette="auto",
                 size=(1200, 1500), grain=True, caption=True) -> str:
    """Render one poster to an SVG string. Fully deterministic in (seed, style,
    palette, size, grain, caption)."""
    W, H = size
    if style == "auto":
        style = pick(rng_for(seed, "choose-style"), STYLE_NAMES)
    if style not in STYLES:
        raise ValueError(f"unknown style: {style} (known: {STYLE_NAMES})")
    if palette == "auto":
        palette = pick(rng_for(seed, "choose-palette"), PALETTE_NAMES)
    if palette not in PALETTES:
        raise ValueError(f"unknown palette: {palette} (known: {PALETTE_NAMES})")
    pal = PALETTES[palette]

    svg = SVG(W, H)
    svg.rect(0, 0, W, H, pal["bg"])
    R = rng_for(seed, f"style:{style}")
    STYLES[style](svg, R, pal, W, H)
    if grain:
        add_grain(svg, rng_for(seed, "grain"), pal["ink"])
    if caption:
        add_caption(svg, seed, style, palette, pal["ink"])
    # caption is drawn last so it sits on top - order is part of the contract
    return svg.render()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_size(s):
    m = re.match(r"^(\d+)[xX](\d+)$", s.strip())
    if not m:
        raise argparse.ArgumentTypeError(f"size must be WxH, got {s!r}")
    return int(m.group(1)), int(m.group(2))


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="hapax",
        description="Every seed is a one-of-one poster. Deterministic generative "
                    "SVG art from any phrase - zero dependencies.")
    ap.add_argument("seed", nargs="?",
                    help="any phrase; omit one to get a fresh random seed")
    ap.add_argument("-o", "--out", help="output path (default: hapax-<hash8>.svg)")
    ap.add_argument("--style", default="auto", choices=["auto"] + STYLE_NAMES)
    ap.add_argument("--palette", default="auto",
                    help="auto or one of: " + ", ".join(PALETTE_NAMES))
    ap.add_argument("--size", default="1200x1500", type=_parse_size,
                    help="WxH, default 1200x1500")
    ap.add_argument("--sheet", type=int, metavar="N",
                    help="render N posters seeded '<seed> #1..N' into a folder")
    ap.add_argument("--no-grain", action="store_true", help="skip film-grain texture")
    ap.add_argument("--no-caption", action="store_true", help="skip edition caption")
    ap.add_argument("--list", action="store_true", help="list styles and palettes")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    if args.list:
        print("styles:   " + ", ".join(STYLE_NAMES))
        print("palettes: " + ", ".join(PALETTE_NAMES))
        return 0

    seed = args.seed
    if seed is None:
        seed = f"untitled-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:6]}"
    if args.palette != "auto" and args.palette not in PALETTES:
        ap.error(f"unknown palette: {args.palette}")

    if args.sheet:
        n = max(1, args.sheet)
        folder = args.out or f"hapax-sheet-{hash8(seed)}"
        os.makedirs(folder, exist_ok=True)
        paths = []
        for i in range(1, n + 1):
            s = f"{seed} #{i}"
            svg = build_poster(s, size=args.size,
                               grain=not args.no_grain, caption=not args.no_caption)
            p = os.path.join(folder, f"hapax-{hash8(s)}.svg")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(svg)
            paths.append(p)
        if not args.quiet:
            print(f"wrote {n} posters -> {folder}/")
        return 0

    style = args.style
    if style == "auto":
        style = pick(rng_for(seed, "choose-style"), STYLE_NAMES)
    palette = args.palette
    if palette == "auto":
        palette = pick(rng_for(seed, "choose-palette"), PALETTE_NAMES)
    svg = build_poster(seed, style=style, palette=palette, size=args.size,
                       grain=not args.no_grain, caption=not args.no_caption)
    out = args.out or f"hapax-{hash8(seed)}.svg"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    if not args.quiet:
        print(f"{out}  [{style}/{palette}]  seed={seed!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
