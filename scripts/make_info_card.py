#!/usr/bin/env python3
"""
Generate a neofetch-style info card as an animated SVG (info-card.svg).
Fades in line-by-line using opacity keyframes and staggers (no transform collision).
Supports STATIC=1 for frozen frame rendering.
"""

import os
import sys
import html

DEFAULT_OUTPUT_PATH = "info-card.svg"

def generate_info_card(output_path: str = DEFAULT_OUTPUT_PATH):
    is_static = os.environ.get("STATIC", "").lower() in ("1", "true", "yes")

    width = 490
    height = 440

    lines_data = [
        {"type": "header", "user": "aakash", "host": "noir-system"},
        {"type": "divider"},
        {"key": "OS", "val": "Ubuntu Linux / x86_64", "val_color": "#e6edf3"},
        {"key": "Host", "val": "github.com/Aakashxnoir", "val_color": "#e6edf3"},
        {"key": "Role", "val": "Full-Stack Dev & AI Builder", "val_color": "#c9a84c"},
        {"key": "Now", "val": "Shipping productivity systems & AI tools", "val_color": "#e6edf3"},
        {"key": "Prev", "val": "Life Tracker · NBOS Skill Swap · College OS", "val_color": "#8b949e"},
        {"key": "Stack", "val": "TypeScript, Python, React, Java, Node", "val_color": "#7ee787"},
        {"key": "Focus", "val": "Clean architecture, darker aesthetics", "val_color": "#e6edf3"},
        {"key": "Highlights", "val": "10+ public repos · rapid shipping", "val_color": "#58a6ff"},
        {"key": "Noir Mode", "val": "True [active]", "val_color": "#c9a84c"},
        {"type": "spacer"},
        {"type": "palette"}
    ]

    css_rules = []
    if is_static:
        css_rules.append(".line { opacity: 1; }")
    else:
        css_rules.append("""
    @keyframes lineFadeIn {
      0% {
        opacity: 0;
      }
      100% {
        opacity: 1;
      }
    }
    .line {
      opacity: 0;
      animation: lineFadeIn 0.38s ease-out forwards;
    }
""")
        for idx in range(len(lines_data)):
            delay = round(0.12 + (idx * 0.08), 2)
            css_rules.append(f"    .l-{idx} {{ animation-delay: {delay}s; }}")

    css_block = "\n".join(css_rules)

    rendered_elements = []
    start_y = 65
    line_height = 24
    curr_y = start_y

    for idx, item in enumerate(lines_data):
        cls = "line" if is_static else f"line l-{idx}"
        itype = item.get("type", "kv")

        if itype == "header":
            u_esc = html.escape(item["user"])
            h_esc = html.escape(item["host"])
            rendered_elements.append(
                f'  <g class="{cls}" transform="translate(32, {curr_y})">\n'
                f'    <text font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="14" font-weight="bold">\n'
                f'      <tspan fill="#7ee787">{u_esc}</tspan>\n'
                f'      <tspan fill="#8b949e">@</tspan>\n'
                f'      <tspan fill="#58a6ff">{h_esc}</tspan>\n'
                f'    </text>\n'
                f'  </g>'
            )
            curr_y += 18
        elif itype == "divider":
            rendered_elements.append(
                f'  <g class="{cls}" transform="translate(32, {curr_y})">\n'
                f'    <text font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="13" fill="#30363d">---------------------------------------</text>\n'
                f'  </g>'
            )
            curr_y += 24
        elif itype == "spacer":
            curr_y += 12
        elif itype == "palette":
            colors_row1 = ["#0d1117", "#ff7b72", "#7ee787", "#d29922", "#58a6ff", "#bc8cff", "#39c5cf", "#e6edf3"]
            colors_row2 = ["#484f58", "#ffa198", "#56d364", "#e3b341", "#79c0ff", "#d2a8ff", "#56d4dd", "#ffffff"]
            
            blocks1 = []
            blocks2 = []
            for b_i, c in enumerate(colors_row1):
                blocks1.append(f'<rect x="{b_i * 26}" y="0" width="20" height="12" rx="3" fill="{c}" />')
            for b_i, c in enumerate(colors_row2):
                blocks2.append(f'<rect x="{b_i * 26}" y="16" width="20" height="12" rx="3" fill="{c}" />')

            rendered_elements.append(
                f'  <g class="{cls}" transform="translate(32, {curr_y})">\n'
                f'    {"".join(blocks1)}\n'
                f'    {"".join(blocks2)}\n'
                f'  </g>'
            )
            curr_y += 36
        else:
            key = html.escape(item["key"])
            val = html.escape(item["val"])
            val_col = item["val_color"]
            rendered_elements.append(
                f'  <g class="{cls}" transform="translate(32, {curr_y})">\n'
                f'    <text font-family="ui-monospace, SFMono-Regular, Menlo, monospace" font-size="13">\n'
                f'      <tspan fill="#c9a84c" font-weight="600">{key:<11}</tspan>\n'
                f'      <tspan fill="#484f58"> : </tspan>\n'
                f'      <tspan fill="{val_col}">{val}</tspan>\n'
                f'    </text>\n'
                f'  </g>'
            )
            curr_y += line_height

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <style>
{css_block}
    .header-bar-text {{
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 11px;
      fill: #8b949e;
    }}
  </style>

  <!-- Terminal Window Container -->
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="#0d1117" stroke="#30363d" stroke-width="1" />

  <!-- Window Chrome Dots -->
  <circle cx="22" cy="22" r="5" fill="#ff5f56" />
  <circle cx="38" cy="22" r="5" fill="#ffbd2e" />
  <circle cx="54" cy="22" r="5" fill="#27c93f" />
  <text x="74" y="26" class="header-bar-text">aakash@noir-system ~ neofetch</text>

  <!-- Info Lines -->
{chr(10).join(rendered_elements)}
</svg>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)

    print(f"Generated {output_path} ({width}x{height}) successfully!")

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT_PATH
    generate_info_card(out)

if __name__ == "__main__":
    main()
