"""Graph node functions for the section writer sub-graph and report graph.

All infrastructure concerns (tool dispatch, scratchpad I/O) live in core.tool_node.
These nodes focus purely on LLM orchestration logic.
"""

from datetime import datetime

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langgraph.types import Send
from loguru import logger

from config import config
from core.states import ReportState, SectionState
from core.tool_node import SECTION_TOOLS, _save_scratchpad
from prompts.section_writer import (
    get_initial_prompt,
    get_synthesis_prompt,
    section_writer_prompt,
)

_llm = config.initialize_llm()
_llm_with_tools = _llm.bind_tools(SECTION_TOOLS)

MAX_RESEARCH_ROUNDS = 4
MIN_SCRATCHPAD_FOR_EARLY_SYNTHESIS = 100


# Section sub-graph node


async def write_sections(state: SectionState) -> dict:
    """Two-phase (research -> synthesis) section writer node."""
    messages = state.get("messages", [])
    section = state["section"]
    scratchpad = state.get("scratchpad", "")
    scratchpad_file = state.get("scratchpad_file", "")

    if not scratchpad_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = section.name.lower().replace(" ", "_")[:30]
        scratchpad_file = f"scratchpad_{slug}_{timestamp}.md"

    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    ai_tool_rounds = len([m for m in messages if getattr(m, "tool_calls", None)])

    logger.info(
        f"Section '{section.name}': round {ai_tool_rounds}, "
        f"{len(tool_messages)} tool results, scratchpad {len(scratchpad)} chars"
    )

    should_synthesize = ai_tool_rounds >= MAX_RESEARCH_ROUNDS or (
        len(scratchpad) > MIN_SCRATCHPAD_FOR_EARLY_SYNTHESIS and ai_tool_rounds >= 3
    )

    if should_synthesize:
        return await _synthesis_phase(
            section, scratchpad, tool_messages, scratchpad_file
        )

    return await _research_phase(section, messages, scratchpad_file)


async def _research_phase(section, messages: list, scratchpad_file: str) -> dict:
    """Phase 1: gather information via tool calls."""
    if not messages:
        messages = [
            SystemMessage(content=section_writer_prompt),
            HumanMessage(content=get_initial_prompt(section)),
        ]

    response = await _llm_with_tools.ainvoke(messages)

    if not getattr(response, "tool_calls", None):
        if not ("Phase 1" in response.content and "complete" in response.content):
            section.content = response.content
            return {
                "messages": messages + [response],
                "completed_sections": [section],
                "scratchpad_file": scratchpad_file,
            }

    return {"messages": messages + [response], "scratchpad_file": scratchpad_file}


async def _synthesis_phase(
    section, scratchpad: str, tool_messages: list, scratchpad_file: str
) -> dict:
    """Phase 2: synthesise research notes into final section content."""
    logger.info(f"Phase 2 synthesis triggered for '{section.name}'")

    if scratchpad:
        research_context = scratchpad
    else:
        research_context = "\n\n".join(
            f"### Research Finding {i + 1}\n{m.content}"
            for i, m in enumerate(tool_messages)
        )
    if not research_context.strip():
        research_context = (
            "No research data available. "
            "Write based on section requirements and general medical knowledge."
        )

    phase2_messages = [
        SystemMessage(
            content=(
                "You are a medical report writer in Phase 2 (Synthesis). "
                "Write the section content based on your research notes. "
                "DO NOT call any tools."
            )
        ),
        HumanMessage(content=get_synthesis_prompt(section, research_context)),
    ]
    response = await _llm.ainvoke(phase2_messages)
    section.content = response.content

    if scratchpad:
        await _save_scratchpad(scratchpad, scratchpad_file)

    return {
        "messages": phase2_messages + [response],
        "completed_sections": [section],
        "scratchpad_file": scratchpad_file,
    }


# Top-level report graph nodes


def initiate_section_writing(state: ReportState) -> list:
    """Fan out research-intensive sections to parallel workers via Send."""
    return [
        Send("build_section_with_tools", {"section": s})
        for s in state["sections"]
        if s.research
    ]


def gather_completed_sections(state: ReportState) -> dict:
    """Collect research sections and make them available to final writers."""
    return {"completed_sections_context": state.get("completed_sections", [])}


def initiate_final_section_writing(state: ReportState) -> list:
    """Fan out non-research sections to write_final_sections via Send."""
    return [
        Send(
            "write_final_sections",
            {
                "section": s,
                "completed_sections_context": state["completed_sections_context"],
                "messages": [],
                "scratchpad": "",
            },
        )
        for s in state["sections"]
        if not s.research
    ]


def compile_final_report(state: ReportState) -> dict:
    """Assemble all completed sections into the final markdown report."""
    completed = {s.name: s.content for s in state["completed_sections"]}
    for section in state["sections"]:
        section.content = completed[section.name]
    return {"final_report": "\n\n".join(s.content for s in state["sections"])}
