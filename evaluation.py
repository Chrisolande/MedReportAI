import ast
import os
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseLanguageModel
from langchain_deepseek import ChatDeepSeek
from loguru import logger
from ragas import evaluate
from ragas.dataset_schema import EvaluationDataset
from ragas.embeddings.base import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    AnswerSimilarity,
    ContextEntityRecall,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
    NoiseSensitivity,
)
from ragas.run_config import RunConfig
from ragas.testset import TestsetGenerator
from ragas.testset.synthesizers.multi_hop.abstract import (
    MultiHopAbstractQuerySynthesizer,
)
from ragas.testset.synthesizers.single_hop.specific import (
    SingleHopSpecificQuerySynthesizer,
)

from rag.chain import RAGOutput


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


@dataclass
class RAGEvaluator:
    """RAG Evaluation pipeline for model-embedding pairs."""

    max_workers: int = 1
    timeout: int = 180
    generative_models: list[str] = field(default_factory=lambda: ["deepseek-chat"])
    embedding_models: list[str] = field(default_factory=lambda: ["fastembed"])
    metrics: list = field(
        default_factory=lambda: [
            ContextRecall(),
            ContextPrecision(),
            AnswerSimilarity(),
            ContextEntityRecall(),
            NoiseSensitivity(),
            Faithfulness(),
        ]
    )
    run_config: RunConfig = field(init=False)

    def __post_init__(self):
        """Initialize RunConfig after dataclass initialization."""
        self.run_config = RunConfig(max_workers=self.max_workers, timeout=self.timeout)

    def parse_contexts(self, data: pd.DataFrame) -> pd.DataFrame:
        """Parse retrieved_contexts from string to list.

        Args:
            data: DataFrame with retrieved_contexts column

        Returns:
            DataFrame with parsed contexts
        """
        if "retrieved_contexts" in data.columns:
            data["retrieved_contexts"] = data["retrieved_contexts"].apply(
                ast.literal_eval
            )
        return data

    def prepare_dataset(self, data: pd.DataFrame) -> EvaluationDataset:
        """Prepare evaluation dataset from dataframe.

        Args:
            data: DataFrame with evaluation data

        Returns:
            RAGAS EvaluationDataset
        """
        eval_data = data[
            ["user_input", "reference", "response", "retrieved_contexts"]
        ].to_dict(orient="records")
        return EvaluationDataset.from_list(eval_data)

    def run_evaluation(
        self, input_csv_path: str, evaluation_embeddings: Embeddings
    ) -> pd.DataFrame:
        """Run evaluation on input data.

        Args:
            input_csv_path: Path to input CSV file
            evaluation_embeddings: Embeddings to use for evaluation

        Returns:
            DataFrame with evaluation results
        """
        print(f"Loading data from {input_csv_path}")
        data = pd.read_csv(input_csv_path)
        data = self.parse_contexts(data)
        eval_dataset = self.prepare_dataset(data)

        # Wrap embeddings for RAGAS
        wrapped_embeddings = LangchainEmbeddingsWrapper(evaluation_embeddings)
        evaluator_llm = LangchainLLMWrapper(ChatDeepSeek(model="deepseek-chat"))

        print(f"Running evaluation with {len(self.metrics)} metrics...")
        results = evaluate(
            dataset=eval_dataset,
            metrics=self.metrics,
            llm=evaluator_llm,
            embeddings=wrapped_embeddings,
            run_config=self.run_config,
        )

        return results.to_pandas()  # type: ignore

    def evaluate_all_models(
        self, evaluation_embeddings: Embeddings, results_dir: str = "RAGEvaluation"
    ) -> dict[str, pd.DataFrame]:
        """Evaluate all model-embedding pairs.

        Args:
            evaluation_embeddings: Embeddings to use for evaluation
            results_dir: Directory containing results files

        Returns:
            Dictionary mapping model pairs to their evaluation results
        """
        all_results = {}

        for model, embedding in zip(self.generative_models, self.embedding_models):
            model_pair = f"{model}_{embedding}"
            output_csv_path = os.path.join(
                results_dir, f"evaluation_results_{model_pair}.csv"
            )
            input_csv_path = os.path.join(results_dir, f"results_{model_pair}.csv")

            # Check if evaluation results already exist
            if os.path.exists(output_csv_path):
                print(f"Loading existing evaluation results for {model_pair}")
                df = pd.read_csv(output_csv_path)
            else:
                # Check if input results exist
                if not os.path.exists(input_csv_path):
                    print(
                        f"Warning: Input file {input_csv_path} not found. Skipping {model_pair}"
                    )
                    continue

                print(f"Running evaluation for {model_pair}")
                df = self.run_evaluation(input_csv_path, evaluation_embeddings)

                # Save results
                os.makedirs(results_dir, exist_ok=True)
                df.to_csv(output_csv_path, index=False)
                print(f"Saved evaluation results to {output_csv_path}")

            all_results[model_pair] = df

        return all_results
