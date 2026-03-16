"""Graph node functions for the section writer sub-graph and report graph.

All infrastructure concerns (tool dispatch, scratchpad I/O) live in core.tool_node.
These nodes focus purely on LLM orchestration logic.
"""

from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.types import Send
from loguru import logger

from config import config
from core.quality import (
    build_references_block,
    enforce_source_linkage,
    register_sources_in_citation_registry,
    validate_report_sections,
)
from core.states import ReportState, SectionState
from core.tool_node import SECTION_TOOLS, save_scratchpad_async
from core.verification import build_conservative_instruction, verify_scratchpad
from prompts.section_writer import (
    get_initial_prompt,
    get_synthesis_prompt,
    section_writer_prompt,
)
from utils.helpers import content_to_text

_llm = config.initialize_llm()
_llm_with_tools = _llm.bind_tools(SECTION_TOOLS)

MAX_RESEARCH_ROUNDS = 4
MIN_SCRATCHPAD_FOR_EARLY_SYNTHESIS = 100


# Section sub-graph node


def _default_scratchpad_file(section) -> str:
    slug = section.name.lower().replace(" ", "_")[:30]
    return f"scratchpad_{slug}_{datetime.now():%Y%m%d_%H%M%S}.md"


def _should_synthesize(tool_rounds: int, scratchpad_len: int) -> bool:
    return tool_rounds >= MAX_RESEARCH_ROUNDS or (
        scratchpad_len > MIN_SCRATCHPAD_FOR_EARLY_SYNTHESIS and tool_rounds >= 3
    )


async def _handle_verification_gap(
    section,
    scratchpad,
    messages,
    scratchpad_file,
    sources,
    tool_messages,
    citation_registry,
    tool_rounds,
):
    """Verify scratchpad and decide next phase."""
    verification = verify_scratchpad(scratchpad)
    if not verification.passed and tool_rounds < MAX_RESEARCH_ROUNDS:
        logger.info(
            f"Section '{section.name}': verification failed, returning to research. "
            f"Failures: {verification.failures}"
        )
        gap_note = (
            "The following quality criteria were not yet met:\n"
            + "\n".join(f"- {f}" for f in verification.failures)
            + "\nContinue researching to address these gaps."
        )
        return await _research_phase(
            section,
            messages + [HumanMessage(content=gap_note)],
            scratchpad_file,
            sources,
        )

    research_context_prefix = ""
    if not verification.passed:
        logger.warning(
            f"Section '{section.name}': verification failed but no rounds remain. "
            f"Proceeding with conservative synthesis."
        )
        research_context_prefix = build_conservative_instruction(verification.failures)

    return await _synthesis_phase(
        section,
        scratchpad,
        tool_messages,
        scratchpad_file,
        sources,
        citation_registry,
        research_context_prefix,
    )


async def write_sections(state: SectionState) -> dict:
    """Two-phase (research -> synthesis) section writer node."""
    messages = state.get("messages", [])
    section = state["section"]
    scratchpad = state.get("scratchpad", "")
    scratchpad_file = state.get("scratchpad_file", "") or _default_scratchpad_file(
        section
    )
    sources = state.get("sources", [])
    citation_registry = state.get("citation_registry", {}) or {}

    tool_rounds = len([m for m in messages if getattr(m, "tool_calls", None)])
    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]

    logger.info(
        f"Section '{section.name}': round {tool_rounds}, "
        f"{len(tool_messages)} tool results, scratchpad {len(scratchpad)} chars"
    )

    if _should_synthesize(tool_rounds, len(scratchpad)):
        return await _handle_verification_gap(
            section,
            scratchpad,
            messages,
            scratchpad_file,
            sources,
            tool_messages,
            citation_registry,
            tool_rounds,
        )
    return await _research_phase(section, messages, scratchpad_file, sources)


async def _research_phase(
    section, messages: list, scratchpad_file: str, sources: list[dict[str, str]]
) -> dict:
    """Phase 1: gather information via tool calls."""
    if not messages:
        messages = [
            SystemMessage(content=section_writer_prompt),
            HumanMessage(content=get_initial_prompt(section)),
        ]

    response = await _llm_with_tools.ainvoke(messages)

    if not getattr(response, "tool_calls", None):
        section.content = response.content
        return {
            "messages": messages + [response],
            "completed_sections": [section],
            "scratchpad_file": scratchpad_file,
        }

    return {"messages": messages + [response], "scratchpad_file": scratchpad_file}


