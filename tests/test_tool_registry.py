"""ToolRegistry: register/dispatch/schema filtering/permissions."""

from chippilot.core.tool_registry import ToolRegistry
from chippilot.core.safety import PermissionEngine
from chippilot.tools import register_domain_tools, DOMAIN_CATEGORIES


def _boom(**kw):
    raise RuntimeError("boom")


def test_dispatch_unknown_tool():
    r = ToolRegistry()
    assert r.dispatch("nope", {}) == "Unknown tool: nope"


def test_dispatch_exception_becomes_error_string():
    r = ToolRegistry()
    r.register("bad", _boom, {"input_schema": {"type": "object"}})
    assert r.dispatch("bad", {}) == "Error: boom"


def test_get_tools_for_filters_category_and_readonly():
    r = ToolRegistry()
    register_domain_tools(r)
    all_domain = r.get_tools_for(DOMAIN_CATEGORIES)
    readonly = r.get_tools_for(DOMAIN_CATEGORIES, readonly=True)
    ro_names = {t["name"] for t in readonly}
    assert "read_file" in ro_names
    assert "lsf_bjobs" in ro_names
    assert "bash" not in ro_names
    assert "write_file" not in ro_names
    assert "lsf_bsub" not in ro_names
    assert len(all_domain) > len(readonly)
    # harness categories are never in DOMAIN_CATEGORIES
    assert all(t["name"] != "TodoWrite" for t in all_domain)


def test_permission_deny_blocks_dispatch():
    engine = PermissionEngine(rules=[{"tool": "bash", "pattern": "rm -rf", "action": "deny"}])
    r = ToolRegistry(permission_engine=engine)
    r.register("bash", lambda **kw: "ran", {"input_schema": {"type": "object"}})
    assert r.dispatch("bash", {"command": "rm -rf /"}) == "Permission denied: bash blocked by rules"
    assert r.dispatch("bash", {"command": "ls"}) == "ran"


def test_permission_ask_needs_approve_callback():
    engine = PermissionEngine(rules=[{"tool": "bash", "pattern": "deploy", "action": "ask"}])
    r = ToolRegistry(permission_engine=engine)
    r.register("bash", lambda **kw: "ran", {"input_schema": {"type": "object"}})
    # no approve callback -> ask resolves to deny
    assert "denied" in r.dispatch("bash", {"command": "deploy prod"})
    # approve callback honored
    assert r.dispatch("bash", {"command": "deploy prod"}, approve=lambda n, i: True) == "ran"
