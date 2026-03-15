from tools import pubmed_search


def test_safe_slug():
    assert pubmed_search._safe_slug("A B/C") == "a_b_c"


def test_format_pubmed_rows():
    class DF:
        def head(self, n):
            return [
                (
                    0,
                    {
                        "Title": "T",
                        "Journal": "J",
                        "Publication Date": "2020",
                        "Url": "U",
                    },
                )
            ]

    rows = pubmed_search._format_pubmed_rows(DF())
    assert rows and "**T**" in rows[0]


def test_build_output():
    out = pubmed_search._build_output("q", "f", ["row1"], 1)
    assert "DATASET_PATH" in out
