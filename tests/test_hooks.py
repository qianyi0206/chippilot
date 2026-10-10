"""HookEngine: settings loading, matcher filtering, exit-code semantics."""

import json

from chippilot.core.hooks import HookEngine
from chippilot.core.tool_registry import ToolRegistry


def _engine(tmp_path, hooks_cfg) -> HookEngine:
    p = tmp_path / "settings.json"
    p.write_text(json.dumps({"hooks": hooks_cfg}))
    return HookEngine(settings_path=p)


def test_no_settings_is_noop(tmp_path):
    e = HookEngine(settings_path=tmp_path / "missing.json")
    assert e.pre_tool_use("bash", {}) == (True, "")
    assert e.post_tool_use("bash", {}, "out") == ""


def test_malformed_settings_is_noop(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text("{ not json")
    e = HookEngine(settings_path=p)
    assert e.pre_tool_use("bash", {}) == (True, "")


def test_matcher_filters_tools(tmp_path):
    e = _engine(tmp_path, {
        "PreToolUse": [
            {"matcher": "bash|write_file",
             "hooks": [{"type": "command", "command": "echo deny >&2; exit 2"}]},
        ],
    })
    allowed, _ = e.pre_tool_use("bash", {"command": "ls"})
    assert not allowed
    assert e.pre_tool_use("read_file", {"path": "x"}) == (True, "")


def test_empty_matcher_matches_all(tmp_path):
    e = _engine(tmp_path, {
        "PreToolUse": [
            {"matcher": "", "hooks": [{"type": "command", "command": "exit 2"}]},
        ],
    })
    allowed, _ = e.pre_tool_use("anything", {})
    assert not allowed


def test_pre_exit2_blocks_with_reason(tmp_path):
    e = _engine(tmp_path, {
        "PreToolUse": [
            {"matcher": "bash",
             "hooks": [{"type": "command", "command": "echo no-destructive >&2; exit 2"}]},
        ],
    })
    allowed, reason = e.pre_tool_use("bash", {})
    assert not allowed
    assert reason == "no-destructive"


def test_pre_nonzero_warns_but_allows(tmp_path):
    e = _engine(tmp_path, {
        "PreToolUse": [
            {"matcher": "bash",
             "hooks": [{"type": "command", "command": "echo careful >&2; exit 1"}]},
        ],
    })
    allowed, note = e.pre_tool_use("bash", {})
    assert allowed
    assert note == "careful"


def test_post_stdout_becomes_feedback(tmp_path):
    e = _engine(tmp_path, {
        "PostToolUse": [
            {"matcher": "git_commit",
             "hooks": [{"type": "command", "command": "echo remember-to-push"}]},
        ],
    })
    assert e.post_tool_use("git_commit", {}, "ok") == "remember-to-push"


def test_flat_command_form_tolerated(tmp_path):
    e = _engine(tmp_path, {
        "PreToolUse": [{"matcher": "bash", "command": "exit 2"}],
    })
    allowed, _ = e.pre_tool_use("bash", {})
    assert not allowed


def test_dispatch_runs_pre_and_post_hooks(tmp_path):
    e = _engine(tmp_path, {
        "PreToolUse": [{"matcher": "deny_me", "command": "exit 2"}],
        "PostToolUse": [{"matcher": "ok_tool", "command": "echo checked"}],
    })
    r = ToolRegistry(hook_engine=e)
    r.register("deny_me", lambda **kw: "ran", {"input_schema": {"type": "object"}})
    r.register("ok_tool", lambda **kw: "ran", {"input_schema": {"type": "object"}})
    assert r.dispatch("deny_me", {}).startswith("Blocked by hook:")
    assert r.dispatch("ok_tool", {}).endswith("[hook] checked")
