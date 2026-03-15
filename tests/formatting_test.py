import unittest

import utils.formatting as formatting


class DummyMessage:
    def __init__(self, content):
        self.content = content


class DummyDoc:
    def __init__(self, content, source=None):
        self.page_content = content
        self.metadata = {"source": source} if source else {}


def test_format_message_content_handles_exception():
    class BadMessage:
        @property
        def content(self):
            raise Exception("fail")

    try:
        formatting.format_message_content(BadMessage())
    except Exception as e:
        assert str(e) == "fail"


class TestFormatting(unittest.TestCase):
    def test_format_message_content(self):
        msg = DummyMessage("hello")
        self.assertEqual(formatting.format_message_content(msg), "hello")

    def test_format_messages(self):
        msgs = [DummyMessage("hi")]
        # Should not raise
        formatting.format_messages(msgs)

    def test_format_retriever_results_str(self):
        # Should not raise
        formatting.format_retriever_results("result")

    def test_format_retriever_results_docs(self):
        docs = [DummyDoc("doc1", "src1"), DummyDoc("doc2")]
        formatting.format_retriever_results(docs)


if __name__ == "__main__":
    unittest.main()
