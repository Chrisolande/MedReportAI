import asyncio

from tools import web_search


class DummyTavily:
    def __init__(self, **kwargs):
        pass

    async def ainvoke(self, args):
        return {"result": args["query"]}


def test_run_tavily_returns_result(monkeypatch):
    monkeypatch.setattr(web_search, "TavilySearch", DummyTavily)

    async def run():
        result = await web_search._run_tavily(
            "q", max_results=1, include_raw_content=True
        )
        assert result == {"result": "q"}

    asyncio.run(run())


def test_run_tavily_returns_empty_list_on_error(monkeypatch):
    class BrokenTavily:
        def __init__(self, **kwargs):
            raise RuntimeError("tavily unavailable")

    monkeypatch.setattr(web_search, "TavilySearch", BrokenTavily)

    async def run():
        result = await web_search._run_tavily(
            "q", max_results=1, include_raw_content=True
        )
        assert result == []

    asyncio.run(run())


def test_web_search_returns_empty_for_blank_query():
    result = asyncio.run(web_search.web_search.ainvoke({"search_query": "   "}))
    assert result == []


def test_web_search_formats_search_results(monkeypatch):
    captured = {}

    async def fake_run_tavily(query, max_results, include_raw_content):
        captured["query"] = query
        captured["max_results"] = max_results
        return [{"results": [{"url": "https://example.org", "title": "Source"}]}]

    class DummyFormatter:
        def __init__(self, markdown_output):
            captured["markdown_output"] = markdown_output

        def deduplicate_and_format_sources(self, search_response):
            captured["search_response"] = search_response
            return "formatted"

    monkeypatch.setattr(web_search, "_run_tavily", fake_run_tavily)
    monkeypatch.setattr(web_search, "SourceFormatter", DummyFormatter)

    result = asyncio.run(
        web_search.web_search.ainvoke(
            {
                "search_query": "pediatric trauma",
                "max_results": 2,
                "include_raw_content": False,
                "markdown_output": True,
            }
        )
    )

    assert result == "formatted"
    assert captured["markdown_output"] is True
    assert (
        captured["search_response"][0][0]["results"][0]["url"] == "https://example.org"
    )


def test_web_search_returns_empty_list_when_formatter_fails(monkeypatch):
    async def fake_run_tavily(query, max_results, include_raw_content):
        return [{"results": []}]

    class BrokenFormatter:
        def __init__(self, markdown_output):
            pass

        def deduplicate_and_format_sources(self, search_response):
            raise RuntimeError("formatting failed")

    monkeypatch.setattr(web_search, "_run_tavily", fake_run_tavily)
    monkeypatch.setattr(web_search, "SourceFormatter", BrokenFormatter)

    result = asyncio.run(
        web_search.web_search.ainvoke({"search_query": "pediatric trauma"})
    )

    assert result == []
