import operator
from typing import Annotated

from langgraph.graph import MessagesState
from typing_extensions import NotRequired, TypedDict

from core.schemas import Section


def _keep_latest(_current, new):
    """Reducer used to resolve concurrent per-branch section payloads."""
    return new


class ReportStateInput(MessagesState):
    topic: NotRequired[str]


class ReportStateOutput(TypedDict):
    final_report: str


class ReportState(MessagesState):
    topic: NotRequired[str]
    sections: list[Section]
    section: Annotated[Section, _keep_latest]
    scratchpad: Annotated[str, _keep_latest]
    scratchpad_file: Annotated[str, _keep_latest]
    active_csv_path: Annotated[str, _keep_latest]
    completed_sections: Annotated[list, operator.add]
    completed_sections_context: list[Section]
    quality_passed: bool
    quality_issues: list[str]
    final_report: str  # Final report


class SectionState(MessagesState):
    section: Section
    completed_sections_context: list[Section]

    scratchpad: str
    scratchpad_file: str
    active_csv_path: str
    sources: Annotated[list[dict[str, str]], _keep_latest]


class SectionStateOutput(TypedDict):
    completed_sections: Annotated[list[Section], operator.add]
