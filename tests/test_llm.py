"""call_llm: prompt-caching breakpoints and retry behaviour."""

from types import SimpleNamespace

from chippilot.core.llm import call_llm


class _FakeMessages:
    def __init__(self):
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(content=[], stop_reason="end_turn")


class _FakeClient:
    def __init__(self):
        self.messages = _FakeMessages()


def test_cache_breakpoints_on_system_and_last_tool():
    client = _FakeClient()
    tools = [
        {"name": "a", "input_schema": {}},
        {"name": "b", "input_schema": {}},
    ]
    call_llm(client, model="m", messages=[], system="sys", tools=tools)
    kw = client.messages.calls[0]
    assert kw["system"] == [{
        "type": "text", "text": "sys",
        "cache_control": {"type": "ephemeral"},
    }]
    assert kw["tools"][-1]["cache_control"] == {"type": "ephemeral"}
    assert "cache_control" not in kw["tools"][0]
    # caller's tool dicts not mutated
    assert all("cache_control" not in t for t in tools)


def test_cache_disabled_keeps_plain_values():
    client = _FakeClient()
    call_llm(client, model="m", messages=[], system="sys",
             tools=[{"name": "a", "input_schema": {}}], cache=False)
    kw = client.messages.calls[0]
    assert kw["system"] == "sys"
    assert "cache_control" not in kw["tools"][0]


def test_retry_then_success():
    import anthropic

    class _Flaky:
        def __init__(self):
            self.calls = 0

        def create(self, **kw):
            self.calls += 1
            if self.calls < 3:
                raise anthropic.APIConnectionError(request=None)
            return SimpleNamespace(content=[], stop_reason="end_turn")

    flaky = _Flaky()
    client = SimpleNamespace(messages=flaky)
    resp = call_llm(client, model="m", messages=[])
    assert resp.stop_reason == "end_turn"
    assert flaky.calls == 3
