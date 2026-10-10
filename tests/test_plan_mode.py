"""Plan mode: readonly gating, exit_plan_mode flow, tool filtering."""

from chippilot.core.agent_loop import PLAN_MODE_SUFFIX
from chippilot.core.tool_registry import ToolRegistry


def _registry_with_tools() -> ToolRegistry:
    r = ToolRegistry()
    r.register("read_file", lambda **kw: "contents", {"input_schema": {"type": "object"}}, readonly=True)
    r.register("write_file", lambda **kw: "wrote", {"input_schema": {"type": "object"}})
    r.register("exit_plan_mode", lambda **kw: "Plan mode is not active.", {
        "input_schema": {"type": "object", "properties": {"plan": {"type": "string"}}},
    }, readonly=True)
    return r


def test_plan_mode_blocks_write_allows_readonly():
    r = _registry_with_tools()
    r.set_plan_mode(True)
    assert "Plan mode" in r.dispatch("write_file", {"path": "x"})
    assert r.dispatch("read_file", {"path": "x"}) == "contents"


def test_plan_mode_off_allows_all():
    r = _registry_with_tools()
    assert r.dispatch("write_file", {"path": "x"}) == "wrote"


def test_get_tools_for_mode_filters_to_readonly():
    r = _registry_with_tools()
    r.set_plan_mode(True)
    names = {t["name"] for t in r.get_tools_for_mode()}
    assert names == {"read_file", "exit_plan_mode"}
    r.set_plan_mode(False)
    assert {t["name"] for t in r.get_tools_for_mode()} == {
        "read_file", "write_file", "exit_plan_mode"}


def test_exit_plan_mode_approve_flips_mode():
    r = _registry_with_tools()
    r.set_plan_mode(True)
    out = r.dispatch("exit_plan_mode", {"plan": "1. do x"}, approve=lambda n, i: True)
    assert "Exited plan mode" in out
    assert not r.plan_mode
    assert r.dispatch("write_file", {"path": "x"}) == "wrote"


def test_exit_plan_mode_deny_stays():
    r = _registry_with_tools()
    r.set_plan_mode(True)
    out = r.dispatch("exit_plan_mode", {"plan": "1. do x"}, approve=lambda n, i: False)
    assert "Staying in plan mode" in out
    assert r.plan_mode


def test_exit_plan_mode_no_approve_denied():
    # Non-interactive contexts (subagents, teammates, MCP) can't exit plan mode.
    r = _registry_with_tools()
    r.set_plan_mode(True)
    assert "Staying in plan mode" in r.dispatch("exit_plan_mode", {"plan": "x"})
    assert r.plan_mode


def test_exit_plan_mode_outside_mode_returns_handler_msg():
    r = _registry_with_tools()
    assert r.dispatch("exit_plan_mode", {"plan": "x"}) == "Plan mode is not active."


def test_plan_mode_suffix_exists():
    assert "plan mode" in PLAN_MODE_SUFFIX.lower()
    assert "exit_plan_mode" in PLAN_MODE_SUFFIX
