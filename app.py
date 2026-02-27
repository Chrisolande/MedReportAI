"""Entry point for MedReportAI – Medical Report Generation System.

This module wires together all refactored sub-packages (config, core, rag,
prompts, utils) into a runnable LangGraph application and exposes the
top-level ``graph`` variable required by ``langgraph.json``.
"""

import asyncio
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from dspy import Predict
from langchain.tools import tool
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_tavily import TavilySearch
from langgraph.graph import END, StateGraph
from langgraph.types import Send
from loguru import logger

from config import config
from core.schemas import ClearScratchpad, ReadFromScratchpad, WriteToScratchpad
from core.signatures import FinalInstructions, MultiQueryGenerator, ReportPlanner
from core.states import (
    ReportState,
    ReportStateInput,
    ReportStateOutput,
    SectionState,
    SectionStateOutput,
)
from prompts.planner import context, report_organization
from prompts.section_writer import (
    get_initial_prompt,
    get_synthesis_prompt,
    section_writer_prompt,
)
from rag.embeddings import initialize_embeddings
from rag.retrieval import build_retriever
from rag.retrieval_formatter import RetrieverReportGenerator
from rag.source_formatter import SourceFormatter
from utils.data_processing import load_documents_from_csv, split_documents
from utils.helpers import setup_environment

# ---------------------------------------------------------------------------
# Environment & LLM initialisation
# ---------------------------------------------------------------------------

setup_environment()

llm = config.initialize_llm()
config.initialize_dspy()

# ---------------------------------------------------------------------------
# Retriever – lazy singleton
# ---------------------------------------------------------------------------

_retriever = None


def _get_retriever():
    """Return the shared retriever, building it on first call."""
    global _retriever
    if _retriever is not None:
        return _retriever

    embeddings = initialize_embeddings(
        model_name=config.model.embedding_model,
        cache_dir=config.model.embedding_cache_dir,
    )

    csv_path = config.paths.data_dir / "tests.csv"
    if not csv_path.exists():
        logger.warning(
            f"Data file not found at {csv_path}. Retriever will not be available."
        )
        return None

    documents = load_documents_from_csv(csv_path)
    splitted_documents = split_documents(documents, embeddings)
    _retriever = build_retriever(splitted_documents, embeddings, config.retriever)
    return _retriever


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _save_scratchpad(content: str, filepath: str) -> None:
    """Persist scratchpad content to a markdown file under ``scratchpads/``."""
    base_dir = Path("scratchpads")
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / filepath).write_text(content, encoding="utf-8")


def _deduplicate_documents(documents: list[list[Document]]) -> list[Document]:
    """Flatten and deduplicate documents by page content."""
    seen: set[str] = set()
    unique: list[Document] = []
    for doc_list in documents:
        for doc in doc_list:
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                unique.append(doc)
    return unique


def _generate_queries(question: str, num_queries: int = 1) -> list[str]:
    """Expand a single question into *num_queries* diverse search queries."""
    if not question.strip():
        logger.error("Empty query provided")
        return [question]
    try:
        optimizer = Predict(MultiQueryGenerator)
        return optimizer(
            question=question, num_queries=num_queries
        ).search_queries
    except Exception as exc:
        logger.error(f"Query generation failed: {exc}")
        return [question]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@tool
async def retriever_tool(search_query: str) -> str:
    """Retrieve PubMed documents and return a formatted markdown report."""
    retriever = _get_retriever()
    if retriever is None:
        return "Retriever is not available – data files may be missing."
    try:
        report_gen = RetrieverReportGenerator()
        result = await retriever.ainvoke(search_query)
        if not result:
            logger.warning(f"No results for query: {search_query}")
            return "No relevant documents found for the given query."
        deduped = _deduplicate_documents([result])
        return report_gen.create_report(deduped)["markdown"]
    except Exception as exc:
        logger.error(f"retriever_tool error: {exc}")
        return f"Error retrieving data: {exc}"


async def _tavily_search_async(
    search_query: str,
    max_results: int = 1,
    num_queries: int = 1,
    include_raw_content: bool = False,
    topic: Literal["general", "news", "finance"] = "general",
) -> list:
    """Run one or more Tavily searches concurrently."""
    if not search_query.strip():
        logger.warning("Empty search query passed to Tavily")
    try:
        tavily = TavilySearch(
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic=topic,
        )
        if num_queries > 1:
            try:
                queries = _generate_queries(
                    question=search_query, num_queries=num_queries
                )
            except Exception as exc:
                logger.warning(f"Query expansion failed, using original: {exc}")
                queries = [search_query]
        else:
            queries = [search_query]
        tasks = [tavily.ainvoke({"query": q}) for q in queries]
        return await asyncio.gather(*tasks)
    except Exception as exc:
        logger.error(f"Tavily search error: {exc}")
        return []


