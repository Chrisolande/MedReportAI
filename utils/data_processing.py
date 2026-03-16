import os
from pathlib import Path

import pandas as pd
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker

from utils.helpers import ensure_directory

_FALLBACK_CONTENT = ["Article", "Title", "Abstract"]
_DEFAULT_METADATA = [
    "Pmid",
    "Title",
    "Url",
    "Authors",
    "Keywords",
    "Journal",
    "Publication Date",
    "References",
]


def _resolve_content_columns(
    df: pd.DataFrame, requested: list[str] | None
) -> list[str]:
    candidates = requested or ["Article"]
    cols = [c for c in candidates if c in df.columns] or [
        c for c in _FALLBACK_CONTENT if c in df.columns
    ]
    if not cols:
        raise ValueError(
            f"No usable content columns. Requested {candidates}, "
            f"available: {list(df.columns)}"
        )
    return cols


def load_and_process_csv(csv_path: str | Path, output_path: str | Path) -> pd.DataFrame:
    """Combine Title + Abstract into an Article column and write to output_path."""
    csv_path, output_path = Path(csv_path), Path(output_path)
    ensure_directory(str(output_path.parent))

    df = pd.read_csv(csv_path)
    df["Article"] = df["Title"].str.cat(df["Abstract"])
    df.drop(columns=["Abstract"], inplace=True)
    df.to_csv(output_path, index=False)
    return df


def load_documents_from_csv(
    csv_path: str | Path,
    content_columns: list[str] | None = None,
    metadata_columns: list[str] | None = None,
    source_column: str = "Pmid",
) -> list[Document]:
    """Load a CSV as a list of LangChain Documents."""
    df = pd.read_csv(csv_path).fillna("")
    content_cols = _resolve_content_columns(df, content_columns)
    meta_cols = [c for c in (metadata_columns or _DEFAULT_METADATA) if c in df.columns]

    def _to_doc(row: pd.Series) -> Document:
        content = "\n\n".join(v for c in content_cols if (v := str(row[c]).strip()))
        meta = {c: str(row[c]).strip() for c in meta_cols if str(row[c]).strip()}
        if src := str(row.get(source_column, "")).strip():
            meta["source"] = src
        return Document(page_content=content, metadata=meta)

    return [_to_doc(row) for _, row in df.iterrows()]


def split_documents(documents: list[Document], embeddings) -> list[Document]:
    """Semantic chunking via SemanticChunker."""
    return SemanticChunker(embeddings).split_documents(documents)


def batch_process(
    documents: list[Document],
    embeddings,
    persist_directory: str = "outputs/faiss_index",
    batch_size: int = 10,
    force_rebuild: bool = False,
) -> FAISS:
    """Return a FAISS index, loading from disk if it already exists."""
    ensure_directory(persist_directory)
    index_path = os.path.join(persist_directory, "index.faiss")

    if not force_rebuild and os.path.exists(index_path):
        return FAISS.load_local(
            persist_directory, embeddings, allow_dangerous_deserialization=True
        )

    batches = [
        documents[i : i + batch_size] for i in range(0, len(documents), batch_size)
    ]
    index = FAISS.from_documents(batches[0], embeddings)
    for batch in batches[1:]:
        index.add_documents(batch)

    index.save_local(persist_directory)
    return index
