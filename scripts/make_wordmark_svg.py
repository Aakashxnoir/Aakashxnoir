#!/usr/bin/env python3
"""
Render "AAKASH" as an EXTRUDED 3D wordmark rasterized to ASCII, and emit it as an
animated SVG (wordmark.svg) that rocks on its vertical axis (SMIL flipbook animation).
Modeled directly after AVIVASHISHTA29's 3D ASCII wordmark architecture.
"""
import argparse
import html
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT_FONTS = [
    "/usr/share/fonts/TTF/FiraSansCondensed-Bold.ttf",
    "/usr/share/fonts/TTF/FiraSans-Bold.ttf",
    "/usr/share/fonts/TTF/OpenSans-CondensedBold.ttf",
    "/usr/share/fonts/TTF/DejaVuSansCondensed-Bold.ttf",
]
FONT_PATH = os.environ.get("WORDMARK_FONT")
if not FONT_PATH or not os.path.exists(FONT_PATH):
    for f in DEFAULT_FONTS:
        if os.path.exists(f):
            FONT_PATH = f
            break

FONT_INDEX = int(os.environ.get("WORDMARK_FONT_INDEX", 0))
TEXT = os.environ.get("WORDMARK_TEXT", "AAKASH")

COLS = int(os.environ.get("WORDMARK_COLS", 84))
ROW_MARGIN = int(os.environ.get("WORDMARK_ROW_MARGIN", 8))
ROWS = 0  # Computed dynamically in fit()

CELL_W = float(os.environ.get("WORDMARK_CELL_W", 6.8))
CELL_H = float(os.environ.get("WORDMARK_CELL_H", 14.5))

MASK_H = 300
TRACKING = float(os.environ.get("WORDMARK_TRACKING", 0.30))
LINE_GAP = 1.20
DEPTH_FRAC = float(os.environ.get("WORDMARK_DEPTH", 0.18))
TILT_DEG = float(os.environ.get("WORDMARK_TILT", 3.5))

CAM_DIST = 6.2
FOCAL = 4.15
FIT = float(os.environ.get("WORDMARK_FIT", 0.82))

RAMP = " .`:-=+*csS#%@"

LIGHT = np.array([-0.15, -0.45, -1.00])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
AMBIENT = 0.25
FOG = 0.30
FOG_SPAN = 0.55

# Palette
BG = "#0d1117"
BG2 = "#111722"
FRAME = "#30363d"
TITLE_TEXT = "#7d8590"
INK = "#c9d1d9"

PAD = 18
TITLEBAR_H = 28


