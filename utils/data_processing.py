import os
from pathlib import Path

import pandas as pd
from langchain_community.document_loaders import CSVLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker


def load_and_process_csv(csv_path: str | Path, output_path: str | Path) -> pd.DataFrame:
    """Load CSV and combine Title + Abstract into Article column.

    Args:
        csv_path: Path to the CSV file

    Returns:
        Processed DataFrame with Article column
    """
    csv_path = Path(csv_path)
    output_path = Path(output_path)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if csv_path.suffix != ".csv" or output_path.suffix != ".csv":
        raise ValueError("Input file must be a CSV")

    df = pd.read_csv(csv_path)

    # Combine Title and Abstract
    df["Article"] = df["Title"].str.cat(df["Abstract"])
    df.drop(columns=["Abstract"], inplace=True)
    df.to_csv(output_path, index=False)
    print(f"Saved processed data to {output_path}")

    return df


def load_documents_from_csv(
    csv_path: str | Path,
    content_columns: list[str] | None = None,
    metadata_columns: list[str] | None = None,
    source_column: str = "Pmid",
) -> list[Document]:
    """Load documents from CSV using LangChain's CSVLoader.

    Args:
        csv_path: Path to CSV file
        source_column: Column to use as document source
        content_columns: Columns to include in document content
        metadata_columns: Columns to include in metadata

    Returns:
        List of LangChain Document objects
    """
    if content_columns is None:
        content_columns = ["Article"]

    if metadata_columns is None:
        metadata_columns = [
            "Pmid",
            "Title",
            "Url",
            "Authors",
            "Keywords",
            "Journal",
            "Publication Date",
            "References",
        ]

    loader = CSVLoader(
        file_path=str(csv_path),
        source_column=source_column,
        content_columns=content_columns,
        metadata_columns=metadata_columns,
    )

    return loader.load()


def split_documents(documents: list[Document], embeddings) -> list[Document]:
    """Split documents using semantic chunking.

    Args:
        documents: List of documents to split
        embeddings: Embeddings model for semantic similarity

    Returns:
        List of split documents
    """
    splitter = SemanticChunker(embeddings)
    return splitter.split_documents(documents)


def batch_process(
    documents: list[Document],
    embeddings,
    persist_directory: str = "faiss_index",
    batch_size: int = 10,
    force_rebuild: bool = False,
) -> FAISS:
    """Create or load FAISS vector index with batch processing.

    Args:
        documents: List of documents to index
        embeddings: Embeddings model
        persist_directory: Directory to persist the index
        batch_size: Number of documents per batch
        force_rebuild: Whether to force rebuild the index

    Returns:
        FAISS vector store
    """
    # Ensure directory exists
    os.makedirs(persist_directory, exist_ok=True)
    index_path = os.path.join(persist_directory, "index.faiss")

    # Load existing index if available and not forcing rebuild
    if not force_rebuild and os.path.exists(index_path):
        print(f"Loading existing FAISS index from {persist_directory}")
        vector_index = FAISS.load_local(
            persist_directory, embeddings, allow_dangerous_deserialization=True
        )
    else:
        print(f"Creating new FAISS index at {persist_directory}")

        # Create batches
        batched_docs = [
            documents[i : i + batch_size] for i in range(0, len(documents), batch_size)
        ]

        # Initialize with first batch
        vector_index = FAISS.from_documents(batched_docs[0], embeddings)

        # Add remaining batches
        for batch in batched_docs[1:]:
            vector_index.add_documents(batch)

        # Persist the vector index
        vector_index.save_local(persist_directory)
        print(f"FAISS index saved to {persist_directory}")

    return vector_index
