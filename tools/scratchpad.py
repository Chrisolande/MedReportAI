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
_EXTERNAL_TOOLS = [web_search, retriever_tool]
_TOOL_BY_NAME = {t.name: t for t in _EXTERNAL_TOOLS}


def _save_scratchpad(content: str, filepath: str) -> None:
    save_scratchpad(content, filepath, app_config.paths.scratchpad_output_dir)


async def _dispatch(name: str, args: dict, state: ScratchpadState, call_id: str):
    """Route a tool call to its handler.

    Returns (scratchpad_update | None, ToolMessage).
    """
    scratchpad = getattr(state, "scratchpad", "")

    if name == "WriteToScratchpad":
        return handle_write(args, scratchpad, call_id)
    if name == "ReadFromScratchpad":
        return None, handle_read(args, scratchpad, call_id)
    if name == "ClearScratchpad":
        return handle_clear(args, call_id, scratchpad)

    content = str(await _TOOL_BY_NAME[name].ainvoke(args))
    return None, ToolMessage(content=content, tool_call_id=call_id)


async def tool_node(state: ScratchpadState) -> dict:
    """Execute tool calls and update state."""
    last_message = state.messages[-1]
    if not getattr(last_message, "tool_calls", None):
        return {"messages": []}

    result_messages: list[ToolMessage] = []
    scratchpad_update = None
    scratchpad_file = getattr(state, "scratchpad_file", "")

    for tc in last_message.tool_calls:
        call_id = str(tc.get("id") or "unknown")
        update, msg = await _dispatch(tc["name"], tc["args"], state, call_id)
        result_messages.append(msg)
        if update is not None:
            scratchpad_update = update

    result: dict = {"messages": result_messages}
    if scratchpad_update is not None:
        result["scratchpad"] = scratchpad_update
        if scratchpad_file:
            _save_scratchpad(scratchpad_update, scratchpad_file)

    return result


def tools_condition(state: ScratchpadState) -> str:
    return "tools" if getattr(state.messages[-1], "tool_calls", None) else END
