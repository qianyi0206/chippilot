"""Subagent: spawn isolated child agents for exploration/work (s04)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from chippilot.core.llm import call_llm

if TYPE_CHECKING:
    from anthropic import Anthropic
    from chippilot.core.tool_registry import ToolRegistry


def make_subagent_runner(client: "Anthropic", model: str, registry: "ToolRegistry | None" = None):
    """Return a callable that runs a subagent with the given client/model.

    When a registry is provided, the subagent's tools come from
    registry.get_tools_for(DOMAIN_CATEGORIES) — a single source of truth for
    schemas and dispatch. Explore agents get readonly tools only;
    general-purpose agents get the full domain toolset. Without a registry,
    falls back to the original hardcoded bash/read/write/edit set.
    """

    def run_subagent(prompt: str, agent_type: str = "Explore") -> str:
        if registry is not None:
            from chippilot.tools import DOMAIN_CATEGORIES
            sub_tools = registry.get_tools_for(
                DOMAIN_CATEGORIES, readonly=(agent_type == "Explore")
            )

            def _dispatch(name: str, inputs: dict) -> str:
                return registry.dispatch(name, inputs)
        else:
            from chippilot.tools.base import run_bash, run_read, run_write, run_edit
            sub_tools = [
                {"name": "bash", "description": "Run command.",
                 "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
                {"name": "read_file", "description": "Read file.",
                 "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
            ]
            if agent_type != "Explore":
                sub_tools += [
                    {"name": "write_file", "description": "Write file.",
                     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
                    {"name": "edit_file", "description": "Edit file.",
                     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
                ]
            sub_handlers = {
                "bash": lambda **kw: run_bash(kw["command"]),
                "read_file": lambda **kw: run_read(kw["path"]),
                "write_file": lambda **kw: run_write(kw["path"], kw["content"]),
                "edit_file": lambda **kw: run_edit(kw["path"], kw["old_text"], kw["new_text"]),
            }

            def _dispatch(name: str, inputs: dict) -> str:
                return sub_handlers.get(name, lambda **kw: "Unknown tool")(**inputs)

        sub_msgs = [{"role": "user", "content": prompt}]
        resp = None
        for _ in range(30):
            try:
                resp = call_llm(
                    client, model=model, messages=sub_msgs, tools=sub_tools,
                )
            except Exception as e:
                return f"(subagent error: {e})"
            sub_msgs.append({"role": "assistant", "content": resp.content})
            if resp.stop_reason != "tool_use":
                break
            results = []
            for b in resp.content:
                if b.type == "tool_use":
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": b.id,
                        "content": str(_dispatch(b.name, b.input))[:50000],
                    })
            sub_msgs.append({"role": "user", "content": results})

        if resp:
            return "".join(b.text for b in resp.content if hasattr(b, "text")) or "(no summary)"
        return "(subagent failed)"

    return run_subagent
