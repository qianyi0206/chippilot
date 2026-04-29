"""Core agent loop: s01 pattern with s06 compression, s08 bg drain, s09 inbox check."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from chippilot.config import TOKEN_THRESHOLD

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
    on_tool_call: callable | None = None,
):
    """Run the agent loop until the model stops using tools.

    Parameters mirror s_full.py but use dependency injection instead of globals.
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

        # --- LLM call ---
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=messages,
            tools=registry.get_tools(),
            max_tokens=8000,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return

        # --- Tool execution ---
        results = []
        used_todo = False
        manual_compress = False

        for block in response.content:
            if block.type == "tool_use":
                if block.name == "compress":
                    manual_compress = True

                output = registry.dispatch(block.name, block.input)

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
