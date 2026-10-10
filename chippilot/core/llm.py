"""Shared LLM call helper: retry with backoff + optional text streaming."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Callable

import anthropic

if TYPE_CHECKING:
    from anthropic import Anthropic

_RETRYABLE = (
    anthropic.APIConnectionError,
    anthropic.APITimeoutError,
    anthropic.RateLimitError,
    anthropic.InternalServerError,
)


def call_llm(
    client: "Anthropic",
    *,
    model: str,
    messages: list,
    system: str | None = None,
    tools: list | None = None,
    max_tokens: int = 8000,
    on_text: Callable[[str], None] | None = None,
    max_retries: int = 3,
    cache: bool = True,
):
    """Call the messages API with retry and optional streamed text output.

    Retries retryable API errors (connection, timeout, rate limit, 5xx) with
    exponential backoff. When on_text is provided the response is streamed and
    each text delta is passed to the callback; the final message (including
    tool_use blocks) is returned either way.

    With cache=True (default) ephemeral prompt-caching breakpoints are placed
    on the system prompt and the tool list, so the stable prefix is reused
    across loop iterations instead of being re-billed every call.
    """
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            kwargs: dict = {"model": model, "messages": messages, "max_tokens": max_tokens}
            if system is not None:
                kwargs["system"] = (
                    [{"type": "text", "text": system,
                      "cache_control": {"type": "ephemeral"}}]
                    if cache else system
                )
            if tools is not None:
                if cache and tools:
                    tools = [dict(t) for t in tools]
                    tools[-1] = {**tools[-1], "cache_control": {"type": "ephemeral"}}
                kwargs["tools"] = tools
            if on_text:
                with client.messages.stream(**kwargs) as stream:
                    for delta in stream.text_stream:
                        on_text(delta)
                    return stream.get_final_message()
            return client.messages.create(**kwargs)
        except _RETRYABLE as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    assert last_err is not None
    raise last_err
