"""MCP server: expose ChipPilot domain tools over stdio.

Uses the low-level mcp.server.Server API so the registry's JSON schemas are
served verbatim — one source of truth for tool definitions. Harness tools
(todos, tasks, teams, subagents) stay internal to the agent; only domain
tools (base/git/LSF/Jira/EDA/storage/monitoring/release) are exposed.

Run:  python -m chippilot.mcp_server   (or `chippilot-mcp`)
Requires: pip install chippilot[mcp]
"""

from __future__ import annotations

import asyncio

from chippilot.core.safety import PermissionEngine
from chippilot.core.tool_registry import ToolRegistry
from chippilot.tools import register_domain_tools


def build_registry() -> ToolRegistry:
    registry = ToolRegistry(permission_engine=PermissionEngine())
    register_domain_tools(registry)
    return registry


def create_server(registry: ToolRegistry | None = None):
    from mcp.server import Server
    from mcp import types

    registry = registry or build_registry()
    server = Server("chippilot")

    @server.list_tools()
    async def list_tools() -> list:
        return [
            types.Tool(
                name=t["name"],
                description=t.get("description", ""),
                inputSchema=t["input_schema"],
            )
            for t in registry.get_tools()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict | None) -> list:
        output = await asyncio.to_thread(registry.dispatch, name, arguments or {})
        return [types.TextContent(type="text", text=output)]

    return server


async def _serve():
    from mcp.server.stdio import stdio_server

    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


def main():
    try:
        import mcp  # noqa: F401
    except ImportError:
        raise SystemExit("MCP support requires: pip install chippilot[mcp]")
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
