from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from loguru import logger

from rag.source_formatter import SourceFormatter


async def _run_tavily(
    query: str,
    max_results: int,
    include_raw_content: bool,
) -> list:
    try:
        tavily = TavilySearch(
            max_results=max_results,
            include_raw_content=include_raw_content,
            topic="general",
        )
        return await tavily.ainvoke({"query": query})
    except Exception as exc:
        logger.error(f"Tavily search error: {exc}")
        return []


@tool
async def web_search(
    search_query: str,
    max_results: int = 1,
    include_raw_content: bool = True,
    markdown_output: bool = False,
) -> list:
    """Search the web for the given query and return deduplicated formatted sources."""
    if not search_query.strip():
        logger.warning("web_search called with empty query")
        return []

    try:
        raw = await _run_tavily(search_query, max_results, include_raw_content)
        return SourceFormatter(
            markdown_output=markdown_output
        ).deduplicate_and_format_sources([raw])
    except Exception as exc:
        logger.error(f"web_search failed: {exc}")
        return []
