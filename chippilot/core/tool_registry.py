"""ToolRegistry: pluggable tool registration, schema serving, and dispatch."""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from chippilot.core.safety import PermissionEngine


class ToolRegistry:
    """Central registry for all agent tools.

    Each tool module calls registry.register() to plug itself in.
    The agent loop uses get_tools() for the LLM API and dispatch() for execution.
    """

    def __init__(self, permission_engine: "PermissionEngine | None" = None):
        self._handlers: dict[str, Callable[..., str]] = {}
        self._schemas: dict[str, dict] = {}
        self._categories: dict[str, str] = {}  # name -> category
        self._readonly: set[str] = set()
        self._permission_engine = permission_engine

    def register(
        self,
        name: str,
        handler: Callable[..., str],
        schema: dict,
        category: str = "general",
        readonly: bool = False,
    ):
        """Register a tool with its handler, JSON schema, and category."""
        self._handlers[name] = handler
        self._schemas[name] = {
            "name": name,
            "description": schema.get("description", name),
            "input_schema": schema["input_schema"],
        }
        self._categories[name] = category
        if readonly:
            self._readonly.add(name)

    def get_tools(self) -> list[dict]:
        """Return the tools array for the LLM API."""
        return list(self._schemas.values())

    def get_tools_for(
        self,
        categories: set[str] | list[str],
        readonly: bool | None = None,
    ) -> list[dict]:
        """Return tools filtered by category (for subagents/teammates).

        readonly=True limits to side-effect-free tools (Explore agents).
        """
        cats = set(categories)
        return [
            self._schemas[name]
            for name, cat in self._categories.items()
            if cat in cats and (readonly is None or (name in self._readonly) == readonly)
        ]

    def dispatch(
        self,
        tool_name: str,
        tool_input: dict,
        *,
        approve: Callable[[str, dict], bool] | None = None,
    ) -> str:
        """Route a tool call, enforcing permissions and catching exceptions.

        `approve` resolves 'ask' decisions interactively; without it an 'ask'
        is treated as denied (non-interactive contexts: subagents, teammates,
        MCP server).
        """
        handler = self._handlers.get(tool_name)
        if not handler:
            return f"Unknown tool: {tool_name}"
        if self._permission_engine:
            decision = self._permission_engine.check(tool_name, tool_input)
            if decision == "deny":
                return f"Permission denied: {tool_name} blocked by rules"
            if decision == "ask":
                allowed = approve(tool_name, tool_input) if approve else False
                if not allowed:
                    return f"Permission denied: {tool_name} not approved"
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
