import asyncio
from typing import Literal

from langchain_core.tools import tool
from langchain_tavily import TavilySearch
from loguru import logger

from rag.source_formatter import SourceFormatter
from tools.query_generator import generate_queries


async def tavily_search_async(
    search_query: str,
    max_results: int = 1,
    num_queries: int = 1,
    include_raw_content: bool = False,
    topic: Literal["general", "news", "finance"] = "general",
):
    if not search_query.strip():
        logger.warning("The search query cannot be an empty string")

    try:
        tavily_search = TavilySearch(
            max_results=max_results,
            num_queries=num_queries,
            include_raw_content=include_raw_content,
            topic=topic,
        )

        if num_queries > 1:
            # Generate multiple queries from the single query
            try:
                search_queries = generate_queries(
                    question=search_query, num_queries=num_queries
                )
            except Exception as e:
                logger.warning(
                    f"Failed to generate query variations, using original query: {str(e)}"
                )
                search_queries = [search_query]
        else:
            search_queries = [search_query]
        # Execute the searches concurrently
        tasks = [tavily_search.ainvoke({"query": q}) for q in search_queries]
        results = await asyncio.gather(*tasks)
        return results
    except Exception as e:
        logger.error(f"An error occurred during web search: {str(e)}")
        return []


@tool
async def web_search(
    search_query: str,
    max_results: int = 1,
    include_raw_content: bool = True,
    markdown_output: bool = False,
):
    """Search the web for the given search queries."""
    try:
        formatter = SourceFormatter(markdown_output=markdown_output)
        search_response = await tavily_search_async(
            search_query,
            max_results=max_results,
            include_raw_content=include_raw_content,
            num_queries=1,
        )
        deduplicated_response = formatter.deduplicate_and_format_sources(
            search_response
        )
        return deduplicated_response
    except Exception as e:
        logger.error(f"An error occurred during web search: {str(e)}")
        return []
