"""Planner agents: report plan generation and final section writing."""

import asyncio

from dspy import Predict
from langchain_core.runnables import RunnableConfig

from config import ReportConfig
from core.signatures import FinalInstructions, ReportPlanner
from core.states import ReportState, SectionState


async def generate_plan(state: ReportState, config: RunnableConfig) -> dict:
    """Generate a structured research plan using DSPy's ReportPlanner."""
    if state.get("sections"):
        return {"sections": state["sections"]}

    report_cfg = ReportConfig.from_runnable_config(config)

    planner = Predict(ReportPlanner)
    result = await asyncio.to_thread(
        planner,
        topic=state.get("topic"),
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
