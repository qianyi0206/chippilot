"""REPL loop, slash commands, and Rich output formatting."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from chippilot.config import PROJECT_NAME, MODEL

if TYPE_CHECKING:
    from chippilot.core.tool_registry import ToolRegistry
    from chippilot.core.todos import TodoManager
    from chippilot.core.tasks import TaskManager
    from chippilot.core.background import BackgroundManager
    from chippilot.core.messaging import MessageBus
    from chippilot.core.teams import TeammateManager
    from chippilot.knowledge.indexer import KnowledgeIndexer

console = Console()

BANNER = f"""\
[bold cyan]ChipPilot[/] - EDA/CAD AI Agent
[dim]Project: {PROJECT_NAME} | Model: {MODEL} | Mock: LSF/Jira/EDA[/dim]
[dim]Type /help for commands, q to quit[/dim]
"""


def print_banner():
    console.print(Panel(BANNER, border_style="cyan"))


def print_tool_call(name: str, output: str):
    truncated = output[:200] + ("..." if len(output) > 200 else "")
    console.print(f"  [dim]> {name}:[/] {truncated}")


def print_assistant_text(text: str):
    try:
        console.print(Markdown(text))
    except Exception:
        console.print(text)


def handle_slash_command(
    cmd: str,
    *,
    history: list,
    task_manager: "TaskManager | None" = None,
    team_manager: "TeammateManager | None" = None,
    bus: "MessageBus | None" = None,
    bg_manager: "BackgroundManager | None" = None,
    knowledge_indexer: "KnowledgeIndexer | None" = None,
    compact_fn: callable | None = None,
    lsf_jobs_fn: callable | None = None,
    lsf_queues_fn: callable | None = None,
    storage_fn: callable | None = None,
    eda_tools_fn: callable | None = None,
    jira_fn: callable | None = None,
) -> bool:
    """Handle a slash command. Returns True if handled, False otherwise."""
    cmd = cmd.strip()

    if cmd == "/help":
        _print_help()
        return True

    if cmd == "/compact":
        if compact_fn and history:
            console.print("[yellow]Compressing context...[/]")
            compact_fn(history)
        else:
            console.print("[dim]Nothing to compact.[/]")
        return True

    if cmd == "/tasks":
        if task_manager:
            console.print(task_manager.list_all())
        else:
            console.print("[dim]Task system not available.[/]")
        return True

    if cmd == "/team":
        if team_manager:
            console.print(team_manager.list_all())
        else:
            console.print("[dim]Team system not available.[/]")
        return True

    if cmd == "/inbox":
        if bus:
            msgs = bus.read_inbox("lead")
            if msgs:
                console.print(json.dumps(msgs, indent=2, ensure_ascii=False))
            else:
                console.print("[dim]Inbox empty.[/]")
        return True

    if cmd == "/jobs":
        if lsf_jobs_fn:
            console.print(lsf_jobs_fn())
        else:
            console.print("[dim]LSF system not available.[/]")
        return True

    if cmd == "/queues":
        if lsf_queues_fn:
            console.print(lsf_queues_fn())
        else:
            console.print("[dim]LSF system not available.[/]")
        return True

    if cmd == "/storage":
        if storage_fn:
            console.print(storage_fn())
        else:
            console.print("[dim]Storage system not available.[/]")
        return True

    if cmd == "/tools":
        if eda_tools_fn:
            console.print(eda_tools_fn())
        else:
            console.print("[dim]EDA system not available.[/]")
        return True

    if cmd == "/jira":
        if jira_fn:
            console.print(jira_fn())
        else:
            console.print("[dim]Jira system not available.[/]")
        return True

    if cmd == "/knowledge":
        if knowledge_indexer:
            console.print(knowledge_indexer.summary())
        else:
            console.print("[dim]Knowledge system not available.[/]")
        return True

    return False


def _print_help():
    table = Table(title="ChipPilot Commands", border_style="cyan")
    table.add_column("Command", style="bold")
    table.add_column("Description")
    table.add_row("/compact", "Compress conversation context")
    table.add_row("/tasks", "Show task board")
    table.add_row("/team", "Show teammate status")
    table.add_row("/inbox", "Read inbox messages")
    table.add_row("/jobs", "LSF job status")
    table.add_row("/queues", "Queue resource utilization")
    table.add_row("/storage", "Storage quota overview")
    table.add_row("/tools", "EDA tool versions")
    table.add_row("/jira", "Recent Jira issues")
    table.add_row("/knowledge", "Knowledge base directory")
    table.add_row("/help", "Show this help")
    table.add_row("q / exit", "Quit")
    console.print(table)
