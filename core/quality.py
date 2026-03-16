"""Quality and source-grounding helpers for report generation."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

NUMBERED_CITATION_PATTERN = re.compile(r"\[\d+\]")
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

# Keep legacy pattern available for backwards compatibility in quality checks
SOURCE_CITATION_PATTERN = NUMBERED_CITATION_PATTERN

_INVALID_URL_PATTERNS = [
    re.compile(p)
    for p in [
        r"\.svg$",
        r"\.png$",
        r"\.jpg$",
        r"\.jpeg$",
        r"\.gif$",
        r"\.ico$",
        r"\.css$",
        r"\.js$",
        r"\.woff",
        r"\.ttf$",
        r"/favicon",
        r"/icon",
        r"/logo",
        r"cdn\.",
        r"static\.",
        r"assets\.",
        r"fonts\.googleapis",
        r"maxcdn\.",
        r"cloudflare",
    ]
]


def is_valid_source_url(url: str) -> bool:
    """Check if URL is a legitimate academic/humanitarian source, not a CDN/SVG/nav
    link."""
    if not url or not url.startswith("http"):
        return False
    lower = url.lower()
    for pattern in _INVALID_URL_PATTERNS:
        if pattern.search(lower):
            return False
    return True


def normalize_pubmed_url(url: str) -> str:
    """Normalize PubMed URLs to canonical form to deduplicate by PMID."""
    match = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url)
    if match:
        return f"https://pubmed.ncbi.nlm.nih.gov/{match.group(1)}/"
    match = re.search(r"ncbi\.nlm\.nih\.gov/pubmed/(\d+)", url)
    if match:
        return f"https://pubmed.ncbi.nlm.nih.gov/{match.group(1)}/"
    return url


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
        url = normalize_pubmed_url(_strip_trailing_punctuation(match.group("url")))
        extracted[url] = {
            "title": _normalize_field(match.group("title")),
            "authors": _normalize_field(match.group("authors")),
        }

    for pattern in (PUBMED_ROW_PATTERN, WEB_SOURCE_PATTERN, WEB_SOURCE_MD_PATTERN):
        for match in pattern.finditer(text):
            url = normalize_pubmed_url(_strip_trailing_punctuation(match.group("url")))
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
        normalized = normalize_pubmed_url(url)
        if normalized not in by_url:
            entry = dict(source)
            entry["url"] = normalized
            entry.setdefault("title", entry.get("label", ""))
            entry.setdefault("authors", "")
            by_url[normalized] = entry
            deduplicated.append(entry)
            continue

        existing = by_url[normalized]
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
        if not is_valid_source_url(url):
            continue
        url = normalize_pubmed_url(url)
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


def register_sources_in_citation_registry(
    sources: list[dict[str, str]],
    citation_registry: dict[str, int],
) -> dict[str, int]:
    """Register all source URLs into the citation registry, returning updated
    registry."""
    registry = dict(citation_registry) if citation_registry else {}
    for source in sources:
        url = source.get("url", "")
        if not url or not is_valid_source_url(url):
            continue
        url = normalize_pubmed_url(url)
        if url not in registry:
            registry[url] = max(registry.values(), default=0) + 1
    return registry


def _format_source_line(label: str, title: str, authors: str, url: str) -> str:
    if authors:
        return f"- [{label}] {title} | Authors: {authors} | URL: {url}"
    return f"- [{label}] {title} | URL: {url}"


def _build_registry_lines(sources, citation_registry):
    lines = []
    for source in sources:
        url = normalize_pubmed_url(source.get("url", ""))
        num = citation_registry.get(url)
        if num is None:
            continue
        title = source.get("title") or source.get("label") or url
        authors = source.get("authors", "").strip()
        lines.append(_format_source_line(str(num), title, authors, url))
    return lines


def _build_plain_lines(sources):
    lines = []
    for source in sources:
        title = source.get("title") or source.get("label") or source.get("url", "")
        authors = source.get("authors", "").strip()
        sid = source.get("id", "S?")
        lines.append(_format_source_line(sid, title, authors, source.get("url", "")))
    return lines


def build_source_registry_text(
    sources: list[dict[str, str]],
    citation_registry: dict[str, int] | None = None,
) -> str:
    if not sources:
        return "No explicit sources were captured."

    if citation_registry:
        lines = _build_registry_lines(sources, citation_registry)
        return "\n".join(lines) if lines else "No explicit sources were captured."

    return "\n".join(_build_plain_lines(sources))


def _format_reference(source: dict[str, str], number: int) -> str:
    title = source.get("title") or source.get("label") or source.get("url", "")
    authors = source.get("authors", "").strip()
    url = source.get("url", "")
    if authors and authors.lower() not in {"not specified", "not available", "unknown"}:
        return f"[{number}] {title}. Authors: {authors}. {url}"
    return f"[{number}] {title}. {url}"


def build_references_block(
    sources: list[dict[str, str]],
    citation_registry: dict[str, int] | None = None,
    body_text: str = "",
) -> str:
    unique_sources = deduplicate_sources(sources)
    if not unique_sources:
        return ""

    if citation_registry and body_text:
        return build_numbered_references(citation_registry, unique_sources, body_text)

    lines = []
    for index, source in enumerate(unique_sources, 1):
        lines.append(_format_reference(source, index))
    return "## References\n\n" + "\n".join(lines)


def build_numbered_references(
    citation_registry: dict[str, int],
    sources: list[dict[str, str]],
    body_text: str,
) -> str:
    """Build references section with only sources whose [N] appears in the body."""
    referenced_numbers: set[int] = set()
    for match in NUMBERED_CITATION_PATTERN.finditer(body_text):
        referenced_numbers.add(int(match.group(0).strip("[]")))

    if not referenced_numbers:
        return ""

    source_by_url: dict[str, dict[str, str]] = {}
    for source in sources:
        url = normalize_pubmed_url(source.get("url", ""))
        if url not in source_by_url:
            source_by_url[url] = source

    lines: list[tuple[int, str]] = []
    for url, num in citation_registry.items():
        if num not in referenced_numbers:
            continue
        source = source_by_url.get(url, {"url": url})
        lines.append((num, _format_reference(source, num)))

    if not lines:
        return ""

    lines.sort(key=lambda x: x[0])
    return "## References\n\n" + "\n".join(line for _, line in lines)


def _strip_existing_refs(body: str) -> str:
    if "\n### Sources" in body:
        body = body.split("\n### Sources", 1)[0].rstrip()
    if "\n## References" in body:
        body = body.split("\n## References", 1)[0].rstrip()
    return body


def _build_grounding_suffix(sources, citation_registry) -> str:
    if citation_registry:
        nums = []
        for source in sources[:3]:
            url = normalize_pubmed_url(source.get("url", ""))
            num = citation_registry.get(url)
            if num is not None:
                nums.append(f"[{num}]")
        tag = ", ".join(nums) if nums else "[1]"
    else:
        tag = ", ".join(f"[{i + 1}]" for i in range(min(3, len(sources))))
    return f"\n\nEvidence grounding: {tag}."


def enforce_source_linkage(
    content: str,
    sources: list[dict[str, str]],
    citation_registry: dict[str, int] | None = None,
) -> str:
    """Ensure output includes citation markers and canonical source registry."""
    if not sources:
        return content.strip()

    body = _strip_existing_refs(content.strip())

    if not NUMBERED_CITATION_PATTERN.search(body):
        body += _build_grounding_suffix(sources, citation_registry)

    return body.strip()


def detect_truncation(content: str) -> list[str]:
    """Detect sections that appear truncated."""
    issues = []
    stripped = content.strip()
    if not stripped:
        return ["Section is empty"]

    words = stripped.split()
    if len(words) < 200:
        issues.append(f"Section under 200 words ({len(words)} words)")

    # Check for terminal punctuation
    if not re.search(r"[.!?:]\s*$", stripped):
        issues.append("Section ends without terminal punctuation (may be truncated)")

    # Check for dangling sentence fragments
    last_line = stripped.split("\n")[-1].strip()
    if (
        last_line
        and not re.search(r"[.!?:]\s*$", last_line)
        and len(last_line.split()) > 3
    ):
        issues.append("Section contains a dangling sentence fragment at the end")

    return issues


def detect_unresolved_placeholders(content: str) -> list[str]:
    """Detect unresolved citation placeholders."""
    issues = []

    # [S1], [S2] style
    s_refs = re.findall(r"\[S\d+\]", content)
    if s_refs:
        issues.append(f"Unresolved [SN] placeholders: {', '.join(sorted(set(s_refs)))}")

    # [Source 1], [Source 2] style
    source_refs = re.findall(r"\[Source\s+\d+\]", content)
    if source_refs:
        issues.append(
            f"Unresolved [Source N] placeholders: {', '.join(sorted(set(source_refs)))}"
        )

    # "Evidence grounding:" followed by bracket refs
    if re.search(r"Evidence grounding:\s*\[", content):
        issues.append("Contains 'Evidence grounding:' block with bracket references")

    # [Research Finding N] style
    finding_refs = re.findall(r"\[Research Finding\s+\d+\]", content)
    if finding_refs:
        issues.append(
            f"Unresolved [Research Finding N] placeholders: {', '.join(sorted(set(finding_refs)))}"
        )

    return issues


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
        if not NUMBERED_CITATION_PATTERN.search(content):
            issues.append(f"{name}: no numbered citations like [1] were found")

    for issue in detect_truncation(content):
        issues.append(f"{name}: {issue}")
    for issue in detect_unresolved_placeholders(content):
        issues.append(f"{name}: {issue}")

    return issues


def validate_report_sections(sections: list[Any]) -> list[str]:
    """Validate all sections and aggregate quality issues."""
    issues: list[str] = []
    for section in sections:
        issues.extend(validate_section_quality(section))
    return issues
