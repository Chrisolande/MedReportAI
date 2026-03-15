from rag.source_formatter import SourceFormatter


def test_extract_sources_list_supports_dict_and_nested_list_inputs():
    formatter = SourceFormatter()

    from_dict = formatter._extract_sources_list(
        {"results": [{"url": "https://a", "title": "A"}]}
    )
    from_list = formatter._extract_sources_list(
        [
            {"results": [{"url": "https://b", "title": "B"}]},
            {"url": "https://c", "title": "C"},
            [{"url": "https://d", "title": "D"}],
        ]
    )

    assert len(from_dict) == 1
    assert len(from_list) == 3


def test_truncate_content_uses_word_boundary_when_possible():
    content = "word " * 300

    truncated = SourceFormatter._truncate_content(content, char_limit=120)

    assert truncated.endswith("... [content truncated]")
    assert len(truncated) < len(content)


def test_deduplicate_and_format_sources_plain_text_output():
    formatter = SourceFormatter(include_raw_content=False, markdown_output=False)
    search_response = {
        "results": [
            {"url": "https://x", "title": "One", "content": "Summary 1"},
            {"url": "https://x", "title": "One dup", "content": "Summary dup"},
            {"url": "https://y", "title": "Two", "content": "Summary 2"},
        ]
    }

    output = formatter.deduplicate_and_format_sources(search_response)

    assert output.startswith("Sources:")
    assert "Source 1: One" in output
    assert "Source 2: Two" in output


def test_deduplicate_and_format_sources_return_dict_has_unique_urls():
    formatter = SourceFormatter()
    unique = formatter.deduplicate_and_format_sources(
        [
            {"results": [{"url": "https://a", "title": "A"}]},
            {"url": "https://a", "title": "A2"},
            {"url": "https://b", "title": "B"},
        ],
        return_dict=True,
    )

    assert sorted(unique.keys()) == ["https://a", "https://b"]
