"""Planner agents: report plan generation and final section writing."""

import asyncio

from dspy import Predict
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from config import ReportConfig
from core.signatures import FinalInstructions, ReportPlanner
from core.states import ReportState, SectionState


def _topic_from_messages(state: ReportState) -> str:
    messages = state.get("messages", [])
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            content = msg.content
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                text_parts = [
                    p.get("text", "").strip()
                    for p in content
                    if isinstance(p, dict) and p.get("type") == "text"
                ]
                merged = " ".join(part for part in text_parts if part).strip()
                if merged:
                    return merged
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

    planner = Predict(ReportPlanner)
    result = await asyncio.to_thread(
        planner,
        topic=topic,
        context=report_cfg.context,
        report_organization=report_cfg.report_organization,
    )
    return {"sections": result.plan.sections}


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
