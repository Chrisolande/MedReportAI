import operator
from typing import Annotated

from langchain_core.messages import AnyMessage
from langgraph.graph import MessagesState
from typing_extensions import NotRequired, TypedDict

from core.schemas import Section


def _keep_latest(_current, new):
    """Always take the newest value from concurrent branches."""
    return new


def _merge_citation_registries(
    current: dict[str, int], new: dict[str, int]
) -> dict[str, int]:
    """Merge citation registries, preserving existing numbers and assigning new ones.

    Numbers from ``new`` are intentionally re-assigned sequentially to avoid
    conflicts when parallel fan-out workers independently number their URLs.
    """
    merged = dict(current) if current else {}
    for url, num in (new or {}).items():
        if url not in merged:
            next_num = max(merged.values(), default=0) + 1
            merged[url] = next_num
    return merged


class ReportStateInput(MessagesState):
    topic: NotRequired[str]


class ReportStateOutput(TypedDict):
    final_report: str
    messages: list[AnyMessage]


class ReportState(MessagesState):
    topic: NotRequired[str]
    run_id: str
    sections: list[Section]
    section: Annotated[Section, _keep_latest]
    scratchpad: Annotated[str, _keep_latest]
    scratchpad_file: Annotated[str, _keep_latest]
    active_csv_path: Annotated[str, _keep_latest]
    completed_sections: Annotated[list, operator.add]
    completed_sections_context: list[Section]
    quality_passed: bool
    quality_issues: list[str]
    final_report: str
    citation_registry: Annotated[dict[str, int], _merge_citation_registries]


class SectionState(MessagesState):
    section: Section
    completed_sections_context: list[Section]
    run_id: str
    scratchpad: str
    scratchpad_file: str
    active_csv_path: str
    sources: Annotated[list[dict[str, str]], _keep_latest]
    citation_registry: Annotated[dict[str, int], _merge_citation_registries]


class SectionStateOutput(TypedDict):
    completed_sections: Annotated[list[Section], operator.add]
