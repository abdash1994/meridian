# TokenLens — Phase 2 Preview

> **This document is a public teaser.** Full Phase 2 specification, plugin implementation guide, and early access to the team edition are available to contributors and interested teams.
>
> **To get access:**
> 1. ⭐ [Star this repo](https://github.com/abdash1994/tokenlens) (signals interest)
> 2. [Open an issue](https://github.com/abdash1994/tokenlens/issues/new?title=Phase+2+interest&body=Tool+I+use:+%0ATeam+size:+%0AWhat+I+need:) with your tool stack and team size
> 3. Connect on [LinkedIn](https://linkedin.com/in/adityabikramdash) — DM "Phase 2"
>
> *Phase 2 ships when the market signals it's needed. Stars and issues are the signal.*

---

## Why Phase 2 Exists

Phase 1 of TokenLens proved the concept on Claude Code: **the intelligence layer on top of raw usage data is more valuable than the data itself.**

The problem: engineering teams don't use one AI tool. They use three, four, sometimes five — across different projects, different engineers, and different workflows.

**Phase 1 answers: "How efficiently am I using Claude Code?"**

**Phase 2 answers: "How efficiently is my entire engineering team using all AI tools — and what's the combined ROI?"**

That shift from individual to team, and from single-tool to multi-tool, is Phase 2.

---

## What Phase 2 Includes

### 1. Multi-Tool Source Architecture

TokenLens Phase 2 introduces a plugin-based source system. Each AI tool is a source module that normalises its usage data to a common schema. The same Efficiency Score, recommendations engine, and ROI calculator works across all of them.

**Source status:**

| Tool | Status | Data method | Credentials needed |
|---|---|---|---|
| Claude Code | ✅ **Active (Phase 1)** | Local JSONL logs | None |
| OpenAI API | 🔄 Phase 2 | REST API `/v1/usage` | `OPENAI_API_KEY` |
| GitHub Copilot | 🔄 Phase 2 | GitHub API `/orgs/{org}/copilot/usage` | `GITHUB_TOKEN` (manage_billing:copilot) |
| Cursor | ⏳ Pending | Waiting for platform log exposure | TBD |
| Windsurf / Codeium | ⏳ Pending | Waiting for API/log access | TBD |

**The plugin contract is already defined.** See `sources/` directory. Adding a new tool requires implementing one `scan()` function.

---

### 2. Cross-Tool Efficiency Score

Phase 2 introduces a normalised efficiency metric that works across tools with different cost models:

- **Claude Code**: token-based, cache-aware → existing A–F score
- **OpenAI API**: token-based, no caching equivalent → score adapts to available signals
- **GitHub Copilot**: seat-based + acceptance rate → acceptance_rate becomes the primary output density signal

The composite score normalises each tool's unique cost structure to the same 0–100 scale.

---

### 3. Team Edition — Central Aggregation

Phase 1 is a local tool. Each engineer runs it on their own machine with their own data.

Phase 2 introduces an **optional central collection agent** — a lightweight, self-hosted server that:
- Aggregates efficiency data from multiple engineers' machines
- Generates team-level and project-level roll-ups
- Surfaces the "10 most wasteful sessions across the entire team this week"
- Sends a weekly digest to the engineering manager (Slack or email)

**Architecture:**
```
Engineer A machine  →  TokenLens agent  →  Central server (self-hosted)  →  Team dashboard
Engineer B machine  →  TokenLens agent  ↗
Engineer C machine  →  TokenLens agent  ↗
```

**Privacy:** No prompt content or code is ever transmitted. Only token counts, costs, and efficiency scores.

---

### 4. Budget Guardrails

Phase 2 adds spend controls:

- Set a monthly budget per project or per team
- Alert at 50%, 80%, 95% of budget (Slack webhook or email)
- Hard stop option: flag sessions to the engineer when a project crosses its limit
- Retrospective: "You went 40% over budget on insight-brain in April. Here's why."

---

### 5. Governance and Compliance Reports

Built for security-first engineering organisations (directly relevant for Sonatype-style teams):

- **Audit trail**: which models were used, when, by whom, on which projects
- **Data residency report**: all models queried, all regions used — for GDPR/SOC2
- **Sensitive pattern detection**: flags sessions that may have included credential patterns or PII in prompts (pattern-match only, no content logging)
- **Monthly spend report**: exportable PDF for finance and procurement teams

---

### 6. VS Code and JetBrains Extension

Phase 2 ships a lightweight IDE extension that:
- Shows your project's current Efficiency Score in the status bar
- Alerts when a session is approaching anomaly territory (live, while you work)
- One-click to open the full TokenLens dashboard from the editor

---

## Phase 2 Pricing Model (Under Consideration)

Phase 1 is and will remain **free and open source**.

Phase 2 is being designed as a freemium:

| Tier | Price | What's included |
|---|---|---|
| **Individual** | Free forever | Phase 1 features + multi-tool local scanning |
| **Team** | $X/engineer/month | Central aggregation, team dashboard, budget alerts |
| **Enterprise** | Custom | Governance reports, SSO, self-hosted, SLA |

*Pricing is under consideration. If you have a view on what's reasonable for your team, say so in the issue.*

---

## The Architectural Bet

Phase 2 is built on one strategic assumption:

> AI coding tools will proliferate. Teams will use 3–5 of them within 18 months. The team that owns the intelligence layer across all of them owns the governance conversation — regardless of which model wins.

TokenLens is designed to be model-agnostic and tool-agnostic by architecture, not by claim.

The `sources/` plugin directory already exists. The normalised schema is already defined. The first two integrations (Claude Code + OpenAI API) prove the pattern.

---

## Want Phase 2 Early?

This is a market validation exercise. Phase 2 ships when there are enough teams that need it.

**Signal your interest:**

- ⭐ **Star this repo** — visible counter of interest
- 🐛 **Open an issue** tagged `phase-2` — tell us your tool stack and what you need
- 💬 **DM on LinkedIn** — [Aditya Bikram Dash](https://linkedin.com/in/adityabikramdash) — for direct conversation about your team's needs

If you're an engineering leader at a company using multiple AI tools and you want early access: DM directly. We'll set up a session and you get Phase 2 before anyone else.

---

*Built by [Aditya Bikram Dash](https://github.com/abdash1994) · TokenLens is MIT licensed with attribution requirement*
