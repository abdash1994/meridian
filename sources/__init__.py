"""
TokenLens — Source Plugin Architecture
Phase 2: Multi-tool AI spend intelligence

Each source plugin reads usage data from one AI coding tool and normalises
it into TokenLens's standard schema. New tools can be added without touching
core scanner or analyzer logic.

Plugin contract:
    Each source module must expose a `scan(db_path, **kwargs) -> dict` function
    that returns: { files_scanned, messages_added, sessions_seen, source_name }

Active sources are discovered at runtime:
    - claude_code  — always active (reads ~/.claude/projects/)
    - openai_api   — active if OPENAI_API_KEY is set in environment
    - github_copilot — active if GITHUB_TOKEN is set (requires manage_billing:copilot scope)
    - cursor       — pending (Cursor does not yet expose local token-level logs)
"""

AVAILABLE_SOURCES = [
    "claude_code",
    "openai_api",       # Phase 2 — requires OPENAI_API_KEY env var
    "github_copilot",   # Phase 2 — requires GITHUB_TOKEN with billing scope
    "cursor",           # Phase 2 — pending Cursor local log exposure
]
