"""EDA tools: mock setws/module load/tool version/run_helium/check_license (6 tools)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from chippilot.config import MOCK_DATA_DIR

if TYPE_CHECKING:
    from chippilot.core.tool_registry import ToolRegistry

_eda_data: dict | None = None
_eda_lock = __import__("threading").Lock()
_thread_local = __import__("threading").local()


def _load():
    global _eda_data
    if _eda_data is not None:
        return
    tools_path = MOCK_DATA_DIR / "eda" / "tools.json"
    modules_path = MOCK_DATA_DIR / "eda" / "modules.json"
    _eda_data = {"tools": [], "modules": [], "licenses": {}}
    if tools_path.exists():
        _eda_data["tools"] = json.loads(tools_path.read_text()).get("tools", [])
    if modules_path.exists():
        data = json.loads(modules_path.read_text())
        _eda_data["modules"] = data.get("modules", [])
        _eda_data["licenses"] = data.get("licenses", {})


def eda_setws(**kw) -> str:
    project = kw.get("project", "")
    block = kw.get("block", "")
    if not project:
        return "Error: project name required"
    _thread_local.current_ws = f"/proj/{project}/{block}" if block else f"/proj/{project}"
    return (
        f"Workspace set: {_thread_local.current_ws}\n"
        f"  Project: {project}\n"
        f"  Block:   {block or '(top-level)'}\n"
        f"  Environment variables updated."
    )


def eda_module_load(**kw) -> str:
    _load()
    name = kw.get("name", "")
    if not name:
        return "Error: module name required"
    mod = next((m for m in _eda_data["modules"] if m["name"] == name), None)
    if mod:
        mod["loaded"] = True
        return f"Module loaded: {name}"
    return f"Module not found: {name}. Use eda_module_list to see available modules."


def eda_module_list(**kw) -> str:
    _load()
    lines = [f"{'MODULE':<35} {'STATUS'}"]
    for m in _eda_data["modules"]:
        status = "loaded" if m["loaded"] else "available"
        lines.append(f"{m['name']:<35} {status}")
    return "\n".join(lines)


def eda_tool_version(**kw) -> str:
    _load()
    name = kw.get("name")
    tools = _eda_data["tools"]
    if name:
        tools = [t for t in tools if t["name"].lower() == name.lower()]
    if not tools:
        return "No matching EDA tools found."
    lines = [f"{'TOOL':<20} {'VERSION':<16} {'VENDOR':<12} PATH"]
    for t in tools:
        lines.append(f"{t['name']:<20} {t['version']:<16} {t['vendor']:<12} {t['path']}")
    return "\n".join(lines)


def eda_tool_versions() -> str:
    """Convenience for /tools slash command."""
    _load()
    return eda_tool_version()


def eda_run_helium(**kw) -> str:
    config = kw.get("config", "")
    if not config:
        return "Error: config file required"
    return (
        f"Helium run initiated (mock):\n"
        f"  Config: {config}\n"
        f"  Mode: {kw.get('mode', 'default')}\n"
        f"  Status: Submitted to LSF queue 'medium'\n"
        f"  Estimated runtime: 2-4 hours\n"
        f"  Output: /proj/crete/helium_out/{config.replace('.cfg', '')}"
    )


def eda_check_license(**kw) -> str:
    _load()
    feature = kw.get("feature")
    lics = _eda_data["licenses"]
    if feature:
        lic = lics.get(feature)
        if not lic:
            return f"Unknown license feature: {feature}"
        return f"{feature}: {lic['available']}/{lic['total']} available ({lic['in_use']} in use)"
    lines = [f"{'FEATURE':<16} {'TOTAL':<8} {'IN USE':<8} {'AVAIL':<8}"]
    for name, lic in lics.items():
        lines.append(f"{name:<16} {lic['total']:<8} {lic['in_use']:<8} {lic['available']:<8}")
    return "\n".join(lines)


def register_eda_tools(registry: "ToolRegistry"):
    registry.register("eda_setws", eda_setws, {
        "description": "Set EDA workspace (project/block) and configure environment (mock).",
        "input_schema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Project name (e.g. crete, corsica)"},
                "block": {"type": "string", "description": "Block name within project"},
            },
            "required": ["project"],
        },
    }, category="eda")

    registry.register("eda_module_load", eda_module_load, {
        "description": "Load an EDA tool module (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Module name (e.g. synopsys/vcs/2024.06-SP1)"}},
            "required": ["name"],
        },
    }, category="eda")

    registry.register("eda_module_list", eda_module_list, {
        "description": "List available EDA tool modules and their load status (mock).",
        "input_schema": {"type": "object", "properties": {}},
    }, category="eda")

    registry.register("eda_tool_version", eda_tool_version, {
        "description": "Show EDA tool versions installed (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
        },
    }, category="eda")

    registry.register("eda_run_helium", eda_run_helium, {
        "description": "Run Cadence Helium verification (mock).",
        "input_schema": {
            "type": "object",
            "properties": {
                "config": {"type": "string", "description": "Helium config file"},
                "mode": {"type": "string"},
            },
            "required": ["config"],
        },
    }, category="eda")

    registry.register("eda_check_license", eda_check_license, {
        "description": "Check EDA license availability (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"feature": {"type": "string", "description": "License feature name"}},
        },
    }, category="eda")
