from langgraph.types import Send

from core.nodes import (
    compile_final_report,
    gather_completed_sections,
    initiate_final_section_writing,
    initiate_section_writing,
    validate_report_quality,
)
from core.quality import (
    build_references_block,
    enforce_source_linkage,
    extract_urls,
    merge_sources,
    validate_report_sections,
)
from core.schemas import Section
from core.states import ReportState


def test_extract_urls_deduplicates_and_normalizes():
    text = "Study: https://example.org/a. Another copy https://example.org/a and https://x.y/z)"
    urls = extract_urls(text)
    assert urls == ["https://example.org/a", "https://x.y/z"]


def test_merge_sources_assigns_stable_ids():
    existing = [{"id": "S1", "url": "https://a.test/1", "label": "a/1"}]
    text = "Found https://a.test/1 and https://b.test/2"

    merged = merge_sources(existing, text)

    assert len(merged) == 2
    assert merged[0]["id"] == "S1"
    assert merged[1]["id"] == "S2"
    assert merged[1]["url"] == "https://b.test/2"


def test_enforce_source_linkage_adds_citation_anchor_without_sources_block():
    content = "## Findings\n\nTrauma prevalence increased in conflict settings."
    sources = [
        {
            "id": "S1",
            "url": "https://pubmed.ncbi.nlm.nih.gov/123",
            "label": "pubmed/123",
            "title": "Study A",
        },
        {
            "id": "S2",
            "url": "https://who.int/report",
            "label": "who/report",
            "title": "WHO Report",
        },
    ]

    linked = enforce_source_linkage(content, sources)

    assert "Evidence grounding: [S1], [S2]." in linked
    assert "### Sources" not in linked


def test_validate_report_sections_flags_research_without_citations():
    sections = [
        Section(
            name="Mental Health Impact",
            description="...",
            research=True,
            content="## Mental Health\n\nSymptoms increased.",
            sources=[
                {
                    "id": "S1",
                    "url": "https://pubmed.ncbi.nlm.nih.gov/123",
                    "label": "pubmed/123",
                }
            ],
        ),
        Section(
            name="Introduction",
            description="...",
            research=False,
            content="# Introduction\n\nScope overview.",
        ),
    ]

    issues = validate_report_sections(sections)

    assert any("no source citations" in issue for issue in issues)


def test_compile_final_report_handles_missing_completed_sections():
    sections = [
        Section(name="Intro", description="...", research=False, content=""),
        Section(name="Findings", description="...", research=True, content=""),
    ]

    state: ReportState = {
        "sections": sections,
        "completed_sections": [
            Section(
                name="Intro",
                description="...",
                research=False,
                content="# Intro",
                sources=[
                    {
                        "id": "S1",
                        "url": "https://pubmed.ncbi.nlm.nih.gov/123",
                        "label": "pubmed/123",
                        "title": "Assessing pediatric outcomes",
                        "authors": "Doe J, Smith A",
                    }
                ],
            )
        ],
        "topic": "x",
        "section": sections[0],
        "scratchpad": "",
        "scratchpad_file": "",
        "active_csv_path": "",
        "completed_sections_context": [],
        "quality_passed": False,
        "quality_issues": [],
        "final_report": "",
    }

    result = compile_final_report(state)

    assert "final_report" in result
    assert "# Intro" in result["final_report"]
    assert (
        "Section content could not be generated in this run." in result["final_report"]
    )


def test_merge_sources_extracts_title_and_authors_from_retriever_markdown():
    text = (
        "## 1. Childhood malnutrition care during siege\n"
        "**Authors:** Helu Yasmin El, Salah Said  \n"
        "**Publication Date:** 2026-Jan-20  \n"
        "**URL:** https://www.ncbi.nlm.nih.gov/pubmed/41559813  \n"
    )

    merged = merge_sources([], text)

    assert len(merged) == 1
    assert merged[0]["title"] == "Childhood malnutrition care during siege"
    assert merged[0]["authors"] == "Helu Yasmin El, Salah Said"


def test_build_references_block_formats_title_authors_link():
    references = build_references_block(
        [
            {
                "id": "S1",
                "url": "https://example.org/study-a",
                "label": "example/study-a",
                "title": "Study A",
                "authors": "Author One, Author Two",
            },
            {
                "id": "S2",
                "url": "https://example.org/study-b",
                "label": "example/study-b",
                "title": "Study B",
                "authors": "",
            },
        ]
    )

    assert references.startswith("## References")
    assert (
        "1. Study A. Authors: Author One, Author Two. https://example.org/study-a"
        in references
    )
    assert "2. Study B. https://example.org/study-b" in references


def test_initiate_section_writing_fans_out_research_sections():
    sections = [
        Section(name="A", description="", research=True, content=""),
        Section(name="B", description="", research=False, content=""),
    ]

    routes = initiate_section_writing({"sections": sections})

    assert isinstance(routes, list)
    assert len(routes) == 1
    assert all(isinstance(route, Send) for route in routes)
    assert routes[0].node == "build_section_with_tools"


def test_initiate_final_section_writing_routes_non_research_sections():
    sections = [
        Section(name="A", description="", research=True, content=""),
        Section(name="B", description="", research=False, content=""),
    ]

    routes = initiate_final_section_writing(
        {"sections": sections, "completed_sections_context": []}
    )

    assert isinstance(routes, list)
    assert len(routes) == 1
    assert routes[0].node == "write_final_sections"


def test_gather_completed_sections_copies_context_list():
    completed = [Section(name="A", description="", research=False, content="ok")]

    update = gather_completed_sections({"completed_sections": completed})

    assert update == {"completed_sections_context": completed}


def test_validate_report_quality_appends_diagnostics_on_failure():
    sections = [
        Section(
            name="Research",
            description="",
            research=True,
            content="No citations here",
            sources=[{"id": "S1", "url": "https://example.org/1", "label": "x/1"}],
        )
    ]

    result = validate_report_quality({"sections": sections, "final_report": "Body"})

    assert result["quality_passed"] is False
    assert result["quality_issues"]
    assert "Quality Checks" in result["final_report"]
