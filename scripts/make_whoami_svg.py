#!/usr/bin/env python3
"""
Compose whoami.svg: the ASCII portrait and the 3D "AAKASH" wordmark side by side
in one terminal window, with the bio typed out under the wordmark.
The portrait prints row by row like `cat`, the wordmark wipes in and then rocks,
and a block cursor keeps blinking after the bio.
Reuses image_to_ascii() from make_ascii_svg.py and make_frames() from
make_wordmark_svg.py. Needs Pillow and NumPy (not the daily workflow).
"""
import argparse
import html
import os

import numpy as np
from PIL import Image

import make_ascii_svg as portrait
import make_wordmark_svg as wm

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

# Window
WIDTH = 860
TITLEBAR_H = 36
PAD = 28
SPLIT_X = 380  # left pane (portrait) | right pane (wordmark)
TITLE = "aakash@github: ~ — whoami"
TAGLINE = "just building cool stuffs"

BG, BG2 = wm.BG, wm.BG2
FRAME, TITLE_TEXT, INK = wm.FRAME, wm.TITLE_TEXT, wm.INK
DIVIDER = "#21262d"
FONT = 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace'

# Portrait grid
P_COLS = 76
P_CHAR_W, P_ROW_H, P_FONT = 4.3, 7.6, 7.1

# Wordmark grid: tighter crop, deeper extrusion and brighter front faces than the
# standalone wordmark, so the letters read at half the size
wm.COLS = 80
wm.CELL_W, wm.CELL_H = 5.5, 11.6
wm.ROW_MARGIN = 1
wm.FIT = 0.92
wm.TRACKING = 0.10
wm.DEPTH_FRAC = 0.28
wm.TILT_DEG = 7.0
wm.AMBIENT = 0.40

# Timeline (seconds)
P_PRINT = 1.3
W_BEGIN, W_REVEAL = 0.3, 1.4
T_BEGIN, T_CHAR = 1.9, 0.055


def portrait_rows(path):
    """Crop the prepped photo to the subject, then map it to glyph rows."""
    img = Image.open(path).convert("L")
    ys, xs = np.nonzero(np.array(img) < 240)
    m = 8
    img = img.crop((max(0, xs.min() - m), max(0, ys.min() - m),
                    min(img.width, xs.max() + m), min(img.height, ys.max() + m)))
    rows = int(round(P_COLS * (P_CHAR_W / P_ROW_H) * img.height / img.width))
    return portrait.image_to_ascii(img, P_COLS, rows)


def chrome(height):
    p = [
        '<defs><linearGradient id="wbg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
        '</linearGradient></defs>\n',
        f'<rect width="{WIDTH}" height="{height}" rx="10" fill="url(#wbg)"/>\n',
        f'<rect x="0.5" y="0.5" width="{WIDTH-1}" height="{height-1}" rx="10" '
        f'fill="none" stroke="{FRAME}"/>\n',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{WIDTH}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>\n',
    ]
    for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        p.append(f'<circle cx="{20 + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dot}"/>\n')
    p.append(f'<text x="{WIDTH/2:.0f}" y="{TITLEBAR_H/2 + 4:.0f}" fill="{TITLE_TEXT}" '
             f'font-size="12" text-anchor="middle">{html.escape(TITLE)}</text>\n')
    p.append(f'<line x1="{SPLIT_X}" y1="{TITLEBAR_H}" x2="{SPLIT_X}" y2="{height}" stroke="{DIVIDER}"/>\n')
    return p


def portrait_layer(rows, left, top, static):
    """All rows in one <text>; a clip grows one row at a time, like `cat` printing."""
    n = len(rows)
    w, h = P_COLS * P_CHAR_W, n * P_ROW_H
    spans = "".join(
        f'<tspan x="{left}" y="{top + i*P_ROW_H + P_FONT - 0.5:.1f}" textLength="{w:.1f}">'
        f'{html.escape(r).replace(" ", "&#160;")}</tspan>'
        for i, r in enumerate(rows)
    )
    text = (f'<text font-size="{P_FONT}" fill="{INK}" '
            f'clip-path="url(#pclip)">{spans}</text>\n')
    if static:
        clip = f'<rect x="{left}" y="{top}" width="{w:.1f}" height="{h:.1f}"/>'
    else:
        vals = ";".join(f"{i*P_ROW_H:.1f}" for i in range(n + 1))
        clip = (f'<rect x="{left}" y="{top}" width="{w:.1f}" height="0">'
                f'<animate attributeName="height" calcMode="discrete" values="{vals}" '
                f'dur="{P_PRINT}s" fill="freeze"/></rect>')
    return [f'<clipPath id="pclip">{clip}</clipPath>\n', text]