async def _synthesis_phase(
    section,
    scratchpad: str,
    tool_messages: list,
    scratchpad_file: str,
    sources: list[dict[str, str]],
    citation_registry: dict[str, int] | None = None,
    research_context_prefix: str = "",
) -> dict:
    """Phase 2: synthesise research notes into final section content."""
    logger.info(f"Phase 2 synthesis triggered for '{section.name}'")

    if citation_registry is None:
        citation_registry = {}

    citation_registry = register_sources_in_citation_registry(
        sources, citation_registry
    )

    research_context = scratchpad or "\n\n".join(
        f"### Research Finding {i + 1}\n{m.content}"
        for i, m in enumerate(tool_messages)
    )

    if research_context_prefix:
        research_context = f"{research_context_prefix}\n\n{research_context}"

    if not research_context.strip():
        section.content = (
            f"## {section.name}\n\n"
            "Insufficient evidence was retrieved to write this section reliably. "
            "Please rerun research with a more specific query or broader date range."
        )
        section.sources = sources
        return {
            "completed_sections": [section],
            "scratchpad_file": scratchpad_file,
            "citation_registry": citation_registry,
        }

    phase2_messages = [
        SystemMessage(
            content=(
                "You are a medical report writer in Phase 2 (Synthesis). "
                "Write the section content based on your research notes. "
                "DO NOT call any tools."
            )
        ),
        HumanMessage(
            content=get_synthesis_prompt(
                section, research_context, citation_registry, sources
            )
        ),
    ]
    response = await _llm.ainvoke(phase2_messages)
    section.content = enforce_source_linkage(
        content_to_text(response.content), sources, citation_registry
    )
    section.sources = sources

    if scratchpad:
        await save_scratchpad_async(scratchpad, scratchpad_file)

    return {
        "messages": phase2_messages + [response],
        "completed_sections": [section],
        "scratchpad_file": scratchpad_file,
        "citation_registry": citation_registry,
    }


# Top-level report graph nodes


def _fan_out(node: str, sections: list, extra_state: dict) -> list[Send]:
    return [
        Send(
            node,
            {
                "section": s,
                "messages": [],
                "scratchpad": "",
                "scratchpad_file": "",
                "active_csv_path": "",
                "sources": [],
                "citation_registry": {},
                **extra_state,
            },
        )
        for s in sections
    ]


def initiate_section_writing(state: ReportState) -> list[Send] | str:
    """Fan out research-intensive sections to parallel workers via Send."""
    sections = [s for s in state["sections"] if s.research]
    extra = {"run_id": state.get("run_id", "")}
    return _fan_out("build_section_with_tools", sections, extra) or "gather_sections"


def gather_completed_sections(state: ReportState) -> dict:
    return {"completed_sections_context": state.get("completed_sections", [])}


def initiate_final_section_writing(state: ReportState) -> list[Send] | str:
    """Fan out non-research sections to write_final_sections via Send."""
    sections = [s for s in state["sections"] if not s.research]
    ctx = {
        "completed_sections_context": state["completed_sections_context"],
        "run_id": state.get("run_id", ""),
    }
    return _fan_out("write_final_sections", sections, ctx) or "compile_final_report"


def compile_final_report(state: ReportState) -> dict:
    """Assemble all completed sections into the final markdown report."""
    completed = {s.name: s.content for s in state.get("completed_sections", [])}
    all_sources: list[dict[str, str]] = []
    missing: list[str] = []
    citation_registry = state.get("citation_registry", {}) or {}

    for section in state["sections"]:
        if section.name in completed:
            section.content = completed[section.name]
        else:
            missing.append(section.name)
            section.content = (
                f"## {section.name}\n\n"
                "Section content could not be generated in this run. "
                "Please retry the pipeline for complete output."
            )
        all_sources.extend(section.sources or [])

    if missing:
        logger.warning("compile_final_report missing sections: " + ", ".join(missing))

    report_body = "\n\n".join(s.content for s in state["sections"])
    if refs := build_references_block(
        all_sources, citation_registry=citation_registry, body_text=report_body
    ):
        report_body = f"{report_body}\n\n{refs}"

    return {"final_report": report_body}


def validate_report_quality(state: ReportState) -> dict:
    """Validate report grounding and append quality diagnostics when needed."""
    issues = validate_report_sections(state.get("sections", []))
    final_report = state.get("final_report", "")

    if issues:
        diagnostics = "\n".join(f"- {i}" for i in issues)
        final_report = (
            f"{final_report}\n\n## Quality Checks\n\n"
            f"The following report quality checks failed:\n{diagnostics}"
        ).strip()

    final_message = AIMessage(content=final_report)

    return {
        "quality_passed": not issues,
        "quality_issues": issues,
        "final_report": final_report,
        "messages": [final_message],
    }
