from dataclasses import dataclass

from IPython.display import Markdown, display
from loguru import logger
from typing_extensions import Any


@dataclass
class SourceFormatter:
    max_tokens_per_source: int = 1000
    include_raw_content: bool = True
    chars_per_token: int = 5
    markdown_output: bool = False

    @staticmethod
    def _extract_sources_list(
        search_response: dict[str, Any] | list,
    ) -> list[dict[str, Any]]:
        """Extract sources list from various response formats."""
        if isinstance(search_response, dict):
            return search_response.get("results", [])
        elif isinstance(search_response, list):
            sources_list = []
            for response in search_response:
                if isinstance(response, dict) and "results" in response:
                    sources_list.extend(response["results"])
                elif isinstance(response, dict):
                    sources_list.append(response)
                elif isinstance(response, list):
                    sources_list.extend(response)
            return sources_list
        else:
            raise ValueError(
                "Input must be either a dict with 'results' key or a list of search results"
            )

    @staticmethod
    def _truncate_content(content: str, char_limit: int = 4000) -> str:
        """Truncate content to specified character limit."""
        if not content:
            return "No content available"
        if len(content) <= char_limit:
            return content
        truncate_point = content.rfind(" ", 0, char_limit)
        if (
            truncate_point == -1 or truncate_point < char_limit * 0.8
        ):  # Returns -1 if not found, check if the " " occurs before the 80% of the char_limit
            truncate_point = char_limit
        return content[:truncate_point].rstrip() + "... [content truncated]"

    def _format_single_source(
        self,
        source: dict[str, Any],
        index: int,
        char_limit: int,
    ) -> str:
        """Format a single source for display."""
        title = source.get("title", "Untitled Source")
        url = source.get("url", "No URL available")
        content = source.get("content", "No content summary available")
        raw_content = source.get("raw_content", "")

        if self.markdown_output:
            lines = [
                f"## Source {index}: {title}",
                f"**URL:** {url}",
                f"**Summary:** {content}",
            ]
        else:
            lines = [
                f"Source {index}: {title}",
                f"URL: {url}",
                f"Most relevant content: {content}",
            ]

        if self.include_raw_content:
            if raw_content:
                truncated_content = self._truncate_content(raw_content, char_limit)
                token_estimate = char_limit // 4

                if self.markdown_output:
                    lines.append(
                        f"**Full content** (Limited to ~{token_estimate} tokens):"
                    )
                    lines.append(f"```\n{truncated_content}\n```")
                else:
                    lines.append(
                        f"Full source content (limited to ~{token_estimate} tokens):"
                    )
                    lines.append(truncated_content)
            else:
                warning = "No raw content available for this source"
                lines.append(
                    f"**Note:** {warning}"
                    if self.markdown_output
                    else f"Note: {warning}"
                )

        return "\n\n".join(lines)

    def _format_unique_sources(
        self,
        unique_sources: dict[str, dict[str, Any]],
        max_tokens_per_source: int,
        chars_per_token: int,
    ) -> str:
        """Format unique sources for display."""
        char_limit = chars_per_token * max_tokens_per_source
        formatted_sections = []
        for i, (url, source) in enumerate(unique_sources.items(), 1):
            section = self._format_single_source(source, i, char_limit)
            formatted_sections.append(section)

        header = "# Sources\n\n" if self.markdown_output else "Sources:\n\n"
        separator = "\n---\n\n" if self.markdown_output else "\n" + "=" * 50 + "\n\n"
        return header + separator.join(formatted_sections)

    def deduplicate_and_format_sources(
        self,
        search_response: dict[str, Any] | list,
        return_dict: bool = False,
    ) -> str | dict[str, dict[str, Any]]:
        """Extract, deduplicate by URL, and format sources for display."""
        logger.info("Processing sources for deduplication and formatting")

        unique_sources = {}
        sources_list = self._extract_sources_list(search_response)

        for source in sources_list:
            url = source.get("url")
            if url and url not in unique_sources:
                unique_sources[url] = source

        logger.info(f"Found {len(unique_sources)} unique sources")

        if return_dict:
            return unique_sources

        if not unique_sources:
            return "No unique sources found after deduplication"

        formatted_output = self._format_unique_sources(
            unique_sources,
            self.max_tokens_per_source,
            self.chars_per_token,
        )

        if self.markdown_output:
            return display(Markdown(formatted_output))  # type: ignore

        return formatted_output
