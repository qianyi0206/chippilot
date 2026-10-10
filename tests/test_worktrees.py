"""WorktreeManager: real git worktree lifecycle + EventBus."""

import json
import subprocess

import pytest

from chippilot.core.worktrees import WorktreeManager


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init"], cwd=r, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=r, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=r, check=True)
    (r / "a.txt").write_text("hello")
    subprocess.run(["git", "add", "a.txt"], cwd=r, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=r, check=True, capture_output=True)
    return r


def test_create_list_run_remove(repo):
    wm = WorktreeManager(repo_root=repo)
    assert wm.git_available

    entry = json.loads(wm.create("feat-x", task_id=7))
    assert entry["branch"] == "wt/feat-x"
    assert (repo / ".worktrees" / "feat-x" / "a.txt").exists()
    assert "feat-x" in wm.list_all()

    out = wm.run_in("feat-x", "git status --short | wc -l")
    assert out.strip() == "0"  # clean checkout

    assert "Removed worktree 'feat-x'" in wm.remove("feat-x")
    idx = wm._load_index()["worktrees"][0]
    assert idx["status"] == "removed"


def test_events_emitted(repo):
    wm = WorktreeManager(repo_root=repo)
    wm.create("ev")
    events = json.loads(wm.events.list_recent())
    kinds = [e["event"] for e in events]
    assert "worktree.create.before" in kinds
    assert "worktree.create.after" in kinds


def test_invalid_name_rejected(repo):
    wm = WorktreeManager(repo_root=repo)
    with pytest.raises(ValueError):
        wm.create("bad name!")


def test_duplicate_name_rejected(repo):
    wm = WorktreeManager(repo_root=repo)
    wm.create("dup")
    with pytest.raises(ValueError):
        wm.create("dup")
