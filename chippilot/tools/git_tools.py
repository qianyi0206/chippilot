"""Git tools: real git operations (9 tools)."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from chippilot.config import WORKDIR

if TYPE_CHECKING:
    from chippilot.core.tool_registry import ToolRegistry


def _git(args: list[str], cwd=None) -> str:
    try:
        r = subprocess.run(
            ["git"] + args, cwd=cwd or WORKDIR,
            capture_output=True, text=True, timeout=60,
        )
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: git command timed out"
    except Exception as e:
        return f"Error: {e}"


def git_status(**kw) -> str:
    return _git(["status", "--short", "--branch"])

def git_log(**kw) -> str:
    n = kw.get("count", 10)
    return _git(["log", f"--oneline", f"-{n}"])

def git_diff(**kw) -> str:
    args = ["diff"]
    if kw.get("staged"):
        args.append("--staged")
    if kw.get("path"):
        args.extend(["--", kw["path"]])
    return _git(args)

def git_branch(**kw) -> str:
    action = kw.get("action", "list")
    name = kw.get("name", "")
    if action == "list":
        return _git(["branch", "-a"])
    elif action == "create":
        return _git(["checkout", "-b", name])
    elif action == "switch":
        return _git(["checkout", name])
    elif action == "delete":
        return _git(["branch", "-d", name])
    return f"Unknown branch action: {action}"

def git_commit(**kw) -> str:
    message = kw.get("message", "")
    if not message:
        return "Error: commit message required"
    # Stage all if requested
    if kw.get("add_all"):
        _git(["add", "-A"])
    return _git(["commit", "-m", message])

def git_tag(**kw) -> str:
    action = kw.get("action", "list")
    name = kw.get("name", "")
    if action == "list":
        return _git(["tag", "-l"])
    elif action == "create":
        msg = kw.get("message", name)
        return _git(["tag", "-a", name, "-m", msg])
    elif action == "delete":
        return _git(["tag", "-d", name])
    return f"Unknown tag action: {action}"

def git_pr_create(**kw) -> str:
    title = kw.get("title", "")
    body = kw.get("body", "")
    target = kw.get("target_branch", "main")
    # Use git-based PR (would be gh or bb in real setup)
    return (
        f"PR created (simulated):\n"
        f"  Title: {title}\n"
        f"  Target: {target}\n"
        f"  Body: {body[:200]}\n"
        f"  Tip: In production, this calls `gh pr create` or Bitbucket API."
    )

def git_hotfix(**kw) -> str:
    branch = kw.get("branch", "")
    base = kw.get("base", "main")
    if not branch:
        return "Error: hotfix branch name required"
    result = _git(["checkout", "-b", f"hotfix/{branch}", base])
    return f"Hotfix branch created: hotfix/{branch}\n{result}"

def git_subtree_sync(**kw) -> str:
    prefix = kw.get("prefix", "")
    remote = kw.get("remote", "")
    ref = kw.get("ref", "main")
    if not prefix or not remote:
        return "Error: prefix and remote required"
    return _git(["subtree", "pull", f"--prefix={prefix}", remote, ref, "--squash"])


def register_git_tools(registry: "ToolRegistry"):
    registry.register("git_status", git_status, {
        "description": "Show git status (real).",
        "input_schema": {"type": "object", "properties": {}},
    }, category="git")

    registry.register("git_log", git_log, {
        "description": "Show git log (real).",
        "input_schema": {
            "type": "object",
            "properties": {"count": {"type": "integer", "description": "Number of commits to show"}},
        },
    }, category="git")

    registry.register("git_diff", git_diff, {
        "description": "Show git diff (real).",
        "input_schema": {
            "type": "object",
            "properties": {
                "staged": {"type": "boolean"},
                "path": {"type": "string"},
            },
        },
    }, category="git")

    registry.register("git_branch", git_branch, {
        "description": "Git branch operations: list/create/switch/delete (real).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "create", "switch", "delete"]},
                "name": {"type": "string"},
            },
        },
    }, category="git")

    registry.register("git_commit", git_commit, {
        "description": "Git commit (real).",
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string"},
                "add_all": {"type": "boolean"},
            },
            "required": ["message"],
        },
    }, category="git")

    registry.register("git_tag", git_tag, {
        "description": "Git tag operations: list/create/delete (real).",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "create", "delete"]},
                "name": {"type": "string"},
                "message": {"type": "string"},
            },
        },
    }, category="git")

    registry.register("git_pr_create", git_pr_create, {
        "description": "Create a pull request (simulated, shows command).",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body": {"type": "string"},
                "target_branch": {"type": "string"},
            },
            "required": ["title"],
        },
    }, category="git")

    registry.register("git_hotfix", git_hotfix, {
        "description": "Create a hotfix branch from base (real git).",
        "input_schema": {
            "type": "object",
            "properties": {
                "branch": {"type": "string"},
                "base": {"type": "string"},
            },
            "required": ["branch"],
        },
    }, category="git")

    registry.register("git_subtree_sync", git_subtree_sync, {
        "description": "Sync a git subtree from remote (real git).",
        "input_schema": {
            "type": "object",
            "properties": {
                "prefix": {"type": "string"},
                "remote": {"type": "string"},
                "ref": {"type": "string"},
            },
            "required": ["prefix", "remote"],
        },
    }, category="git")
