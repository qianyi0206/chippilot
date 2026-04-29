"""Jira tools: mock create/search/get/transition/comment (5 tools)."""

from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING

from chippilot.config import MOCK_DATA_DIR

if TYPE_CHECKING:
    from chippilot.core.tool_registry import ToolRegistry

_mock_issues: list[dict] | None = None
_next_id = 1300
_jira_lock = __import__("threading").Lock()


def _load():
    global _mock_issues
    if _mock_issues is not None:
        return
    path = MOCK_DATA_DIR / "jira" / "issues.json"
    if path.exists():
        _mock_issues = json.loads(path.read_text()).get("issues", [])
    else:
        _mock_issues = []


def jira_create(**kw) -> str:
    _load()
    global _next_id
    summary = kw.get("summary", "")
    if not summary:
        return "Error: summary required"
    priority = kw.get("priority", "Medium")
    project = kw.get("project", "CAD")

    # Enforce CAD required fields
    missing = []
    if not kw.get("lsf_jobid") and project == "CAD":
        missing.append("lsf_jobid (recommended for CAD issues)")
    if not kw.get("log_path") and project == "CAD":
        missing.append("log_path (recommended for CAD issues)")

    with _jira_lock:
        key = f"{project}-{_next_id}"
        _next_id += 1
    issue = {
        "key": key,
        "summary": summary,
        "status": "Open",
        "priority": priority,
        "assignee": kw.get("assignee"),
        "reporter": "current_user",
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "lsf_jobid": kw.get("lsf_jobid"),
        "log_path": kw.get("log_path"),
        "reproduce_steps": kw.get("reproduce_steps"),
    }
    _mock_issues.append(issue)
    warning = ""
    if missing:
        warning = f"\nWarning: Missing recommended fields: {', '.join(missing)}"
    return f"Created {key}: {summary}{warning}"


def jira_search(**kw) -> str:
    _load()
    query = kw.get("query", "").lower()
    status = kw.get("status")
    assignee = kw.get("assignee")

    results = _mock_issues
    if status:
        results = [i for i in results if i.get("status", "").lower() == status.lower()]
    if assignee:
        results = [i for i in results if i.get("assignee") == assignee]
    if query:
        results = [i for i in results if query in i.get("summary", "").lower() or query in i.get("key", "").lower()]

    if not results:
        return "No matching issues."
    lines = [f"{'KEY':<12} {'STATUS':<14} {'PRIORITY':<10} {'ASSIGNEE':<12} SUMMARY"]
    for i in results:
        lines.append(
            f"{i['key']:<12} {i.get('status',''):<14} {i.get('priority',''):<10} "
            f"{i.get('assignee') or '-':<12} {i.get('summary','')[:50]}"
        )
    return "\n".join(lines)


def jira_get(**kw) -> str:
    _load()
    key = kw.get("key", "")
    issue = next((i for i in _mock_issues if i.get("key") == key), None)
    if not issue:
        return f"Issue {key} not found"
    return json.dumps(issue, indent=2, ensure_ascii=False)


def jira_transition(**kw) -> str:
    _load()
    key = kw.get("key", "")
    new_status = kw.get("status", "")
    valid = ["Open", "In Progress", "In Review", "Done", "Closed", "To Do"]
    if new_status not in valid:
        return f"Error: Invalid status. Valid: {', '.join(valid)}"
    issue = next((i for i in _mock_issues if i.get("key") == key), None)
    if not issue:
        return f"Issue {key} not found"
    old = issue["status"]
    issue["status"] = new_status
    return f"{key}: {old} -> {new_status}"


def jira_comment(**kw) -> str:
    _load()
    key = kw.get("key", "")
    body = kw.get("body", "")
    issue = next((i for i in _mock_issues if i.get("key") == key), None)
    if not issue:
        return f"Issue {key} not found"
    comments = issue.setdefault("comments", [])
    comments.append({"author": "current_user", "body": body, "created": time.strftime("%Y-%m-%dT%H:%M:%S")})
    return f"Comment added to {key}"


def jira_recent_issues() -> str:
    """Convenience for /jira slash command."""
    _load()
    return jira_search()


def register_jira_tools(registry: "ToolRegistry"):
    registry.register("jira_create", jira_create, {
        "description": "Create a Jira issue (mock). CAD project requires lsf_jobid and log_path.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "priority": {"type": "string", "enum": ["Critical", "High", "Medium", "Low"]},
                "project": {"type": "string"},
                "assignee": {"type": "string"},
                "lsf_jobid": {"type": "integer", "description": "Related LSF job ID"},
                "log_path": {"type": "string", "description": "Path to relevant log file"},
                "reproduce_steps": {"type": "string"},
            },
            "required": ["summary"],
        },
    }, category="jira")

    registry.register("jira_search", jira_search, {
        "description": "Search Jira issues (mock).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "status": {"type": "string"},
                "assignee": {"type": "string"},
            },
        },
    }, category="jira")

    registry.register("jira_get", jira_get, {
        "description": "Get Jira issue details (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"key": {"type": "string"}},
            "required": ["key"],
        },
    }, category="jira")

    registry.register("jira_transition", jira_transition, {
        "description": "Transition a Jira issue to new status (mock).",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "status": {"type": "string", "enum": ["Open", "In Progress", "In Review", "Done", "Closed", "To Do"]},
            },
            "required": ["key", "status"],
        },
    }, category="jira")

    registry.register("jira_comment", jira_comment, {
        "description": "Add a comment to a Jira issue (mock).",
        "input_schema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["key", "body"],
        },
    }, category="jira")
