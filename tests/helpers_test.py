from utils.helpers import content_to_text, ensure_directory, validate_file_exists


def test_content_to_text_flattens_supported_list_items():
    content = ["alpha", {"text": "beta"}, 42, {"x": "ignored"}]

    result = content_to_text(content)

    assert result == "alpha\nbeta\n"


def test_ensure_directory_and_validate_file_exists(tmp_path):
    target_dir = tmp_path / "a" / "b"
    target_file = target_dir / "test.txt"

    ensure_directory(str(target_dir))
    target_file.write_text("ok", encoding="utf-8")

    assert target_dir.exists()
    assert validate_file_exists(str(target_file)) is True
    assert validate_file_exists(str(target_dir / "missing.txt")) is False
