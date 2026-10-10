"""TaskManager: file-based task board with dependencies."""

import json

from chippilot.core.tasks import TaskManager


def test_create_get_list(tmp_path):
    tm = TaskManager(tasks_dir=tmp_path)
    created = json.loads(tm.create("Fix bug", "details"))
    assert created["id"] == 1
    assert created["status"] == "pending"
    assert (tmp_path / "task_1.json").exists()
    got = json.loads(tm.get(1))
    assert got["subject"] == "Fix bug"
    assert "#1: Fix bug" in tm.list_all()


def test_complete_unblocks_dependents(tmp_path):
    tm = TaskManager(tasks_dir=tmp_path)
    json.loads(tm.create("A"))
    b = json.loads(tm.create("B"))
    tm.update(b["id"], add_blocked_by=[1])
    tm.update(1, status="completed")
    b_after = json.loads(tm.get(2))
    assert b_after["blockedBy"] == []


def test_claim_and_delete(tmp_path):
    tm = TaskManager(tasks_dir=tmp_path)
    tm.create("job")
    assert "Claimed task #1 for alice" in tm.claim(1, "alice")
    got = json.loads(tm.get(1))
    assert got["owner"] == "alice" and got["status"] == "in_progress"
    tm.update(1, status="deleted")
    assert not (tmp_path / "task_1.json").exists()


def test_missing_task_raises(tmp_path):
    import pytest
    tm = TaskManager(tasks_dir=tmp_path)
    with pytest.raises(ValueError):
        tm.get(99)
