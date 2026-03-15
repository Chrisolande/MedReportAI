from langchain_core.documents import Document

from rag.retrieval_formatter import RetrieverReportGenerator


def test_process_retriever_results_groups_by_url_and_preserves_metadata():
    generator = RetrieverReportGenerator()
    docs = [
        Document(
            page_content="chunk 1",
            metadata={
                "Title": "Paper A",
                "Url": "https://example.org/a",
                "Authors": "One",
            },
        ),
        Document(
            page_content="chunk 2",
            metadata={
                "Title": "Paper A",
                "Url": "https://example.org/a",
                "Authors": "One",
            },
        ),
        Document(
            page_content="chunk 3",
            metadata={
                "Title": "Paper B",
                "Url": "No URL Available",
            },
        ),
    ]

    grouped = generator._process_retriever_results(docs)

    assert len(grouped) == 2
    assert len(grouped["https://example.org/a"]) == 2
    assert grouped["https://example.org/a"][0]["title"] == "Paper A"


def test_create_report_includes_stats_and_multichunk_section():
    generator = RetrieverReportGenerator(report_title="Custom Title")
    docs = [
        Document(
            page_content="chunk 1",
            metadata={
                "Title": "Paper A",
                "Url": "https://example.org/a",
                "relevance_score": 0.9,
            },
        ),
        Document(
            page_content="chunk 2",
            metadata={
                "Title": "Paper A",
                "Url": "https://example.org/a",
                "relevance_score": 0.8,
            },
        ),
    ]

    report = generator.create_report(docs)

    assert report["stats"]["total_docs"] == 1
    assert report["stats"]["total_chunks"] == 2
    assert "Custom Title" in report["markdown"]
    assert "Documents with Multiple Chunks" in report["markdown"]
