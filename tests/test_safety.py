"""PermissionEngine rule evaluation."""

import json

from chippilot.core.safety import PermissionEngine, DEFAULT_RULES


def test_default_rules_deny_dangerous_bash():
    e = PermissionEngine(rules=list(DEFAULT_RULES))
    assert e.check("bash", {"command": "sudo rm -rf /"}) == "deny"
    assert e.check("bash", {"command": "ls -la"}) == "allow"


def test_first_matching_rule_wins():
    e = PermissionEngine(rules=[
        {"tool": "bash", "pattern": "ls", "action": "allow"},
        {"tool": "bash", "pattern": "ls", "action": "deny"},
    ])
    assert e.check("bash", {"command": "ls"}) == "allow"


def test_wildcard_tool_and_missing_pattern():
    e = PermissionEngine(rules=[
        {"tool": "*", "pattern": "prod", "action": "ask"},
        {"tool": "bash", "action": "deny"},
    ])
    assert e.check("git_commit", {"message": "prod release"}) == "ask"
    assert e.check("bash", {"command": "anything"}) == "deny"
    assert e.check("read_file", {"path": "x"}) == "allow"


def test_loads_rules_from_file(tmp_path):
    p = tmp_path / "permissions.json"
    p.write_text(json.dumps({"rules": [{"tool": "bash", "pattern": "x", "action": "deny"}]}))
    e = PermissionEngine(rules_path=p)
    assert e.check("bash", {"command": "x"}) == "deny"


def test_invalid_action_rejected():
    import pytest
    with pytest.raises(ValueError):
        PermissionEngine(rules=[{"tool": "bash", "action": "maybe"}])
