"""
TokenLens - AI Engineering Intelligence Platform
scanner.py: Incremental JSONL parser. Reads Claude Code session logs,
extracts token usage, and persists to a local SQLite database.
"""

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path.home() / ".tokenlens" / "tokenlens.db"

PRICING = {
    "opus":   {"input": 5.00,  "output": 25.00, "cache_write": 6.25, "cache_read": 0.50},
    "sonnet": {"input": 3.00,  "output": 15.00, "cache_write": 3.75, "cache_read": 0.30},
    "haiku":  {"input": 1.00,  "output": 5.00,  "cache_write": 1.25, "cache_read": 0.10},
}

DEFAULT_PROJECTS_DIRS = [
    Path.home() / ".claude" / "projects",
    Path.home() / "Library" / "Developer" / "Xcode" / "CodingAssistant" / "ClaudeAgentConfig" / "projects",
]


def get_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path: Path = DB_PATH):
    conn = get_db(db_path)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id     TEXT PRIMARY KEY,
            project_name   TEXT NOT NULL,
            first_seen     TEXT,
            last_seen      TEXT,
            input_tokens   INTEGER DEFAULT 0,
            output_tokens  INTEGER DEFAULT 0,
            cache_write_tokens INTEGER DEFAULT 0,
            cache_read_tokens  INTEGER DEFAULT 0,
            cost_usd       REAL DEFAULT 0,
            message_count  INTEGER DEFAULT 0,
            model          TEXT,
            entrypoint     TEXT,
            git_branch     TEXT,
            cwd            TEXT
        );

        CREATE TABLE IF NOT EXISTS messages (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          TEXT NOT NULL,
            project_name        TEXT NOT NULL,
            timestamp           TEXT NOT NULL,
            model               TEXT,
            input_tokens        INTEGER DEFAULT 0,
            output_tokens       INTEGER DEFAULT 0,
            cache_write_tokens  INTEGER DEFAULT 0,
            cache_read_tokens   INTEGER DEFAULT 0,
            cost_usd            REAL DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        );

        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
        CREATE INDEX IF NOT EXISTS idx_messages_project ON messages(project_name);

        CREATE TABLE IF NOT EXISTS scan_state (
            file_path    TEXT PRIMARY KEY,
            file_size    INTEGER,
            mtime        REAL,
            last_scanned TEXT
        );
    """)
    conn.commit()
    conn.close()


def _project_name_from_path(dir_name: str) -> str:
    """Convert directory slug like '-Users-john-myproject' → 'myproject'."""
    parts = [p for p in dir_name.split("-") if p]
    if len(parts) >= 3 and parts[0] == "Users":
        return "-".join(parts[2:]) or dir_name
    return dir_name.strip("-") or dir_name


def _model_tier(model: str) -> str | None:
    m = model.lower()
    if "opus" in m:
        return "opus"
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    return None


def _calc_cost(model: str, input_t: int, output_t: int, cache_write_t: int, cache_read_t: int) -> float:
    tier = _model_tier(model)
    if not tier:
        return 0.0
    p = PRICING[tier]
    mtok = 1_000_000
    return (
        input_t       * p["input"]       / mtok
        + output_t    * p["output"]      / mtok
        + cache_write_t * p["cache_write"] / mtok
        + cache_read_t  * p["cache_read"]  / mtok
    )


def scan(projects_dirs: list[Path] | None = None, db_path: Path = DB_PATH, verbose: bool = False) -> dict:
    init_db(db_path)
    conn = get_db(db_path)

    if projects_dirs is None:
        projects_dirs = [d for d in DEFAULT_PROJECTS_DIRS if d.exists()]

    files_scanned = 0
    files_skipped = 0
    messages_added = 0
    sessions_seen: set[str] = set()

    for base_dir in projects_dirs:
        for project_dir in base_dir.iterdir():
            if not project_dir.is_dir():
                continue
            project_name = _project_name_from_path(project_dir.name)

            for jsonl_file in project_dir.glob("*.jsonl"):
                stat = jsonl_file.stat()
                file_path = str(jsonl_file)

                row = conn.execute(
                    "SELECT file_size, mtime FROM scan_state WHERE file_path = ?",
                    (file_path,)
                ).fetchone()

                if row and row["file_size"] == stat.st_size and abs(row["mtime"] - stat.st_mtime) < 1:
                    files_skipped += 1
                    continue

                files_scanned += 1
                added = _process_file(conn, jsonl_file, project_name, verbose)
                messages_added += added
                sessions_seen.add(jsonl_file.stem)

                conn.execute(
                    "INSERT OR REPLACE INTO scan_state(file_path, file_size, mtime, last_scanned) VALUES (?,?,?,?)",
                    (file_path, stat.st_size, stat.st_mtime, datetime.now(timezone.utc).isoformat())
                )

    conn.commit()
    conn.close()

    return {
        "files_scanned": files_scanned,
        "files_skipped": files_skipped,
        "messages_added": messages_added,
        "sessions_seen": len(sessions_seen),
    }


def _process_file(conn: sqlite3.Connection, path: Path, project_name: str, verbose: bool) -> int:
    session_id = path.stem

    session_stats = {
        "input": 0, "output": 0, "cache_write": 0, "cache_read": 0,
        "cost": 0.0, "count": 0, "first_seen": None, "last_seen": None,
        "model": None, "entrypoint": None, "git_branch": None, "cwd": None,
    }
    # Collect message rows; flush after session row is written (FK constraint)
    pending_messages: list[tuple] = []

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if obj.get("type") != "assistant":
                    continue

                msg   = obj.get("message", {})
                usage = msg.get("usage", {})
                if not usage:
                    continue

                model         = msg.get("model", "unknown")
                input_t       = usage.get("input_tokens", 0)
                output_t      = usage.get("output_tokens", 0)
                cache_write_t = usage.get("cache_creation_input_tokens", 0)
                cache_read_t  = usage.get("cache_read_input_tokens", 0)
                cost          = _calc_cost(model, input_t, output_t, cache_write_t, cache_read_t)
                ts            = obj.get("timestamp", "")

                session_stats["input"]       += input_t
                session_stats["output"]      += output_t
                session_stats["cache_write"] += cache_write_t
                session_stats["cache_read"]  += cache_read_t
                session_stats["cost"]        += cost
                session_stats["count"]       += 1

                if ts:
                    if not session_stats["first_seen"] or ts < session_stats["first_seen"]:
                        session_stats["first_seen"] = ts
                    if not session_stats["last_seen"] or ts > session_stats["last_seen"]:
                        session_stats["last_seen"] = ts

                if not session_stats["model"] and model != "unknown":
                    session_stats["model"] = model
                if not session_stats["entrypoint"]:
                    session_stats["entrypoint"] = obj.get("entrypoint")
                if not session_stats["git_branch"]:
                    session_stats["git_branch"] = obj.get("gitBranch")
                if not session_stats["cwd"]:
                    session_stats["cwd"] = obj.get("cwd")

                pending_messages.append(
                    (session_id, project_name, ts, model,
                     input_t, output_t, cache_write_t, cache_read_t, cost)
                )

    except OSError:
        return 0

    if session_stats["count"] == 0:
        return 0

    # Insert session first (parent), then messages (children)
    conn.execute(
        """INSERT OR REPLACE INTO sessions
           (session_id, project_name, first_seen, last_seen,
            input_tokens, output_tokens, cache_write_tokens, cache_read_tokens,
            cost_usd, message_count, model, entrypoint, git_branch, cwd)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            session_id, project_name,
            session_stats["first_seen"], session_stats["last_seen"],
            session_stats["input"],      session_stats["output"],
            session_stats["cache_write"], session_stats["cache_read"],
            session_stats["cost"],       session_stats["count"],
            session_stats["model"],      session_stats["entrypoint"],
            session_stats["git_branch"], session_stats["cwd"],
        )
    )

    conn.executemany(
        """INSERT OR IGNORE INTO messages
           (session_id, project_name, timestamp, model,
            input_tokens, output_tokens, cache_write_tokens, cache_read_tokens, cost_usd)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        pending_messages,
    )

    if verbose:
        print(f"  ✓ {project_name}/{session_id[:8]}… "
              f"${session_stats['cost']:.4f}  {session_stats['count']} msgs")

    return len(pending_messages)
