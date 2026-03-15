"""Quality and source-grounding helpers for report generation."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

SOURCE_CITATION_PATTERN = re.compile(r"\[S\d+\]")
URL_PATTERN = re.compile(r"https?://[^\s)\]>]+")
RETRIEVER_SOURCE_PATTERN = re.compile(
    r"##\s*\d+\.\s*(?P<title>[^\n]+)\n"
    r"\*\*Authors:\*\*\s*(?P<authors>[^\n]+).*?\n"
    r"\*\*URL:\*\*\s*(?P<url>https?://[^\s)\]>]+)",
    re.DOTALL,
)
PUBMED_ROW_PATTERN = re.compile(
    r"-\s+\*\*(?P<title>.+?)\*\*\s*\([^\n]*\)\s*\n\s*-\s*(?P<url>https?://[^\s)\]>]+)",
    re.DOTALL,
)
WEB_SOURCE_PATTERN = re.compile(
    r"Source\s+\d+:\s*(?P<title>[^\n]+)\nURL:\s*(?P<url>https?://[^\s)\]>]+)",
)
WEB_SOURCE_MD_PATTERN = re.compile(
    r"##\s*Source\s+\d+:\s*(?P<title>[^\n]+)\n\*\*URL:\*\*\s*(?P<url>https?://[^\s)\]>]+)",
)


def _strip_trailing_punctuation(url: str) -> str:
    return url.rstrip(".,;:)")


def extract_urls(text: str) -> list[str]:
    """Extract and normalize URLs from free-form tool output text."""
    urls = [
        _strip_trailing_punctuation(match.group(0))
        for match in URL_PATTERN.finditer(text)
    ]
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        unique.append(url)
    return unique


def _derive_label(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc or "source"
    path = parsed.path.strip("/")
    if not path:
        return host
    last_segment = path.split("/")[-1]
    return f"{host}/{last_segment}"


def _normalize_field(value: str) -> str:
    return " ".join(value.replace("**", "").split()).strip()


def _extract_source_metadata(text: str) -> dict[str, dict[str, str]]:
    """Extract source title/author metadata from known tool output layouts."""
    extracted: dict[str, dict[str, str]] = {}

    for match in RETRIEVER_SOURCE_PATTERN.finditer(text):
        url = _strip_trailing_punctuation(match.group("url"))
        extracted[url] = {
            "title": _normalize_field(match.group("title")),
            "authors": _normalize_field(match.group("authors")),
        }

    for pattern in (PUBMED_ROW_PATTERN, WEB_SOURCE_PATTERN, WEB_SOURCE_MD_PATTERN):
        for match in pattern.finditer(text):
            url = _strip_trailing_punctuation(match.group("url"))
            extracted.setdefault(url, {})
            extracted[url]["title"] = _normalize_field(match.group("title"))

    return extracted


def deduplicate_sources(sources: list[dict[str, str]]) -> list[dict[str, str]]:
    """Deduplicate sources by URL while keeping richest available metadata."""
    deduplicated: list[dict[str, str]] = []
    by_url: dict[str, dict[str, str]] = {}

    for source in sources:
        url = source.get("url", "")
        if not url:
            continue
        if url not in by_url:
            normalized = dict(source)
            normalized.setdefault("title", normalized.get("label", ""))
            normalized.setdefault("authors", "")
            by_url[url] = normalized
            deduplicated.append(normalized)
            continue

        existing = by_url[url]
        for field in ("title", "authors", "label"):
            if not existing.get(field) and source.get(field):
                existing[field] = source[field]

    return deduplicated


def merge_sources(
    existing_sources: list[dict[str, str]], text: str
) -> list[dict[str, str]]:
    """Merge URLs found in text into a stable per-section source registry."""
    merged = [dict(source) for source in existing_sources]
    by_url = {source.get("url", ""): source for source in merged}
    metadata_by_url = _extract_source_metadata(text)

    for url in extract_urls(text):
        metadata = metadata_by_url.get(url, {})
        if url in by_url:
            existing = by_url[url]
            for field in ("title", "authors"):
                if not existing.get(field) and metadata.get(field):
                    existing[field] = metadata[field]
            continue

        source_id = f"S{len(merged) + 1}"
        entry = {
            "id": source_id,
            "url": url,
            "label": _derive_label(url),
            "title": metadata.get("title", ""),
            "authors": metadata.get("authors", ""),
        }
        merged.append(entry)
        by_url[url] = entry

    return merged


def build_source_registry_text(sources: list[dict[str, str]]) -> str:
    if not sources:
        return "No explicit sources were captured."
    lines = []
    for source in sources:
        title = source.get("title") or source.get("label") or source.get("url", "")
        authors = source.get("authors", "").strip()
        if authors:
            lines.append(
                f"- [{source['id']}] {title} | Authors: {authors} | URL: {source.get('url', '')}"
            )
        else:
            lines.append(f"- [{source['id']}] {title} | URL: {source.get('url', '')}")
    return "\n".join(lines)


def _format_reference(source: dict[str, str], index: int) -> str:
    title = source.get("title") or source.get("label") or source.get("url", "")
    authors = source.get("authors", "").strip()
    url = source.get("url", "")
    if authors and authors.lower() not in {"not specified", "not available", "unknown"}:
        return f"{index}. {title}. Authors: {authors}. {url}"
    return f"{index}. {title}. {url}"


def build_references_block(sources: list[dict[str, str]]) -> str:
    unique_sources = deduplicate_sources(sources)
    if not unique_sources:
        return ""

    lines = [
        _format_reference(source, index)
        for index, source in enumerate(unique_sources, 1)
    ]
    return "## References\n\n" + "\n".join(lines)


def enforce_source_linkage(content: str, sources: list[dict[str, str]]) -> str:
    """Ensure output includes citation markers and canonical source registry."""
    if not sources:
        return content.strip()

    body = content.strip()
    if "\n### Sources" in body:
        body = body.split("\n### Sources", 1)[0].rstrip()
    if "\n## References" in body:
        body = body.split("\n## References", 1)[0].rstrip()

    if not SOURCE_CITATION_PATTERN.search(body):
        citations = ", ".join(f"[{source['id']}]" for source in sources[:3])
        body += f"\n\nEvidence grounding: {citations}."

    return body.strip()


def validate_section_quality(section: Any) -> list[str]:
    """Validate a section for grounding and formatting constraints."""
    issues: list[str] = []
    name = getattr(section, "name", "Unnamed section")
    content = (getattr(section, "content", "") or "").strip()
    research = bool(getattr(section, "research", False))
    sources = getattr(section, "sources", []) or []

    if not content:
        issues.append(f"{name}: content is empty")
        return issues

    if research:
        if not sources:
            issues.append(f"{name}: no sources were captured")
        if not SOURCE_CITATION_PATTERN.search(content):
            issues.append(f"{name}: no source citations like [S1] were found")

    return issues


def validate_report_sections(sections: list[Any]) -> list[str]:
    """Validate all sections and aggregate quality issues."""
    issues: list[str] = []
    for section in sections:
        issues.extend(validate_section_quality(section))
    return issues
