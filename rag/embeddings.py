import os
from dataclasses import dataclass, field

from fastembed import TextEmbedding
from langchain_core.embeddings import Embeddings


@dataclass
class FastEmbed(Embeddings):
    """FastEmbed wrapper for LangChain compatibility."""

    fe: TextEmbedding = field(default_factory=TextEmbedding)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [emb.tolist() for emb in self.fe.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(self.fe.embed([text]))[0].tolist()


def initialize_embeddings(
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    cache_dir: str = "~/.cache/fastembed",
) -> FastEmbed:
    return FastEmbed(
        TextEmbedding(model_name=model_name, cache_dir=os.path.expanduser(cache_dir))
    )
