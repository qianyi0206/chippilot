"""Configuration center: .env + project.yaml + constants."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

# If using a third-party base URL, remove auth token to avoid conflicts
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

# --- Paths ---
WORKDIR = Path.cwd()
TEAM_DIR = WORKDIR / ".team"
INBOX_DIR = TEAM_DIR / "inbox"
TASKS_DIR = WORKDIR / ".tasks"
SKILLS_DIR = WORKDIR / "skills"
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
CAD_DIR = Path(__file__).resolve().parent.parent / "cad"
MOCK_DATA_DIR = Path(__file__).resolve().parent.parent / "mock_data"

# --- LLM ---
MODEL = os.environ.get("MODEL_ID", "claude-sonnet-4-6")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")

# --- Agent ---
TOKEN_THRESHOLD = 100_000
POLL_INTERVAL = 5
IDLE_TIMEOUT = 60
MAX_AGENT_TURNS = 50
MAX_SUBAGENT_TURNS = 30

# --- Project ---
PROJECT_NAME = os.getenv("CHIPPILOT_PROJECT", "default")

# --- Message types ---
VALID_MSG_TYPES = frozenset({
    "message", "broadcast", "shutdown_request",
    "shutdown_response", "plan_approval_response",
})
