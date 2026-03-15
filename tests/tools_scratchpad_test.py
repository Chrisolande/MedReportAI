import asyncio

from tools import scratchpad


class DummyState:
    def __init__(self):
        self.messages = [
            type(
                "Msg",
                (),
                {"tool_calls": [{"name": "WriteToScratchpad", "args": {}, "id": 1}]},
            )()
        ]
        self.scratchpad = ""
        self.scratchpad_file = ""


def test_tool_node_handles_write(monkeypatch):
    monkeypatch.setattr(
        scratchpad,
        "_handle_write",
        lambda args, state, call_id: ("new", type("Msg", (), {"content": "done"})()),
    )
    state = DummyState()
    result = asyncio.run(scratchpad.tool_node(state))
    assert "messages" in result


def test_tools_condition_tools():
    state = type("S", (), {"messages": [type("M", (), {"tool_calls": [1]})()]})()
    assert scratchpad.tools_condition(state) == "tools"


def test_tools_condition_end():
    state = type("S", (), {"messages": [type("M", (), {"tool_calls": None})()]})()
    from langgraph.graph import END

    assert scratchpad.tools_condition(state) == END
