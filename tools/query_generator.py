from utils.dspy_bootstrap import ensure_dspy_cache_dir


from dspy import Predict
from langsmith import traceable
from loguru import logger

from core.signatures import MultiQueryGenerator

ensure_dspy_cache_dir()


@traceable(name="Multiquery Generator")
def generate_queries(question: str, num_queries: int = 1):
    if not question.strip():
        logger.error("Empty query provided")
        return [question]

    try:
        query_optimizer = Predict(MultiQueryGenerator)
        return query_optimizer(
            question=question, num_queries=num_queries
        ).search_queries
    except Exception as e:
        logger.error(f"An error occurred during query generation: {str(e)}")
        return [question]
