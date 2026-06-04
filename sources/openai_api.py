"""
TokenLens — Source: OpenAI API
Phase 2 (coming)

Fetches token usage for GPT-4o, GPT-4-turbo, and other OpenAI models
via the OpenAI Usage API. Normalises to TokenLens's standard schema
so the same Efficiency Score, ROI calculator, and recommendations
engine works across both Claude and OpenAI spend.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SETUP (Phase 2):
    export OPENAI_API_KEY=YOUR_OPENAI_API_KEY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

API endpoint used:
    GET https://api.openai.com/v1/usage?date=YYYY-MM-DD
    Authorization: Bearer YOUR_OPENAI_API_KEY

Data available:
    - n_requests, operation, snapshot_id (model)
    - n_context_tokens_total (≈ input_tokens)
    - n_generated_tokens_total (≈ output_tokens)
    Note: OpenAI does not expose cache_read / cache_write equivalents yet.

Pricing normalisation:
    GPT-4o:       $2.50/MTok input  · $10.00/MTok output
    GPT-4-turbo:  $10.00/MTok input · $30.00/MTok output
    GPT-3.5:      $0.50/MTok input  · $1.50/MTok output

Status: PHASE 2 — not yet active. Star the repo + open an issue to vote for this.
"""

SOURCE_NAME = "OpenAI API"
REQUIRES_CREDENTIALS = True
CREDENTIAL_ENV_VAR = "OPENAI_API_KEY"
CREDENTIAL_SCOPE = "Read-only access to usage statistics"
STATUS = "phase_2"

OPENAI_PRICING = {
    "gpt-4o":           {"input": 2.50,  "output": 10.00},
    "gpt-4-turbo":      {"input": 10.00, "output": 30.00},
    "gpt-4":            {"input": 30.00, "output": 60.00},
    "gpt-3.5-turbo":    {"input": 0.50,  "output": 1.50},
}


def is_available() -> bool:
    """Returns True if OPENAI_API_KEY is set in the environment."""
    import os
    return bool(os.environ.get("OPENAI_API_KEY"))


def scan(db_path, **kwargs) -> dict:
    """
    Phase 2 implementation — not active yet.
    Will fetch OpenAI usage, normalise to TokenLens schema, and write to db.
    """
    raise NotImplementedError(
        "OpenAI API source is Phase 2. "
        "Star github.com/abdash1994/tokenlens and open an issue to prioritise this."
    )
