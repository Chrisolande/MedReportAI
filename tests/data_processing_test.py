from utils.data_processing import load_documents_from_csv


def test_load_documents_from_csv_falls_back_to_title_and_abstract(tmp_path):
    csv_path = tmp_path / "pubmed_like.csv"
    csv_path.write_text(
        "Pmid,Title,Abstract,Journal\n"
        "123,Sample title,Sample abstract,Sample journal\n",
        encoding="utf-8",
    )

    documents = load_documents_from_csv(csv_path)

    assert len(documents) == 1
    assert documents[0].page_content == "Sample title\n\nSample abstract"
    assert documents[0].metadata["source"] == "123"
    assert documents[0].metadata["Journal"] == "Sample journal"
