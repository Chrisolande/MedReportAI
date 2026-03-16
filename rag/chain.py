import os
from dataclasses import dataclass, field
from typing import Any, Literal

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_deepseek import ChatDeepSeek


@dataclass
class RAGOutput:
    """RAG pipeline handling retrieval, generation, and context tracking."""

    prompt_name: str
    retriever: Any
    llm_model: Literal["deepseek-chat", "deepseek-reasoner"]
    question: str | None = None
    docs: list[Document] | None = None

    _retrieved_contexts_list: list[list[str]] = field(default_factory=list, init=False)
    _chain: Any = field(default=None, init=False)

    def __post_init__(self):
        try:
            if os.environ.get("LANGSMITH_PULL_PROMPTS", "").strip().lower() in (
                "1",
                "true",
                "yes",
                "on",
            ):
                from langsmith import Client

                self.prompt_template = Client().pull_prompt(self.prompt_name)
            else:
                self.prompt_template = PromptTemplate.from_template(
                    "Question:\n{question}\n\nContext:\n{context}\n"
                )
            self.llm_instance = ChatDeepSeek(model=self.llm_model)
        except Exception as e:
            raise RuntimeError(f"Failed to initialize RAG: {e}") from e

    @staticmethod
    def _format_docs(docs: list[Document]) -> str:
        return "\n\n".join(doc.page_content for doc in docs) if docs else ""

    @staticmethod
    def _extract_content(doc: Any) -> str:
        return doc.page_content if hasattr(doc, "page_content") else str(doc)

    def _capture_contexts(self, state: dict[str, Any]) -> dict[str, Any]:
        docs = state.get("context", [])
        self._retrieved_contexts_list.append(
            [
                self._extract_content(d)
                for d in (docs if isinstance(docs, list) else [docs])
            ]
            if docs
            else []
        )
        return state

    @property
    def retrieved_contexts_list(self) -> list[list[str]]:
        return self._retrieved_contexts_list

    def _build_chain(self):
        return (
            {
                "context": self.retriever | self._format_docs,
                "question": RunnablePassthrough(),
            }
            | RunnableLambda(self._capture_contexts)
            | self.prompt_template
            | self.llm_instance
            | StrOutputParser()
        )

    def invoke(self, question: str) -> str:
        if self._chain is None:
            self._chain = self._build_chain()
        return self._chain.invoke(question)

    def clear_contexts(self):
        self._retrieved_contexts_list = []