def wordmark_layer(frames, dur, left, top, static):
    art_w, art_h = wm.COLS * wm.CELL_W, wm.ROWS * wm.CELL_H
    if static:
        return [wm.frame_group(frames[0], left, top)]
    end = W_BEGIN + W_REVEAL
    return [
        f'<clipPath id="wipe"><rect x="{left}" y="{top}" height="{art_h:.1f}" width="0">'
        f'<animate attributeName="width" from="0" to="{art_w:.0f}" begin="{W_BEGIN}s" '
        f'dur="{W_REVEAL}s" fill="freeze"/></rect></clipPath>\n',
        f'<g clip-path="url(#wipe)">{wm.frame_group(frames[0], left, top)}'
        f'<set attributeName="opacity" to="0" begin="{end:.2f}s"/></g>\n',
        *wm.rock_frames([wm.frame_group(r, left, top, ' opacity="0"') for r in frames], dur, end),
    ]


def tagline_layer(left, baseline, static):
    """`$ just building cool stuffs` typed a character at a time, then a blinking block."""
    fs, cw = 12, 7.22  # ~0.6em advance for common monospace fonts
    prompt_w = 2 * cw
    text_w = len(TAGLINE) * cw
    p = [f'<text x="{left}" y="{baseline}" font-size="{fs}" fill="{TITLE_TEXT}">$</text>\n']
    x0 = left + prompt_w
    if static:
        p.append(f'<text x="{x0:.1f}" y="{baseline}" font-size="{fs}" fill="{INK}" '
                 f'textLength="{text_w:.1f}">{html.escape(TAGLINE)}</text>\n')
        p.append(f'<rect x="{x0 + text_w + 2:.1f}" y="{baseline - 10}" width="7" height="13" fill="{INK}"/>\n')
        return p
    n = len(TAGLINE)
    type_dur = n * T_CHAR
    widths = ";".join(f"{i*cw:.1f}" for i in range(n + 1))
    xs = ";".join(f"{x0 + i*cw + 2:.1f}" for i in range(n + 1))
    p += [
        f'<clipPath id="tclip"><rect x="{x0:.1f}" y="{baseline - 14}" height="20" width="0">'
        f'<animate attributeName="width" calcMode="discrete" values="{widths}" '
        f'begin="{T_BEGIN}s" dur="{type_dur:.2f}s" fill="freeze"/></rect></clipPath>\n',
        f'<text x="{x0:.1f}" y="{baseline}" font-size="{fs}" fill="{INK}" textLength="{text_w:.1f}" '
        f'clip-path="url(#tclip)">{html.escape(TAGLINE)}</text>\n',
        f'<rect x="{x0 + 2:.1f}" y="{baseline - 10}" width="7" height="13" fill="{INK}">'
        f'<animate attributeName="x" calcMode="discrete" values="{xs}" '
        f'begin="{T_BEGIN}s" dur="{type_dur:.2f}s" fill="freeze"/>'
        f'<animate attributeName="opacity" calcMode="discrete" values="1;0" '
        f'dur="1.1s" begin="{T_BEGIN + type_dur:.2f}s" repeatCount="indefinite"/></rect>\n',
    ]
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--photo", default=os.path.join(ROOT, "source-prepped.png"))
    ap.add_argument("--out", default=os.path.join(ROOT, "whoami.svg"))
    ap.add_argument("--static", action="store_true", help="final frame only, no animation")
    a = ap.parse_args()

    rows = portrait_rows(a.photo)
    frames, dur = wm.make_frames("rock")

    p_w, p_h = P_COLS * P_CHAR_W, len(rows) * P_ROW_H
    height = int(round(TITLEBAR_H + PAD + p_h + PAD))
    p_left = round((SPLIT_X - p_w) / 2, 1)

    art_w, art_h = wm.COLS * wm.CELL_W, wm.ROWS * wm.CELL_H
    tag_gap, tag_h = 26, 12
    block_h = art_h + tag_gap + tag_h
    w_left = round(SPLIT_X + (WIDTH - SPLIT_X - art_w) / 2, 1)
    w_top = round(TITLEBAR_H + (height - TITLEBAR_H - block_h) / 2, 1)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" font-family=\'{FONT}\'>\n',
        *chrome(height),
        *portrait_layer(rows, p_left, TITLEBAR_H + PAD, a.static),
        *wordmark_layer(frames, dur, w_left, w_top, a.static),
        *tagline_layer(w_left + 6, round(w_top + art_h + tag_gap + tag_h - 2, 1), a.static),
        "</svg>\n",
    ]
    out = "".join(svg)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(out)
    print(f"wrote {a.out} ({WIDTH}x{height}) {len(out)/1024:.1f} KB, "
          f"portrait {P_COLS}x{len(rows)}, wordmark {wm.COLS}x{wm.ROWS} x{len(frames)} frames")


if __name__ == "__main__":
    main()
