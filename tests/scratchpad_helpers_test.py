from utils.scratchpad_helpers import (
    handle_clear,
    handle_read,
    handle_write,
    save_scratchpad,
)


def test_handle_write_append_and_replace_modes():
    appended, _ = handle_write({"notes": "new", "mode": "append"}, "base", "1")
    replaced, _ = handle_write({"notes": "new", "mode": "replace"}, "base", "2")

    assert appended == "base\n\nnew"
    assert replaced == "new"


def test_handle_read_and_clear_responses():
    read_msg = handle_read({"query": "keywords"}, "notes here", "1")
    unchanged, cancel_msg = handle_clear({"confirm": False}, "2", "existing notes")
    cleared, ok_msg = handle_clear({"confirm": True}, "3", "existing notes")

    assert "query: 'keywords'" in read_msg.content
    assert "notes here" in read_msg.content
    assert unchanged == "existing notes"
    assert "cancelled" in cancel_msg.content
    assert cleared == ""
    assert "cleared successfully" in ok_msg.content


def test_save_scratchpad_persists_content(tmp_path):
    save_scratchpad("hello", "note.md", str(tmp_path))

    assert (tmp_path / "note.md").read_text(encoding="utf-8") == "hello"
