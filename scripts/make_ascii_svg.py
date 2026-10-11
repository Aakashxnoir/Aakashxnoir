#!/usr/bin/env python3
"""
Convert preprocessed photo (source-prepped.png) to a self-typing animated monochrome ASCII SVG.
Uses SMIL animations for row-by-row horizontal wipe clipping with a riding block cursor.
Writes avi-ascii.svg (and aakash-ascii.svg).
Supports STATIC=1 for frozen frame preview.
"""

import os
import sys
import html
from PIL import Image
import numpy as np

DEFAULT_INPUT = "source-prepped.png"
DEFAULT_OUTPUT = "avi-ascii.svg"
ALT_OUTPUT = "aakash-ascii.svg"

# Density ramp: bright (sparse/spaces) -> dark (dense)
RAMP = " .`:-=+*cs#%@"

def generate_ascii_svg(input_path: str = DEFAULT_INPUT, output_path: str = DEFAULT_OUTPUT):
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found. Run prep_photo.py first.")
        sys.exit(1)

    img = Image.open(input_path).convert("L")
    is_static = os.environ.get("STATIC", "").lower() in ("1", "true", "yes")

    # Dimensions to align with info-card.svg
    svg_width = 370
    svg_height = 440

    # Typography & aspect ratio metrics
    char_w = 4.3
    row_height = 7.6
    font_size = 7.1
    char_aspect = char_w / row_height # ~0.5658

    # Grid columns target ~76 to fill card width with balanced padding
    grid_cols = 76
    img_aspect = img.width / max(1, img.height)
    # Proportional rows to preserve exact aspect ratio without stretching
    grid_rows = int(round(grid_cols * char_aspect / img_aspect))
    grid_rows = max(36, min(48, grid_rows))

    resized = img.resize((grid_cols, grid_rows), Image.Resampling.LANCZOS)
    arr = np.array(resized)

    # Convert pixels to ASCII glyphs
    ascii_rows = []
    ramp_len = len(RAMP)
    for r in range(grid_rows):
        row_str = []
        for c in range(grid_cols):
            val = arr[r, c]
            idx = int((255.0 - float(val)) / 255.0 * (ramp_len - 1))
            idx = max(0, min(ramp_len - 1, idx))
            row_str.append(RAMP[idx])
        ascii_rows.append("".join(row_str))

    content_width = round(grid_cols * char_w, 1)
    content_x = round((svg_width - content_width) / 2.0, 1)

    total_content_height = grid_rows * row_height
    # Vertically center text area between header (y=42) and bottom (y=430)
    start_y = round(42 + (390 - total_content_height) / 2.0, 1)

    # Animation timing
    total_time = 2.4
    row_duration = 0.07

    defs_clips = []
    text_elements = []
    cursor_elements = []

    for i, line in enumerate(ascii_rows):
        row_top = start_y + (i * row_height)
        baseline_y = row_top + font_size - 0.5
        escaped_line = html.escape(line).replace(" ", "&#160;")

        t_start = round((i / max(1, grid_rows - 1)) * (total_time - row_duration), 3)
        t_end = round(t_start + row_duration, 3)

        clip_id = f"rclip-{i}"

        if is_static:
            defs_clips.append(
                f'    <clipPath id="{clip_id}">\n'
                f'      <rect x="{content_x}" y="{row_top:.1f}" width="{content_width}" height="{row_height:.1f}" />\n'
                f'    </clipPath>'
            )
        else:
            defs_clips.append(
                f'    <clipPath id="{clip_id}">\n'
                f'      <rect x="{content_x}" y="{row_top:.1f}" width="0" height="{row_height:.1f}">\n'
                f'        <animate attributeName="width" from="0" to="{content_width}" begin="{t_start}s" dur="{row_duration}s" fill="freeze" />\n'
                f'      </rect>\n'
                f'    </clipPath>'
            )

        text_elements.append(
            f'    <text x="{content_x}" y="{baseline_y:.1f}" clip-path="url(#{clip_id})">{escaped_line}</text>'
        )

        if not is_static:
            if i == grid_rows - 1:
                cursor_elements.append(
                    f'    <rect x="{content_x}" y="{row_top:.1f}" width="4" height="{row_height:.1f}" fill="#58a6ff" opacity="0">\n'
                    f'      <animate attributeName="x" from="{content_x}" to="{content_x + content_width:.1f}" begin="{t_start}s" dur="{row_duration}s" fill="freeze" />\n'
                    f'      <set attributeName="opacity" to="1" begin="{t_start}s" />\n'
                    f'      <animate attributeName="opacity" values="1;0;1;0;1;1" dur="2s" begin="{t_end}s" fill="freeze" />\n'
                    f'    </rect>'
                )
            else:
                cursor_elements.append(
                    f'    <rect x="{content_x}" y="{row_top:.1f}" width="4" height="{row_height:.1f}" fill="#58a6ff" opacity="0">\n'
                    f'      <animate attributeName="x" from="{content_x}" to="{content_x + content_width:.1f}" begin="{t_start}s" dur="{row_duration}s" fill="freeze" />\n'
                    f'      <set attributeName="opacity" to="1" begin="{t_start}s" />\n'
                    f'      <set attributeName="opacity" to="0" begin="{t_end}s" />\n'
                    f'    </rect>'
                )

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}">
  <style>
    .window-header {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 11px;
      fill: #8b949e;
    }}
    .ascii-text text {{
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
      font-size: {font_size}px;
      letter-spacing: 0px;
      fill: #c9d1d9;
      white-space: pre;
    }}
  </style>

  <defs>
{chr(10).join(defs_clips)}
  </defs>

  <!-- Terminal Window Background -->
  <rect x="0.5" y="0.5" width="{svg_width - 1}" height="{svg_height - 1}" rx="8" fill="#0d1117" stroke="#30363d" stroke-width="1" />

  <!-- Terminal Header Bar -->
  <circle cx="22" cy="22" r="5" fill="#ff5f56" />
  <circle cx="38" cy="22" r="5" fill="#ffbd2e" />
  <circle cx="54" cy="22" r="5" fill="#27c93f" />
  <text x="74" y="26" class="window-header">aakash@noir-system ~ cat avatar.ascii</text>

  <!-- ASCII Portrait -->
  <g class="ascii-text">
{chr(10).join(text_elements)}
  </g>

  <!-- Typing Cursors -->
{chr(10).join(cursor_elements)}
</svg>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Generated {output_path} ({svg_width}x{svg_height}) successfully!")

    if output_path != ALT_OUTPUT:
        with open(ALT_OUTPUT, "w", encoding="utf-8") as f:
            f.write(svg_content)
        print(f"Also created copy {ALT_OUTPUT}")

def main():
    inp = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT
    out = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    generate_ascii_svg(inp, out)

if __name__ == "__main__":
    main()