def build_shell():
    probe = TEXT.replace("\n", "")
    font_size = MASK_H
    for _ in range(40):
        try:
            font = ImageFont.truetype(FONT_PATH, font_size, index=FONT_INDEX)
        except Exception:
            font = ImageFont.load_default()
            break
        l, t, r, b = font.getbbox(probe)
        if b - t <= MASK_H:
            break
        font_size = int(font_size * 0.92)
    h = b - t
    track = int(round(TRACKING * font_size))
    lines = TEXT.split("\n")
    line_h = int(round(h * LINE_GAP))

    def line_w(s):
        return sum(font.getlength(c) for c in s) + track * (len(s) - 1)

    total_w = int(round(max(line_w(s) for s in lines))) + 8
    total_h = line_h * (len(lines) - 1) + h + 8
    img = Image.new("L", (total_w, total_h), 0)
    d = ImageDraw.Draw(img)
    for li, s in enumerate(lines):
        pen = 4.0 + (total_w - 8 - line_w(s)) / 2.0
        base = -t + 4 + li * line_h
        for ch in s:
            d.text((pen, base), ch, font=font, fill=255)
            pen += font.getlength(ch) + track

    mask = np.array(img) > 127
    xs_any = np.nonzero(mask.any(0))[0]
    ys_any = np.nonzero(mask.any(1))[0]
    mask = mask[ys_any[0]:ys_any[-1] + 1, xs_any[0]:xs_any[-1] + 1]

    H, W = mask.shape
    depth = max(3, int(round(H * DEPTH_FRAC)))
    cy, cx = np.nonzero(mask)

    pts, nrm = [], []
    front = np.stack([cx, cy, np.full_like(cx, -0.6, dtype=float)], 1)
    pts.append(front)
    nrm.append(np.tile([0.0, 0.0, -1.0], (len(front), 1)))
    back = np.stack([cx, cy, np.full_like(cx, depth)], 1).astype(float)
    pts.append(back)
    nrm.append(np.tile([0.0, 0.0, 1.0], (len(back), 1)))

    pad = np.pad(mask, 1)
    edge = mask & (~pad[1:-1, 2:] | ~pad[1:-1, :-2] | ~pad[2:, 1:-1] | ~pad[:-2, 1:-1])
    ey, ex = np.nonzero(edge)
    nx = (~pad[1:-1, 2:])[ey, ex].astype(float) - (~pad[1:-1, :-2])[ey, ex].astype(float)
    ny = (~pad[2:, 1:-1])[ey, ex].astype(float) - (~pad[:-2, 1:-1])[ey, ex].astype(float)
    ln = np.sqrt(nx * nx + ny * ny)
    ln[ln == 0] = 1.0
    nx, ny = nx / ln, ny / ln
    zsteps = np.linspace(0, depth, max(3, depth // 2))
    for z in zsteps:
        pts.append(np.stack([ex, ey, np.full_like(ex, z, dtype=float)], 1))
        nrm.append(np.stack([nx, ny, np.zeros_like(nx)], 1))

    P = np.concatenate(pts).astype(np.float32)
    N = np.concatenate(nrm).astype(np.float32)

    P[:, 0] -= W / 2.0
    P[:, 1] -= H / 2.0
    P[:, 2] -= depth / 2.0
    P /= float(W)
    return P, N


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float32)


def project(P, N, yaw):
    M = rot_x(math.radians(TILT_DEG)) @ rot_y(yaw)
    p = P @ M.T
    n = N @ M.T
    vis = n[:, 2] < 0.0
    p, n = p[vis], n[vis]

    z = p[:, 2] + CAM_DIST
    f = FOCAL / z
    lam = n @ LIGHT
    inten = AMBIENT + (1 - AMBIENT) * np.clip(lam, 0, 1)
    t = np.clip((z - CAM_DIST) / FOG_SPAN, -1.0, 1.0)
    inten *= 1.0 - FOG * (t + 1.0) / 2.0
    idx = np.clip((inten * (len(RAMP) - 1)).round().astype(int), 1, len(RAMP) - 1)
    return p[:, 0] * f, p[:, 1] * f, z, idx


def fit(projected):
    global ROWS
    xs = np.concatenate([q[0] for q in projected])
    ys = np.concatenate([q[1] for q in projected])
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    ar = CELL_W / CELL_H
    scale = FIT * (COLS - 1) / (x1 - x0)
    ROWS = int(math.ceil((y1 - y0) * ar * scale)) + 1 + 2 * ROW_MARGIN
    cx = (COLS - 1) / 2.0 - (x0 + x1) / 2.0 * scale
    cy = (ROWS - 1) / 2.0 - (y0 + y1) / 2.0 * scale * ar
    return scale, cx, cy


def rasterize(q, scale, cx, cy):
    x, y, z, idx = q
    col = np.round(cx + x * scale).astype(int)
    row = np.round(cy + y * scale * (CELL_W / CELL_H)).astype(int)
    ok = (col >= 0) & (col < COLS) & (row >= 0) & (row < ROWS)
    col, row, z, idx = col[ok], row[ok], z[ok], idx[ok]

    grid = np.zeros((ROWS, COLS), np.int8)
    order = np.argsort(-z)
    grid[row[order], col[order]] = idx[order]
    return ["".join(RAMP[i] for i in r) for r in grid]


def emit(frames, mode, out, dur, reveal):
    art_w = COLS * CELL_W
    art_h = ROWS * CELL_H
    canvas_w = art_w + PAD * 2
    canvas_h = TITLEBAR_H + art_h + PAD
    art_top = TITLEBAR_H + PAD * 0.35
    fs = CELL_H * 0.92
    n = len(frames)

    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_w:.0f}" height="{canvas_h:.0f}" '
        f'viewBox="0 0 {canvas_w:.0f} {canvas_h:.0f}" font-family="ui-monospace, SFMono-Regular, '
        f'Menlo, Consolas, monospace">\n',
        '<defs><linearGradient id="wbg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
        '</linearGradient></defs>\n',
        f'<rect width="{canvas_w:.0f}" height="{canvas_h:.0f}" rx="12" fill="url(#wbg)"/>\n',
        f'<rect x="0.5" y="0.5" width="{canvas_w-1:.0f}" height="{canvas_h-1:.0f}" rx="12" '
        f'fill="none" stroke="{FRAME}" stroke-width="1"/>\n',
        f'<line x1="0" y1="{TITLEBAR_H}" x2="{canvas_w:.0f}" y2="{TITLEBAR_H}" stroke="{FRAME}"/>\n',
    ]
    for i, dot in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        p.append(f'<circle cx="{PAD + i*16}" cy="{TITLEBAR_H/2}" r="5" fill="{dot}"/>\n')
    p.append(f'<text x="{canvas_w/2:.0f}" y="{TITLEBAR_H/2 + 4:.0f}" fill="{TITLE_TEXT}" '
             f'font-size="12" text-anchor="middle">aakash@github: ~$ ./wordmark.sh --3d</text>\n')

    def frame_g(rows, extra=""):
        out_rows = []
        for ry, line in enumerate(rows):
            s = line.rstrip()
            if not s.strip():
                continue
            lead = len(s) - len(s.lstrip(" "))
            body = s[lead:]
            x = PAD + lead * CELL_W
            y = art_top + ry * CELL_H + CELL_H * 0.78
            out_rows.append(
                f'<text xml:space="preserve" x="{x:.1f}" y="{y:.1f}" font-size="{fs:.1f}" '
                f'textLength="{len(body)*CELL_W:.1f}" lengthAdjust="spacing">{html.escape(body)}</text>'
            )
        return f'<g fill="{INK}"{extra}>' + "".join(out_rows) + "</g>\n"

    if mode == "static":
        p.append(frame_g(frames[0]))
        p.append("</svg>\n")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write("".join(p))
        print("wrote", out)
        return

    # Intro wipe animation
    p.append(f'<clipPath id="wipe"><rect x="{PAD}" y="{art_top:.1f}" height="{art_h:.1f}" width="0">'
             f'<animate attributeName="width" from="0" to="{art_w:.0f}" begin="0s" '
             f'dur="{reveal:.2f}s" fill="freeze"/></rect></clipPath>\n')
    p.append(f'<g clip-path="url(#wipe)">{frame_g(frames[0])}'
             f'<set attributeName="opacity" to="0" begin="{reveal:.2f}s"/></g>\n')
    p.append(f'<rect x="{PAD}" y="{art_top+2:.1f}" width="{CELL_W*1.6:.1f}" height="{art_h-4:.1f}" '
             f'fill="{INK}" opacity="0.16">\n'
             f'<animate attributeName="x" from="{PAD}" to="{PAD+art_w:.0f}" begin="0s" '
             f'dur="{reveal:.2f}s" fill="freeze"/>\n'
             f'<set attributeName="opacity" to="0" begin="{reveal:.2f}s"/></rect>\n')

    if mode == "once":
        step = dur / n
        for i, rows in enumerate(frames):
            begin = reveal + i * step
            sets = f'<set attributeName="opacity" to="1" begin="{begin:.3f}s"/>'
            if i != n - 1:
                sets += f'<set attributeName="opacity" to="0" begin="{begin+step:.3f}s"/>'
            p.append(frame_g(rows, ' opacity="0"').replace("</g>\n", sets + "</g>\n"))
    else:  # rock mode
        for i, rows in enumerate(frames):
            if i == 0:
                vals, kt = "1;0", f"0;{1/n:.5f}"
            else:
                vals, kt = "0;1;0", f"0;{i/n:.5f};{(i+1)/n:.5f}"
            anim = (f'<animate attributeName="opacity" calcMode="discrete" values="{vals}" '
                    f'keyTimes="{kt}" dur="{dur:.2f}s" begin="{reveal:.2f}s" '
                    f'repeatCount="indefinite"/>')
            p.append(frame_g(rows, ' opacity="0"').replace("</g>\n", anim + "</g>\n"))

    p.append("</svg>\n")
    svg = "".join(p)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {out} ({canvas_w:.0f}x{canvas_h:.0f}) {len(svg)/1024:.1f} KB {n} frames")


