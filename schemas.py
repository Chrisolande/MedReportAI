from typing import Annotated, Literal

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class ScratchpadState(BaseModel):
    """State that includes conversation messages and a persistent scratchpad."""

    messages: Annotated[list[AnyMessage], add_messages]
    scratchpad: str = Field(
        default="",
        description="Persistent scratchpad for storing important context and notes",
    )


class WriteToScratchpad(BaseModel):
    """Write or append to the scratchpad for context retention."""

    notes: str = Field(description="The notes to write to the scratchpad")
    mode: Literal["append", "replace"] = Field(
        default="append",
        description="'append' adds to existing notes, 'replace' overwrites the existing notes",
    )


class ReadFromScratchpad(BaseModel):
    """Read context from scratchpad."""

    query: str = Field(
        default="all",
        description="What to look for in the scratchpad. Use 'all' for everything",
    )


class ClearScratchpad(BaseModel):
    """Clear the scratchpad to free up context."""

    confirm: bool = Field(
        description="Must be True to confirm the clearing of the scratchpad"
    )


class Section(BaseModel):
    name: str = Field(
        description="Medical research section title reflecting PubMed study focus (e.g., 'Pediatric Mental Health Outcomes', 'Conflict-Related Injuries', 'Public Health Impact')"
    )
    description: str = Field(
        description="Medical research context explaining what peer-reviewed evidence this section will analyze"
    )
    research: bool = Field(
        description="True if requires current PubMed literature search, systematic reviews, or specific clinical studies. False only for background/methodology sections"
    )
    content: str = Field(
        description="Specific medical evidence requirements: study types needed (RCTs, cohort studies, case reports), population focus, clinical outcomes, or epidemiological data"
    )

    audience_complexity: str = Field(
        description="Medical evidence level: 'clinical_practitioners', 'public_health_officials', 'medical_researchers', or 'policy_makers'",
        default="clinical_practitioners",
    )

    estimated_length: str = Field(
        description="Evidence depth: 'brief', 'standard', or 'comprehensive'",
        default="standard",
    )

    dependencies: list[str] = Field(
        description="Sections that must precede this one for proper medical context",
        default_factory=list,
    )

    success_criteria: str = Field(
        description="Specific medical research outcome or evidence synthesis goal",
        default="",
    )


class Sections(BaseModel):
    sections: list[Section] = Field(
        description="Medical literature review sections following systematic review or evidence synthesis structure"
    )

    total_estimated_length: str = Field(
        description="Medical review scope: 'rapid_review', 'systematic_review', or 'comprehensive_meta_analysis'",
        default="systematic_review",
    )

    primary_audience: str = Field(
        description="Target medical audience: 'clinicians', 'public_health_officials', 'researchers', 'humanitarian_workers', or 'policy_makers'",
        default="clinicians",
    )

    narrative_strategy: str = Field(
        description="Medical research approach: 'systematic_review', 'scoping_review', 'epidemiological_analysis', or 'clinical_evidence_synthesis'",
        default="systematic_review",
    )
