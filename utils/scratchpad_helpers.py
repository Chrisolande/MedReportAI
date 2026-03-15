"""Shared scratchpad handler utilities for MedReportAI."""

from pathlib import Path

from langchain_core.messages import ToolMessage


def save_scratchpad(content: str, filepath: str, base_dir: str) -> None:
    """Persist scratchpad content to the specified directory."""
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)
    (base / filepath).write_text(content, encoding="utf-8")


def handle_write(args: dict, scratchpad: str, call_id: str):
    notes = args.get("notes", "")
    new_content = (
        notes
        if args.get("mode") == "replace"
        else (f"{scratchpad}\n\n{notes}" if scratchpad else notes)
    )
    return new_content, ToolMessage(
        content=f"Wrote to scratchpad: {notes}", tool_call_id=call_id
    )


def handle_read(args: dict, scratchpad: str, call_id: str) -> ToolMessage:
    content = scratchpad or "Scratchpad is empty."
    query = args.get("query", "all")
    label = f"(query: '{query}') " if query != "all" else ""
    return ToolMessage(
        content=f"Scratchpad contents {label}:\n\n{content}", tool_call_id=call_id
    )


def handle_clear(args: dict, call_id: str):
    if args.get("confirm", False):
        return "", ToolMessage(
            content="Scratchpad cleared successfully.", tool_call_id=call_id
        )
    return None, ToolMessage(
        content="Scratchpad clear cancelled (confirm=False).", tool_call_id=call_id
    )
