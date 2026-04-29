"""LLM client factory. Currently Anthropic; pre-wired for multi-provider."""

from anthropic import Anthropic

from chippilot.config import ANTHROPIC_BASE_URL


def create_client() -> Anthropic:
    """Create an Anthropic client (or compatible provider)."""
    return Anthropic(base_url=ANTHROPIC_BASE_URL)
