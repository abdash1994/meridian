"""
TokenLens — Source: GitHub Copilot
Phase 2 (coming)

Fetches Copilot seat usage and suggestion acceptance data via the
GitHub REST API. Normalises to TokenLens's standard schema for
cross-tool efficiency scoring and team ROI reporting.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SETUP (Phase 2):
    export GITHUB_TOKEN=YOUR_GITHUB_PERSONAL_ACCESS_TOKEN

    Required OAuth scopes:
        manage_billing:copilot   (for org-level usage)
        read:org                 (for team membership)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

API endpoints used:
    GET /orgs/{org}/copilot/usage
        → Daily breakdown: suggestions, acceptances, active seats
    GET /orgs/{org}/copilot/billing/seats
        → Per-seat usage by engineer

Data available:
    - total_suggestions_count
    - total_acceptances_count       → acceptance_rate = key efficiency metric
    - total_lines_suggested
    - total_lines_accepted          → lines_saved = proxy for output density
    - total_active_users
    - breakdown by language and editor

Efficiency mapping to TokenLens schema:
    acceptance_rate        → proxy for Output Density signal
    lines_accepted/day     → proxy for developer value output
    seat_utilisation       → team adoption rate

Note: Copilot does not expose input token counts. Cost is seat-based ($19/user/month).
      TokenLens will calculate cost from seat count × days active, not per-token.

Status: PHASE 2 — not yet active. Star the repo + open an issue to vote for this.
"""

SOURCE_NAME = "GitHub Copilot"
REQUIRES_CREDENTIALS = True
CREDENTIAL_ENV_VAR = "GITHUB_TOKEN"
CREDENTIAL_SCOPE = "manage_billing:copilot, read:org"
STATUS = "phase_2"


def is_available() -> bool:
    """Returns True if GITHUB_TOKEN is set in the environment."""
    import os
    return bool(os.environ.get("GITHUB_TOKEN"))


def scan(db_path, org: str = None, **kwargs) -> dict:
    """
    Phase 2 implementation — not active yet.
    Will fetch Copilot org usage, normalise to TokenLens schema, and write to db.
    """
    raise NotImplementedError(
        "GitHub Copilot source is Phase 2. "
        "Star github.com/abdash1994/tokenlens and open an issue to prioritise this."
    )
