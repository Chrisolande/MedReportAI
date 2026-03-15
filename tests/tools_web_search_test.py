import asyncio

from tools import web_search


class DummyTavily:
    def __init__(self, **kwargs):
        pass

    async def ainvoke(self, args):
        return {"result": args["query"]}


def test_tavily_search_async(monkeypatch):
    monkeypatch.setattr(web_search, "TavilySearch", DummyTavily)
    monkeypatch.setattr(
        web_search,
        "generate_queries",
        lambda question, num_queries: [question] * num_queries,
    )

    async def run():
        results = await web_search.tavily_search_async(
            "q", max_results=1, num_queries=2
        )
        assert isinstance(results, list)

    asyncio.run(run())


def test_tavily_search_async_falls_back_when_query_generation_fails(monkeypatch):
    monkeypatch.setattr(web_search, "TavilySearch", DummyTavily)

    def explode(question, num_queries):
        raise RuntimeError("generation failed")

    monkeypatch.setattr(web_search, "generate_queries", explode)

    async def run():
        results = await web_search.tavily_search_async(
            "q", max_results=1, num_queries=3
        )
        assert results == [{"result": "q"}]

    asyncio.run(run())


def test_tavily_search_async_returns_empty_list_on_error(monkeypatch):
    class BrokenTavily:
        def __init__(self, **kwargs):
            raise RuntimeError("tavily unavailable")

    monkeypatch.setattr(web_search, "TavilySearch", BrokenTavily)

    async def run():
        results = await web_search.tavily_search_async("q")
        assert results == []

    asyncio.run(run())


def test_web_search_formats_search_results(monkeypatch):
    captured = {}

    async def fake_search(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return [{"results": [{"url": "https://example.org", "title": "Source"}]}]

    class DummyFormatter:
        def __init__(self, markdown_output):
            captured["markdown_output"] = markdown_output

        def deduplicate_and_format_sources(self, search_response):
            captured["search_response"] = search_response
            return "formatted"

    monkeypatch.setattr(web_search, "tavily_search_async", fake_search)
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
    assert captured["search_response"][0]["results"][0]["url"] == "https://example.org"


def test_web_search_returns_empty_list_when_formatter_fails(monkeypatch):
    async def fake_search(*args, **kwargs):
        return [{"results": []}]

    class BrokenFormatter:
        def __init__(self, markdown_output):
            pass

        def deduplicate_and_format_sources(self, search_response):
            raise RuntimeError("formatting failed")

    monkeypatch.setattr(web_search, "tavily_search_async", fake_search)
    monkeypatch.setattr(web_search, "SourceFormatter", BrokenFormatter)

    result = asyncio.run(
        web_search.web_search.ainvoke({"search_query": "pediatric trauma"})
    )

    assert result == []
