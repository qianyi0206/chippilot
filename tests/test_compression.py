"""microcompact: clears old tool results, keeps latest 3."""

from chippilot.core.compression import microcompact, estimate_tokens


def _tool_msg(tid: int, size: int = 200):
    return {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": f"t{tid}", "content": "x" * size}],
    }


def test_microcompact_keeps_last_three():
    msgs = [_tool_msg(i) for i in range(6)]
    microcompact(msgs)
    for i in range(3):
        assert msgs[i]["content"][0]["content"] == "[cleared]"
    for i in range(3, 6):
        assert msgs[i]["content"][0]["content"] != "[cleared]"


def test_microcompact_noop_when_few_results():
    msgs = [_tool_msg(1), _tool_msg(2)]
    before = msgs[0]["content"][0]["content"]
    microcompact(msgs)
    assert msgs[0]["content"][0]["content"] == before


def test_estimate_tokens_scales_with_messages():
    assert estimate_tokens([{"role": "user", "content": "abcd"}]) > 0
