#!/usr/bin/env python3
"""Generate N one-of-one posters and a browsable gallery page for them.

Usage:
    python examples/contact_sheet.py "album" -n 12 -o sheet/
    python examples/contact_sheet.py "album" -n 12 --style constellation

Seeds are "<seed> #1" .. "<seed> #N", so a base phrase gives you a
numbered edition of N distinct posters. The output folder contains the
SVGs plus index.html - open it in any browser to see the whole edition.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import hapax  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="numbered edition + browsable index.html")
    ap.add_argument("seed", help="base phrase; '#k' is appended per poster")
    ap.add_argument("-n", "--count", type=int, default=9)
    ap.add_argument("-o", "--out", default="edition")
    ap.add_argument("--style", default="auto", choices=["auto"] + hapax.STYLE_NAMES)
    ap.add_argument("--palette", default="auto",
                    help="auto or: " + ", ".join(hapax.PALETTE_NAMES))
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    cards = []
    for i in range(1, args.count + 1):
        seed = f"{args.seed} #{i}"
        svg = hapax.build_poster(seed, style=args.style, palette=args.palette)
        fname = f"hapax-{hapax.hash8(seed)}.svg"
        with open(os.path.join(args.out, fname), "w", encoding="utf-8") as out:
            out.write(svg)
        style = args.style if args.style != "auto" else _pick(seed, "choose-style",
                                                              hapax.STYLE_NAMES)
        palette = args.palette if args.palette != "auto" else _pick(seed, "choose-palette",
                                                                    hapax.PALETTE_NAMES)
        cards.append((fname, seed, f"{style} / {palette}"))
        print(f"{args.out}/{fname}  <- {seed!r}")

    _write_index(args.out, cards, args.seed)
    print(f"edition of {args.count} -> {args.out}/index.html")


def _pick(seed, domain, names):
    return hapax.pick(hapax.rng_for(seed, domain), names)


def _write_index(folder, cards, base_seed):
    items = []
    for fname, seed, bits in cards:
        items.append(
            f'<figure><img src="{fname}" loading="lazy">'
            f'<figcaption>{hapax.esc(seed)}<span>{bits} · {hapax.hash8(seed)}</span></figcaption></figure>')
    html = f"""<!doctype html><meta charset="utf-8">
<title>hapax edition - {hapax.esc(base_seed)}</title>
<style>
  body{{background:#111;color:#eee;font:16px/1.5 ui-monospace,Menlo,monospace;
       margin:2rem auto;max-width:1200px;padding:0 1rem}}
  h1{{font-weight:600;font-size:1.1rem}} h1 span{{opacity:.5}}
  main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1.4rem}}
  figure{{margin:0;background:#1a1a1a;padding:.6rem;border-radius:8px}}
  img{{width:100%;display:block;border-radius:4px}}
  figcaption{{margin-top:.5rem;font-size:.75rem;opacity:.9}}
  figcaption span{{display:block;opacity:.55}}
</style>
<h1>hapax edition <span>"{hapax.esc(base_seed)}" — {len(cards)} one-of-one posters</span></h1>
<main>{''.join(items)}</main>"""
    with open(os.path.join(folder, "index.html"), "w", encoding="utf-8") as out:
        out.write(html)


if __name__ == "__main__":
    main()
