#!/usr/bin/env python3
"""
TokenLens — AI Engineering Intelligence Platform
cli.py: Command-line entry point.

Usage:
  python3 cli.py dashboard        # scan + open browser dashboard
  python3 cli.py scan             # scan and show summary
  python3 cli.py today            # today's spend
  python3 cli.py week             # last 7 days
  python3 cli.py projects         # per-project efficiency table
  python3 cli.py recs             # print recommendations
  python3 cli.py roi              # print ROI estimate
"""

import argparse
import sys
from datetime import datetime, timezone

import analyzer
import scanner
import server as srv


RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"
RED   = "\033[31m"
GRN   = "\033[32m"
YLW   = "\033[33m"
BLU   = "\033[34m"
MAG   = "\033[35m"
CYN   = "\033[36m"
WHT   = "\033[37m"

GRADE_COLOR = {"A": GRN, "B": BLU, "C": YLW, "D": YLW, "F": RED}


def _grade(g: str) -> str:
    return f"{GRADE_COLOR.get(g, WHT)}{BOLD}{g}{RESET}"


def _bar(value: float, max_val: float, width: int = 20, color: str = BLU) -> str:
    filled = int((value / max_val) * width) if max_val > 0 else 0
    filled = min(filled, width)
    return color + "█" * filled + DIM + "░" * (width - filled) + RESET


