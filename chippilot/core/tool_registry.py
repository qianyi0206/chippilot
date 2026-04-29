"""ToolRegistry: pluggable tool registration, schema serving, and dispatch."""

from __future__ import annotations

from typing import Any, Callable


class ToolRegistry:
    """Central registry for all agent tools.

    Each tool module calls registry.register() to plug itself in.
    The agent loop uses get_tools() for the LLM API and dispatch() for execution.
    """

    def __init__(self):
        self._handlers: dict[str, Callable[..., str]] = {}
        self._schemas: dict[str, dict] = {}
        self._categories: dict[str, str] = {}  # name -> category

    def register(
        self,
        name: str,
        handler: Callable[..., str],
        schema: dict,
        category: str = "general",
    ):
        """Register a tool with its handler, JSON schema, and category."""
        self._handlers[name] = handler
        self._schemas[name] = {
            "name": name,
            "description": schema.get("description", name),
            "input_schema": schema["input_schema"],
        }
        self._categories[name] = category

    def get_tools(self) -> list[dict]:
        """Return the tools array for the LLM API."""
        return list(self._schemas.values())

    def get_tools_for(self, categories: set[str] | list[str]) -> list[dict]:
        """Return tools filtered by category (for subagents)."""
        cats = set(categories)
        return [
            self._schemas[name]
            for name, cat in self._categories.items()
            if cat in cats
        ]

    def dispatch(self, tool_name: str, tool_input: dict) -> str:
        """Route a tool call, catching exceptions."""
        handler = self._handlers.get(tool_name)
        if not handler:
            return f"Unknown tool: {tool_name}"
        try:
            result = handler(**tool_input)
            return str(result)
        except Exception as e:
            return f"Error: {e}"

    def has(self, name: str) -> bool:
        return name in self._handlers

    @property
    def tool_names(self) -> list[str]:
        return list(self._handlers.keys())
