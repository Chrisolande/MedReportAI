"""Tool-node infrastructure for the section writer sub-graph.

Handles routing and dispatching of all tool calls made by the LLM during section
research, including scratchpad operations and external tools.
"""

import asyncio
from pathlib import Path

from langchain_core.messages import ToolMessage
from langgraph.graph import END

from core.schemas import ClearScratchpad, ReadFromScratchpad, WriteToScratchpad
from core.states import SectionState
from tools.pubmed_search import pubmed_scraper_tool
from tools.retrieval import retriever_tool
from tools.web_search import web_search

# Module-level tool registry - built once, not on every tool_node call


SECTION_TOOLS = [
    WriteToScratchpad,
    ReadFromScratchpad,
    ClearScratchpad,
    web_search,
    retriever_tool,
    pubmed_scraper_tool,
]

_TOOL_BY_NAME: dict = {
    (t.name if hasattr(t, "name") else t.__name__): t for t in SECTION_TOOLS
}


# Scratchpad persistence


async def _save_scratchpad(content: str, filepath: str) -> None:
    """Persist scratchpad content to a markdown file under outputs/scratchpads/."""

    def _write() -> None:
        base_dir = Path("outputs/scratchpads")
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / filepath).write_text(content, encoding="utf-8")

    await asyncio.to_thread(_write)


# Per-tool handlers


def _handle_write(tool_args: dict, state: SectionState, tool_call_id: str):
    notes = tool_args.get("notes", "")
    mode = tool_args.get("mode", "append")
    existing = state.get("scratchpad", "")

    if mode == "replace":
        new_content = notes
    else:
        separator = "\n\n" if existing else ""
        new_content = f"{existing}{separator}{notes}"

    return new_content, ToolMessage(
        content=f"Wrote to scratchpad: {notes}", tool_call_id=tool_call_id
    )


def _handle_read(tool_args: dict, state: SectionState, tool_call_id: str):
    scratchpad = state.get("scratchpad") or "Scratchpad is empty."
    query = tool_args.get("query", "all")

    if query != "all":
        content = f"Scratchpad contents (query: '{query}'):\n\n{scratchpad}"
    else:
        content = f"Scratchpad contents:\n\n{scratchpad}"

    return ToolMessage(content=content, tool_call_id=tool_call_id)


def _handle_clear(tool_args: dict, tool_call_id: str):
    if tool_args.get("confirm", False):
        return "", ToolMessage(
            content="Scratchpad cleared successfully.", tool_call_id=tool_call_id
        )
    return None, ToolMessage(
        content="Scratchpad clear cancelled (confirm=False).", tool_call_id=tool_call_id
    )


async def _handle_external(tool_name: str, tool_args: dict, tool_call_id: str):
    tool = _TOOL_BY_NAME[tool_name]
    observation = await tool.ainvoke(tool_args)
    return ToolMessage(content=str(observation), tool_call_id=tool_call_id)


# Node and edge


async def tool_node(state: SectionState) -> dict:
    """Execute all pending tool calls and return updated state."""
    last_message = state["messages"][-1]
    if not getattr(last_message, "tool_calls", None):
        return {"messages": []}

    result_messages: list[ToolMessage] = []
    scratchpad_update = None
    scratchpad_file: str = state.get("scratchpad_file", "")

    tool_calls = getattr(last_message, "tool_calls", [])
    for tool_call in tool_calls:
        name = str(tool_call.get("name", ""))
        args = tool_call.get("args", {})
        call_id = str(tool_call.get("id", ""))

        if name == "WriteToScratchpad":
            scratchpad_update, msg = _handle_write(args, state, call_id)
            result_messages.append(msg)
        elif name == "ReadFromScratchpad":
            result_messages.append(_handle_read(args, state, call_id))
        elif name == "ClearScratchpad":
            scratchpad_update, msg = _handle_clear(args, call_id)
            result_messages.append(msg)
        else:
            result_messages.append(await _handle_external(name, args, call_id))

    update: dict = {"messages": result_messages}
    if scratchpad_update is not None:
        update["scratchpad"] = scratchpad_update
        if scratchpad_file:
            await _save_scratchpad(scratchpad_update, scratchpad_file)

    return update


def tools_condition(state: SectionState) -> str:
    """Route to tools if tool calls are pending, otherwise end."""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END
