from langchain_core.messages import ToolMessage
from langgraph.graph import END

from config import config as app_config
from core.schemas import (
    ClearScratchpad,
    ReadFromScratchpad,
    ScratchpadState,
    WriteToScratchpad,
)
from tools.retrieval import retriever_tool
from tools.web_search import web_search
from utils.scratchpad_helpers import (
    handle_clear,
    handle_read,
    handle_write,
    save_scratchpad,
)

SECTION_TOOLS = [
    WriteToScratchpad,
    ReadFromScratchpad,
    ClearScratchpad,
    web_search,
    retriever_tool,
]
_TOOL_BY_NAME = {
    (t.name if hasattr(t, "name") else t.__name__): t for t in SECTION_TOOLS
}


def _save_scratchpad(content: str, filepath: str) -> None:
    save_scratchpad(content, filepath, app_config.paths.scratchpad_output_dir)


def _handle_write(args: dict, state: ScratchpadState, call_id: str):
    return handle_write(args, getattr(state, "scratchpad", ""), call_id)


def _handle_read(args: dict, state: ScratchpadState, call_id: str) -> ToolMessage:
    return handle_read(args, getattr(state, "scratchpad", ""), call_id)


def _handle_clear(args: dict, call_id: str):
    return handle_clear(args, call_id)


async def tool_node(state: ScratchpadState) -> dict:
    """Execute tool calls and update state."""
    last_message = state.messages[-1]
    if not getattr(last_message, "tool_calls", None):
        return {"messages": []}

    result_messages: list[ToolMessage] = []
    scratchpad_update = None
    scratchpad_file = getattr(state, "scratchpad_file", "")

    for tc in last_message.tool_calls:  # type: ignore
        name = tc.get("name")
        args = tc.get("args")
        call_id_raw = tc.get("id")
        call_id = str(call_id_raw) if call_id_raw is not None else "unknown"

        if name == "WriteToScratchpad":
            scratchpad_update, msg = _handle_write(args, state, call_id)
        elif name == "ReadFromScratchpad":
            msg = _handle_read(args, state, call_id)
        elif name == "ClearScratchpad":
            scratchpad_update, msg = _handle_clear(args, call_id)
        else:
            msg = ToolMessage(
                content=str(await _TOOL_BY_NAME[name].ainvoke(args)),
                tool_call_id=call_id,
            )
        result_messages.append(msg)

    update: dict = {"messages": result_messages}
    if scratchpad_update is not None:
        update["scratchpad"] = scratchpad_update
        if scratchpad_file:
            _save_scratchpad(scratchpad_update, scratchpad_file)

    return update


def tools_condition(state: ScratchpadState) -> str:
    return "tools" if getattr(state.messages[-1], "tool_calls", None) else END
