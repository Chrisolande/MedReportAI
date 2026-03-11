import operator
from typing import Annotated

from langgraph.graph import MessagesState
from typing_extensions import TypedDict

from core.schemas import Section


def _keep_latest(_current, new):
    """Reducer used to resolve concurrent per-branch section payloads."""
    return new


class ReportStateInput(TypedDict):
    topic: str


class ReportStateOutput(TypedDict):
    final_report: str


class ReportState(TypedDict):
    topic: str
    sections: list[Section]
    section: Annotated[Section, _keep_latest]
    scratchpad: Annotated[str, _keep_latest]
    scratchpad_file: Annotated[str, _keep_latest]
    completed_sections: Annotated[list, operator.add]
    completed_sections_context: (
        str  # String of any completed sections from research to write final sections
    )
    final_report: str  # Final report


class SectionState(MessagesState):
    section: Section
    completed_sections_context: (
        str  # Narrative flow / dependency text from earlier sections
    )

    scratchpad: str
    scratchpad_file: str


class SectionStateOutput(TypedDict):
    completed_sections: Annotated[list[Section], operator.add]
