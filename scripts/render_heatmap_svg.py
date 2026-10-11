#!/usr/bin/env python3
"""
Render contribution calendar data to an animated SVG (contrib-heatmap.svg).
Uses a diagonal cascading reveal animation with CSS keyframes, Less->More legend,
and activity statistics.
"""

import os
import sys
import json
from datetime import datetime, date, timedelta

DEFAULT_JSON_PATH = "data/contributions.json"
DEFAULT_OUTPUT_PATH = "contrib-heatmap.svg"

# Palette: level 0 to level 5 (level 5 is neon highlight)
PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def render_heatmap(json_path: str = DEFAULT_JSON_PATH, output_path: str = DEFAULT_OUTPUT_PATH):
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found. Run fetch_contributions.py first.")
        sys.exit(1)
        
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    username = data.get("username", "Aakashxnoir")
    total_contribs = data.get("total_contributions", 0)
    current_streak = data.get("current_streak", 0)
    longest_streak = data.get("longest_streak", 0)
    days_data = data.get("days", [])
    
    # Map dates to dict for quick lookup
    day_map = {d["date"]: d for d in days_data}
    
    if not days_data:
        print("No days found in contributions data.")
        return
        
    # Determine date range
    # The last day is typically today or the end of the 53rd week
    last_date_str = days_data[-1]["date"]
    last_date = datetime.strptime(last_date_str, "%Y-%m-%d").date()
    
    # Find the end of that week (Saturday)
    # Python weekday(): Monday is 0, Sunday is 6.
    # In GitHub calendar, Sunday is row 0, Saturday is row 6.
    # Sunday-based weekday: (date.weekday() + 1) % 7
    days_to_sat = (5 - last_date.weekday()) % 7
    calendar_end = last_date + timedelta(days=days_to_sat)
    # 53 weeks = 53 * 7 = 371 days
    calendar_start = calendar_end - timedelta(days=(53 * 7) - 1)
    
    # Build 53 columns x 7 rows
    grid = [] # list of 53 weeks, each week is list of 7 days
    curr = calendar_start
    month_positions = []
    prev_month = -1
    
    for w in range(53):
        week_days = []
        for r in range(7):
            d_str = curr.isoformat()
            info = day_map.get(d_str, {"count": 0, "level": 0, "date": d_str})
            
            # Map level to color
            lvl = info.get("level", 0)
            cnt = info.get("count", 0)
            
            # If level is 4 and count is very high, promote to level 5 (neon top end)
            if lvl >= 4 and cnt >= 10:
                color_idx = 5
            elif lvl < len(PALETTE):
                color_idx = lvl
            else:
                color_idx = len(PALETTE) - 1
                
            color = PALETTE[color_idx]
            week_days.append({
                "date": d_str,
                "count": cnt,
                "color": color,
                "level": lvl,
                "week": w,
                "weekday": r
            })
            
            # Track month labels on week change when day is in first week of month
            if r == 0:
                m_num = curr.month
                if m_num != prev_month:
                    month_positions.append((w, MONTH_NAMES[m_num - 1]))
                    prev_month = m_num
                    
            curr += timedelta(days=1)
        grid.append(week_days)
        
    is_static = os.environ.get("STATIC", "").lower() in ("1", "true", "yes")
    
    # SVG Dimensions
    width = 860
    height = 210
    cell_size = 11
    cell_gap = 3
    stride = cell_size + cell_gap # 14
    grid_x = 68
    grid_y = 62
    
    # CSS generation
    css_rules = []
    if is_static:
        css_rules.append(".cell { opacity: 1; }")
    else:
        css_rules.append("""
    @keyframes reveal {
      0% {
        opacity: 0;
        transform: translateY(-5px) scale(0.85);
      }
      100% {
        opacity: 1;
        transform: translateY(0) scale(1);
      }
    }
    .cell {
      opacity: 0;
      animation: reveal 0.28s cubic-bezier(0.16, 1, 0.3, 1) forwards;
      transform-box: fill-box;
      transform-origin: center;
    }
    .cell:hover {
      stroke: #58a6ff;
      stroke-width: 1.5px;
      cursor: pointer;
    }
""")
        # Generate diagonal delay classes: diag = week + weekday (0 .. 52+6 = 58)
        for d in range(59):
            delay = round(d * 0.022, 3)
            css_rules.append(f"    .d-{d} {{ animation-delay: {delay}s; }}")
            
    css_block = "\n".join(css_rules)
    
    # Render Month labels
    month_svg = []
    # Avoid overlapping labels if months are too close (at least 3 weeks apart)
    last_mw = -10
    for mw, mname in month_positions:
        if mw - last_mw >= 3 and mw < 51:
            mx = grid_x + (mw * stride)
            month_svg.append(f'    <text x="{mx}" y="{grid_y - 10}" fill="#7d8590" font-size="10" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">{mname}</text>')
            last_mw = mw
            
    # Weekday labels
    # Row 1 = Mon, Row 3 = Wed, Row 5 = Fri
    weekday_labels = [
        (1, "Mon"),
        (3, "Wed"),
        (5, "Fri")
    ]
    weekday_svg = []
    for r_idx, wname in weekday_labels:
        wy = grid_y + (r_idx * stride) + 9
        weekday_svg.append(f'    <text x="32" y="{wy}" fill="#7d8590" font-size="9" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">{wname}</text>')
        
    # Grid rects
    cells_svg = []
    for w_idx, week in enumerate(grid):
        for r_idx, day in enumerate(week):
            cx = grid_x + (w_idx * stride)
            cy = grid_y + (r_idx * stride)
            diag = w_idx + r_idx
            cls = "cell" if is_static else f"cell d-{diag}"
            cnt = day["count"]
            d_str = day["date"]
            c_text = "No contributions" if cnt == 0 else f"{cnt} contribution{'s' if cnt != 1 else ''}"
            
            cells_svg.append(
                f'    <rect class="{cls}" x="{cx}" y="{cy}" width="{cell_size}" height="{cell_size}" rx="2" fill="{day["color"]}">'
                f'<title>{d_str}: {c_text}</title></rect>'
            )
            
    # Legend
    legend_x = 705
    legend_y = 186
    legend_svg = [
        f'    <text x="{legend_x - 30}" y="{legend_y + 8}" fill="#7d8590" font-size="10" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">Less</text>'
    ]
    for idx, color in enumerate(PALETTE):
        lx = legend_x + (idx * 13)
        legend_svg.append(f'    <rect x="{lx}" y="{legend_y}" width="10" height="10" rx="2" fill="{color}" />')
    legend_svg.append(
        f'    <text x="{legend_x + (len(PALETTE) * 13) + 6}" y="{legend_y + 8}" fill="#7d8590" font-size="10" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">More</text>'
    )
    
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <style>
{css_block}
    .header-text {{
      font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
      font-size: 12px;
      fill: #8b949e;
    }}
    .stat-bold {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-weight: 600;
      font-size: 12px;
      fill: #e6edf3;
    }}
    .stat-muted {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      font-size: 11px;
      fill: #7d8590;
    }}
  </style>

  <!-- Container Box -->
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="#0d1117" stroke="#30363d" stroke-width="1" />

  <!-- Terminal Top Bar -->
  <circle cx="22" cy="22" r="5" fill="#ff5f56" />
  <circle cx="38" cy="22" r="5" fill="#ffbd2e" />
  <circle cx="54" cy="22" r="5" fill="#27c93f" />
  <text x="74" y="26" class="header-text">github.com/{username} ~ contribution_matrix.sh</text>

  <!-- Month Labels -->
{chr(10).join(month_svg)}

  <!-- Weekday Labels -->
{chr(10).join(weekday_svg)}

  <!-- Grid Cells -->
{chr(10).join(cells_svg)}

  <!-- Footer Stats -->
  <g transform="translate(32, 194)">
    <text x="0" y="0" class="stat-bold">{total_contribs:,} contributions in the last year</text>
    <text x="235" y="0" class="stat-muted">•  Current streak: {current_streak}d  •  Longest: {longest_streak}d</text>
  </g>

  <!-- Legend -->
{chr(10).join(legend_svg)}
</svg>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
        
    print(f"Generated {output_path} ({width}x{height}) successfully!")

def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_JSON_PATH
    output_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT_PATH
    render_heatmap(json_path, output_path)

if __name__ == "__main__":
    main()
