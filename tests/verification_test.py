from core.verification import build_conservative_instruction, verify_scratchpad


def _make_quant_entry(n_points: int = 3) -> str:
    """Build a scratchpad entry with a QUANTITATIVE DATA block."""
    lines = "\n".join(f"- [Metric {i}]: value {i}" for i in range(1, n_points + 1))
    return (
        "Source: Example Study\n"
        "**QUANTITATIVE DATA**:\n"
        f"{lines}\n"
        "Summary: Evidence gathered."
    )


def _make_plain_entry() -> str:
    return "Source: Background Context\nSummary: General information about the topic."


def _build_scratchpad(*entries: str) -> str:
    return "\n---\n".join(entries)


def test_verify_scratchpad_passes_with_sufficient_evidence():
    pad = _build_scratchpad(
        _make_quant_entry(4),
        _make_quant_entry(3),
        _make_plain_entry(),
    )
    # Ensure minimum length
    pad += " " * max(0, 500 - len(pad))
    result = verify_scratchpad(pad)
    assert result.passed is True
    assert result.failures == []


def test_verify_scratchpad_fails_with_insufficient_sources():
    pad = _build_scratchpad(_make_quant_entry(), _make_quant_entry())
    pad += " " * max(0, 500 - len(pad))
    result = verify_scratchpad(pad)
    assert result.passed is False
    assert any("Insufficient sources" in f for f in result.failures)


def test_verify_scratchpad_fails_with_insufficient_quantitative_data():
    pad = _build_scratchpad(
        _make_quant_entry(3),
        _make_plain_entry(),
        _make_plain_entry(),
    )
    pad += " " * max(0, 500 - len(pad))
    result = verify_scratchpad(pad)
    assert result.passed is False
    assert any("Insufficient quantitative data" in f for f in result.failures)


def test_verify_scratchpad_fails_short_scratchpad():
    pad = _build_scratchpad(
        _make_quant_entry(),
        _make_quant_entry(),
        _make_plain_entry(),
    )
    # Force it to be short by truncating
    pad = pad[:200]
    result = verify_scratchpad(pad)
    assert result.passed is False
    assert any("too short" in f for f in result.failures)


def test_build_conservative_instruction_lists_failures():
    failures = [
        "Insufficient sources: found 1, need at least 3",
        "Scratchpad too short: 100 characters, minimum 500",
    ]
    instruction = build_conservative_instruction(failures)
    assert "CONSERVATIVE WRITING MODE" in instruction
    assert "Insufficient sources" in instruction
    assert "Scratchpad too short" in instruction
    assert "hedge claims" in instruction
