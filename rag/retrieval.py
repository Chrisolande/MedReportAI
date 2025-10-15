import os
from collections.abc import Sequence
from typing import Any

import numpy as np
from fastembed.rerank.cross_encoder import TextCrossEncoder
from langchain.retrievers import ContextualCompressionRetriever, EnsembleRetriever
from langchain.retrievers.document_compressors import (
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

from config import RetrieverConfig
from utils.data_processing import batch_process


class FastEmbedRerank(BaseDocumentCompressor):
    """Custom reranker using FastEmbed's cross-encoder.

    Reranks retrieved documents based on relevance to the query.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model_name: str = Field(
        default="Xenova/ms-marco-miniLM-L-6-v2", description="Cross-encoder model name"
    )
    cache_dir: str = Field(
        default="~/.cache/fastembed", description="Cache directory for models"
    )
    top_n: int = Field(default=5, description="Number of top documents to return")
    encoder: TextCrossEncoder | None = Field(
        default=None, description="Cross encoder instance"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.encoder is None:
            self.encoder = TextCrossEncoder(
                model_name=self.model_name, cache_dir=os.path.expanduser(self.cache_dir)
            )

    def _convert_to_documents(self, docs: Sequence[Document]) -> list[Document]:
        """Convert various document types to standard Document format."""
        converted_docs = []
        for doc in docs:
            if hasattr(doc, "state"):
                # Handle _DocumentWithState objects
                doc = Document(page_content=doc.page_content, metadata=doc.metadata)
                converted_docs.append(doc)
            else:
                converted_docs.append(doc)
        return converted_docs

    def _normalize_scores(self, scores: list[float]) -> list[float]:
        """Normalize scores using sigmoid function."""
        probs = 1 / (1 + np.exp(-np.array(scores)))
        return probs.tolist()

    def compress_documents(
        self,
        documents: Sequence[Document],
        query: str,
        callbacks: Callbacks | None = None,
    ) -> list[Document]:
        """Rerank and compress documents based on relevance to query.

        Args:
            documents: Documents to rerank
            query: Query string
            callbacks: Optional callbacks

        Returns:
            Reranked and filtered documents
        """
        if not documents:
            logger.error("No documents provided for reranking step")
            return []

        if self.encoder is None:
            self.encoder = TextCrossEncoder(
                model_name=self.model_name, cache_dir=os.path.expanduser(self.cache_dir)
            )

        documents = self._convert_to_documents(documents)
        logger.debug(f"Reranking {len(documents)} documents")

        # Filter out documents with empty content
        valid_docs = [doc for doc in documents if doc.page_content.strip()]
        if not valid_docs:
            logger.error("The documents provided have no page contents!")
            return []

        try:
            # Extract text content
            doc_texts = [doc.page_content for doc in valid_docs]

            # Get reranking scores
            scores = list(self.encoder.rerank(query, doc_texts))
            norm_scores = self._normalize_scores(scores)

            # Attach scores and create scored documents
            scored_docs = []
            for doc, score in zip(valid_docs, norm_scores):
                doc.metadata["relevance_score"] = float(score)
                scored_docs.append(doc)

            # Sort by relevance and return top_n
            reranked_docs = sorted(
                scored_docs, key=lambda d: d.metadata["relevance_score"], reverse=True
            )
            return reranked_docs[: self.top_n]

        except Exception as e:
            logger.error(f"An error occurred during Reranking: {str(e)}")
            return []


def build_retriever(
    splitted_documents: list[Document],
    embeddings: Embeddings,
    config: RetrieverConfig | None = None,
) -> ContextualCompressionRetriever | Any:
    """Build a comprehensive retriever with ensemble retrieval and compression.

    Args:
        splitted_documents: Pre-split documents
        embeddings: Embeddings model
        config: Retriever configuration

    Returns:
        Configured ContextualCompressionRetriever
    """
    if config is None:
        config = RetrieverConfig()

    if not splitted_documents:
        raise ValueError("No documents are passed")

    try:
        # Create dense retriever (vector-based)
        vector_store = batch_process(splitted_documents, embeddings)
        dense_retriever = vector_store.as_retriever(search_kwargs={"k": config.k})

        # Create sparse retriever (BM25)
        sparse_retriever = BM25Retriever.from_documents(splitted_documents, k=config.k)

        # Ensemble retriever combining both
        ensemble_retriever = EnsembleRetriever(
            retrievers=[sparse_retriever, dense_retriever],
            weights=[config.sparse_weight, config.dense_weight],
        )

        # Build compression pipeline
        pipeline_compressor = DocumentCompressorPipeline(
            transformers=[
                # Filter by similarity threshold
                EmbeddingsFilter(
                    embeddings=embeddings,
                    similarity_threshold=config.similarity_threshold,
                ),
                # Remove redundant documents
                EmbeddingsRedundantFilter(
                    embeddings=embeddings,
                    similarity_threshold=config.redundancy_threshold,
                ),
                # Rerank remaining documents
                FastEmbedRerank(
                    model_name=config.reranker_model,
                    cache_dir=config.reranker_cache_dir,
                    top_n=config.top_n,
                ),
            ]
        )

        return ContextualCompressionRetriever(
            base_compressor=pipeline_compressor, base_retriever=ensemble_retriever
        )

    except Exception as e:
        logger.error(f"An error occurred during retrieval: {str(e)}")
        # Fallback to simple dense retriever
        vector_store = batch_process(splitted_documents, embeddings)
        return vector_store.as_retriever(search_kwargs={"k": config.k})
