"""PermissionEngine: rule-based allow/ask/deny checks for tool calls.

Replaces the hardcoded dangerous-command blocklist. Rules are loaded from
.chippilot/permissions.json (relative to WORKDIR) with sensible defaults.
"""

from __future__ import annotations

import json
from pathlib import Path

from chippilot.config import WORKDIR

RULES_PATH = WORKDIR / ".chippilot" / "permissions.json"

# First matching rule wins; unmatched calls are allowed.
DEFAULT_RULES: list[dict] = [
    {"tool": "bash", "pattern": "rm -rf /", "action": "deny"},
    {"tool": "bash", "pattern": "sudo", "action": "deny"},
    {"tool": "bash", "pattern": "shutdown", "action": "deny"},
    {"tool": "bash", "pattern": "reboot", "action": "deny"},
    {"tool": "bash", "pattern": "> /dev/", "action": "deny"},
    {"tool": "write_file", "pattern": ".env", "action": "ask"},
]

VALID_ACTIONS = ("allow", "ask", "deny")


class PermissionEngine:
    """Evaluate tool calls against ordered allow/ask/deny rules.

    A rule matches when its `tool` equals the tool name (or "*") and its
    `pattern` appears in any string value of the tool input. `pattern` may be
    omitted to match every call to that tool.
    """

    def __init__(self, rules: list[dict] | None = None, rules_path: Path | None = None):
        self.rules_path = rules_path or RULES_PATH
        if rules is not None:
            self.rules = list(rules)
        else:
            self.rules = self._load_rules()
        for r in self.rules:
            if r.get("action") not in VALID_ACTIONS:
                raise ValueError(f"Invalid rule action: {r}")

    def _load_rules(self) -> list[dict]:
        if self.rules_path.exists():
            try:
                data = json.loads(self.rules_path.read_text())
                return list(data.get("rules", []))
            except Exception:
                return list(DEFAULT_RULES)
        return list(DEFAULT_RULES)

    def check(self, tool_name: str, tool_input: dict) -> str:
        """Return 'allow', 'ask', or 'deny' for a tool call."""
        values = [v for v in (tool_input or {}).values() if isinstance(v, str)]
        for rule in self.rules:
            if rule.get("tool") not in (tool_name, "*"):
                continue
            pattern = rule.get("pattern")
            if pattern is None or any(pattern in v for v in values):
                return rule["action"]
        return "allow"
