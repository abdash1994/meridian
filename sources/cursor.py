"""
TokenLens — Source: Cursor
Phase 2 (pending Cursor platform support)

Cursor is a VS Code fork with built-in AI completions powered by
Claude and GPT-4o. It currently does not expose local token-level
usage logs in a machine-readable format.

This source will activate once Cursor exposes one of:
    a) Local JSONL logs (similar to Claude Code's ~/.claude/projects/)
    b) A usage API endpoint accessible with a Cursor API key
    c) A VS Code extension API that surfaces token data

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
What we're watching:
    - Cursor changelog for any usage data exposure
    - Community requests on cursor.sh/forum for usage analytics
    - The cursor-usage open source community for any reverse-engineered paths

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

If you work at Cursor or know where the logs are stored:
    → Open an issue at github.com/abdash1994/tokenlens
    → We'll implement this immediately.

Status: PENDING — blocked on Cursor platform log exposure.
"""

SOURCE_NAME = "Cursor"
REQUIRES_CREDENTIALS = True
CREDENTIAL_ENV_VAR = "CURSOR_API_KEY"  # hypothetical — does not exist yet
STATUS = "pending_platform"


def is_available() -> bool:
    return False  # Not available until Cursor exposes usage data


def scan(db_path, **kwargs) -> dict:
    raise NotImplementedError(
        "Cursor source is pending platform support. "
        "See sources/cursor.py for details on what we're waiting for."
    )
