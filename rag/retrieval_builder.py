import os
from collections.abc import Sequence
from hashlib import sha256
from pathlib import Path
from typing import Any

import numpy as np
from fastembed.rerank.cross_encoder import TextCrossEncoder
from langchain_classic.retrievers import (
    ContextualCompressionRetriever,
    EnsembleRetriever,
)
from langchain_classic.retrievers.document_compressors import (
    DocumentCompressorPipeline,
    EmbeddingsFilter,
)
from langchain_community.document_transformers import EmbeddingsRedundantFilter
from langchain_community.retrievers import BM25Retriever
from langchain_core.callbacks import Callbacks
from langchain_core.documents import BaseDocumentCompressor, Document
from langchain_core.embeddings import Embeddings
from loguru import logger
from pydantic import ConfigDict, Field

from config import AppConfig, RetrieverConfig
from rag.embeddings import initialize_embeddings
from utils.data_processing import (
    batch_process,
    load_documents_from_csv,
    split_documents,
)

config = AppConfig()
RETRIEVAL_INDEX_VERSION = "v2"


def _resolve_csv_path(csv_path: str | None, default_csv_path: str) -> str:
    if csv_path and (candidate := Path(csv_path)).exists():
        logger.info(f"Using explicit PubMed CSV for retrieval: {candidate}")
        return str(candidate)
    if csv_path:
        logger.warning(
            f"Provided csv_path does not exist ({csv_path}); falling back to default"
        )
    return default_csv_path


def _dataset_hash(csv_path: str) -> str:
    p = Path(csv_path)
    stat = p.stat()
    fingerprint = (
        f"{RETRIEVAL_INDEX_VERSION}::{p.resolve()}::{stat.st_mtime_ns}::{stat.st_size}"
    )
    return sha256(fingerprint.encode()).hexdigest()[:16]


def _filter_empty_documents(documents: Sequence[Document]) -> list[Document]:
    valid = [d for d in documents if d.page_content.strip()]
    if removed := len(documents) - len(valid):
        logger.warning(
            f"Skipping {removed} empty documents before retriever construction"
        )
    return valid


class FastEmbedRerank(BaseDocumentCompressor):
    """Cross-encoder reranker using FastEmbed."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_name: str = Field(default="Xenova/ms-marco-miniLM-L-6-v2")
    cache_dir: str = Field(default="~/.cache/fastembed")
    top_n: int = Field(default=5)
    encoder: TextCrossEncoder | None = Field(default=None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.encoder is None:
            self.encoder = TextCrossEncoder(
                model_name=self.model_name,
                cache_dir=os.path.expanduser(self.cache_dir),
            )

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Callbacks | None = None,
    ) -> list[Document]:
        if not documents:
            logger.error("No documents provided for reranking")
            return []

        # Normalise _DocumentWithState objects
        docs = [
            Document(page_content=d.page_content, metadata=d.metadata)
            for d in documents
        ]
        valid = [d for d in docs if d.page_content.strip()]
        if not valid:
            logger.error("All documents have empty page_content")
            return []

        try:
            scores = list(self.encoder.rerank(query, [d.page_content for d in valid]))  # type: ignore
            norm = (1 / (1 + np.exp(-np.array(scores)))).tolist()
            for doc, score in zip(valid, norm):
                doc.metadata["relevance_score"] = float(score)
            return sorted(
                valid, key=lambda d: d.metadata["relevance_score"], reverse=True
            )[: self.top_n]
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            return []


def build_retriever(
    splitted_documents: list[Document],
    embeddings: Embeddings,
    retriever_config: RetrieverConfig | None = None,
    persist_directory: str | None = None,
) -> ContextualCompressionRetriever | Any:
    """Build ensemble retriever with compression pipeline, falling back to dense-only on
    error."""
    cfg = retriever_config or RetrieverConfig()

    if not splitted_documents:
        raise ValueError("No documents provided")
    docs = _filter_empty_documents(splitted_documents)
    if not docs:
        raise ValueError("No non-empty documents available for retrieval")

    persist_dir = persist_directory or cfg.paths.faiss_index_dir

    try:
        vector_store = batch_process(docs, embeddings, persist_directory=persist_dir)
        ensemble = EnsembleRetriever(
            retrievers=[
                BM25Retriever.from_documents(docs, k=cfg.k),
                vector_store.as_retriever(search_kwargs={"k": cfg.k}),
            ],
            weights=[cfg.sparse_weight, cfg.dense_weight],
        )
        pipeline = DocumentCompressorPipeline(
            transformers=[
                EmbeddingsFilter(
                    embeddings=embeddings, similarity_threshold=cfg.similarity_threshold
                ),
                EmbeddingsRedundantFilter(
                    embeddings=embeddings, similarity_threshold=cfg.redundancy_threshold
                ),
                FastEmbedRerank(
                    model_name=cfg.reranker_model,
                    cache_dir=cfg.reranker_cache_dir,
                    top_n=cfg.top_n,
                ),
            ]
        )
        return ContextualCompressionRetriever(
            base_compressor=pipeline, base_retriever=ensemble
        )

    except Exception as e:
        logger.error(f"Retriever build failed ({e}); falling back to dense retriever")
        vector_store = batch_process(docs, embeddings, persist_directory=persist_dir)
        return vector_store.as_retriever(search_kwargs={"k": cfg.k})


def get_retriever(csv_path: str | None = None) -> ContextualCompressionRetriever:
    embeddings = initialize_embeddings(
        model_name=config.model.embedding_model,
        cache_dir=config.model.embedding_cache_dir,
    )
    resolved = _resolve_csv_path(csv_path, config.paths.default_csv_path)
    logger.info("Loading and splitting documents...")
    docs = split_documents(load_documents_from_csv(resolved), embeddings)
    logger.info(f"Created {len(docs)} document chunks")

    persist_dir = str(Path(config.paths.faiss_index_dir) / _dataset_hash(resolved))
    return build_retriever(
        docs, embeddings, config.retriever, persist_directory=persist_dir
    )
