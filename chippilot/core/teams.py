"""TeammateManager: spawn/idle/auto-claim persistent teammates (s09/s11)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from chippilot.config import TEAM_DIR, TASKS_DIR, WORKDIR, POLL_INTERVAL, IDLE_TIMEOUT, MODEL
from chippilot.core.llm import call_llm
from chippilot.core.compression import microcompact
from chippilot.tools.base import run_bash, run_read, run_write, run_edit

if TYPE_CHECKING:
    from anthropic import Anthropic
    from chippilot.core.messaging import MessageBus
    from chippilot.core.tasks import TaskManager
    from chippilot.core.tool_registry import ToolRegistry
    from chippilot.core.worktrees import WorktreeManager

_SPECIAL_TOOLS = ("send_message", "idle", "claim_task")
_BASE_TOOLS = ("bash", "read_file", "write_file", "edit_file")


class TeammateManager:
    def __init__(
        self,
        bus: "MessageBus",
        task_mgr: "TaskManager",
        client: "Anthropic",
        registry: "ToolRegistry | None" = None,
        worktree_mgr: "WorktreeManager | None" = None,
    ):
        TEAM_DIR.mkdir(exist_ok=True)
        self.bus = bus
        self.task_mgr = task_mgr
        self.client = client
        self.registry = registry
        self.worktree_mgr = worktree_mgr
        self.config_path = TEAM_DIR / "config.json"
        self.config = self._load_config()
        self.threads: dict[str, threading.Thread] = {}

    def _load_config(self) -> dict:
        if self.config_path.exists():
            return json.loads(self.config_path.read_text())
        return {"team_name": "default", "members": []}

    def _save(self):
        self.config_path.write_text(json.dumps(self.config, indent=2))

    def _find(self, name: str) -> dict | None:
        for m in self.config["members"]:
            if m["name"] == name:
                return m
        return None

    def spawn(self, name: str, role: str, prompt: str) -> str:
        member = self._find(name)
        if member:
            if member["status"] not in ("idle", "shutdown"):
                return f"Error: '{name}' is currently {member['status']}"
            member["status"] = "working"
            member["role"] = role
        else:
            member = {"name": name, "role": role, "status": "working"}
            self.config["members"].append(member)

        # s12: give each teammate an isolated git worktree when available.
        wt_path = None
        if self.worktree_mgr and self.worktree_mgr.git_available:
            try:
                entry = json.loads(self.worktree_mgr.create(f"tm-{name}"))
                wt_path = entry["path"]
                member["worktree"] = wt_path
            except Exception as e:
                wt_path = None
                member["worktree_error"] = str(e)
        self._save()

        t = threading.Thread(target=self._loop, args=(name, role, prompt), daemon=True)
        self.threads[name] = t
        t.start()
        suffix = f", worktree: {wt_path}" if wt_path else ""
        return f"Spawned '{name}' (role: {role}{suffix})"

    def _set_status(self, name: str, status: str):
        member = self._find(name)
        if member:
            member["status"] = status
            self._save()

    def _loop(self, name: str, role: str, prompt: str):
        team_name = self.config["team_name"]
        member = self._find(name) or {}
        wt = member.get("worktree")
        cwd = Path(wt) if wt else None
        workdir_note = f"Work in worktree {wt}." if wt else f"Work in {WORKDIR}."
        sys_prompt = (
            f"You are '{name}', role: {role}, team: {team_name}. {workdir_note} "
            f"Use idle when done with current work. You may auto-claim tasks."
        )
        messages = [{"role": "user", "content": prompt}]

        special_tools = [
            {"name": "send_message", "description": "Send message.",
             "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}}, "required": ["to", "content"]}},
            {"name": "idle", "description": "Signal no more work.",
             "input_schema": {"type": "object", "properties": {}}},
            {"name": "claim_task", "description": "Claim task by ID.",
             "input_schema": {"type": "object", "properties": {"task_id": {"type": "integer"}}, "required": ["task_id"]}},
        ]
        if self.registry is not None:
            from chippilot.tools import DOMAIN_CATEGORIES
            tools = self.registry.get_tools_for(DOMAIN_CATEGORIES) + special_tools
        else:
            tools = [
                {"name": "bash", "description": "Run command.",
                 "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
                {"name": "read_file", "description": "Read file.",
                 "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
                {"name": "write_file", "description": "Write file.",
                 "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
                {"name": "edit_file", "description": "Edit file.",
                 "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
            ] + special_tools

        def _dispatch(tool_name: str, inputs: dict) -> str:
            if tool_name == "send_message":
                return self.bus.send(name, inputs["to"], inputs["content"])
            if tool_name == "claim_task":
                return self.task_mgr.claim(inputs["task_id"], name)
            if tool_name == "idle":
                return "Entering idle phase."
            if tool_name in _BASE_TOOLS:
                base_handlers = {
                    "bash": lambda: run_bash(inputs["command"], cwd=cwd),
                    "read_file": lambda: run_read(inputs["path"], inputs.get("limit"), cwd=cwd),
                    "write_file": lambda: run_write(inputs["path"], inputs["content"], cwd=cwd),
                    "edit_file": lambda: run_edit(inputs["path"], inputs["old_text"], inputs["new_text"], cwd=cwd),
                }
                return base_handlers[tool_name]()
            if self.registry is not None:
                return self.registry.dispatch(tool_name, inputs)
            return "Unknown tool"

        while True:
            # -- WORK PHASE --
            for _ in range(50):
                microcompact(messages)
                inbox = self.bus.read_inbox(name)
                for msg in inbox:
                    if msg.get("type") == "shutdown_request":
                        self._set_status(name, "shutdown")
                        return
                    messages.append({"role": "user", "content": json.dumps(msg)})
                try:
                    response = call_llm(
                        self.client, model=MODEL, system=sys_prompt,
                        messages=messages, tools=tools,
                    )
                except Exception as e:
                    print(f"  [{name}] API error: {e}")
                    self._set_status(name, "shutdown")
                    return
                messages.append({"role": "assistant", "content": response.content})
                if response.stop_reason != "tool_use":
                    break
                results = []
                idle_requested = False
                for block in response.content:
                    if block.type == "tool_use":
                        if block.name == "idle":
                            idle_requested = True
                        output = _dispatch(block.name, block.input)
                        print(f"  [{name}] {block.name}: {str(output)[:120]}")
                        results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
                messages.append({"role": "user", "content": results})
                if idle_requested:
                    break

            # -- IDLE PHASE: poll for messages and unclaimed tasks --
            self._set_status(name, "idle")
            resume = False
            for _ in range(IDLE_TIMEOUT // max(POLL_INTERVAL, 1)):
                time.sleep(POLL_INTERVAL)
                inbox = self.bus.read_inbox(name)
                if inbox:
                    for msg in inbox:
                        if msg.get("type") == "shutdown_request":
                            self._set_status(name, "shutdown")
                            return
                        messages.append({"role": "user", "content": json.dumps(msg)})
                    resume = True
                    break
                unclaimed = []
                for f in sorted(TASKS_DIR.glob("task_*.json")):
                    t = json.loads(f.read_text())
                    if t.get("status") == "pending" and not t.get("owner") and not t.get("blockedBy"):
                        unclaimed.append(t)
                if unclaimed:
                    task = unclaimed[0]
                    self.task_mgr.claim(task["id"], name)
                    if len(messages) <= 3:
                        messages.insert(0, {"role": "user", "content":
                            f"<identity>You are '{name}', role: {role}, team: {team_name}.</identity>"})
                        messages.insert(1, {"role": "assistant", "content": f"I am {name}. Continuing."})
                    messages.append({"role": "user", "content":
                        f"<auto-claimed>Task #{task['id']}: {task['subject']}\n{task.get('description', '')}</auto-claimed>"})
                    messages.append({"role": "assistant", "content": f"Claimed task #{task['id']}. Working on it."})
                    resume = True
                    break

            if not resume:
                self._set_status(name, "shutdown")
                return
            self._set_status(name, "working")

    def list_all(self) -> str:
        if not self.config["members"]:
            return "No teammates."
        lines = [f"Team: {self.config['team_name']}"]
        for m in self.config["members"]:
            wt = f" @ {m['worktree']}" if m.get("worktree") else ""
            lines.append(f"  {m['name']} ({m['role']}): {m['status']}{wt}")
        return "\n".join(lines)

    def member_names(self) -> list:
        return [m["name"] for m in self.config["members"]]
