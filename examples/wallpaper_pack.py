#!/usr/bin/env python3
"""Turn one phrase into a full wallpaper pack for all your screens.

Usage:
    python examples/wallpaper_pack.py "quantum" -o walls/
    python examples/wallpaper_pack.py "quantum" --style orbits --palette tide

Writes one SVG per screen profile. Note: each size is its own one-of-one
composition of the seed (the layout engine works in canvas coordinates),
so your desktop and phone get sibling posters, not crops of one another.

SVG is resolution-independent: open it in a browser and screenshot, or
rasterize properly with any of:
    resvg --width 1920 walls/hapax-*.svg out.png
    inkscape walls/hapax-*.svg -o out.png -w 1920
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import hapax  # noqa: E402

PROFILES = [
    ("desktop", 1920, 1080),
    ("desktop-4k", 3840, 2160),
    ("laptop", 2880, 1800),
    ("ultrawide", 3440, 1440),
    ("phone", 1170, 2532),
    ("tablet", 2048, 2732),
]


def main():
    ap = argparse.ArgumentParser(description="one phrase -> a pack of screen-size posters")
    ap.add_argument("seed")
    ap.add_argument("-o", "--out", default="wallpapers")
    ap.add_argument("--style", default="auto", choices=["auto"] + hapax.STYLE_NAMES)
    ap.add_argument("--palette", default="auto",
                    help="auto or: " + ", ".join(hapax.PALETTE_NAMES))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    h8 = hapax.hash8(args.seed)
    for name, w, h in PROFILES:
        svg = hapax.build_poster(args.seed, style=args.style,
                                 palette=args.palette, size=(w, h))
        path = os.path.join(args.out, f"{name}-{w}x{h}.svg")
        with open(path, "w", encoding="utf-8") as out:
            out.write(svg)
        print(f"{path}")
    print(f"pack for seed {args.seed!r} ({h8}) -> {args.out}/")
    print("tip: rasterize with resvg/inkscape, or open in a browser and screenshot")


if __name__ == "__main__":
    main()
