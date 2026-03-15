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
