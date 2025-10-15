from dataclasses import dataclass, field
from typing import Any, Literal

from langchain import hub
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_deepseek import ChatDeepSeek


@dataclass
class RAGOutput:
    """RAG pipeline wrapper that handles retrieval, generation, and context tracking."""

    prompt_name: str
    retriever: Any
    llm_model: Literal["deepseek-chat", "deepseek-reasoner"]
    question: str | None = None
    docs: list[Document] | None = None

    _prompt_template: Any = field(default=None)
    _llm_instance: Any = field(default=None)
    _retrieved_contexts_list: list[list[str]] = field(default_factory=list)
    _chain: Any = field(default=None)

    def __post_init__(self):
        """Initialize prompt template and LLM instance."""
        try:
            self._prompt_template = hub.pull(self.prompt_name)
            self._llm_instance = ChatDeepSeek(model=self.llm_model)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize the RAG: {e}")

    def _format_docs(self, docs: list[Document]) -> str:
        """Format documents into a single string for context.

        Args:
            docs: List of Document objects

        Returns:
            Formatted string of document contents
        """
        if not docs:
            return ""

        if not isinstance(docs, list):
            raise ValueError(f"Expected list, got {type(docs)}")

        if not all(isinstance(doc, Document) for doc in docs):
            raise ValueError("All items must be Document instances")

        return "\n\n".join(doc.page_content for doc in docs)

    def _extract_content(self, doc: Any) -> str:
        """Extract content from various document formats.

        Args:
            doc: Document in various formats

        Returns:
            Extracted text content
        """
        if isinstance(doc, str):
            return doc
        elif isinstance(doc, Document):
            return doc.page_content
        elif hasattr(doc, "page_content"):
            return doc.page_content
        else:
            return str(doc)

    def capture_retrieved_contexts(self, state: dict[str, Any]) -> dict[str, Any]:
        """Capture retrieved contexts during chain execution.

        Args:
            state: Current chain state

        Returns:
            Unchanged state (side effect: stores contexts)
        """
        retrieved_docs = state.get("context", [])
        if not retrieved_docs:
            self._retrieved_contexts_list.append([])
            return state

        if not isinstance(retrieved_docs, list):
            retrieved_docs = [retrieved_docs]

        # Extract content from documents
        retrieved_contexts = [self._extract_content(doc) for doc in retrieved_docs]
        self._retrieved_contexts_list.append(retrieved_contexts)
        return state

    @property
    def retrieved_contexts_list(self) -> list[list[str]]:
        """Get the list of all retrieved contexts."""
        return self._retrieved_contexts_list

    @property
    def prompt_template(self):
        """Get the prompt template."""
        return self._prompt_template

    @property
    def llm_instance(self):
        """Get the LLM instance."""
        return self._llm_instance

    def create_chain(self):
        """Create the RAG chain with retrieval, prompt, and generation.

        Returns:
            Configured chain
        """
        self._chain = (
            {
                "context": self.retriever | self._format_docs,
                "question": RunnablePassthrough(),
            }
            | RunnableLambda(self.capture_retrieved_contexts)
            | self._prompt_template
            | self._llm_instance
            | StrOutputParser()
        )
        return self._chain

    def invoke(self, question: str) -> str:
        """Invoke the RAG chain with a question.

        Args:
            question: User question

        Returns:
            Generated answer
        """
        if self._chain is None:
            self.create_chain()
        return self._chain.invoke(question)

    def clear_contexts(self):
        """Clear stored retrieved contexts."""
        self._retrieved_contexts_list = []
