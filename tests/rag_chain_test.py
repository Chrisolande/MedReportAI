from rag.chain import RAGOutput


class DummyRetriever:
    def __or__(self, other):
        return self

    def invoke(self, question):
        return "context"


class DummyPrompt:
    def __call__(self, *a, **k):
        return "prompt"


class DummyLLM:
    def __call__(self, *a, **k):
        return "llm"


def test_ragoutput_format_docs():
    docs = [
        type("Doc", (), {"page_content": "abc"})(),
        type("Doc", (), {"page_content": "def"})(),
    ]
    assert RAGOutput._format_docs(docs) == "abc\n\ndef"


def test_ragoutput_extract_content():
    doc = type("Doc", (), {"page_content": "abc"})()
    assert RAGOutput._extract_content(doc) == "abc"
    assert RAGOutput._extract_content("xyz") == "xyz"


def test_ragoutput_capture_contexts():
    rag = RAGOutput("prompt", DummyRetriever(), "deepseek-chat")
    state = {"context": [type("Doc", (), {"page_content": "abc"})()]}
    rag._capture_contexts(state)
    assert rag.retrieved_contexts_list
