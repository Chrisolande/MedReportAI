import operator
from typing import Annotated

from langgraph.graph import MessagesState
from typing_extensions import TypedDict

from schemas import Section


class ReportStateInput(TypedDict):
    topic: str


class ReportStateOutput(TypedDict):
    final_report: str


class ReportState(TypedDict):
    topic: str
    sections: list[Section]
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
    # completed_sections: list[
    #     Section
    # ]  # Final key we duplicate in the outer state before sending it to the Send() API

    scratchpad: str
    scratchpad_file: str


class SectionStateOutput(TypedDict):
    completed_sections: list[Section]
