"""Entry point for MedReportAI.

Boots the environment, constructs the LangGraph pipeline, and exposes
``graph`` so that ``langgraph.json`` can reference ``app:graph``.
"""

from langgraph.graph import END, StateGraph

from agents.planner import generate_plan, write_final_sections
from config import ReportConfig, config
from core.nodes import (
    compile_final_report,
    gather_completed_sections,
    initiate_final_section_writing,
    initiate_section_writing,
    write_sections,
)
from core.states import (
    ReportState,
    ReportStateInput,
    ReportStateOutput,
    SectionState,
    SectionStateOutput,
)
from core.tool_node import tool_node, tools_condition

config.initialize_dspy()


# Section sub-graph


_section_builder = StateGraph(SectionState, output_schema=SectionStateOutput)
_section_builder.add_node("write_sections", write_sections)
_section_builder.add_node("tools", tool_node)
_section_builder.add_conditional_edges(
    "write_sections", tools_condition, {"tools": "tools", "__end__": END}
)
_section_builder.add_edge("tools", "write_sections")
_section_builder.set_entry_point("write_sections")


# Top-level report graph

_builder = StateGraph(
    ReportState,
    input_schema=ReportStateInput,
    output_schema=ReportStateOutput,
    context_schema=ReportConfig,
)
_builder.add_node("generate_report_plan", generate_plan)
_builder.add_node("build_section_with_tools", _section_builder.compile())
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

graph = _builder.compile()