@tool
async def web_search(
    search_query: str,
    max_results: int = 1,
    include_raw_content: bool = True,
    markdown_output: bool = False,
) -> str:
    """Search the web and return deduplicated, formatted source content."""
    try:
        formatter = SourceFormatter(markdown_output=markdown_output)
        response = await _tavily_search_async(
            search_query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            num_queries=1,
        )
        return formatter.deduplicate_and_format_sources(response)
    except Exception as exc:
        logger.error(f"web_search error: {exc}")
        return ""


# ---------------------------------------------------------------------------
# Tool-node infrastructure
# ---------------------------------------------------------------------------

_section_tools = [
    WriteToScratchpad,
    ReadFromScratchpad,
    ClearScratchpad,
    web_search,
    retriever_tool,
]
_llm_with_tools = llm.bind_tools(_section_tools)
_tool_by_name: dict = {
    (t.name if hasattr(t, "name") else t.__name__): t for t in _section_tools
}


def _handle_write(
    tool_args: dict, state: SectionState, tool_call_id: str
) -> tuple[str, ToolMessage]:
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


def _handle_read(
    tool_args: dict, state: SectionState, tool_call_id: str
) -> ToolMessage:
    scratchpad = state.get("scratchpad") or "Scratchpad is empty."
    query = tool_args.get("query", "all")
    if query != "all":
        content = f"Scratchpad contents (query: '{query}'):\n\n{scratchpad}"
    else:
        content = f"Scratchpad contents:\n\n{scratchpad}"
    return ToolMessage(content=content, tool_call_id=tool_call_id)


def _handle_clear(
    tool_args: dict, tool_call_id: str
) -> tuple[str | None, ToolMessage]:
    if tool_args.get("confirm", False):
        return "", ToolMessage(
            content="Scratchpad cleared successfully.", tool_call_id=tool_call_id
        )
    return None, ToolMessage(
        content="Scratchpad clear cancelled (confirm=False).",
        tool_call_id=tool_call_id,
    )


async def _handle_external(
    tool_name: str, tool_args: dict, tool_call_id: str
) -> ToolMessage:
    t = _tool_by_name[tool_name]
    observation = await t.ainvoke(tool_args)
    return ToolMessage(content=str(observation), tool_call_id=tool_call_id)


async def tool_node(state: SectionState) -> dict:
    """Execute all pending tool calls and return updated state."""
    last_message = state["messages"][-1]
    if not getattr(last_message, "tool_calls", None):
        return {"messages": []}

    result_messages: list[ToolMessage] = []
    scratchpad_update: str | None = None
    scratchpad_file: str = state.get("scratchpad_file", "")

    for tool_call in last_message.tool_calls:
        name = tool_call["name"]
        args = tool_call["args"]
        call_id = tool_call["id"]

        if name == "WriteToScratchpad":
            scratchpad_update, msg = _handle_write(args, state, call_id)
            result_messages.append(msg)
        elif name == "ReadFromScratchpad":
            result_messages.append(_handle_read(args, state, call_id))
        elif name == "ClearScratchpad":
            scratchpad_update, msg = _handle_clear(args, call_id)
            result_messages.append(msg)
        else:
            result_messages.append(
                await _handle_external(name, args, call_id)
            )

    update: dict = {"messages": result_messages}
    if scratchpad_update is not None:
        update["scratchpad"] = scratchpad_update
        if scratchpad_file:
            _save_scratchpad(scratchpad_update, scratchpad_file)
    return update


def tools_condition(state: SectionState) -> str:
    """Route to *tools* if tool calls are pending, otherwise end."""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END


# ---------------------------------------------------------------------------
# Report configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class ReportConfig:
    """Configurable fields injected into the report-generation pipeline."""

    context: str = context
    report_organization: str = report_organization

    @classmethod
    def from_runnable_config(
        cls, runnable_config: RunnableConfig | None = None
    ) -> "ReportConfig":
        cfg = runnable_config.get("configurable", {}) if runnable_config else {}
        return cls(
            context=(
                os.environ.get("CONTEXT") or cfg.get("context") or context
            ),
            report_organization=(
                os.environ.get("REPORT_ORGANIZATION")
                or cfg.get("report_organization")
                or report_organization
            ),
        )


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


def generate_plan(state: ReportState, config: RunnableConfig) -> dict:
    """Generate a structured research plan using DSPy's ReportPlanner."""
    report_cfg = ReportConfig.from_runnable_config(config)
    planner = Predict(ReportPlanner)
    result = planner(
        topic=state.get("topic"),
        context=report_cfg.context,
        report_organization=report_cfg.report_organization,
    )
    return {"sections": result.plan.sections}


