"""Release tools: mock rel_csr/collect_verilog_line/ip_version (3 tools)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chippilot.core.tool_registry import ToolRegistry


def release_csr(**kw) -> str:
    """Run CSR release flow (mock)."""
    version = kw.get("version", "")
    project = kw.get("project", "crete")
    if not version:
        return "Error: version required (e.g. v1.2.3)"
    return (
        f"CSR Release initiated (mock):\n"
        f"  Project: {project}\n"
        f"  Version: {version}\n"
        f"  Steps:\n"
        f"    1. Validate all regression tests passed\n"
        f"    2. Collect release notes from Jira\n"
        f"    3. Tag release in git: {project}-{version}\n"
        f"    4. Package deliverables to /proj/{project}/release/{version}\n"
        f"    5. Update version manifest\n"
        f"  Status: Queued for execution"
    )


def release_collect_verilog(**kw) -> str:
    """Collect verilog line count for IP (mock)."""
    ip_name = kw.get("ip_name", "")
    if not ip_name:
        return "Error: ip_name required"
    return (
        f"Verilog Line Count for {ip_name}:\n"
        f"  RTL:          45,230 lines\n"
        f"  Testbench:    23,456 lines\n"
        f"  Assertions:    5,678 lines\n"
        f"  Total:        74,364 lines\n"
        f"  Files:           342\n"
        f"  Modules:          89"
    )


def release_ip_version(**kw) -> str:
    """Check/manage IP version (mock)."""
    ip_name = kw.get("ip_name", "")
    action = kw.get("action", "check")
    if not ip_name:
        return "Error: ip_name required"
    if action == "check":
        return (
            f"IP Version Info for {ip_name}:\n"
            f"  Current:  v2.3.1\n"
            f"  Previous: v2.3.0, v2.2.5, v2.2.4\n"
            f"  Status:   Released\n"
            f"  Tag:      crete-{ip_name}-v2.3.1\n"
            f"  Date:     2026-03-20"
        )
    elif action == "bump":
        bump_type = kw.get("bump_type", "patch")
        new_ver = {"major": "v3.0.0", "minor": "v2.4.0", "patch": "v2.3.2"}.get(bump_type, "v2.3.2")
        return f"IP {ip_name} version bumped: v2.3.1 -> {new_ver} ({bump_type})"
    return f"Unknown action: {action}"


def register_release_tools(registry: "ToolRegistry"):
    registry.register("release_csr", release_csr, {
        "description": "Run CSR (Customer Ship Release) flow (mock).",
        "input_schema": {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "project": {"type": "string"},
            },
            "required": ["version"],
        },
    }, category="release")

    registry.register("release_collect_verilog", release_collect_verilog, {
        "description": "Collect verilog line count for an IP block (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"ip_name": {"type": "string"}},
            "required": ["ip_name"],
        },
    }, category="release")

    registry.register("release_ip_version", release_ip_version, {
        "description": "Check or bump IP version (mock).",
        "input_schema": {
            "type": "object",
            "properties": {
                "ip_name": {"type": "string"},
                "action": {"type": "string", "enum": ["check", "bump"]},
                "bump_type": {"type": "string", "enum": ["major", "minor", "patch"]},
            },
            "required": ["ip_name"],
        },
    }, category="release")