def main():
    global TEXT
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["spin", "once", "rock", "static"], default="rock")
    ap.add_argument("--text", default=None)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "wordmark.svg"))
    ap.add_argument("--frames", type=int, default=None)
    ap.add_argument("--dur", type=float, default=None)
    ap.add_argument("--reveal", type=float, default=1.6)
    ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()

    if a.text:
        TEXT = a.text

    P, N = build_shell()
    rest = math.radians(-13)
    if a.mode == "spin":
        nf = a.frames or 36
        yaws = [rest + 2 * math.pi * i / nf for i in range(nf)]
        dur = a.dur or 7.0
    elif a.mode == "once":
        nf = a.frames or 32
        yaws = [rest + 2 * math.pi * i / nf for i in range(nf)] + [rest]
        dur = a.dur or 3.6
    else:  # rock
        nf = a.frames or 20
        amp = math.radians(11)
        yaws = [rest + amp * math.sin(2 * math.pi * i / nf) for i in range(nf)]
        dur = a.dur or 5.0

    proj = [project(P, N, y) for y in yaws]
    scale, cx, cy = fit(proj)
    frames = [rasterize(q, scale, cx, cy) for q in proj]

    if a.preview:
        for row in frames[0]:
            print(row.rstrip())
        return

    emit(frames, a.mode, a.out, dur, a.reveal)


if __name__ == "__main__":
    main()
