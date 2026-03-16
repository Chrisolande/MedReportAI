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

    assert "## Research Notes" in prompt
    assert "Findings" in prompt
    assert "Evidence" in prompt
    assert "Phase 2" in prompt


def test_synthesis_prompt_includes_numbered_citations():
    section = Section(
        name="Evidence",
        description="desc",
        research=True,
        content="",
    )
    registry = {
        "https://pubmed.ncbi.nlm.nih.gov/123/": 1,
        "https://who.int/report": 2,
    }
    sources = [
        {
            "url": "https://pubmed.ncbi.nlm.nih.gov/123/",
            "title": "Study A",
            "authors": "Smith J",
        },
        {"url": "https://who.int/report", "title": "WHO Report", "authors": ""},
    ]

    prompt = get_synthesis_prompt(
        section,
        research_context="Findings",
        citation_registry=registry,
        sources=sources,
    )

    assert "[1]" in prompt
    assert "[2]" in prompt
    assert "Study A" in prompt
    assert "WHO Report" in prompt
    assert "numbered citation [N]" in prompt
    assert "## Source Registry" in prompt
