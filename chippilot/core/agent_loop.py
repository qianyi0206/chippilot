"""Core agent loop: s01 pattern with s06 compression, s08 bg drain, s09 inbox check."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Callable

from chippilot.config import TOKEN_THRESHOLD
from chippilot.core.llm import call_llm

PLAN_MODE_SUFFIX = (
    "\n\n# PLAN MODE\nYou are in read-only plan mode: investigate with the "
    "available read tools only. When you understand the task, call "
    "exit_plan_mode with a concrete step-by-step plan for the user to approve."
)

if TYPE_CHECKING:
    from anthropic import Anthropic
    from chippilot.core.tool_registry import ToolRegistry
    from chippilot.core.todos import TodoManager
    from chippilot.core.compression import estimate_tokens, microcompact, auto_compact
    from chippilot.core.background import BackgroundManager
    from chippilot.core.messaging import MessageBus


def agent_loop(
    messages: list,
    *,
    client: "Anthropic",
    model: str,
    system_prompt: str,
    registry: "ToolRegistry",
    bg_manager: "BackgroundManager | None" = None,
    bus: "MessageBus | None" = None,
    todo_manager: "TodoManager | None" = None,
    compression_enabled: bool = True,
    on_tool_call: Callable[[str, str], None] | None = None,
    on_text: Callable[[str], None] | None = None,
    approve: Callable[[str, dict], bool] | None = None,
) -> dict:
    """Run the agent loop until the model stops using tools.

    Returns {"streamed": bool} — True when the final response's text was
    already streamed to the user via on_text (skip re-printing it).
    API failures are retried inside call_llm; a terminal failure appends a
    graceful error message instead of crashing the REPL.
    """
    from chippilot.core.compression import estimate_tokens, microcompact, auto_compact

    rounds_without_todo = 0

    while True:
        # --- s06: compression pipeline ---
        if compression_enabled:
            microcompact(messages)
            if estimate_tokens(messages) > TOKEN_THRESHOLD:
                messages[:] = auto_compact(messages, client=client, model=model)

        # --- s08: drain background notifications ---
        if bg_manager:
            notifs = bg_manager.drain()
            if notifs:
                txt = "\n".join(
                    f"[bg:{n['task_id']}] {n['status']}: {n['result']}"
                    for n in notifs
                )
                messages.append({
                    "role": "user",
                    "content": f"<background-results>\n{txt}\n</background-results>",
                })
                messages.append({
                    "role": "assistant",
                    "content": "Noted background results.",
                })

        # --- s09: check lead inbox ---
        if bus:
            inbox = bus.read_inbox("lead")
            if inbox:
                messages.append({
                    "role": "user",
                    "content": f"<inbox>{json.dumps(inbox, indent=2)}</inbox>",
                })
                messages.append({
                    "role": "assistant",
                    "content": "Noted inbox messages.",
                })

        # --- LLM call (retry inside call_llm) ---
        system = system_prompt + PLAN_MODE_SUFFIX if registry.plan_mode else system_prompt
        try:
            response = call_llm(
                client,
                model=model,
                system=system,
                messages=messages,
                tools=registry.get_tools_for_mode(),
                on_text=on_text,
            )
        except Exception as e:
            messages.append({
                "role": "assistant",
                "content": f"[LLM call failed after retries: {e}]",
            })
            return {"streamed": False}
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return {"streamed": on_text is not None}

        # --- Tool execution ---
        results = []
        used_todo = False
        manual_compress = False

        for block in response.content:
            if block.type == "tool_use":
                if block.name == "compress":
                    manual_compress = True

                output = registry.dispatch(block.name, block.input, approve=approve)

                if on_tool_call:
                    on_tool_call(block.name, output)

                results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(output),
                })

                if block.name == "TodoWrite":
                    used_todo = True

        # --- s03: nag reminder ---
        if todo_manager:
            rounds_without_todo = 0 if used_todo else rounds_without_todo + 1
            if todo_manager.has_open_items() and rounds_without_todo >= 3:
                results.insert(0, {
                    "type": "text",
                    "text": "<reminder>Update your todos.</reminder>",
                })

        messages.append({"role": "user", "content": results})

        # --- s06: manual compress ---
        if manual_compress and compression_enabled:
            messages[:] = auto_compact(messages, client=client, model=model)
