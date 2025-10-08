from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseLanguageModel
from loguru import logger
from ragas.dataset_schema import EvaluationDataset
from ragas.embeddings.base import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.testset import TestsetGenerator
from ragas.testset.synthesizers.multi_hop.abstract import (
    MultiHopAbstractQuerySynthesizer,
)
from ragas.testset.synthesizers.single_hop.specific import (
    SingleHopSpecificQuerySynthesizer,
)

from rag_chain import RAGOutput


def generate_test_dataset(
    documents: list[Document],
    embeddings: Embeddings,
    llm: BaseLanguageModel,
    testset_size: int = 10,
    output_path: str | Path = "RAGEvaluation/generated_testset.csv",
) -> pd.DataFrame:
    # Wrap models for RAGAs
    evaluator_llm = LangchainLLMWrapper(llm)
    wrapped_embeddings = LangchainEmbeddingsWrapper(embeddings)

    # Create test generator

    generator = TestsetGenerator(llm=evaluator_llm, embedding_model=wrapped_embeddings)
    query_distribution = [
        (MultiHopAbstractQuerySynthesizer(llm=evaluator_llm), 0.5),
        (SingleHopSpecificQuerySynthesizer(llm=evaluator_llm), 0.5),
    ]

    logger.info(f"Generating a dataset of size {testset_size}")
    dataset = generator.generate_with_langchain_docs(
        documents,
        testset_size=testset_size,
        query_distribution=query_distribution,
    )

    # Convert to a pandas dataframe and save
    df = dataset.to_pandas()  # type: ignore
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Generated testset saved to {output_path}")

    return df


def evaluate_rag_pipeline(
    rag_chain: RAGOutput,
    input_csv_path: str,
    output_csv_path: str,
    question_column: str = "user_input",
) -> pd.DataFrame:
    """Evaluate RAG pipeline on a test dataset.

    Args:
        rag_chain: Configured RAG chain
        input_csv_path: Path to input test dataset
        output_csv_path: Path to save results
        question_column: Name of column containing questions

    Returns:
        DataFrame with evaluation results
    """
    input_path = Path(input_csv_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_csv_path}")

    # Create the output directory if it doesn't exist
    output_path = Path(output_csv_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load the dataset
    print(f"Loading the dataset from {input_csv_path}")
    data = pd.read_csv(input_csv_path)

    if question_column not in data.columns:
        raise ValueError(f"Column '{question_column}' not found in the dataset")

    # Process each question
    responses = []
    print(f"Processing {len(data)} questions ...")

    for i, (_, row) in enumerate(data.iterrows(), start=1):
        user_input = row[question_column]

        try:
            response = rag_chain.invoke(user_input)
            responses.append(response)

            if i % 10 == 0:
                print(f"Processed {i} / {len(data)} questions")
        except Exception as e:
            print(f"Error processing question {i}: {e}")
            responses.append(f"ERROR: {str(e)}")

    # Add results to the dataframe
    data["response"] = responses
    data["retrieved_contexts"] = rag_chain.retrieved_contexts_list

    # Save the resutls
    data.to_csv(output_csv_path, index=False)
    print(f"Saved results to {output_csv_path}")
    return data


def create_evaluation_dataset(
    results_df: pd.DataFrame,
) -> EvaluationDataset:
    """Create an evaluation dataset from results for metrics calculation.

    Args:
        results_df: DataFrame with RAG results

    Returns:
        RAGAS EvaluationDataset
    """
    eval_data = results_df[
        ["user_input", "reference_contexts", "reference", "synthesizer_name"]
    ].to_dict(orient="records")

    return EvaluationDataset.from_list(eval_data)