def write_sections(state: SectionState) -> dict:
    """Two-phase (extraction → synthesis) section writer node."""
    messages = state.get("messages", [])
    section = state["section"]
    scratchpad = state.get("scratchpad", "")
    scratchpad_file = state.get("scratchpad_file", "")

    if not scratchpad_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        MAX_SLUG_LENGTH = 30
        slug = section.name.lower().replace(" ", "_")[:MAX_SLUG_LENGTH]
        scratchpad_file = f"scratchpad_{slug}_{timestamp}.md"

    tool_messages = [m for m in messages if isinstance(m, ToolMessage)]
    ai_tool_rounds = len(
        [m for m in messages if getattr(m, "tool_calls", None)]
    )

    logger.info(
        f"Section '{section.name}': round {ai_tool_rounds}, "
        f"{len(tool_messages)} tool results, scratchpad {len(scratchpad)} chars"
    )

    MAX_RESEARCH_ROUNDS = 4
    MIN_SCRATCHPAD_LENGTH_FOR_EARLY_SYNTHESIS = 100
    should_synthesize = ai_tool_rounds >= MAX_RESEARCH_ROUNDS or (
        len(scratchpad) > MIN_SCRATCHPAD_LENGTH_FOR_EARLY_SYNTHESIS
        and ai_tool_rounds >= 3
    )

    if should_synthesize:
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
        response = llm.invoke(phase2_messages)
        section.content = response.content
        if scratchpad:
            _save_scratchpad(scratchpad, scratchpad_file)
        return {
            "messages": phase2_messages + [response],
            "completed_sections": [section],
            "scratchpad_file": scratchpad_file,
        }

    # Phase 1: Research
    if not messages:
        messages = [
            SystemMessage(content=section_writer_prompt),
            HumanMessage(content=get_initial_prompt(section)),
        ]

    response = _llm_with_tools.invoke(messages)

    # LLM decided it has enough information without tool use
    if not getattr(response, "tool_calls", None):
        if "Phase 1" in response.content and "complete" in response.content:
            logger.info(f"LLM signalled Phase 1 complete for '{section.name}'")
        else:
            section.content = response.content
            return {
                "messages": messages + [response],
                "completed_sections": [section],
                "scratchpad_file": scratchpad_file,
            }

    return {"messages": messages + [response], "scratchpad_file": scratchpad_file}


def initiate_section_writing(state: ReportState) -> list:
    """Fan out research-intensive sections to parallel workers via ``Send``."""
    return [
        Send("build_section_with_tools", {"section": s})
        for s in state["sections"]
        if s.research
    ]


def gather_completed_sections(state: ReportState) -> dict:
    """Collect research sections and make them available to final writers."""
    return {"completed_sections_context": state.get("completed_sections", [])}


def write_final_sections(state: SectionState) -> dict:
    """Write non-research sections (intro, conclusion) from accumulated context."""
    section = state["section"]
    completed_context = state.get("completed_sections_context", "")
    final_instructions = Predict(FinalInstructions)
    section.content = final_instructions(
        section_title=section.name,
        section_topic=section.description,
        context=completed_context,
    ).section_content
    return {"completed_sections": [section]}


def initiate_final_section_writing(state: ReportState) -> list:
    """Fan out non-research sections to ``write_final_sections`` via ``Send``."""
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


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

# -- Section sub-graph -------------------------------------------------------
_section_graph = StateGraph(SectionState, output_schema=SectionStateOutput)
_section_graph.add_node("write_sections", write_sections)
_section_graph.add_node("tools", tool_node)
_section_graph.add_conditional_edges(
    "write_sections", tools_condition, {"tools": "tools", "__end__": END}
)
_section_graph.add_edge("tools", "write_sections")
_section_graph.set_entry_point("write_sections")

# -- Top-level report graph --------------------------------------------------
_builder = StateGraph(
    ReportState,
    input_schema=ReportStateInput,
    output_schema=ReportStateOutput,
    context_schema=ReportConfig,
)
_builder.add_node("generate_report_plan", generate_plan)
_builder.add_node("build_section_with_tools", _section_graph.compile())
_builder.add_node("gather_sections", gather_completed_sections)
_builder.add_node("write_final_sections", write_final_sections)
_builder.add_node("compile_final_report", compile_final_report)

_builder.add_conditional_edges(
    "generate_report_plan",
    initiate_section_writing,
    ["build_section_with_tools"],
)
_builder.add_edge("build_section_with_tools", "gather_sections")
_builder.add_conditional_edges(
    "gather_sections",
    initiate_final_section_writing,
    ["write_final_sections"],
)
_builder.add_edge("write_final_sections", "compile_final_report")
_builder.set_entry_point("generate_report_plan")

# Publicly exposed graph – referenced by langgraph.json
graph = _builder.compile()
