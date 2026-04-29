"""Monitoring tools: mock job_monitor/check_rd_hosts/Grafana (3 tools)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from chippilot.config import MOCK_DATA_DIR

if TYPE_CHECKING:
    from chippilot.core.tool_registry import ToolRegistry


def _load_hosts() -> list[dict]:
    path = MOCK_DATA_DIR / "lsf" / "hosts.json"
    if path.exists():
        return json.loads(path.read_text()).get("hosts", [])
    return []


def monitor_jobs(**kw) -> str:
    """Overview of job execution health (mock)."""
    return (
        "Job Monitor Dashboard:\n"
        "=====================\n"
        "  Active jobs:     791\n"
        "  Pending jobs:    253\n"
        "  Suspended:        21\n"
        "  Failed (24h):     12\n"
        "  Avg wait time:   4.2 min\n"
        "  Avg runtime:     2.1 hours\n"
        "\n"
        "Alerts:\n"
        "  [WARN] Queue 'short' pending ratio at 11.6%\n"
        "  [WARN] sim-node-023 memory usage at 95%\n"
        "  [OK]   All other metrics within normal range"
    )


def monitor_hosts(**kw) -> str:
    """Check compute host status (mock)."""
    hosts = _load_hosts()
    name = kw.get("name")
    if name:
        hosts = [h for h in hosts if name in h["name"]]
    if not hosts:
        return "No matching hosts."
    lines = [f"{'HOST':<18} {'STATUS':<8} {'CPUS':<6} {'MEM USED':<12} {'LOAD':<8} {'JOBS'}"]
    for h in hosts:
        lines.append(
            f"{h['name']:<18} {h['status']:<8} {h['cpus']:<6} "
            f"{h['used_mem']:<12} {h['load']:<8.2f} {h['running_jobs']}"
        )
    return "\n".join(lines)


def monitor_grafana(**kw) -> str:
    """Get Grafana dashboard link/summary (mock)."""
    dashboard = kw.get("dashboard", "lsf-overview")
    return (
        f"Grafana Dashboard: {dashboard}\n"
        f"URL: https://grafana.internal/d/{dashboard}\n"
        f"\n"
        f"Quick stats (last 1h):\n"
        f"  CPU utilization:  72%\n"
        f"  Memory pressure:  65%\n"
        f"  Network I/O:      3.2 GB/s\n"
        f"  Storage IOPS:     45K"
    )


def register_monitoring_tools(registry: "ToolRegistry"):
    registry.register("monitor_jobs", monitor_jobs, {
        "description": "Show job execution health dashboard (mock).",
        "input_schema": {"type": "object", "properties": {}},
    }, category="monitoring")

    registry.register("monitor_hosts", monitor_hosts, {
        "description": "Check compute host status and resources (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string", "description": "Filter by hostname substring"}},
        },
    }, category="monitoring")

    registry.register("monitor_grafana", monitor_grafana, {
        "description": "Get Grafana monitoring dashboard info (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"dashboard": {"type": "string"}},
        },
    }, category="monitoring")
