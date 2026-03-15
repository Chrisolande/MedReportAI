from core.schemas import Section
from prompts.section_writer import get_synthesis_prompt


def test_synthesis_prompt_includes_source_registry_block():
    section = Section(
        name="Evidence",
        description="desc",
        research=True,
        content="",
    )

    prompt = get_synthesis_prompt(section, research_context="Findings")

    assert "## Your Research Notes (Scratchpad)" in prompt
    assert "Findings" in prompt
    assert "PHASE 2 DIRECTIVE: WRITE ONLY" in prompt
    assert "START your response with the section heading" in prompt
    assert "# Evidence" in prompt
