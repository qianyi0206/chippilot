"""LSF tools: mock bsub/bjobs/bqueues/bhist/bkill + SSUSP/USUSP diagnosis (8 tools)."""

from __future__ import annotations

import json
import random
import time
from pathlib import Path
from typing import TYPE_CHECKING

from chippilot.config import MOCK_DATA_DIR

if TYPE_CHECKING:
    from chippilot.core.tool_registry import ToolRegistry

# --- Mock state ---
_mock_jobs: list[dict] | None = None
_next_job_id = 2000000
_lsf_lock = __import__("threading").Lock()


def _load_mock_data():
    global _mock_jobs
    if _mock_jobs is not None:
        return
    jobs_path = MOCK_DATA_DIR / "lsf" / "jobs.json"
    if jobs_path.exists():
        _mock_jobs = json.loads(jobs_path.read_text()).get("jobs", [])
    else:
        _mock_jobs = []


def _load_queues() -> list[dict]:
    queues_path = MOCK_DATA_DIR / "lsf" / "queues.json"
    if queues_path.exists():
        return json.loads(queues_path.read_text()).get("queues", [])
    return []


def _load_hosts() -> list[dict]:
    hosts_path = MOCK_DATA_DIR / "lsf" / "hosts.json"
    if hosts_path.exists():
        return json.loads(hosts_path.read_text()).get("hosts", [])
    return []


# --- Tool implementations ---

def lsf_bsub(**kw) -> str:
    """Submit a job to LSF (mock)."""
    _load_mock_data()
    global _next_job_id

    queue = kw.get("queue", "short")
    command = kw.get("command", "echo hello")
    rusage = kw.get("rusage", "")
    job_name = kw.get("job_name", "")

    with _lsf_lock:
        job_id = _next_job_id
        _next_job_id += 1
    job = {
        "job_id": job_id,
        "user": "current_user",
        "queue": queue,
        "status": "PEND",
        "command": command,
        "submit_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "start_time": None,
        "host": None,
        "cpu_used": None,
        "mem_used": None,
    }
    if job_name:
        job["job_name"] = job_name
    _mock_jobs.append(job)
    return f"Job <{job_id}> is submitted to queue <{queue}>.\nCommand: {command}"


def lsf_bjobs(**kw) -> str:
    """List jobs (mock)."""
    _load_mock_data()
    user = kw.get("user")
    status = kw.get("status")
    job_id = kw.get("job_id")

    jobs = _mock_jobs
    if user:
        jobs = [j for j in jobs if j.get("user") == user]
    if status:
        jobs = [j for j in jobs if j.get("status") == status.upper()]
    if job_id:
        jobs = [j for j in jobs if j.get("job_id") == job_id]

    if not jobs:
        return "No matching jobs found."

    lines = [f"{'JOBID':<10} {'USER':<12} {'STAT':<8} {'QUEUE':<12} {'HOST':<16} {'COMMAND'}"]
    for j in jobs:
        lines.append(
            f"{j['job_id']:<10} {j.get('user',''):<12} {j['status']:<8} "
            f"{j.get('queue',''):<12} {j.get('host') or '-':<16} {j.get('command','')[:40]}"
        )
    return "\n".join(lines)


def lsf_bjobs_all() -> str:
    """Convenience for /jobs slash command."""
    _load_mock_data()
    return lsf_bjobs()


def lsf_bqueues(**kw) -> str:
    """Show queue info (mock)."""
    queues = _load_queues()
    name = kw.get("queue")
    if name:
        queues = [q for q in queues if q["name"] == name]
    if not queues:
        return "No matching queues."
    lines = [f"{'QUEUE':<14} {'NJOBS':<8} {'PEND':<8} {'RUN':<8} {'SUSP':<8} {'HOSTS':<8} DESCRIPTION"]
    for q in queues:
        total = q["running"] + q["pending"] + q["suspended"]
        lines.append(
            f"{q['name']:<14} {total:<8} {q['pending']:<8} {q['running']:<8} "
            f"{q['suspended']:<8} {q['hosts']:<8} {q['description']}"
        )
    return "\n".join(lines)


def lsf_bqueues_all() -> str:
    """Convenience for /queues slash command."""
    return lsf_bqueues()


def lsf_bhist(**kw) -> str:
    """Show job history (mock)."""
    _load_mock_data()
    job_id = kw.get("job_id")
    if not job_id:
        return "Error: job_id required"
    job = next((j for j in _mock_jobs if j.get("job_id") == job_id), None)
    if not job:
        return f"No history for job {job_id}"
    return (
        f"Job <{job_id}>, User <{job.get('user', '?')}>, Queue <{job.get('queue', '?')}>\n"
        f"  Submitted: {job.get('submit_time', '?')}\n"
        f"  Started:   {job.get('start_time', '-')}\n"
        f"  Host:      {job.get('host', '-')}\n"
        f"  CPU used:  {job.get('cpu_used', '-')}\n"
        f"  MEM used:  {job.get('mem_used', '-')}\n"
        f"  Status:    {job['status']}"
    )


def lsf_bkill(**kw) -> str:
    """Kill a job (mock)."""
    _load_mock_data()
    job_id = kw.get("job_id")
    if not job_id:
        return "Error: job_id required"
    job = next((j for j in _mock_jobs if j.get("job_id") == job_id), None)
    if not job:
        return f"Job {job_id} not found"
    if job["status"] in ("DONE", "EXIT"):
        return f"Job <{job_id}> already finished ({job['status']})"
    job["status"] = "EXIT"
    return f"Job <{job_id}> is being terminated"


