"""Storage tools: mock quota/disk usage/snapshot check (3 tools)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from chippilot.config import MOCK_DATA_DIR

if TYPE_CHECKING:
    from chippilot.core.tool_registry import ToolRegistry


def _load_quotas() -> list[dict]:
    path = MOCK_DATA_DIR / "storage" / "quotas.json"
    if path.exists():
        return json.loads(path.read_text()).get("quotas", [])
    return []


def _load_snapshots() -> list[dict]:
    path = MOCK_DATA_DIR / "storage" / "snapshots.json"
    if path.exists():
        return json.loads(path.read_text()).get("snapshots", [])
    return []


def storage_quota(**kw) -> str:
    path_filter = kw.get("path")
    quotas = _load_quotas()
    if path_filter:
        quotas = [q for q in quotas if path_filter in q["path"]]
    if not quotas:
        return "No matching storage quotas."
    lines = [f"{'PATH':<30} {'QUOTA':<10} {'USED':<10} {'USAGE%':<10} {'FILES':<12} STATUS"]
    for q in quotas:
        status = "WARNING" if q["usage_pct"] > 85 else "OK"
        lines.append(
            f"{q['path']:<30} {q['quota']:<10} {q['used']:<10} "
            f"{q['usage_pct']:<10.1f} {q['files']:<12} {status}"
        )
    return "\n".join(lines)


def storage_quota_all() -> str:
    """Convenience for /storage slash command."""
    return storage_quota()


def storage_disk_usage(**kw) -> str:
    path = kw.get("path", "/proj/crete/work")
    # Mock top-level directory breakdown
    return (
        f"Disk usage for {path}:\n"
        f"  regression/    18.5TB  (41%)\n"
        f"  sim/           12.3TB  (27%)\n"
        f"  synthesis/      8.2TB  (18%)\n"
        f"  sta/            4.1TB  (9%)\n"
        f"  misc/           2.1TB  (5%)\n"
        f"  Total:         45.2TB"
    )


def storage_snapshot_check(**kw) -> str:
    volume = kw.get("volume")
    snaps = _load_snapshots()
    if volume:
        snaps = [s for s in snaps if volume in s["volume"]]
    if not snaps:
        return "No snapshots found."
    lines = [f"{'VOLUME':<25} {'SNAPSHOT':<15} {'CREATED':<22} {'SIZE'}"]
    for s in snaps:
        lines.append(f"{s['volume']:<25} {s['name']:<15} {s['created']:<22} {s['size']}")
    return "\n".join(lines)


def register_storage_tools(registry: "ToolRegistry"):
    registry.register("storage_quota", storage_quota, {
        "description": "Check storage quota and usage (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Filter by path substring"}},
        },
    }, category="storage")

    registry.register("storage_disk_usage", storage_disk_usage, {
        "description": "Show disk usage breakdown for a path (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
        },
    }, category="storage")

    registry.register("storage_snapshot_check", storage_snapshot_check, {
        "description": "Check available snapshots for data recovery (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"volume": {"type": "string"}},
        },
    }, category="storage")
