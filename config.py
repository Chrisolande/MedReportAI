import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import dspy
from dotenv import load_dotenv
from dspy import LM, configure
from langchain_deepseek import ChatDeepSeek


@dataclass
class ModelConfig:
    """Configuration for LLM models."""

    deepseek_model: Literal["deepseek-chat", "deepseek-reasoner"] = "deepseek-chat"
    deepseek_temperature: float = 1.3
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_cache_dir: str = "~/.cache/fastembed"


@dataclass
class RetrieverConfig:
    """Configuration for retrieval system."""

    k: int = 15
    sparse_weight: float = 0.65
    dense_weight: float = 0.35
    similarity_threshold: float = 0.6
    redundancy_threshold: float = 0.95
    top_n: int = 5
    reranker_model: str = "Xenova/ms-marco-miniLM-L-6-v2"
    reranker_cache_dir: str = "~/.cache/fastembed"


@dataclass
class PathConfig:
    """Configuration for file paths."""

    data_dir: Path = Path("data")
    rag_eval_dir: Path = Path("RAGEvaluation")
    faiss_index_dir: str = "faiss_index"

    def __post_init__(self):
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.rag_eval_dir.mkdir(exist_ok=True)


class AppConfig:
    """Main application configuration."""

    def __init__(self):
        # Load environment variables
        load_dotenv()

        # Initialize sub-configs
        self.model = ModelConfig()
        self.retriever = RetrieverConfig()
        self.paths = PathConfig()

        # API keys
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

    def initialize_llm(self) -> ChatDeepSeek:
        """Initialize the main LLM."""
        return ChatDeepSeek(
            model=self.model.deepseek_model, temperature=self.model.deepseek_temperature
        )

    def initialize_dspy(self):
        """Initialize DSPy configuration."""
        dspy_lm = LM(
            "deepseek/deepseek-chat",
            api_key=self.deepseek_api_key,
            base_url="https://api.deepseek.com",
        )
        configure(lm=dspy_lm)
        dspy.settings.configure(track_usage=True)
        return dspy_lm


# Global config instance
config = AppConfig()
