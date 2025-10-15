import os
from dataclasses import dataclass, field

from fastembed import TextEmbedding
from langchain_core.embeddings import Embeddings


@dataclass
class FastEmbed(Embeddings):
    """Custom FastEmbed wrapper for LangChain compatibility.

    Wraps FastEmbed TextEmbedding to work with LangChain's Embeddings interface.
    """

    fe: TextEmbedding = field(default_factory=TextEmbedding)

    def embed_documents(self, texts: list[str]):
        """Embed a list of documents.

        Args:
            texts: List of text documents to embed

        Returns:
            List of embeddings as lists of floats
        """
        return [emb.tolist() for emb in self.fe.embed(texts)]

    def embed_query(self, text: str):
        """Embed a single query text.

        Args:
            text: Query text to embed

        Returns:
            Embedding as a list of floats
        """
        return list(self.fe.embed([text]))[0].tolist()


def initialize_embeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2", cache_dir="~/.cache/fastembed"
):
    """Initialize the embeddings model.

    Args:
        model_name: Name of the FastEmbed model to use
        cache_dir: Directory to cache the model files

    Returns:
        Initialized FastEmbed instance
    """
    return FastEmbed(
        TextEmbedding(model_name=model_name, cache_dir=os.path.expanduser(cache_dir))
    )
