"""MessageBus: JSONL inboxes, drain-on-read, broadcast."""

import chippilot.core.messaging as messaging_mod
from chippilot.core.messaging import MessageBus


def test_send_and_read_drains(tmp_path, monkeypatch):
    monkeypatch.setattr(messaging_mod, "INBOX_DIR", tmp_path / "inbox")
    bus = MessageBus()
    bus.send("alice", "bob", "hello")
    bus.send("alice", "bob", "again", "broadcast")
    msgs = bus.read_inbox("bob")
    assert [m["content"] for m in msgs] == ["hello", "again"]
    assert msgs[0]["from"] == "alice"
    assert msgs[1]["type"] == "broadcast"
    # drained: second read is empty
    assert bus.read_inbox("bob") == []


def test_broadcast_skips_sender(tmp_path, monkeypatch):
    monkeypatch.setattr(messaging_mod, "INBOX_DIR", tmp_path / "inbox")
    bus = MessageBus()
    assert bus.broadcast("lead", "ping", ["lead", "a", "b"]) == "Broadcast to 2 teammates"
    assert bus.read_inbox("lead") == []
    assert len(bus.read_inbox("a")) == 1
    assert len(bus.read_inbox("b")) == 1
