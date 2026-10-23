#!/usr/bin/env python3
"""Batch-render a poster for every phrase in a text file.

Usage:
    python examples/batch_from_file.py phrases.txt -o my-posters/
    python examples/batch_from_file.py phrases.txt -o my-posters/ --style mosaic

Input: one phrase per line. Blank lines and lines starting with '#' are
skipped. Every phrase becomes its own one-of-one SVG in the output folder.

Requires nothing but the hapax.py that ships in this repo
(it imports hapax from the repo root, wherever you run it from).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import hapax  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="render one poster per line of a text file")
    ap.add_argument("phrases", help="text file, one phrase per line")
    ap.add_argument("-o", "--out", default="posters", help="output folder")
    ap.add_argument("--style", default="auto", choices=["auto"] + hapax.STYLE_NAMES)
    ap.add_argument("--palette", default="auto",
                    help="auto or: " + ", ".join(hapax.PALETTE_NAMES))
    ap.add_argument("--size", default="1200x1500")
    args = ap.parse_args()

    w, h = (int(v) for v in args.size.lower().split("x"))
    with open(args.phrases, encoding="utf-8") as fh:
        phrases = [ln.strip() for ln in fh
                   if ln.strip() and not ln.strip().startswith("#")]
    if not phrases:
        sys.exit("no phrases found in " + args.phrases)

    os.makedirs(args.out, exist_ok=True)
    for phrase in phrases:
        svg = hapax.build_poster(phrase, style=args.style, palette=args.palette,
                                 size=(w, h))
        path = os.path.join(args.out, f"hapax-{hapax.hash8(phrase)}.svg")
        with open(path, "w", encoding="utf-8") as out:
            out.write(svg)
        print(f"{path}  <- {phrase!r}")
    print(f"{len(phrases)} posters -> {args.out}/")


if __name__ == "__main__":
    main()
