"""Entry point: argument parsing + REPL startup."""

from __future__ import annotations

import sys

# Force UTF-8 on stdin/stdout so Chinese input works in all terminals
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from chippilot.config import MODEL
from chippilot.core.client import create_client
from chippilot.core.tool_registry import ToolRegistry
from chippilot.core.agent_loop import agent_loop
from chippilot.core.todos import TodoManager
from chippilot.core.tasks import TaskManager
from chippilot.core.background import BackgroundManager
from chippilot.core.messaging import MessageBus
from chippilot.core.teams import TeammateManager
from chippilot.core.skills import SkillLoader
from chippilot.core.subagent import make_subagent_runner
from chippilot.core.compression import auto_compact
from chippilot.core.protocols import make_shutdown_handler, make_plan_handler
from chippilot.core.safety import PermissionEngine
from chippilot.core.worktrees import WorktreeManager
from chippilot.knowledge.indexer import KnowledgeIndexer
from chippilot.knowledge.loader import KnowledgeLoader
from chippilot.prompts.system import build_system_prompt
from chippilot.tools import register_all_tools
from chippilot.cli import (
    console, print_banner, print_tool_call, print_assistant_text,
    stream_text, confirm_tool_call,
    handle_slash_command,
)


def main():
    client = create_client()

    # --- Registry first: teammates/subagents share its schemas + dispatch ---
    permission_engine = PermissionEngine()
    registry = ToolRegistry(permission_engine=permission_engine)

    # --- Initialize all managers ---
    todo = TodoManager()
    task_mgr = TaskManager()
    bg = BackgroundManager()
    bus = MessageBus()
    worktree_mgr = WorktreeManager()
    team = TeammateManager(bus, task_mgr, client, registry=registry, worktree_mgr=worktree_mgr)
    skill_loader = SkillLoader()
    knowledge_indexer = KnowledgeIndexer()
    knowledge_loader = KnowledgeLoader(knowledge_indexer)
    subagent_runner = make_subagent_runner(client, MODEL, registry)
    shutdown_handler = make_shutdown_handler(bus)
    plan_handler = make_plan_handler(bus)

    # --- Populate registry ---
    register_all_tools(
        registry,
        todo_manager=todo,
        task_manager=task_mgr,
        bg_manager=bg,
        bus=bus,
        team_manager=team,
        skill_loader=skill_loader,
        knowledge_loader=knowledge_loader,
        subagent_runner=subagent_runner,
        shutdown_handler=shutdown_handler,
        plan_handler=plan_handler,
        worktree_manager=worktree_mgr,
    )

    # --- System prompt ---
    system_prompt = build_system_prompt(
        skill_loader=skill_loader,
        knowledge_indexer=knowledge_indexer,
    )

    # --- Import slash-command data functions ---
    from chippilot.tools.lsf_tools import lsf_bjobs_all, lsf_bqueues_all
    from chippilot.tools.storage_tools import storage_quota_all
    from chippilot.tools.eda_tools import eda_tool_versions
    from chippilot.tools.jira_tools import jira_recent_issues

    # --- REPL ---
    print_banner()
    history: list[dict] = []

    def compact_fn(msgs):
        msgs[:] = auto_compact(msgs, client=client, model=MODEL)

    while True:
        try:
            query = console.input("[bold cyan]chippilot >>[/] ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/]")
            break

        query = query.strip()
        if query.lower() in ("q", "exit", ""):
            if query.lower() in ("q", "exit"):
                console.print("[dim]Goodbye.[/]")
            break

        if query.startswith("/"):
            handled = handle_slash_command(
                query,
                history=history,
                task_manager=task_mgr,
                team_manager=team,
                bus=bus,
                bg_manager=bg,
                knowledge_indexer=knowledge_indexer,
                compact_fn=compact_fn,
                lsf_jobs_fn=lsf_bjobs_all,
                lsf_queues_fn=lsf_bqueues_all,
                storage_fn=storage_quota_all,
                eda_tools_fn=eda_tool_versions,
                jira_fn=jira_recent_issues,
            )
            if handled:
                continue
            console.print(f"[red]Unknown command: {query}[/]")
            continue

        history.append({"role": "user", "content": query})

        result = agent_loop(
            history,
            client=client,
            model=MODEL,
            system_prompt=system_prompt,
            registry=registry,
            bg_manager=bg,
            bus=bus,
            todo_manager=todo,
            on_tool_call=print_tool_call,
            on_text=stream_text,
            approve=confirm_tool_call,
        )

        # Print assistant response unless it was already streamed
        if history and not result.get("streamed"):
            last = history[-1]
            if last.get("role") == "assistant":
                content = last.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if hasattr(block, "text"):
                            print_assistant_text(block.text)
                elif isinstance(content, str):
                    print_assistant_text(content)
        console.print()


if __name__ == "__main__":
    main()
