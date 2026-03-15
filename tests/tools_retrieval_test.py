import asyncio

from langchain_core.documents import Document

from tools import retrieval


def test_deduplicate_documents_keeps_first_instance_by_page_content():
    docs = [
        [Document(page_content="A", metadata={"id": 1})],
        [Document(page_content="A", metadata={"id": 2})],
        [Document(page_content="B", metadata={"id": 3})],
    ]
    out = retrieval.deduplicate_documents(docs)
    assert len(out) == 2
    assert out[0].page_content == "A"
    assert out[1].page_content == "B"


def test_retriever_tool_error(monkeypatch):
    monkeypatch.setattr(
        retrieval,
        "get_retriever",
        lambda csv_path=None: type(
            "R", (), {"ainvoke": staticmethod(lambda q: None)}
        )(),
    )
    monkeypatch.setattr(
        retrieval,
        "RetrieverReportGenerator",
        lambda: type(
            "R", (), {"create_report": staticmethod(lambda docs: {"markdown": ""})}
        )(),
    )
    result = asyncio.run(retrieval.retriever_tool.ainvoke({"search_query": "q"}))
    assert "No relevant documents" in result or "Error" in result
