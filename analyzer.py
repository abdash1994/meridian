"""
TokenLens - AI Engineering Intelligence Platform
analyzer.py: Intelligence engine. Computes Efficiency Scores, detects anomalies,
generates actionable recommendations, and calculates developer ROI.
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scanner import DB_PATH, get_db

# Hourly developer cost assumption (USD). Used for ROI calculation.
# Source: US Bureau of Labor Statistics median software engineer wage ~$120k/yr,
# ~$130k total compensation → ~$125/hr fully loaded (benefits, overhead).
# Configurable via CLI --dev-rate flag or /api/roi?dev_rate=X
DEV_HOURLY_RATE = 125.0

# Attribution rate: fraction of AI output tokens we credit as replacing developer work.
# Conservative at 40% — GitHub Copilot research (2022) showed 55% productivity gain;
# Stanford HAI (2023) showed 35-45% on complex tasks. 40% is defensible to a CFO.
# Configurable via CLI --attribution flag or /api/roi?attribution=X
ATTRIBUTION_RATE = 0.40

# Developer typing speed (chars/min) — used to convert AI output to time saved.
# Effective coding speed (net of thinking, debugging) ~200 chars/min.
DEV_CHARS_PER_MIN = 200.0

# Average chars per output token (GPT/Claude standard is ~4 chars/token)
CHARS_PER_TOKEN = 4.0


# ── Efficiency Score ──────────────────────────────────────────────────────────

def _efficiency_grade(score: float) -> str:
    if score >= 88:  return "A"
    if score >= 74:  return "B"
    if score >= 58:  return "C"
    if score >= 40:  return "D"
    return "F"


def _calc_efficiency_score(
    cache_read: int,
    cache_write: int,
    fresh_input: int,
    output: int,
) -> float:
    """
    Composite score (0–100) weighing four signals:

    1. Cache Hit Rate (40 pts)  — cache_read / total_context_tokens
       Highest-leverage cost lever. Warm caches cut input costs 90%.

    2. Output Density (30 pts)  — output / (fresh_input + cache_read)
       Are prompts yielding rich, useful responses relative to context size?

    3. Cache Warm Rate (20 pts) — cache_write > 0 at all?
       Teams that never write to cache are leaving easy savings on the table.

    4. Context Efficiency (10 pts) — penalises sessions that
       never cache anything (pure fresh-input pattern).
    """
    total_context = fresh_input + cache_write + cache_read

    # 1. Cache hit rate
    if total_context > 0:
        cache_hit_rate = cache_read / total_context
    else:
        cache_hit_rate = 0.0
    cache_score = cache_hit_rate * 40

    # 2. Output density (capped at 1.0 to avoid runaway scores)
    denominator = fresh_input + cache_read
    if denominator > 0:
        output_density = min(output / denominator, 1.0)
    else:
        output_density = 0.0
    output_score = output_density * 30

    # 3. Cache warm rate (binary: are you caching at all?)
    warm_score = 20 if cache_write > 0 else 0

    # 4. Context efficiency penalty if 100% fresh input
    if total_context > 0:
        fresh_ratio = fresh_input / total_context
        context_score = (1 - fresh_ratio) * 10
    else:
        context_score = 0

    return round(cache_score + output_score + warm_score + context_score, 1)


# ── Summary ───────────────────────────────────────────────────────────────────

def get_summary(db_path: Path = DB_PATH) -> dict:
    conn = get_db(db_path)

    row = conn.execute("""
        SELECT
            COALESCE(SUM(cost_usd), 0)            AS total_cost,
            COALESCE(SUM(input_tokens), 0)        AS input_t,
            COALESCE(SUM(output_tokens), 0)       AS output_t,
            COALESCE(SUM(cache_write_tokens), 0)  AS cache_write_t,
            COALESCE(SUM(cache_read_tokens), 0)   AS cache_read_t,
            COUNT(*)                               AS total_sessions,
            MIN(first_seen)                        AS first_date,
            MAX(last_seen)                         AS last_date
        FROM sessions
    """).fetchone()

    total_cost       = row["total_cost"]
    input_t          = row["input_t"]
    output_t         = row["output_t"]
    cache_write_t    = row["cache_write_t"]
    cache_read_t     = row["cache_read_t"]
    total_sessions   = row["total_sessions"]
    total_tokens     = input_t + output_t + cache_write_t + cache_read_t

    efficiency_score = _calc_efficiency_score(cache_read_t, cache_write_t, input_t, output_t)
    efficiency_grade = _efficiency_grade(efficiency_score)

    total_context = input_t + cache_write_t + cache_read_t
    cache_efficiency = round(cache_read_t / total_context, 4) if total_context > 0 else 0.0

    roi = _calc_roi(output_t, total_cost)

    # Scan metadata
    scan_state = conn.execute(
        "SELECT MAX(last_scanned) AS ls FROM scan_state"
    ).fetchone()
    last_scan = scan_state["ls"] if scan_state else None

    conn.close()

    return {
        "total_cost":        round(total_cost, 4),
        "total_tokens":      total_tokens,
        "input_tokens":      input_t,
        "output_tokens":     output_t,
        "cache_write_tokens": cache_write_t,
        "cache_read_tokens": cache_read_t,
        "total_sessions":    total_sessions,
        "cache_efficiency":  cache_efficiency,
        "efficiency_score":  efficiency_score,
        "efficiency_grade":  efficiency_grade,
        "roi":               roi,
        "first_date":        row["first_date"],
        "last_date":         row["last_date"],
        "last_scan":         last_scan,
    }


# ── Daily Chart Data ──────────────────────────────────────────────────────────

def get_daily_chart(days: int = 30, db_path: Path = DB_PATH) -> list[dict]:
    conn = get_db(db_path)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    rows = conn.execute("""
        SELECT
            DATE(timestamp)                        AS day,
            ROUND(SUM(cost_usd), 4)               AS cost,
            SUM(input_tokens)                      AS input_t,
            SUM(output_tokens)                     AS output_t,
            SUM(cache_write_tokens)                AS cache_write_t,
            SUM(cache_read_tokens)                 AS cache_read_t
        FROM messages
        WHERE timestamp >= ?
        GROUP BY day
        ORDER BY day ASC
    """, (cutoff,)).fetchall()

    conn.close()
    return [dict(r) for r in rows]


# ── Projects Breakdown ────────────────────────────────────────────────────────

def get_projects(db_path: Path = DB_PATH) -> list[dict]:
    conn = get_db(db_path)

    rows = conn.execute("""
        SELECT
            project_name,
            COUNT(*)                               AS sessions,
            ROUND(SUM(cost_usd), 4)               AS total_cost,
            SUM(input_tokens)                      AS input_t,
            SUM(output_tokens)                     AS output_t,
            SUM(cache_write_tokens)                AS cache_write_t,
            SUM(cache_read_tokens)                 AS cache_read_t,
            MAX(last_seen)                         AS last_active,
            GROUP_CONCAT(DISTINCT model)           AS models
        FROM sessions
        GROUP BY project_name
        ORDER BY total_cost DESC
    """).fetchall()

    # 7-day cost per project for trend
    cutoff_7d = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    trend_rows = conn.execute("""
        SELECT project_name, ROUND(SUM(cost_usd), 4) AS cost_7d
        FROM messages
        WHERE timestamp >= ?
        GROUP BY project_name
    """, (cutoff_7d,)).fetchall()
    trend_map = {r["project_name"]: r["cost_7d"] for r in trend_rows}

    conn.close()

    result = []
    for r in rows:
        cache_write = r["cache_write_t"]
        cache_read  = r["cache_read_t"]
        fresh_input = r["input_t"]
        output      = r["output_t"]

        total_context = fresh_input + cache_write + cache_read
        cache_eff = round(cache_read / total_context, 4) if total_context > 0 else 0.0
        score = _calc_efficiency_score(cache_read, cache_write, fresh_input, output)
        grade = _efficiency_grade(score)

        result.append({
            "project":         r["project_name"],
            "sessions":        r["sessions"],
            "total_cost":      r["total_cost"],
            "input_tokens":    r["input_t"],
            "output_tokens":   r["output_t"],
            "cache_write_tokens": r["cache_write_t"],
            "cache_read_tokens":  r["cache_read_t"],
            "cache_efficiency":   cache_eff,
            "efficiency_score":   score,
            "efficiency_grade":   grade,
            "last_active":     r["last_active"],
            "cost_7d":         trend_map.get(r["project_name"], 0.0),
            "models":          r["models"] or "",
        })

    return result


# ── Sessions Explorer ─────────────────────────────────────────────────────────

def get_sessions(limit: int = 25, project: str | None = None, db_path: Path = DB_PATH) -> list[dict]:
    conn = get_db(db_path)

    # Calculate per-project avg cost to detect anomalies
    avg_costs = {}
    for row in conn.execute("SELECT project_name, AVG(cost_usd) AS avg FROM sessions GROUP BY project_name"):
        avg_costs[row["project_name"]] = row["avg"]

    where = "WHERE project_name = ?" if project else ""
    params = (project,) if project else ()
    limit_param = (limit,)

    rows = conn.execute(f"""
        SELECT
            session_id, project_name, first_seen, last_seen,
            input_tokens, output_tokens, cache_write_tokens, cache_read_tokens,
            cost_usd, message_count, model, entrypoint, git_branch
        FROM sessions
        {where}
        ORDER BY last_seen DESC
        LIMIT ?
    """, (*params, *limit_param)).fetchall()

    conn.close()

    result = []
    for r in rows:
        cache_read  = r["cache_read_tokens"]
        cache_write = r["cache_write_tokens"]
        fresh_input = r["input_tokens"]
        output      = r["output_tokens"]
        total_context = fresh_input + cache_write + cache_read
        cache_eff = round(cache_read / total_context, 4) if total_context > 0 else 0.0
        score = _calc_efficiency_score(cache_read, cache_write, fresh_input, output)
        grade = _efficiency_grade(score)

        proj = r["project_name"]
        avg = avg_costs.get(proj, 0)
        is_anomaly = r["cost_usd"] > avg * 3.5 if avg > 0 else False

        result.append({
            "session_id":       r["session_id"],
            "project":          r["project_name"],
            "first_seen":       r["first_seen"],
            "last_seen":        r["last_seen"],
            "input_tokens":     r["input_tokens"],
            "output_tokens":    r["output_tokens"],
            "cache_write_tokens": r["cache_write_tokens"],
            "cache_read_tokens":  r["cache_read_tokens"],
            "cost_usd":         round(r["cost_usd"], 4),
            "message_count":    r["message_count"],
            "model":            r["model"] or "unknown",
            "entrypoint":       r["entrypoint"] or "cli",
            "git_branch":       r["git_branch"] or "",
            "cache_efficiency": cache_eff,
            "efficiency_score": score,
            "efficiency_grade": grade,
            "is_anomaly":       is_anomaly,
        })

    return result


# ── Recommendations Engine ────────────────────────────────────────────────────

def get_recommendations(db_path: Path = DB_PATH) -> list[dict]:
    projects = get_projects(db_path)
    summary = get_summary(db_path)
    recs = []

    overall_cache_eff = summary["cache_efficiency"]
    total_cost = summary["total_cost"]

    # --- Rec 1: Cache under-utilisation (biggest lever) ---
    poor_cache = [p for p in projects if p["cache_efficiency"] < 0.25 and p["total_cost"] > 0.01]
    if poor_cache:
        worst = sorted(poor_cache, key=lambda x: x["total_cost"], reverse=True)[0]
        potential_saving = worst["total_cost"] * 0.55
        recs.append({
            "id":          "cache-cold",
            "type":        "cache",
            "impact":      "high",
            "title":       f"Warm the cache in '{worst['project']}'",
            "description": (
                f"Only {worst['cache_efficiency']*100:.1f}% of context tokens are served from cache in this project. "
                "Engineers are re-sending large contexts on every turn. Adding a persistent system prompt or "
                "using `cache_control: ephemeral` on large static contexts typically reduces input costs by 55–80%."
            ),
            "action":      "Add `cache_control: {type: 'ephemeral'}` to static system prompts and large document blocks.",
            "savings_usd": round(potential_saving, 2),
            "project":     worst["project"],
        })

    # --- Rec 2: All-time no-cache projects ---
    zero_cache = [p for p in projects if p["cache_write_tokens"] == 0 and p["total_cost"] > 0.05]
    if zero_cache:
        total_saveable = sum(p["total_cost"] * 0.45 for p in zero_cache)
        names = ", ".join(p["project"] for p in zero_cache[:3])
        recs.append({
            "id":          "no-cache-at-all",
            "type":        "cache",
            "impact":      "high",
            "title":       "These projects have never used prompt caching",
            "description": (
                f"Projects [{names}] have accumulated spend with zero cache writes. "
                "Every token of context is paid for at full input rate every single turn. "
                "Implementing basic caching here is the single highest-ROI optimisation available."
            ),
            "action":      "Review system prompts and long-context patterns — add cache_control breakpoints.",
            "savings_usd": round(total_saveable, 2),
            "project":     None,
        })

    # --- Rec 3: Anomalous sessions ---
    sessions = get_sessions(limit=100, db_path=db_path)
    anomalies = [s for s in sessions if s["is_anomaly"]]
    if anomalies:
        worst_session = sorted(anomalies, key=lambda x: x["cost_usd"], reverse=True)[0]
        recs.append({
            "id":          "anomaly-sessions",
            "type":        "anomaly",
            "impact":      "medium",
            "title":       f"{len(anomalies)} session(s) with abnormal token burn",
            "description": (
                f"Session {worst_session['session_id'][:12]}… in '{worst_session['project']}' "
                f"cost ${worst_session['cost_usd']:.3f} — 3.5× above that project's average. "
                "This often indicates: (a) large file dumps without chunking, "
                "(b) runaway tool-call loops, or (c) missing context pruning."
            ),
            "action":      "Review these sessions in the Session Explorer. Add explicit context limits or summarisation steps.",
            "savings_usd": round(sum(s["cost_usd"] * 0.6 for s in anomalies), 2),
            "project":     worst_session["project"],
        })

    # --- Rec 4: Output density is low (low value per token) ---
    low_density = [
        p for p in projects
        if p["output_tokens"] > 0
        and (p["input_tokens"] + p["cache_read_tokens"]) > 0
        and (p["output_tokens"] / (p["input_tokens"] + p["cache_read_tokens"])) < 0.05
        and p["total_cost"] > 0.10
    ]
    if low_density:
        ld = sorted(low_density, key=lambda x: x["total_cost"], reverse=True)[0]
        recs.append({
            "id":          "low-output-density",
            "type":        "pattern",
            "impact":      "medium",
            "title":       f"Low output density in '{ld['project']}'",
            "description": (
                f"For every 100 context tokens consumed, only "
                f"{ld['output_tokens']/(ld['input_tokens']+ld['cache_read_tokens'])*100:.1f} output tokens are generated. "
                "This suggests prompts may be overly verbose, context windows too large, or tasks too narrow. "
                "Tighter prompts with clearer task scoping typically improve this ratio 2–4×."
            ),
            "action":      "Audit system prompts for verbosity. Consider breaking large tasks into focused sub-prompts.",
            "savings_usd": round(ld["total_cost"] * 0.25, 2),
            "project":     ld["project"],
        })

    # --- Rec 5: Cost trending up ---
    daily = get_daily_chart(days=14, db_path=db_path)
    if len(daily) >= 6:
        first_half = sum(d["cost"] for d in daily[:len(daily)//2])
        second_half = sum(d["cost"] for d in daily[len(daily)//2:])
        if first_half > 0 and second_half > first_half * 1.3:
            growth_pct = round((second_half - first_half) / first_half * 100, 0)
            recs.append({
                "id":          "cost-trending-up",
                "type":        "budget",
                "impact":      "medium",
                "title":       f"Costs up {growth_pct:.0f}% in the last 7 days",
                "description": (
                    f"Spend in the second half of the last 14 days is ${second_half:.2f} vs "
                    f"${first_half:.2f} in the first half — a {growth_pct:.0f}% increase. "
                    "Review recent project activity and set budget alerts to catch runaway spend early."
                ),
                "action":      "Set project-level budget thresholds and enable daily digest alerts.",
                "savings_usd": round(second_half * 0.2, 2),
                "project":     None,
            })

    # Sort: high impact first, then by savings
    priority = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: (priority.get(r["impact"], 3), -r["savings_usd"]))

    return recs


# ── ROI Calculator ────────────────────────────────────────────────────────────

def _calc_roi(
    output_tokens: int,
    ai_cost_usd: float,
    dev_hourly_rate: float = DEV_HOURLY_RATE,
    attribution_rate: float = ATTRIBUTION_RATE,
) -> dict:
    """
    Estimates developer time saved by AI-generated output.

    Methodology (all figures configurable):
    - Each output token ≈ CHARS_PER_TOKEN chars of code/text
    - Effective developer coding speed ≈ DEV_CHARS_PER_MIN chars/min
    - Attribution rate: fraction of output that directly replaces developer effort
      (40% default — conservative vs GitHub Copilot study's 55%, Stanford HAI 35-45%)
    - Developer value = hours_saved × loaded hourly rate

    References:
    - GitHub Copilot productivity study (Kalliamvakou, 2022): 55% faster task completion
    - Stanford HAI study (Noy & Zhang, 2023): 35-45% productivity gain on writing tasks
    - We use 40% as a CFO-defensible midpoint.
    """
    chars_generated   = output_tokens * CHARS_PER_TOKEN
    dev_minutes_saved = (chars_generated / DEV_CHARS_PER_MIN) * attribution_rate
    dev_hours_saved   = dev_minutes_saved / 60
    dev_cost_saved    = dev_hours_saved * dev_hourly_rate
    roi_multiplier    = round(dev_cost_saved / ai_cost_usd, 1) if ai_cost_usd > 0 else 0.0

    return {
        "output_tokens":    output_tokens,
        "dev_hours_saved":  round(dev_hours_saved, 1),
        "dev_cost_saved":   round(dev_cost_saved, 2),
        "ai_cost":          round(ai_cost_usd, 4),
        "roi_multiplier":   roi_multiplier,
        "dev_hourly_rate":  dev_hourly_rate,
        "attribution_rate": attribution_rate,
    }


def get_roi(
    db_path: Path = DB_PATH,
    dev_hourly_rate: float = DEV_HOURLY_RATE,
    attribution_rate: float = ATTRIBUTION_RATE,
) -> dict:
    conn = get_db(db_path)
    row  = conn.execute(
        "SELECT COALESCE(SUM(output_tokens),0) AS ot, COALESCE(SUM(cost_usd),0) AS cost FROM sessions"
    ).fetchone()
    conn.close()
    return _calc_roi(row["ot"], row["cost"], dev_hourly_rate, attribution_rate)


# ── Model Distribution ────────────────────────────────────────────────────────

def get_model_distribution(db_path: Path = DB_PATH) -> list[dict]:
    conn = get_db(db_path)
    rows = conn.execute("""
        SELECT
            COALESCE(model, 'unknown')             AS model,
            COUNT(*)                               AS sessions,
            ROUND(SUM(cost_usd), 4)               AS total_cost,
            SUM(input_tokens + output_tokens + cache_write_tokens + cache_read_tokens) AS total_tokens
        FROM sessions
        GROUP BY model
        ORDER BY total_cost DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Roadmap to A ──────────────────────────────────────────────────────────────

def get_roadmap_to_a(db_path: Path = DB_PATH) -> list[dict]:
    """
    Returns an ordered list of concrete steps to improve the overall Efficiency Score
    from the current grade to A (88+). Each step includes estimated score gain and
    a specific action, so engineers have a clear improvement path — not just a grade.
    """
    s     = get_summary(db_path)
    score = s["efficiency_score"]
    grade = s["efficiency_grade"]

    if score >= 88:
        return []  # Already at A

    steps = []
    gap   = 88 - score

    # Step 1: Cache warm-up (if not caching at all — 20pts available)
    if s["cache_write_tokens"] == 0:
        steps.append({
            "step":        1,
            "title":       "Enable prompt caching",
            "description": "You have zero cache writes. Adding `cache_control: {type: 'ephemeral'}` "
                           "to your system prompt activates caching and immediately unlocks 20 score points.",
            "score_gain":  20,
            "difficulty":  "easy",
            "time":        "10 minutes",
        })

    # Step 2: Improve cache hit rate (40pts possible)
    cache_eff = s["cache_efficiency"]
    if cache_eff < 0.5:
        target_gain = round((0.7 - cache_eff) * 40, 0)
        steps.append({
            "step":        2,
            "title":       "Increase cache hit rate to 70%+",
            "description": f"Current cache hit rate is {cache_eff*100:.1f}%. Caching your system prompt "
                           "and large static contexts raises this significantly. "
                           "Target: 70%+ hit rate for a B grade, 85%+ for A.",
            "score_gain":  int(target_gain),
            "difficulty":  "medium",
            "time":        "1–2 hours",
        })

    # Step 3: Output density (30pts possible)
    denom = s["input_tokens"] + s["cache_read_tokens"]
    if denom > 0:
        out_ratio = s["output_tokens"] / denom
        if out_ratio < 0.10:
            steps.append({
                "step":        3,
                "title":       "Improve output density with tighter prompts",
                "description": f"Current output density: {out_ratio*100:.1f}% — "
                               "you consume a lot of context per token of useful output. "
                               "Breaking large tasks into focused sub-prompts and reducing "
                               "system prompt verbosity typically improves this 2–4×.",
                "score_gain":  15,
                "difficulty":  "medium",
                "time":        "Ongoing — 1 week of iteration",
            })

    # Step 4: Fix anomalous sessions
    sessions = get_sessions(limit=100, db_path=db_path)
    anomalies = [s for s in sessions if s["is_anomaly"]]
    if anomalies:
        steps.append({
            "step":        4,
            "title":       f"Resolve {len(anomalies)} anomalous session(s)",
            "description": "Sessions burning 3.5× their project average are dragging your per-session "
                           "scores down. Investigate for large file dumps, runaway loops, or "
                           "missing context limits. Each session fixed improves project-level grades.",
            "score_gain":  5,
            "difficulty":  "easy",
            "time":        "30 minutes investigation",
        })

    # Sort by easiest first
    difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
    steps.sort(key=lambda x: difficulty_order.get(x["difficulty"], 1))

    return steps


# ── DB Pruning ────────────────────────────────────────────────────────────────

def prune_before(date_str: str, db_path: Path = DB_PATH) -> dict:
    """
    Delete all sessions and messages with timestamps before date_str (YYYY-MM-DD).
    Useful for keeping the database size manageable over long periods.
    """
    try:
        # Validate date format before touching the DB
        datetime.strptime(date_str, "%Y-%m-%d")
        cutoff = f"{date_str}T00:00:00"
        conn   = get_db(db_path)

        # Count what will be deleted
        sessions_count = conn.execute(
            "SELECT COUNT(*) FROM sessions WHERE last_seen < ?", (cutoff,)
        ).fetchone()[0]
        messages_count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE timestamp < ?", (cutoff,)
        ).fetchone()[0]

        if sessions_count == 0:
            conn.close()
            return {"deleted_sessions": 0, "deleted_messages": 0, "cutoff": date_str}

        # Delete (messages first due to FK constraint)
        conn.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff,))
        conn.execute("DELETE FROM sessions WHERE last_seen < ?",  (cutoff,))
        conn.execute("DELETE FROM scan_state WHERE last_scanned < ?", (cutoff,))
        conn.execute("VACUUM")
        conn.commit()
        conn.close()

        return {
            "deleted_sessions": sessions_count,
            "deleted_messages": messages_count,
            "cutoff":           date_str,
        }
    except Exception as e:
        return {"error": str(e)}
