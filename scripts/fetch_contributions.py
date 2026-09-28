#!/usr/bin/env python3
"""
Fetch public GitHub contribution calendar data without tokens or auth.
Parses the contribution graph HTML fragment and computes streaks and statistics.
Outputs data to data/contributions.json.
"""

import os
import sys
import json
import re
from datetime import datetime, date, timezone
import requests
from bs4 import BeautifulSoup

DEFAULT_USERNAME = "Aakashxnoir"

def fetch_contributions(username: str):
    url = f"https://github.com/users/{username}/contributions"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    return resp.text

def parse_contributions(html_content: str):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Extract total contributions in the last year
    total_contributions = 0
    header = soup.find(id="js-contribution-activity-description")
    if not header:
        header = soup.find("h2", class_=lambda c: c and "contribution" in c.lower())
    
    if header:
        m = re.search(r"([\d,]+)\s+contributions", header.get_text())
        if m:
            total_contributions = int(m.group(1).replace(",", ""))
            
    days = []
    
    # Cells can be <td class="ContributionCalendar-day" ...> or have data-date attribute
    day_elements = soup.find_all(lambda tag: tag.name in ["td", "button"] and tag.has_attr("data-date"))
    
    for el in day_elements:
        d_str = el.get("data-date")
        level_str = el.get("data-level", "0")
        try:
            level = int(level_str)
        except ValueError:
            level = 0
            
        # Count extraction: can be in text, aria-label, tooltip, or inside a tool-tip element
        count = 0
        
        # Check tooltip or aria-label
        # E.g. "No contributions on Sunday, September 28, 2025." or "3 contributions on Friday, January 2, 2026."
        text_to_check = el.get("aria-label", "")
        if not text_to_check:
            # Check associated tool-tip
            tid = el.get("id")
            if tid:
                tooltip = soup.find("tool-tip", attrs={"for": tid})
                if tooltip:
                    text_to_check = tooltip.get_text()
        if not text_to_check:
            text_to_check = el.get_text()
            
        m = re.search(r"(\d+)\s+contribution", text_to_check)
        if m:
            count = int(m.group(1))
        elif "No contribution" in text_to_check or "no contribution" in text_to_check:
            count = 0
        elif level > 0 and count == 0:
            # Fallback estimation if text format changed but level exists
            count = level
            
        days.append({
            "date": d_str,
            "count": count,
            "level": level
        })
        
    # Sort days by date
    days.sort(key=lambda x: x["date"])
    
    # If total_contributions wasn't parsed from header, sum the days
    if total_contributions == 0 and days:
        total_contributions = sum(d["count"] for d in days)
        
    # Calculate streaks and stats
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    best_day = {"date": None, "count": 0}
    monthly_totals = {}
    
    today_str = date.today().isoformat()
    
    # Iterate through days
    for d in days:
        cnt = d["count"]
        d_date = d["date"]
        
        # Monthly totals
        month_key = d_date[:7]
        monthly_totals[month_key] = monthly_totals.get(month_key, 0) + cnt
        
        # Best day
        if cnt > best_day["count"]:
            best_day = {"date": d_date, "count": cnt}
            
        # Longest streak calculation
        if cnt > 0:
            temp_streak += 1
            if temp_streak > longest_streak:
                longest_streak = temp_streak
        else:
            temp_streak = 0
            
    # Current streak calculation (walking backwards from today/last day)
    curr_s = 0
    # Find last day with data up to today
    valid_days = [d for d in days if d["date"] <= today_str]
    for d in reversed(valid_days):
        if d["count"] > 0:
            curr_s += 1
        else:
            # If today has 0, streak might still be active if yesterday had >0
            if d["date"] == today_str and curr_s == 0:
                continue
            break
    current_streak = curr_s
    
    return {
        "username": DEFAULT_USERNAME,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_contributions": total_contributions,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "best_day": best_day,
        "monthly_totals": monthly_totals,
        "days": days
    }

def main():
    username = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("GITHUB_USERNAME", DEFAULT_USERNAME)
    os.makedirs("data", exist_ok=True)
    
    print(f"Fetching contributions for @{username}...")
    html = fetch_contributions(username)
    data = parse_contributions(html)
    data["username"] = username
    
    output_path = os.path.join("data", "contributions.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    print(f"Saved {len(data['days'])} days to {output_path}")
    print(f"Total: {data['total_contributions']} | Current Streak: {data['current_streak']} | Longest Streak: {data['longest_streak']}")

if __name__ == "__main__":
    main()
