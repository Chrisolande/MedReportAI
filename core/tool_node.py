"""Tool-node infrastructure for the section writer sub-graph.

Handles routing and dispatching of all tool calls made by the LLM during section
research, including scratchpad operations and external tools.
"""

import asyncio
import re
from dataclasses import dataclass, field

from langchain_core.messages import ToolMessage
from langgraph.graph import END

from core.quality import merge_sources
from core.schemas import ClearScratchpad, ReadFromScratchpad, WriteToScratchpad
from core.states import SectionState
from tools.pubmed_search import pubmed_scraper_tool
from tools.retrieval import retriever_tool
from tools.web_search import web_search
from utils.helpers import content_to_text
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
    pubmed_scraper_tool,
]

_TOOL_BY_NAME: dict = {
    (t.name if hasattr(t, "name") else t.__name__): t for t in SECTION_TOOLS
}


# Utilities


async def _save_scratchpad(content: str, filepath: str) -> None:
    from config import config as app_config

    await asyncio.to_thread(
        save_scratchpad, content, filepath, app_config.paths.scratchpad_output_dir
    )


def _extract_dataset_path(tool_output: str) -> str | None:
    match = re.search(r"^DATASET_PATH:\s*(.+)$", tool_output, re.MULTILINE)
    if not match:
        return None
    raw = match.group(1).strip().split("\\n")[0].split("\n")[0].strip("`")
    return raw or None


# Per-tool handlers


def _handle_write(args: dict, state: SectionState, call_id: str):
    return handle_write(args, state.get("scratchpad", ""), call_id)


def _handle_read(args: dict, state: SectionState, call_id: str) -> ToolMessage:
    return handle_read(args, state.get("scratchpad", ""), call_id)


def _handle_clear(args: dict, call_id: str):
    return handle_clear(args, call_id)


async def _handle_external(name: str, args: dict, call_id: str) -> ToolMessage:
    observation = await _TOOL_BY_NAME[name].ainvoke(args)
    return ToolMessage(content=str(observation), tool_call_id=call_id)


# Node and edge


@dataclass
class _CallContext:
    """Accumulates mutable side-effects across all tool calls in one node invocation."""

    state: SectionState
    messages: list[ToolMessage] = field(default_factory=list)
    sources: list = field(default_factory=list)
    scratchpad_update: str | None = None
    active_csv_update: str | None = None

    def __post_init__(self):
        self.sources = list(self.state.get("sources", []))

    async def dispatch(self, name: str, args: dict, call_id: str) -> None:
        if name == "WriteToScratchpad":
            self.scratchpad_update, msg = _handle_write(args, self.state, call_id)
            self.messages.append(msg)
        elif name == "ReadFromScratchpad":
            self.messages.append(_handle_read(args, self.state, call_id))
        elif name == "ClearScratchpad":
            self.scratchpad_update, msg = _handle_clear(args, call_id)
            self.messages.append(msg)
        else:
            await self._dispatch_external(name, args, call_id)

    async def _dispatch_external(self, name: str, args: dict, call_id: str) -> None:
        if name == "retriever_tool" and (
            csv := self.state.get("active_csv_path", "").strip()
        ):
            args["csv_path"] = csv
        msg = await _handle_external(name, args, call_id)
        self.messages.append(msg)
        text = content_to_text(msg.content)
        self.sources = merge_sources(self.sources, text)
        if name == "pubmed_scraper_tool":
            self.active_csv_update = _extract_dataset_path(text)

    def build_update(self) -> dict:
        update: dict = {"messages": self.messages}
        if self.active_csv_update:
            update["active_csv_path"] = self.active_csv_update
        if self.sources != list(self.state.get("sources", [])):
            update["sources"] = self.sources
        if self.scratchpad_update is not None:
            update["scratchpad"] = self.scratchpad_update
        return update


async def tool_node(state: SectionState) -> dict:
    """Execute all pending tool calls and return updated state."""
    last_message = state["messages"][-1]
    if not getattr(last_message, "tool_calls", None):
        return {"messages": []}

    ctx = _CallContext(state)
    scratchpad_file = state.get("scratchpad_file", "")

    for tc in last_message.tool_calls:
        await ctx.dispatch(
            str(tc.get("name", "")), dict(tc.get("args", {})), str(tc.get("id", ""))
        )

    update = ctx.build_update()
    if ctx.scratchpad_update is not None and scratchpad_file:
        await _save_scratchpad(ctx.scratchpad_update, scratchpad_file)

    return update


def tools_condition(state: SectionState) -> str:
    """Route to tools if tool calls are pending, otherwise end."""
    return "tools" if getattr(state["messages"][-1], "tool_calls", None) else END