def lsf_diagnose_ssusp(**kw) -> str:
    """Diagnose SSUSP (Self-Suspending) job (mock)."""
    _load_mock_data()
    job_id = kw.get("job_id")
    if job_id:
        job = next((j for j in _mock_jobs if j.get("job_id") == job_id), None)
        if not job:
            return f"Job {job_id} not found"
        if job["status"] != "SSUSP":
            return f"Job {job_id} is not SSUSP (current: {job['status']})"

    return (
        "SSUSP Diagnosis Report:\n"
        "======================\n"
        "Common causes of SSUSP (system-suspended):\n"
        "1. Memory limit exceeded - job RSS > queue/host memory limit\n"
        "   -> Check: bjobs -l <jobid> | grep MEMLIMIT\n"
        "   -> Fix: bmod -M <higher_limit> <jobid>, then bresume <jobid>\n"
        "2. Runtime limit exceeded - job walltime > RUNLIMIT\n"
        "   -> Check: bjobs -l <jobid> | grep RUNLIMIT\n"
        "   -> Fix: bmod -W <new_limit> <jobid>, then bresume <jobid>\n"
        "3. Host load too high - load exceeds threshold\n"
        "   -> Check: bhosts <hostname> and lsload <hostname>\n"
        "   -> Fix: Wait for load to drop, or bmig <jobid> to another host\n"
        "4. Disk quota exceeded - /tmp or work directory full\n"
        "   -> Check: df -h on the execution host\n"
        "   -> Fix: Clean up disk space, then bresume <jobid>\n\n"
        "Recommended action: Load the SSUSP knowledge doc for full checklist."
    )


def lsf_diagnose_ususp(**kw) -> str:
    """Diagnose USUSP (User-Suspended) job (mock)."""
    return (
        "USUSP Diagnosis Report:\n"
        "======================\n"
        "USUSP means the job was manually suspended by user or admin.\n\n"
        "Possible reasons:\n"
        "1. User ran 'bstop <jobid>' intentionally\n"
        "2. Admin suspended for maintenance\n"
        "3. Script called bstop as part of workflow\n\n"
        "Resolution:\n"
        "- If user-suspended: bresume <jobid>\n"
        "- If admin-suspended: Contact CAD team\n"
        "- Check job detail: bjobs -l <jobid> | grep 'suspend'"
    )


def lsf_resource_plan(**kw) -> str:
    """Plan resource allocation across queues (mock)."""
    queues = _load_queues()
    total_hosts = sum(q["hosts"] for q in queues)
    total_running = sum(q["running"] for q in queues)
    total_pending = sum(q["pending"] for q in queues)

    lines = [
        "Resource Plan Summary:",
        f"  Total hosts: {total_hosts}",
        f"  Total running: {total_running}",
        f"  Total pending: {total_pending}",
        f"  Utilization: {total_running / max(sum(q['max_jobs'] for q in queues), 1) * 100:.1f}%",
        "",
        "Queue pressure analysis:",
    ]
    for q in queues:
        pressure = q["pending"] / max(q["max_jobs"], 1) * 100
        status = "HIGH" if pressure > 20 else "NORMAL" if pressure > 5 else "LOW"
        lines.append(f"  {q['name']:<14} pending_ratio={pressure:.1f}% [{status}]")
    return "\n".join(lines)


def register_lsf_tools(registry: "ToolRegistry"):
    registry.register("lsf_bsub", lsf_bsub, {
        "description": "Submit a job to LSF queue (mock).",
        "input_schema": {
            "type": "object",
            "properties": {
                "queue": {"type": "string", "description": "Queue name: short/medium/long/interactive/night/gpu"},
                "command": {"type": "string", "description": "Command to run"},
                "rusage": {"type": "string", "description": "Resource usage string"},
                "job_name": {"type": "string"},
            },
            "required": ["command"],
        },
    }, category="lsf")

    registry.register("lsf_bjobs", lsf_bjobs, {
        "description": "List LSF jobs, optionally filtered (mock).",
        "input_schema": {
            "type": "object",
            "properties": {
                "user": {"type": "string"},
                "status": {"type": "string", "enum": ["RUN", "PEND", "SSUSP", "USUSP", "DONE", "EXIT"]},
                "job_id": {"type": "integer"},
            },
        },
    }, category="lsf")

    registry.register("lsf_bqueues", lsf_bqueues, {
        "description": "Show LSF queue information (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"queue": {"type": "string"}},
        },
    }, category="lsf")

    registry.register("lsf_bhist", lsf_bhist, {
        "description": "Show LSF job history (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "integer"}},
            "required": ["job_id"],
        },
    }, category="lsf")

    registry.register("lsf_bkill", lsf_bkill, {
        "description": "Kill an LSF job (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "integer"}},
            "required": ["job_id"],
        },
    }, category="lsf")

    registry.register("lsf_diagnose_ssusp", lsf_diagnose_ssusp, {
        "description": "Diagnose SSUSP (system-suspended) job causes and fixes (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "integer"}},
        },
    }, category="lsf")

    registry.register("lsf_diagnose_ususp", lsf_diagnose_ususp, {
        "description": "Diagnose USUSP (user-suspended) job causes and fixes (mock).",
        "input_schema": {
            "type": "object",
            "properties": {"job_id": {"type": "integer"}},
        },
    }, category="lsf")

    registry.register("lsf_resource_plan", lsf_resource_plan, {
        "description": "Analyze queue resource allocation and pressure (mock).",
        "input_schema": {"type": "object", "properties": {}},
    }, category="lsf")
