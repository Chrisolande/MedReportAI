from pathlib import Path

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


def _save_scratchpad(content: str, filepath: str):
    """Persist scratchpad content to markdown file."""
    base_dir = Path(app_config.paths.scratchpad_output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)
    full_path = base_dir / filepath
    full_path.write_text(content, encoding="utf-8")


def _handle_write(tool_args, state, tool_call_id):
    notes = tool_args.get("notes", "")
    mode = tool_args.get("mode", "append")

    if mode == "replace":
        new_content = notes
    else:
        separator = "\n\n" if state.scratchpad else ""
        new_content = f"{state.scratchpad}{separator}{notes}"

    return new_content, ToolMessage(
        content=f"Wrote to scratchpad: {notes}", tool_call_id=tool_call_id
    )


def _handle_read(tool_args, state, tool_call_id):
    scratchpad_content = state.scratchpad or "Scratchpad is empty."
    query = tool_args.get("query", "all")

    if query != "all":
        content = f"Scratchpad contents (query: '{query}'): \n\n{scratchpad_content}"
    else:
        content = f"Scratchpad contents: \n\n{scratchpad_content}"

    return ToolMessage(content=content, tool_call_id=tool_call_id)


def _handle_clear(tool_args, tool_call_id):
    confirm = tool_args.get("confirm", False)

    if confirm:
        return "", ToolMessage(
            content="Scratchpad cleared successfully.",
            tool_call_id=tool_call_id,
        )
    return None, ToolMessage(
        content="Scratchpad clear cancelled (confirm=False).",
        tool_call_id=tool_call_id,
    )


async def _handle_external(tool_name, tool_args, tool_call_id, tool_by_name):
    tool = tool_by_name[tool_name]
    observation = await tool.ainvoke(tool_args)
    return ToolMessage(content=str(observation), tool_call_id=tool_call_id)


async def tool_node(state: ScratchpadState) -> dict:
    """Execute tool calls and update state accordingly."""

    section_tools = [
        WriteToScratchpad,
        ClearScratchpad,
        ReadFromScratchpad,
        web_search,
        retriever_tool,
    ]
    tool_by_name = {
        (tool.name if hasattr(tool, "name") else tool.__name__): tool
        for tool in section_tools
    }

    last_message = state.messages[-1]
    if not getattr(last_message, "tool_calls", None):
        return {"messages": []}

    result_messages = []
    scratchpad_update = None
    scratchpad_file = getattr(state, "scratchpad_file", "")
    for tool_call in last_message.tool_calls:  # type: ignore
        tool_name, tool_args, tool_call_id = (
            tool_call["name"],
            tool_call["args"],
            tool_call["id"],
        )

        if tool_name == "WriteToScratchpad":
            scratchpad_update, msg = _handle_write(tool_args, state, tool_call_id)
            result_messages.append(msg)  # Keep scratchpad confirmations
        elif tool_name == "ReadFromScratchpad":
            msg = _handle_read(tool_args, state, tool_call_id)
            result_messages.append(msg)  # Keep read responses
        elif tool_name == "ClearScratchpad":
            scratchpad_update, msg = _handle_clear(tool_args, tool_call_id)
            result_messages.append(msg)  # Keep clear confirmations
        else:
            # Execute tool but don't add its response to messages
            msg = await _handle_external(
                tool_name, tool_args, tool_call_id, tool_by_name
            )
            result_messages.append(msg)

    update = {"messages": result_messages}
    if scratchpad_update is not None:
        update["scratchpad"] = scratchpad_update  # type:ignore
        if scratchpad_file:
            _save_scratchpad(scratchpad_update, scratchpad_file)

    return update


def tools_condition(state: ScratchpadState):  # Use the SectionState?
    """Determine whether to call tools or end the agent loop."""
    last_message = state.messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:  # type: ignore
        return "tools"
    return END


def get_section_tools():
    """Get all tools for section writing."""
    from tools.retrieval import retriever_tool
    from tools.web_search import web_search

    return [
        WriteToScratchpad,
        ReadFromScratchpad,
        ClearScratchpad,
        web_search,
        retriever_tool,
    ]
