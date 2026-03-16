from typing import Annotated, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class ScratchpadState(BaseModel):
    """Conversation messages plus a persistent scratchpad."""

    messages: Annotated[list[AnyMessage], add_messages]
    scratchpad: str = Field(default="")


class WriteToScratchpad(BaseModel):
    """Write or append to the scratchpad."""

    notes: str = Field(description="Notes to write")
    mode: Literal["append", "replace"] = Field(default="append")


class ReadFromScratchpad(BaseModel):
    """Read from the scratchpad."""

    query: str = Field(
        default="all",
        description="What to look for. Use 'all' for everything.",
    )


class ClearScratchpad(BaseModel):
    """Clear the scratchpad."""

    confirm: bool = Field(description="Must be True to confirm")


class Section(BaseModel):
    name: str = Field(
        description="Section title reflecting PubMed study focus "
        "(e.g. 'Pediatric Mental Health Outcomes', 'Conflict-Related Injuries')"
    )
    description: str = Field(
        description="What peer-reviewed evidence this section will analyze"
    )
    research: bool = Field(
        description="True if requires PubMed search, systematic reviews, or clinical studies. "
        "False only for background or methodology sections."
    )
    content: str = Field(
        description="Evidence requirements: study types, population focus, clinical outcomes, "
        "or epidemiological data needed"
    )
    audience_complexity: str = Field(
        default="clinical_practitioners",
        description="One of: 'clinical_practitioners', 'public_health_officials', "
        "'medical_researchers', 'policy_makers'",
    )
    estimated_length: str = Field(
        default="standard",
        description="One of: 'brief', 'standard', 'comprehensive'",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Sections that must precede this one",
    )
    success_criteria: str = Field(
        default="",
        description="Specific evidence synthesis goal for this section",
    )
    sources: list[dict[str, str]] = Field(
        default_factory=list,
        description="Per-section source registry with stable IDs for citation grounding",
    )


class Sections(BaseModel):
    sections: list[Section] = Field(
        description="Sections following systematic review or evidence synthesis structure"
    )
    total_estimated_length: str = Field(
        default="systematic_review",
        description="One of: 'rapid_review', 'systematic_review', 'comprehensive_meta_analysis'",
    )
    primary_audience: str = Field(
        default="clinicians",
        description="One of: 'clinicians', 'public_health_officials', 'researchers', "
        "'humanitarian_workers', 'policy_makers'",
    )
    narrative_strategy: str = Field(
        default="systematic_review",
        description="One of: 'systematic_review', 'scoping_review', "
        "'epidemiological_analysis', 'clinical_evidence_synthesis'",
    )
