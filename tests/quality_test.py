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
    detect_truncation,
    detect_unresolved_placeholders,
    enforce_source_linkage,
    extract_urls,
    is_valid_source_url,
    merge_sources,
    normalize_pubmed_url,
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
            "url": "https://pubmed.ncbi.nlm.nih.gov/123/",
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
    registry = {
        "https://pubmed.ncbi.nlm.nih.gov/123/": 1,
        "https://who.int/report": 2,
    }

    linked = enforce_source_linkage(content, sources, registry)

    assert "Evidence grounding: [1], [2]." in linked
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

    assert any("no numbered citations" in issue for issue in issues)


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
        "citation_registry": {},
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
        "[1] Study A. Authors: Author One, Author Two. https://example.org/study-a"
        in references
    )
    assert "[2] Study B. https://example.org/study-b" in references


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


def test_is_valid_source_url_filters_cdn_and_assets():
    assert is_valid_source_url("https://pubmed.ncbi.nlm.nih.gov/123456/") is True
    assert is_valid_source_url("https://cdn.example.com/icon.svg") is False
    assert is_valid_source_url("https://static.example.com/logo.png") is False
    assert is_valid_source_url("https://fonts.googleapis.com/css") is False
    assert is_valid_source_url("https://example.com/favicon.ico") is False
    assert is_valid_source_url("") is False
    assert is_valid_source_url("ftp://not-http.org") is False


def test_normalize_pubmed_url_deduplicates_by_pmid():
    assert (
        normalize_pubmed_url("https://pubmed.ncbi.nlm.nih.gov/12345/")
        == "https://pubmed.ncbi.nlm.nih.gov/12345/"
    )
    assert (
        normalize_pubmed_url("https://www.ncbi.nlm.nih.gov/pubmed/12345")
        == "https://pubmed.ncbi.nlm.nih.gov/12345/"
    )
    assert (
        normalize_pubmed_url("https://pubmed.ncbi.nlm.nih.gov/12345")
        == "https://pubmed.ncbi.nlm.nih.gov/12345/"
    )
    assert (
        normalize_pubmed_url("https://example.org/article")
        == "https://example.org/article"
    )


def test_merge_sources_filters_invalid_urls():
    text = "Found https://cdn.example.com/style.css and https://pubmed.ncbi.nlm.nih.gov/999/"
    merged = merge_sources([], text)
    assert len(merged) == 1
    assert merged[0]["url"] == "https://pubmed.ncbi.nlm.nih.gov/999/"


def test_build_numbered_references_only_includes_cited():
    registry = {
        "https://example.org/a": 1,
        "https://example.org/b": 2,
        "https://example.org/c": 3,
    }
    sources = [
        {"url": "https://example.org/a", "title": "Study A", "authors": ""},
        {"url": "https://example.org/b", "title": "Study B", "authors": ""},
        {"url": "https://example.org/c", "title": "Study C", "authors": ""},
    ]
    body = "Some finding [1] and another [3] but not 2."
    refs = build_references_block(sources, citation_registry=registry, body_text=body)
    assert "[1] Study A" in refs
    assert "[3] Study C" in refs
    assert "[2] Study B" not in refs


def test_compile_final_report_with_numbered_citations():
    sections = [
        Section(
            name="Findings",
            description="...",
            research=True,
            content="## Findings\n\nPrevalence is high [1] and rising [2].",
            sources=[
                {"url": "https://example.org/a", "title": "Study A", "authors": ""},
                {
                    "url": "https://example.org/b",
                    "title": "Study B",
                    "authors": "J Smith",
                },
            ],
        ),
    ]

    state: ReportState = {
        "sections": sections,
        "completed_sections": [sections[0]],
        "topic": "test",
        "section": sections[0],
        "scratchpad": "",
        "scratchpad_file": "",
        "active_csv_path": "",
        "completed_sections_context": [],
        "quality_passed": False,
        "quality_issues": [],
        "final_report": "",
        "citation_registry": {
            "https://example.org/a": 1,
            "https://example.org/b": 2,
        },
    }

    result = compile_final_report(state)
    assert "[1] Study A" in result["final_report"]
    assert "[2] Study B. Authors: J Smith" in result["final_report"]


def test_detect_truncation_flags_short_and_unterminated():
    # Short content without terminal punctuation
    short = "This is a brief section that ends abruptly without"
    issues = detect_truncation(short)
    assert any("under 200 words" in i for i in issues)
    assert any("terminal punctuation" in i for i in issues)
    assert any("dangling sentence fragment" in i for i in issues)

    # Properly terminated content (still short)
    terminated = "This section has proper punctuation."
    issues = detect_truncation(terminated)
    assert any("under 200 words" in i for i in issues)
    assert not any("terminal punctuation" in i for i in issues)

    # Long content with terminal punctuation
    long_content = " ".join(["word"] * 250) + "."
    issues = detect_truncation(long_content)
    assert not any("under 200 words" in i for i in issues)
    assert not any("terminal punctuation" in i for i in issues)


def test_detect_unresolved_placeholders_catches_all_patterns():
    content = (
        "Prevalence was high [S1] and increasing [S2]. "
        "According to [Source 1], outcomes were poor. "
        "Evidence grounding: [1], [2]. "
        "See [Research Finding 1] for details."
    )
    issues = detect_unresolved_placeholders(content)
    assert any("[SN] placeholders" in i for i in issues)
    assert any("[Source N] placeholders" in i for i in issues)
    assert any("Evidence grounding:" in i for i in issues)
    assert any("[Research Finding N] placeholders" in i for i in issues)

    # Clean content should have no issues
    clean = "Prevalence was 45% according to recent studies [1]. Outcomes improved [2]."
    issues = detect_unresolved_placeholders(clean)
    assert issues == []
