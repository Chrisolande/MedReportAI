from core.schemas import Section
from prompts.section_writer import get_synthesis_prompt


def test_synthesis_prompt_includes_source_registry_block():
    section = Section(
        name="Evidence",
        description="desc",
        research=True,
        content="",
    )

    prompt = get_synthesis_prompt(
        section,
        research_context="Findings",
        source_registry="- [S1] pubmed/123: https://pubmed.ncbi.nlm.nih.gov/123",
    )

    assert "Captured Source Registry" in prompt
    assert "[S1] pubmed/123" in prompt
