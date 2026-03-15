from pathlib import Path
from types import SimpleNamespace

from langchain_core.documents import Document

from rag import retrieval_builder


def test_resolve_csv_path_prefers_existing_explicit_file(tmp_path):
    explicit = tmp_path / "explicit.csv"
    explicit.write_text("x", encoding="utf-8")

    resolved = retrieval_builder._resolve_csv_path(str(explicit), "default.csv")

    assert resolved == str(explicit)


def test_resolve_csv_path_falls_back_to_default_for_missing_file(tmp_path):
    resolved = retrieval_builder._resolve_csv_path(
        str(tmp_path / "missing.csv"), "data/default.csv"
    )

    assert resolved == "data/default.csv"


def test_dataset_hash_changes_with_file_updates(tmp_path):
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("first", encoding="utf-8")
    initial = retrieval_builder._dataset_hash(str(csv_path))

    csv_path.write_text("second version", encoding="utf-8")
    updated = retrieval_builder._dataset_hash(str(csv_path))

    assert len(initial) == 16
    assert initial != updated


def test_filter_empty_documents_discards_blank_content():
    documents = [
        Document(page_content="Alpha", metadata={}),
        Document(page_content="  ", metadata={}),
        Document(page_content="Beta", metadata={}),
    ]

    filtered = retrieval_builder._filter_empty_documents(documents)

    assert [doc.page_content for doc in filtered] == ["Alpha", "Beta"]


def test_fastembed_rerank_handles_empty_inputs():
    reranker = retrieval_builder.FastEmbedRerank.model_construct(
        encoder=SimpleNamespace(rerank=lambda query, docs: []),
        model_name="dummy",
        cache_dir="~/.cache/fastembed",
        top_n=5,
    )

    assert reranker.compress_documents([], "query") == []
    assert (
        reranker.compress_documents(
            [Document(page_content="   ", metadata={})], "query"
        )
        == []
    )


def test_fastembed_rerank_scores_and_sorts_documents():
    reranker = retrieval_builder.FastEmbedRerank.model_construct(
        encoder=SimpleNamespace(rerank=lambda query, docs: [0.0, 4.0]),
        model_name="dummy",
        cache_dir="~/.cache/fastembed",
        top_n=1,
    )
    documents = [
        Document(page_content="lower", metadata={}),
        Document(page_content="higher", metadata={}),
    ]

    result = reranker.compress_documents(documents, "child trauma")

    assert len(result) == 1
    assert result[0].page_content == "higher"
    assert 0 < result[0].metadata["relevance_score"] <= 1


def test_build_retriever_raises_for_missing_documents():
    embeddings = object()

    try:
        retrieval_builder.build_retriever([], embeddings)
    except ValueError as exc:
        assert "No documents provided" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing documents")

    try:
        retrieval_builder.build_retriever(
            [Document(page_content="   ", metadata={})], embeddings
        )
    except ValueError as exc:
        assert "No non-empty documents" in str(exc)
    else:
        raise AssertionError("Expected ValueError for blank documents")


def test_build_retriever_constructs_compression_pipeline(monkeypatch, tmp_path):
    captured = {}

    class DummyVectorStore:
        def as_retriever(self, search_kwargs):
            captured["search_kwargs"] = search_kwargs
            return {"dense": search_kwargs}

    monkeypatch.setattr(
        retrieval_builder,
        "batch_process",
        lambda docs, embeddings, persist_directory: DummyVectorStore(),
    )
    monkeypatch.setattr(
        retrieval_builder.BM25Retriever,
        "from_documents",
        staticmethod(lambda docs, k: {"bm25": (len(docs), k)}),
    )
    monkeypatch.setattr(
        retrieval_builder,
        "EnsembleRetriever",
        lambda retrievers, weights: {"retrievers": retrievers, "weights": weights},
    )
    monkeypatch.setattr(
        retrieval_builder,
        "EmbeddingsFilter",
        lambda embeddings, similarity_threshold: (
            "filter",
            similarity_threshold,
        ),
    )
    monkeypatch.setattr(
        retrieval_builder,
        "EmbeddingsRedundantFilter",
        lambda embeddings, similarity_threshold: (
            "redundant",
            similarity_threshold,
        ),
    )
    monkeypatch.setattr(
        retrieval_builder,
        "FastEmbedRerank",
        lambda model_name, cache_dir, top_n: ("rerank", model_name, cache_dir, top_n),
    )
    monkeypatch.setattr(
        retrieval_builder,
        "DocumentCompressorPipeline",
        lambda transformers: {"transformers": transformers},
    )
    monkeypatch.setattr(
        retrieval_builder,
        "ContextualCompressionRetriever",
        lambda base_compressor, base_retriever: {
            "compressor": base_compressor,
            "retriever": base_retriever,
        },
    )

    result = retrieval_builder.build_retriever(
        [Document(page_content="useful content", metadata={})],
        embeddings=object(),
        persist_directory=str(tmp_path / "faiss"),
    )

    assert captured["search_kwargs"] == {"k": retrieval_builder.RetrieverConfig().k}
    assert result["compressor"]["transformers"][0][0] == "filter"
    assert result["retriever"]["weights"] == [0.65, 0.35]


def test_build_retriever_falls_back_to_dense_retriever(monkeypatch, tmp_path):
    calls = {"count": 0}

    class DummyVectorStore:
        def as_retriever(self, search_kwargs):
            return {"dense_only": search_kwargs}

    def fake_batch_process(docs, embeddings, persist_directory):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("boom")
        return DummyVectorStore()

    monkeypatch.setattr(retrieval_builder, "batch_process", fake_batch_process)

    result = retrieval_builder.build_retriever(
        [Document(page_content="useful content", metadata={})],
        embeddings=object(),
        persist_directory=str(tmp_path / "faiss"),
    )

    assert result == {"dense_only": {"k": retrieval_builder.RetrieverConfig().k}}
    assert calls["count"] == 2


def test_get_retriever_resolves_documents_and_persist_directory(monkeypatch):
    captured = {}

    monkeypatch.setattr(
        retrieval_builder, "initialize_embeddings", lambda **kwargs: "emb"
    )
    monkeypatch.setattr(
        retrieval_builder,
        "load_documents_from_csv",
        lambda path: [Document(page_content="doc", metadata={})],
    )
    monkeypatch.setattr(
        retrieval_builder,
        "split_documents",
        lambda docs, embeddings: [Document(page_content="chunk", metadata={})],
    )
    monkeypatch.setattr(retrieval_builder, "_dataset_hash", lambda path: "hash123")

    def fake_build_retriever(docs, embeddings, retriever_config, persist_directory):
        captured["docs"] = docs
        captured["embeddings"] = embeddings
        captured["persist_directory"] = persist_directory
        return "retriever"

    monkeypatch.setattr(retrieval_builder, "build_retriever", fake_build_retriever)

    result = retrieval_builder.get_retriever("data/custom.csv")

    assert result == "retriever"
    assert captured["embeddings"] == "emb"
    assert captured["docs"][0].page_content == "chunk"
    assert captured["persist_directory"] == str(
        Path(retrieval_builder.config.paths.faiss_index_dir) / "hash123"
    )
