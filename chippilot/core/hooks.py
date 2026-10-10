"""HookEngine: user-configured shell hooks fired around tool calls.

Follows the Claude Code settings format. Hooks live in
.chippilot/settings.json (relative to WORKDIR):

{
  "hooks": {
    "PreToolUse": [
      {"matcher": "bash|write_file",
       "hooks": [{"type": "command", "command": "./scripts/check.sh"}]}
    ],
    "PostToolUse": [...]
  }
}

Each hook command receives a JSON payload on stdin:
  {"hook_event_name", "tool_name", "tool_input", "tool_output"?, "cwd"}

Exit-code semantics (same as Claude Code):
  0   -> allow; stdout becomes extra context for PostToolUse
  2   -> block (PreToolUse) with stderr as the reason
  any other non-zero -> allow, stderr surfaced as a warning to the agent
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from chippilot.config import WORKDIR

SETTINGS_PATH = WORKDIR / ".chippilot" / "settings.json"

EVENTS = ("PreToolUse", "PostToolUse")
HOOK_TIMEOUT = 30


class HookEngine:
    """Run configured shell commands before/after tool execution."""

    def __init__(self, settings_path: Path | None = None):
        self.settings_path = settings_path or SETTINGS_PATH
        # {event: [(compiled_matcher_or_None, [command, ...])]}
        self._hooks: dict[str, list[tuple[re.Pattern | None, list[str]]]] = {
            e: [] for e in EVENTS
        }
        self._load()

    def _load(self):
        if not self.settings_path.exists():
            return
        try:
            data = json.loads(self.settings_path.read_text())
        except Exception:
            return
        hooks_cfg = data.get("hooks", {})
        if not isinstance(hooks_cfg, dict):
            return
        for event in EVENTS:
            entries = hooks_cfg.get(event, [])
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                matcher = self._compile(entry.get("matcher"))
                commands = [
                    h["command"]
                    for h in entry.get("hooks", [])
                    if isinstance(h, dict)
                    and h.get("type") == "command"
                    and h.get("command")
                ]
                if entry.get("command"):  # tolerate the flat form
                    commands.append(entry["command"])
                if commands:
                    self._hooks[event].append((matcher, commands))

    @staticmethod
    def _compile(matcher) -> "re.Pattern | None":
        if not matcher or matcher in ("*", ".*"):
            return None
        try:
            return re.compile(str(matcher))
        except re.error:
            return None

    def _commands(self, event: str, tool_name: str) -> list[str]:
        out: list[str] = []
        for matcher, commands in self._hooks[event]:
            if matcher is None or matcher.search(tool_name):
                out.extend(commands)
        return out

    @staticmethod
    def _run(command: str, payload: dict) -> tuple[int, str, str]:
        try:
            proc = subprocess.run(
                command,
                shell=True,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=HOOK_TIMEOUT,
                cwd=str(WORKDIR),
            )
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except Exception as e:
            return -1, "", str(e)

    def has_hooks(self) -> bool:
        return any(self._hooks[e] for e in EVENTS)

    def pre_tool_use(self, tool_name: str, tool_input: dict) -> tuple[bool, str]:
        """Return (allowed, note). note is the block reason when denied,
        or hook warnings to surface to the agent when allowed."""
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "cwd": str(WORKDIR),
        }
        warnings: list[str] = []
        for command in self._commands("PreToolUse", tool_name):
            rc, out, err = self._run(command, payload)
            if rc == 2:
                return False, err or out or f"blocked by hook: {command}"
            if rc != 0 and err:
                warnings.append(err)
        return True, "\n".join(warnings)

    def post_tool_use(self, tool_name: str, tool_input: dict, tool_output: str) -> str:
        """Return extra feedback text to append to the tool result."""
        payload = {
            "hook_event_name": "PostToolUse",
            "tool_name": tool_name,
            "tool_input": tool_input,
            "tool_output": tool_output,
            "cwd": str(WORKDIR),
        }
        feedback: list[str] = []
        for command in self._commands("PostToolUse", tool_name):
            rc, out, err = self._run(command, payload)
            if out:
                feedback.append(out)
            elif rc != 0 and err:
                feedback.append(err)
        return "\n".join(feedback)
