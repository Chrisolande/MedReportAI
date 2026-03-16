"""Pre-synthesis verification gate for section research quality."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class VerificationResult:
    passed: bool
    failures: list[str]


def _check_source_count(entries: list[str]) -> str | None:
    if len(entries) < 3:
        return f"Insufficient sources: found {len(entries)}, need at least 3"
    return None


def _check_quantitative_data(entries: list[str]) -> str | None:
    quant_rich = 0
    for entry in entries:
        if re.findall(r"\*\*QUANTITATIVE DATA\*\*:", entry):
            data_points = re.findall(r"^\s*-\s+\[", entry, re.MULTILINE)
            if len(data_points) >= 3:
                quant_rich += 1
    if quant_rich < 2:
        return f"Insufficient quantitative data: {quant_rich} entries with 3+ data points, need at least 2"
    return None


def _check_web_only(entries: list[str], web_search_only: bool) -> str | None:
    if web_search_only and any("Web Search" in e for e in entries):
        return "Web-search-only sources present without PubMed/retriever fallback"
    return None


def _check_min_length(scratchpad: str) -> str | None:
    if len(scratchpad) < 500:
        return f"Scratchpad too short: {len(scratchpad)} characters, minimum 500"
    return None


def verify_scratchpad(
    scratchpad: str, web_search_only: bool = False
) -> VerificationResult:
    """Verify scratchpad has sufficient evidence for synthesis."""
    entries = [e.strip() for e in scratchpad.split("---") if e.strip()]
    checks = [
        _check_source_count(entries),
        _check_quantitative_data(entries),
        _check_web_only(entries, web_search_only),
        _check_min_length(scratchpad),
    ]
    failures = [f for f in checks if f is not None]
    return VerificationResult(passed=len(failures) == 0, failures=failures)


def build_conservative_instruction(failures: list[str]) -> str:
    """Build a conservative writing instruction when verification fails."""
    return (
        "\N{WARNING SIGN} CONSERVATIVE WRITING MODE: The research evidence below did not fully meet "
        "quality thresholds. The following issues were identified:\n"
        + "\n".join(f"- {f}" for f in failures)
        + "\n\nWrite conservatively: hedge claims, note evidence gaps explicitly, "
        "and avoid overstating findings. Prefer qualified language."
    )
