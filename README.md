# TokenLens — AI Engineering Intelligence Platform

> **Built by [Aditya Bikram Dash](https://github.com/abdash1994)**

[![License: MIT](https://img.shields.io/badge/License-MIT-6366F1.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Zero Dependencies](https://img.shields.io/badge/Dependencies-Zero-10B981)](https://github.com/abdash1994/tokenlens)
[![GitHub Pages](https://img.shields.io/badge/Pitch%20Deck-Live-8B5CF6)](https://abdash1994.github.io/tokenlens)

**Don't just track your AI spend — understand it, reduce it, and prove its value.**

TokenLens reads Claude Code's local session logs and turns raw token data into an **Efficiency Score**, **actionable recommendations with dollar savings**, and a **developer ROI calculator** — all with zero cloud dependencies and a single command.

---

## Live Demo

**[View the Pitch Deck →](https://abdash1994.github.io/tokenlens)**

---

## What Makes TokenLens Different

| | Other tools | **TokenLens** |
|---|---|---|
| Token counts & cost charts | ✅ | ✅ |
| **Efficiency Score (A–F)** | ❌ | ✅ |
| **Actionable recommendations** | ❌ | ✅ |
| **Dollar savings estimates** | ❌ | ✅ |
| **Cache efficiency analysis** | ❌ | ✅ |
| **Anomaly detection** | ❌ | ✅ |
| **Developer ROI calculator** | ❌ | ✅ |
| **Project benchmarking** | ❌ | ✅ |
| **Built-in pitch deck** | ❌ | ✅ |

---

## Quick Start

**Requirements:** Python 3.10+ · macOS / Linux / Windows · No pip installs needed

```bash
git clone https://github.com/abdash1994/tokenlens
cd tokenlens
python3 cli.py dashboard
```

Opens your browser at **http://localhost:7777** — dashboard + pitch deck ready.

> **Tip:** Run this from your system **Terminal app** (not from inside an IDE like Cursor or VS Code) so the server stays alive as long as you need it. Closing the terminal window stops the server.

---

## How It Works

Claude Code writes one JSONL file per session to `~/.claude/projects/`. TokenLens:

1. **Scans** those files incrementally (only new/changed files processed)
2. **Stores** parsed data in SQLite at `~/.tokenlens/tokenlens.db`
3. **Scores** each session and project with its Intelligence Engine
4. **Serves** a real-time dashboard at `localhost:7777`

**Your data never leaves your machine.** No cloud. No accounts. No telemetry.

---

## CLI Commands

```bash
python3 cli.py dashboard   # Full browser dashboard (default)
python3 cli.py scan        # Scan logs + print summary
python3 cli.py today       # Today's spend
python3 cli.py week        # Last 7 days
python3 cli.py projects    # Per-project efficiency table
python3 cli.py recs        # Optimisation recommendations
python3 cli.py roi         # Developer ROI estimate
```

---

## The Efficiency Score

Every project and session gets a composite **0–100 score** with an **A–F grade**:

| Signal | Weight | What it measures |
|---|---|---|
| Cache Hit Rate | 40% | % of context served from cache vs. paid fresh |
| Output Density | 30% | Output tokens per context token — value per dollar |
| Cache Warm Rate | 20% | Are you writing to cache at all? |
| Context Efficiency | 10% | Penalises pure fresh-input patterns |

A project moving from **D → B** typically cuts spend by **30–50%** with no change to output quality.

---

## Recommendations Engine

Detects five waste patterns and generates specific fixes with **estimated dollar savings**:

- **Cache cold start** — Hit rate <25% → save 40–80% of input cost
- **Zero-cache projects** — No cache writes at all → save ~45%
- **Session anomalies** — Cost >3.5× project average → investigate loops/dumps
- **Low output density** — Output <5% of context → tighten prompt scoping
- **Rising cost trend** — 7-day spend >130% of prior week → set budget alerts

---

## Developer ROI

Converts AI spend into business language your CTO understands:

- **Dev hours saved** from AI-generated output (conservative 40% attribution)
- **Dollar value created** at configurable loaded developer rate ($125/hr default)
- **ROI multiplier** — how much value per dollar spent

---

## Architecture

```
tokenlens/
├── scanner.py          # Incremental JSONL → SQLite parser
├── analyzer.py         # Intelligence engine (scoring, recs, ROI, anomalies)
├── server.py           # HTTP server + REST API
├── cli.py              # CLI entry point
├── dashboard/
│   ├── index.html      # Live dashboard SPA
│   └── pitch.html      # Built-in pitch deck (live data)
└── docs/
    └── index.html      # Static pitch deck (GitHub Pages)
```

**Zero external dependencies** — Python standard library only (`sqlite3`, `http.server`, `json`, `pathlib`).

---

## API Pricing Reference

Costs calculated using Anthropic API pricing (May 2026):

| Model | Input | Output | Cache Write | Cache Read |
|---|---|---|---|---|
| claude-opus-* | $5.00/MTok | $25.00/MTok | $6.25/MTok | $0.50/MTok |
| claude-sonnet-* | $3.00/MTok | $15.00/MTok | $3.75/MTok | $0.30/MTok |
| claude-haiku-* | $1.00/MTok | $5.00/MTok | $1.25/MTok | $0.10/MTok |

---

## Attribution

This project was created by **Aditya Bikram Dash** ([@abdash1994](https://github.com/abdash1994)).

If you fork or build on this project, you must visibly credit the original author per the [LICENSE](LICENSE).

---

## Roadmap

- **Phase 1 (done):** Individual tool — dashboard, efficiency scoring, recommendations, ROI
- **Phase 2:** Team edition — central aggregation, org-level roll-up, budget alerts, Slack
- **Phase 3:** Enterprise governance — compliance reports, sensitive-data detection, CI/CD integration

---

*Built for engineers who want to stop guessing and start optimising.*
