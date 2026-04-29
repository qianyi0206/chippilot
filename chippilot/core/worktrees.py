"""WorktreeManager + EventBus for directory-level task isolation (s12)."""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

from chippilot.config import WORKDIR


class EventBus:
    """Append-only lifecycle events for observability."""

    def __init__(self, event_log_path: Path):
        self.path = event_log_path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("")

    def emit(self, event: str, task: dict | None = None,
             worktree: dict | None = None, error: str | None = None):
        payload = {
            "event": event, "ts": time.time(),
            "task": task or {}, "worktree": worktree or {},
        }
        if error:
            payload["error"] = error
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")

    def list_recent(self, limit: int = 20) -> str:
        n = max(1, min(int(limit or 20), 200))
        lines = self.path.read_text(encoding="utf-8").splitlines()
        recent = lines[-n:]
        items = []
        for line in recent:
            try:
                items.append(json.loads(line))
            except Exception:
                items.append({"event": "parse_error", "raw": line})
        return json.dumps(items, indent=2)


class WorktreeManager:
    """Create/list/run/remove git worktrees with lifecycle index."""

    def __init__(self, repo_root: Path | None = None):
        self.repo_root = repo_root or self._detect_repo_root()
        self.dir = self.repo_root / ".worktrees"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir / "index.json"
        if not self.index_path.exists():
            self.index_path.write_text(json.dumps({"worktrees": []}, indent=2))
        self.events = EventBus(self.dir / "events.jsonl")
        self.git_available = self._is_git_repo()

    def _detect_repo_root(self) -> Path:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=WORKDIR, capture_output=True, text=True, timeout=10,
            )
            if r.returncode == 0:
                root = Path(r.stdout.strip())
                if root.exists():
                    return root
        except Exception:
            pass
        return WORKDIR

    def _is_git_repo(self) -> bool:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_root, capture_output=True, text=True, timeout=10,
            )
            return r.returncode == 0
        except Exception:
            return False

    def _run_git(self, args: list[str]) -> str:
        if not self.git_available:
            raise RuntimeError("Not in a git repository.")
        r = subprocess.run(
            ["git", *args], cwd=self.repo_root,
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            msg = (r.stdout + r.stderr).strip()
            raise RuntimeError(msg or f"git {' '.join(args)} failed")
        return (r.stdout + r.stderr).strip() or "(no output)"

    def _load_index(self) -> dict:
        return json.loads(self.index_path.read_text())

    def _save_index(self, data: dict):
        self.index_path.write_text(json.dumps(data, indent=2))

    def _find(self, name: str) -> dict | None:
        idx = self._load_index()
        for wt in idx.get("worktrees", []):
            if wt.get("name") == name:
                return wt
        return None

    def create(self, name: str, task_id: int = None, base_ref: str = "HEAD") -> str:
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", name or ""):
            raise ValueError("Invalid worktree name.")
        if self._find(name):
            raise ValueError(f"Worktree '{name}' already exists")

        path = self.dir / name
        branch = f"wt/{name}"
        self.events.emit("worktree.create.before", worktree={"name": name, "base_ref": base_ref})
        try:
            self._run_git(["worktree", "add", "-b", branch, str(path), base_ref])
            entry = {
                "name": name, "path": str(path), "branch": branch,
                "task_id": task_id, "status": "active", "created_at": time.time(),
            }
            idx = self._load_index()
            idx["worktrees"].append(entry)
            self._save_index(idx)
            self.events.emit("worktree.create.after", worktree=entry)
            return json.dumps(entry, indent=2)
        except Exception as e:
            self.events.emit("worktree.create.failed", worktree={"name": name}, error=str(e))
            raise

    def list_all(self) -> str:
        wts = self._load_index().get("worktrees", [])
        if not wts:
            return "No worktrees."
        lines = []
        for wt in wts:
            suffix = f" task={wt['task_id']}" if wt.get("task_id") else ""
            lines.append(f"[{wt.get('status', 'unknown')}] {wt['name']} -> {wt['path']}{suffix}")
        return "\n".join(lines)

    def run_in(self, name: str, command: str) -> str:
        wt = self._find(name)
        if not wt:
            return f"Error: Unknown worktree '{name}'"
        path = Path(wt["path"])
        if not path.exists():
            return f"Error: Path missing: {path}"
        try:
            r = subprocess.run(command, shell=True, cwd=path,
                               capture_output=True, text=True, timeout=300)
            out = (r.stdout + r.stderr).strip()
            return out[:50000] if out else "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Timeout (300s)"

    def remove(self, name: str, force: bool = False) -> str:
        wt = self._find(name)
        if not wt:
            return f"Error: Unknown worktree '{name}'"
        self.events.emit("worktree.remove.before", worktree={"name": name})
        try:
            args = ["worktree", "remove"]
            if force:
                args.append("--force")
            args.append(wt["path"])
            self._run_git(args)
            idx = self._load_index()
            for item in idx.get("worktrees", []):
                if item.get("name") == name:
                    item["status"] = "removed"
                    item["removed_at"] = time.time()
            self._save_index(idx)
            self.events.emit("worktree.remove.after", worktree={"name": name, "status": "removed"})
            return f"Removed worktree '{name}'"
        except Exception as e:
            self.events.emit("worktree.remove.failed", worktree={"name": name}, error=str(e))
            raise
