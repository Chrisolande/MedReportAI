"""Planner agents: report plan generation and final section writing."""

import asyncio
import uuid

from dspy import Predict
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from config import ReportConfig
from core.signatures import FinalInstructions, ReportPlanner
from core.states import ReportState, SectionState


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return " ".join(
            p.get("text", "").strip()
            for p in content
            if isinstance(p, dict) and p.get("type") == "text"
        ).strip()
    return ""


def _topic_from_messages(state: ReportState) -> str:
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            text = _extract_text(msg.content)
            if text:
                return text
    return ""


async def generate_plan(state: ReportState, config: RunnableConfig) -> dict:
    """Generate a structured research plan using DSPy's ReportPlanner."""
    if state.get("sections"):
        return {"sections": state["sections"]}

    report_cfg = ReportConfig.from_runnable_config(config)

    topic = state.get("topic") or _topic_from_messages(state)
    if not topic:
        prompt_msg = (
            "Please provide a report topic, either in the `topic` field "
            "or as a user message."
        )
        return {
            "sections": [],
            "final_report": prompt_msg,
            "messages": [AIMessage(content=prompt_msg)],
        }

    run_id = str(uuid.uuid4())[:8]

    planner = Predict(ReportPlanner)
    result = await asyncio.to_thread(
        planner,
        topic=topic,
        context=report_cfg.context,
        report_organization=report_cfg.report_organization,
    )
    return {"sections": result.plan.sections, "run_id": run_id}


async def write_final_sections(state: SectionState) -> dict:
    """Write non-research sections (intro, conclusion) from accumulated context."""
    section = state["section"]
    completed_context = state.get("completed_sections_context", "")

    final_instructions = Predict(FinalInstructions)
    result = await asyncio.to_thread(
        final_instructions,
        section_title=section.name,
        section_topic=section.description,
        context=completed_context,
    )
    section.content = result.section_content

    return {"completed_sections": [section]}
