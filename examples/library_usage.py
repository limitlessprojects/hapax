#!/usr/bin/env python3
"""Use hapax as a library instead of a CLI - build custom pipelines.

Usage:
    python examples/library_usage.py

This one walks through the whole API surface in ~40 lines:
resolve what the seed chooses, render, then post-process the SVG string.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import hapax  # noqa: E402

SEED = "the library example"


def main():
    # 1. what does this seed choose on its own?
    style = hapax.pick(hapax.rng_for(SEED, "choose-style"), hapax.STYLE_NAMES)
    palette = hapax.pick(hapax.rng_for(SEED, "choose-palette"), hapax.PALETTE_NAMES)
    print(f"seed {SEED!r} wants {style}/{palette} (fingerprint {hapax.hash8(SEED)})")

    # 2. render it - pure function of (seed, style, palette, size, grain, caption)
    svg = hapax.build_poster(SEED, size=(1200, 1500))
    assert svg == hapax.build_poster(SEED, size=(1200, 1500))  # deterministic, always

    # 3. the palette is data - inspect or reuse it
    pal = hapax.PALETTES[palette]
    print(f"palette {palette}: bg={pal['bg']} ink={pal['ink']} accents={len(pal['colors'])}")

    # 4. post-process the SVG string yourself (it is just text)
    #    e.g. drop your own caption line under the edition mark:
    svg = svg.replace("</svg>",
        '<text x="54" y="1448" font-family="monospace" '
        f'font-size="13" fill="{pal["ink"]}" opacity="0.45">'
        f'made with hapax - MIT - {os.environ.get("USER", "someone")}</text></svg>')

    out = "custom-poster.svg"
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {out} ({len(svg):,} bytes)")

    # 5. need your own generator behavior? copy hapax.py and add a style:
    #    def style_tidechart(svg, R, pal, W, H): ...
    #    hapax.STYLES["tidechart"] = style_tidechart   # (edit the file to persist)
    print("styles registry:", ", ".join(hapax.STYLES))


if __name__ == "__main__":
    main()