def _human_tokens(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def cmd_scan(args):
    print(f"\n{BLU}⚡ TokenLens — scanning usage logs…{RESET}\n")
    result = scanner.scan(verbose=args.verbose)
    print(f"  Files scanned  : {BOLD}{result['files_scanned']}{RESET}")
    print(f"  Files skipped  : {DIM}{result['files_skipped']}{RESET}")
    print(f"  Messages added : {BOLD}{result['messages_added']}{RESET}")
    print(f"  Sessions seen  : {BOLD}{result['sessions_seen']}{RESET}")
    print()
    cmd_summary(args)


def cmd_summary(args):
    s = analyzer.get_summary()
    grade = s["efficiency_grade"]
    score = s["efficiency_score"]
    roi   = s["roi"]

    print(f"\n{BOLD}{'─'*52}{RESET}")
    print(f"  {BOLD}{MAG}TokenLens  AI Engineering Intelligence{RESET}")
    print(f"{'─'*52}")
    print(f"  Total spend       {BOLD}${s['total_cost']:.4f}{RESET}")
    print(f"  Total tokens      {BOLD}{_human_tokens(s['total_tokens'])}{RESET}")
    print(f"  Sessions          {BOLD}{s['total_sessions']}{RESET}")
    print(f"  Cache efficiency  {BOLD}{s['cache_efficiency']*100:.1f}%{RESET}  "
          f"{_bar(s['cache_efficiency'], 1.0, 16, GRN)}")
    print(f"  Efficiency score  {BOLD}{score:.0f}/100{RESET}  {_grade(grade)}")
    print(f"  Dev time saved    {BOLD}{roi['dev_hours_saved']}h{RESET}  "
          f"≈ ${roi['dev_cost_saved']:.2f} value")
    print(f"  ROI multiplier    {BOLD}{roi['roi_multiplier']}×{RESET}")
    print(f"{'─'*52}\n")


def cmd_today(args):
    daily = analyzer.get_daily_chart(days=1)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today = next((d for d in daily if d["day"] == today_str), None)
    if not today:
        print(f"\n  {DIM}No usage recorded today yet.{RESET}\n")
        return
    print(f"\n  {BOLD}Today ({today_str}){RESET}")
    print(f"  Cost    ${today['cost']:.4f}")
    print(f"  Input   {_human_tokens(today['input_t'])}")
    print(f"  Output  {_human_tokens(today['output_t'])}")
    print(f"  Cache↑  {_human_tokens(today['cache_write_t'])}")
    print(f"  Cache↓  {_human_tokens(today['cache_read_t'])}\n")


def cmd_week(args):
    daily = analyzer.get_daily_chart(days=7)
    if not daily:
        print(f"\n  {DIM}No usage in the last 7 days.{RESET}\n")
        return
    max_cost = max(d["cost"] for d in daily) or 1
    print(f"\n  {BOLD}Last 7 days{RESET}\n")
    total = 0.0
    for d in daily:
        bar = _bar(d["cost"], max_cost, 20)
        print(f"  {d['day']}  {bar}  ${d['cost']:.4f}")
        total += d["cost"]
    print(f"\n  {BOLD}Total: ${total:.4f}{RESET}\n")


def cmd_projects(args):
    projects = analyzer.get_projects()
    if not projects:
        print(f"\n  {DIM}No projects found. Run scan first.{RESET}\n")
        return
    print(f"\n  {BOLD}{'Project':<28} {'Cost':>8}  {'Cache%':>7}  {'Score':>6}  Grade{RESET}")
    print(f"  {'─'*62}")
    for p in projects:
        ce = f"{p['cache_efficiency']*100:.0f}%"
        print(
            f"  {p['project']:<28} "
            f"${p['total_cost']:>7.4f}  "
            f"{ce:>7}  "
            f"{p['efficiency_score']:>5.0f}  "
            f"  {_grade(p['efficiency_grade'])}"
        )
    print()


def cmd_recs(args):
    recs = analyzer.get_recommendations()
    if not recs:
        print(f"\n  {GRN}✓ No significant optimisation opportunities found.{RESET}\n")
        return
    impact_color = {"high": RED, "medium": YLW, "low": DIM}
    print(f"\n  {BOLD}Recommendations{RESET}\n")
    for i, r in enumerate(recs, 1):
        ic = impact_color.get(r["impact"], WHT)
        print(f"  {BOLD}{i}. {r['title']}{RESET}  {ic}[{r['impact'].upper()}]{RESET}  "
              f"save ≈${r['savings_usd']:.2f}")
        print(f"     {DIM}{r['description'][:120]}…{RESET}")
        print(f"     {CYN}→ {r['action']}{RESET}\n")


def cmd_roi(args):
    roi = analyzer.get_roi()
    print(f"\n  {BOLD}ROI Estimate{RESET}")
    print(f"  AI cost paid        ${roi['ai_cost']:.4f}")
    print(f"  Dev hours saved     {roi['dev_hours_saved']}h")
    print(f"  Developer value     ${roi['dev_cost_saved']:.2f}  "
          f"(@ ${roi['dev_hourly_rate']}/hr)")
    print(f"  {BOLD}ROI multiplier      {roi['roi_multiplier']}×{RESET}\n")


def cmd_dashboard(args):
    host = os.environ.get("HOST", "localhost")
    port = int(os.environ.get("PORT", 7777))
    srv.run(host=host, port=port, open_browser=not args.no_browser)


import os


def main():
    parser = argparse.ArgumentParser(
        prog="tokenlens",
        description="TokenLens — AI Engineering Intelligence Platform",
    )
    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="Scan usage logs and show summary")
    p_scan.add_argument("--verbose", "-v", action="store_true")
    p_scan.set_defaults(func=cmd_scan)

    p_sum = sub.add_parser("summary", help="Show overall summary")
    p_sum.set_defaults(func=cmd_summary)

    p_today = sub.add_parser("today", help="Show today's usage")
    p_today.set_defaults(func=cmd_today)

    p_week = sub.add_parser("week", help="Show last 7 days")
    p_week.set_defaults(func=cmd_week)

    p_proj = sub.add_parser("projects", help="Per-project efficiency table")
    p_proj.set_defaults(func=cmd_projects)

    p_recs = sub.add_parser("recs", help="Show optimisation recommendations")
    p_recs.set_defaults(func=cmd_recs)

    p_roi = sub.add_parser("roi", help="Show developer ROI estimate")
    p_roi.set_defaults(func=cmd_roi)

    p_dash = sub.add_parser("dashboard", help="Open browser dashboard (default)")
    p_dash.add_argument("--no-browser", action="store_true", help="Don't auto-open browser")
    p_dash.set_defaults(func=cmd_dashboard)

    args = parser.parse_args()

    if not args.command:
        # Default: dashboard
        args.no_browser = False
        cmd_dashboard(args)
        return

    args.func(args)


if __name__ == "__main__":
    main()
