import asyncio

import pandas as pd

from tools import pubmed_search


def _make_df(records):
    """Build a real pandas DataFrame from a list of dicts."""
    return pd.DataFrame(records)


def test_pubmed_scraper_tool_rejects_empty_query():
    result = asyncio.run(
        pubmed_search.pubmed_scraper_tool.ainvoke({"search_query": "   "})
    )

    assert "cannot be empty" in result


def test_pubmed_scraper_tool_requires_entrez_email(monkeypatch):
    monkeypatch.delenv("ENTREZ_EMAIL", raising=False)

    result = asyncio.run(
        pubmed_search.pubmed_scraper_tool.ainvoke({"search_query": "nutrition"})
    )

    assert "ENTREZ_EMAIL is not configured" in result


def test_pubmed_scraper_tool_handles_empty_result_set(monkeypatch):
    class DummyScraper:
        def __init__(self, **kwargs):
            pass

        async def scrape_async(self):
            return _make_df([])

    monkeypatch.setenv("ENTREZ_EMAIL", "research@example.org")
    monkeypatch.setattr(pubmed_search, "PubMedScraper", DummyScraper)

    result = asyncio.run(
        pubmed_search.pubmed_scraper_tool.ainvoke({"search_query": "nutrition"})
    )

    assert "No PubMed studies found" in result


def test_pubmed_scraper_tool_handles_records_without_titles(monkeypatch):
    df = _make_df([{"Title": "", "Journal": "J", "Publication Date": "2020"}])

    class DummyScraper:
        def __init__(self, **kwargs):
            pass

        async def scrape_async(self):
            return df

    monkeypatch.setenv("ENTREZ_EMAIL", "research@example.org")
    monkeypatch.setattr(pubmed_search, "PubMedScraper", DummyScraper)
    monkeypatch.setattr(pubmed_search, "_deduplicate_csv", lambda path: None)

    result = asyncio.run(
        pubmed_search.pubmed_scraper_tool.ainvoke({"search_query": "nutrition"})
    )

    assert "no usable citation fields" in result.lower()


def test_pubmed_scraper_tool_returns_formatted_output(monkeypatch):
    captured = {}

    df = _make_df(
        [
            {
                "Title": "Study Title",
                "Journal": "The Journal",
                "Publication Date": "2024",
                "Url": "https://example.org/study",
            }
        ]
    )

    class DummyScraper:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def scrape_async(self):
            return df

    monkeypatch.setenv("ENTREZ_EMAIL", "research@example.org")
    monkeypatch.setattr(pubmed_search, "PubMedScraper", DummyScraper)
    monkeypatch.setattr(pubmed_search, "_deduplicate_csv", lambda path: None)

    result = asyncio.run(
        pubmed_search.pubmed_scraper_tool.ainvoke(
            {"search_query": "Child Trauma", "max_results": 500}
        )
    )

    assert captured["max_results"] == 100
    assert captured["output_file"].startswith("data/pubmed_live_child_trauma")
    assert "DATASET_PATH:" in result
    assert "https://example.org/study" in result


def test_pubmed_scraper_tool_uses_csv_path_when_provided(monkeypatch):
    captured = {}

    df = _make_df(
        [
            {
                "Title": "Study",
                "Journal": "J",
                "Publication Date": "2024",
                "Url": "https://example.org/s",
            }
        ]
    )

    class DummyScraper:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        async def scrape_async(self):
            return df

    monkeypatch.setenv("ENTREZ_EMAIL", "research@example.org")
    monkeypatch.setattr(pubmed_search, "PubMedScraper", DummyScraper)
    monkeypatch.setattr(pubmed_search, "_deduplicate_csv", lambda path: None)

    result = asyncio.run(
        pubmed_search.pubmed_scraper_tool.ainvoke(
            {"search_query": "nutrition", "csv_path": "data/pubmed_run_abc.csv"}
        )
    )

    assert captured["output_file"] == "data/pubmed_run_abc.csv"
    assert "DATASET_PATH: data/pubmed_run_abc.csv" in result


def test_pubmed_scraper_tool_returns_failure_message_on_exception(monkeypatch):
    class DummyScraper:
        def __init__(self, **kwargs):
            pass

        async def scrape_async(self):
            raise RuntimeError("service unavailable")

    monkeypatch.setenv("ENTREZ_EMAIL", "research@example.org")
    monkeypatch.setattr(pubmed_search, "PubMedScraper", DummyScraper)

    result = asyncio.run(
        pubmed_search.pubmed_scraper_tool.ainvoke({"search_query": "nutrition"})
    )

    assert result == "PubMed scraping failed after retries: service unavailable"


def test_safe_slug():
    assert pubmed_search._safe_slug("A B/C") == "a_b_c"


def test_format_pubmed_rows():
    df = _make_df(
        [
            {
                "Title": "T",
                "Journal": "J",
                "Publication Date": "2020",
                "Url": "U",
            }
        ]
    )

    rows = pubmed_search._format_pubmed_rows(df)
    assert rows and "**T**" in rows[0]


def test_build_output():
    out = pubmed_search._build_output("q", "f", ["row1"], 1)
    assert "DATASET_PATH" in out
