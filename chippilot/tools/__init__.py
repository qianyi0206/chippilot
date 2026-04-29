"""Tool registration entry point."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chippilot.core.tool_registry import ToolRegistry


def register_all_tools(registry: "ToolRegistry", **managers):
    """Register all tools into the given registry.

    managers may include: todo_manager, task_manager, bg_manager, bus,
    team_manager, skill_loader, knowledge_loader, worktree_manager, etc.
    """
    from chippilot.tools.base import register_base_tools
    register_base_tools(registry)

    from chippilot.tools.git_tools import register_git_tools
    register_git_tools(registry)

    from chippilot.tools.lsf_tools import register_lsf_tools
    register_lsf_tools(registry)

    from chippilot.tools.jira_tools import register_jira_tools
    register_jira_tools(registry)

    from chippilot.tools.eda_tools import register_eda_tools
    register_eda_tools(registry)

    from chippilot.tools.storage_tools import register_storage_tools
    register_storage_tools(registry)

    from chippilot.tools.monitoring_tools import register_monitoring_tools
    register_monitoring_tools(registry)

    from chippilot.tools.release_tools import register_release_tools
    register_release_tools(registry)

    # Core harness tools (from managers)
    _register_harness_tools(registry, **managers)


def _register_harness_tools(registry: "ToolRegistry", **mgrs):
    """Register all harness mechanism tools (s03-s12)."""
    todo = mgrs.get("todo_manager")
    if todo:
        registry.register("TodoWrite", lambda **kw: todo.update(kw["items"]), {
            "description": "Update task tracking list.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {"type": "string"},
                                "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                                "activeForm": {"type": "string"},
                            },
                            "required": ["content", "status", "activeForm"],
                        },
                    },
                },
                "required": ["items"],
            },
        }, category="harness")

    subagent_runner = mgrs.get("subagent_runner")
    if subagent_runner:
        registry.register("task", lambda **kw: subagent_runner(kw["prompt"], kw.get("agent_type", "Explore")), {
            "description": "Spawn a subagent for isolated exploration or work.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "agent_type": {"type": "string", "enum": ["Explore", "general-purpose"]},
                },
                "required": ["prompt"],
            },
        }, category="harness")

    skill_loader = mgrs.get("skill_loader")
    if skill_loader:
        registry.register("load_skill", lambda **kw: skill_loader.load(kw["name"]), {
            "description": "Load specialized knowledge by name.",
            "input_schema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
        }, category="harness")

    knowledge_loader = mgrs.get("knowledge_loader")
    if knowledge_loader:
        registry.register("load_knowledge", lambda **kw: knowledge_loader.load(kw["topic"], kw.get("doc_name")), {
            "description": "Load domain knowledge document by topic/name from the cad/ knowledge base.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Category: eda, lsf, git, storage, monitoring, scripts, workflow"},
                    "doc_name": {"type": "string", "description": "Specific document filename (optional)"},
                },
                "required": ["topic"],
            },
        }, category="knowledge")

    registry.register("compress", lambda **kw: "Compressing...", {
        "description": "Manually compress conversation context.",
        "input_schema": {"type": "object", "properties": {}},
    }, category="harness")

    bg = mgrs.get("bg_manager")
    if bg:
        registry.register("background_run", lambda **kw: bg.run(kw["command"], kw.get("timeout", 120)), {
            "description": "Run command in background thread.",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}, "timeout": {"type": "integer"}},
                "required": ["command"],
            },
        }, category="harness")
        registry.register("check_background", lambda **kw: bg.check(kw.get("task_id")), {
            "description": "Check background task status.",
            "input_schema": {
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
            },
        }, category="harness")

    task_mgr = mgrs.get("task_manager")
    if task_mgr:
        registry.register("task_create", lambda **kw: task_mgr.create(kw["subject"], kw.get("description", "")), {
            "description": "Create a persistent file task.",
            "input_schema": {
                "type": "object",
                "properties": {"subject": {"type": "string"}, "description": {"type": "string"}},
                "required": ["subject"],
            },
        }, category="harness")
        registry.register("task_get", lambda **kw: task_mgr.get(kw["task_id"]), {
            "description": "Get task details by ID.",
            "input_schema": {
                "type": "object",
                "properties": {"task_id": {"type": "integer"}},
                "required": ["task_id"],
            },
        }, category="harness")
        registry.register("task_update", lambda **kw: task_mgr.update(
            kw["task_id"], kw.get("status"), kw.get("add_blocked_by"), kw.get("add_blocks")
        ), {
            "description": "Update task status or dependencies.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "deleted"]},
                    "add_blocked_by": {"type": "array", "items": {"type": "integer"}},
                    "add_blocks": {"type": "array", "items": {"type": "integer"}},
                },
                "required": ["task_id"],
            },
        }, category="harness")
        registry.register("task_list", lambda **kw: task_mgr.list_all(), {
            "description": "List all tasks.",
            "input_schema": {"type": "object", "properties": {}},
        }, category="harness")
        registry.register("claim_task", lambda **kw: task_mgr.claim(kw["task_id"], "lead"), {
            "description": "Claim a task from the board.",
            "input_schema": {
                "type": "object",
                "properties": {"task_id": {"type": "integer"}},
                "required": ["task_id"],
            },
        }, category="harness")

    bus = mgrs.get("bus")
    team = mgrs.get("team_manager")
    if bus:
        registry.register("send_message", lambda **kw: bus.send("lead", kw["to"], kw["content"], kw.get("msg_type", "message")), {
            "description": "Send a message to a teammate.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "content": {"type": "string"},
                    "msg_type": {"type": "string"},
                },
                "required": ["to", "content"],
            },
        }, category="harness")
        registry.register("read_inbox", lambda **kw: __import__("json").dumps(bus.read_inbox("lead"), indent=2), {
            "description": "Read and drain the lead's inbox.",
            "input_schema": {"type": "object", "properties": {}},
        }, category="harness")

    if bus and team:
        registry.register("broadcast", lambda **kw: bus.broadcast("lead", kw["content"], team.member_names()), {
            "description": "Send message to all teammates.",
            "input_schema": {
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
            },
        }, category="harness")
        registry.register("spawn_teammate", lambda **kw: team.spawn(kw["name"], kw["role"], kw["prompt"]), {
            "description": "Spawn a persistent autonomous teammate.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "prompt": {"type": "string"},
                },
                "required": ["name", "role", "prompt"],
            },
        }, category="harness")
        registry.register("list_teammates", lambda **kw: team.list_all(), {
            "description": "List all teammates.",
            "input_schema": {"type": "object", "properties": {}},
        }, category="harness")

    shutdown_handler = mgrs.get("shutdown_handler")
    if shutdown_handler:
        registry.register("shutdown_request", lambda **kw: shutdown_handler(kw["teammate"]), {
            "description": "Request a teammate to shut down.",
            "input_schema": {
                "type": "object",
                "properties": {"teammate": {"type": "string"}},
                "required": ["teammate"],
            },
        }, category="harness")

    plan_handler = mgrs.get("plan_handler")
    if plan_handler:
        registry.register("plan_approval", lambda **kw: plan_handler(kw["request_id"], kw["approve"], kw.get("feedback", "")), {
            "description": "Approve or reject a teammate's plan.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "request_id": {"type": "string"},
                    "approve": {"type": "boolean"},
                    "feedback": {"type": "string"},
                },
                "required": ["request_id", "approve"],
            },
        }, category="harness")

    registry.register("idle", lambda **kw: "Lead does not idle.", {
        "description": "Enter idle state.",
        "input_schema": {"type": "object", "properties": {}},
    }, category="harness")
