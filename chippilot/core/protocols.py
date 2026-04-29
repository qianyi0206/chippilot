"""Shutdown and plan approval handshake protocols (s10)."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chippilot.core.messaging import MessageBus

# Global tracking dicts
shutdown_requests: dict[str, dict] = {}
plan_requests: dict[str, dict] = {}


def make_shutdown_handler(bus: "MessageBus"):
    """Return a callable that sends shutdown requests."""

    def handle_shutdown_request(teammate: str) -> str:
        req_id = str(uuid.uuid4())[:8]
        shutdown_requests[req_id] = {"target": teammate, "status": "pending"}
        bus.send("lead", teammate, "Please shut down.", "shutdown_request", {"request_id": req_id})
        # Clean up completed shutdown requests to prevent unbounded growth
        done = [k for k, v in shutdown_requests.items() if v["status"] != "pending"]
        for k in done:
            shutdown_requests.pop(k, None)
        return f"Shutdown request {req_id} sent to '{teammate}'"

    return handle_shutdown_request


def make_plan_handler(bus: "MessageBus"):
    """Return a callable that handles plan approval/rejection."""

    def handle_plan_review(request_id: str, approve: bool, feedback: str = "") -> str:
        req = plan_requests.get(request_id)
        if not req:
            return f"Error: Unknown plan request_id '{request_id}'"
        req["status"] = "approved" if approve else "rejected"
        status = req["status"]
        from_name = req["from"]
        plan_requests.pop(request_id, None)
        bus.send("lead", from_name, feedback, "plan_approval_response",
                 {"request_id": request_id, "approve": approve, "feedback": feedback})
        return f"Plan {status} for '{from_name}'"

    return handle_plan_review
