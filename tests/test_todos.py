"""TodoManager validation + rendering."""

import pytest

from chippilot.core.todos import TodoManager


def _item(content="do x", status="pending", af="doing x"):
    return {"content": content, "status": status, "activeForm": af}


def test_update_and_render():
    t = TodoManager()
    out = t.update([_item(), _item("do y", "in_progress", "doing y")])
    assert "[>] do y <- doing y" in out
    assert "(0/2 completed)" in out


def test_requires_content_status_activeform():
    t = TodoManager()
    with pytest.raises(ValueError):
        t.update([{"status": "pending", "activeForm": "x"}])
    with pytest.raises(ValueError):
        t.update([_item(status="weird")])
    with pytest.raises(ValueError):
        t.update([{"content": "x", "status": "pending"}])


def test_single_in_progress_and_cap():
    t = TodoManager()
    with pytest.raises(ValueError):
        t.update([_item("a", "in_progress", "a"), _item("b", "in_progress", "b")])
    with pytest.raises(ValueError):
        t.update([_item(f"task {i}") for i in range(21)])


def test_has_open_items():
    t = TodoManager()
    assert not t.has_open_items()
    t.update([_item(status="completed")])
    assert not t.has_open_items()
    t.update([_item()])
    assert t.has_open_items()
