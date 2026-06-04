"""
TokenLens — Source: Claude Code
Phase 1 (active)

Reads token usage from Claude Code's local JSONL session logs.
No credentials required — data is already on your machine.

Data location: ~/.claude/projects/<project>/<session-id>.jsonl
"""

# This source is implemented in scanner.py (Phase 1 core).
# Phase 2 will refactor this into the plugin interface here,
# keeping full backwards compatibility.

SOURCE_NAME = "Claude Code"
REQUIRES_CREDENTIALS = False
DATA_LOCATION = "~/.claude/projects/"
STATUS = "active"
