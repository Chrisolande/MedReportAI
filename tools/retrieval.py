from langchain.tools import tool
from langchain_core.documents import Document
from loguru import logger

from rag.retrieval_builder import get_retriever
from rag.retrieval_formatter import RetrieverReportGenerator


def deduplicate_documents(documents: list[list[Document]]):
    seen = set()
    unique_docs = []

    for doc_list in documents:
        for doc in doc_list:
            if doc.page_content not in seen:
                seen.add(doc.page_content)
                unique_docs.append(doc)

    return unique_docs


@tool
async def retriever_tool(search_query: str, csv_path: str = ""):
    """Retrieves pubmed data using the provided query and generates a report in markdown
    format."""
    try:
        retriever = get_retriever(csv_path=csv_path or None)
        report_gen = RetrieverReportGenerator()
        result = await retriever.ainvoke(search_query)

        if not result:
            logger.warning(f"No results found for query: {search_query}")
            return "No relevant documents found for the given query"

        deduplicated_results = deduplicate_documents([result])
        report = report_gen.create_report(deduplicated_results)
        return report["markdown"]
    except Exception as e:
        logger.error(f"Error in retriever_tool: {str(e)}")
        return f"Error retrieving data: {str(e)}"
