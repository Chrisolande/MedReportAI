from tools import query_generator


def test_generate_queries_empty(monkeypatch):
    monkeypatch.setattr(query_generator, "Predict", lambda _: None)
    assert query_generator.generate_queries("", 1) == [""]


def test_generate_queries_success(monkeypatch):
    class Dummy:
        def __call__(self, question, num_queries):
            class R:
                search_queries = ["q1", "q2"]

            return R()

    monkeypatch.setattr(query_generator, "Predict", lambda _: Dummy())
    out = query_generator.generate_queries("q", 2)
    assert out == ["q1", "q2"]
