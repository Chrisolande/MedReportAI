import asyncio

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END

from core import tool_node


def test_extract_dataset_path_handles_present_and_missing_values():
    assert (
        tool_node._extract_dataset_path(
            "DATASET_PATH: data/pubmed_live_example.csv\nBody"
        )
        == "data/pubmed_live_example.csv"
    )
    assert tool_node._extract_dataset_path("No dataset marker here") is None


def test_call_context_build_update_tracks_all_side_effects(monkeypatch):
    state = {
        "scratchpad": "existing notes",
        "sources": [],
        "active_csv_path": "",
        "run_id": "abc123",
        "citation_registry": {},
    }
    write_message = ToolMessage(content="saved", tool_call_id="call-write")
    read_message = ToolMessage(content="existing notes", tool_call_id="call-read")

    monkeypatch.setattr(
        tool_node,
        "_handle_write",
        lambda args, current_state, call_id: ("updated notes", write_message),
    )
    monkeypatch.setattr(
        tool_node,
        "_handle_read",
        lambda args, current_state, call_id: read_message,
    )

    captured_args = {}

    async def fake_external(name, args, call_id):
        captured_args.update(args)
        return ToolMessage(
            content=(
                "DATASET_PATH: data/pubmed_run_abc123.csv\n"
                "https://example.org/study-one\n"
                "## 1. Study One\n"
                "**Authors:** Team One\n"
                "**URL:** https://example.org/study-one"
            ),
            tool_call_id=call_id,
        )

    monkeypatch.setattr(tool_node, "_handle_external", fake_external)

    ctx = tool_node._CallContext(
        {
            **state,
            "active_csv_path": "",
        }
    )

    asyncio.run(ctx.dispatch("WriteToScratchpad", {"notes": "x"}, "call-write"))
    asyncio.run(ctx.dispatch("ReadFromScratchpad", {"query": "all"}, "call-read"))
    asyncio.run(
        ctx.dispatch(
            "pubmed_scraper_tool", {"search_query": "malnutrition"}, "call-pubmed"
        )
    )

    update = ctx.build_update()

    assert update["scratchpad"] == "updated notes"
    assert update["active_csv_path"] == "data/pubmed_run_abc123.csv"
    assert len(update["messages"]) == 3
    assert update["sources"][0]["url"] == "https://example.org/study-one"
    assert update["sources"][0]["authors"] == "Team One"
    assert captured_args["csv_path"] == "data/pubmed_run_abc123.csv"
    assert "citation_registry" in update
    assert update["citation_registry"]["https://example.org/study-one"] == 1


def test_call_context_injects_active_csv_for_retriever(monkeypatch):
    captured_args = {}

    async def fake_external(name, args, call_id):
        captured_args.update(args)
        return ToolMessage(content="https://example.org/record", tool_call_id=call_id)

    monkeypatch.setattr(tool_node, "_handle_external", fake_external)

    ctx = tool_node._CallContext(
        {
            "messages": [],
            "scratchpad": "",
            "sources": [],
            "active_csv_path": "data/current.csv",
            "run_id": "test42",
            "citation_registry": {},
        }
    )

    asyncio.run(ctx.dispatch("retriever_tool", {"search_query": "query"}, "call-1"))

    assert captured_args["csv_path"] == "data/pubmed_run_test42.csv"
    assert ctx.sources[0]["url"] == "https://example.org/record"


def test_tool_node_returns_empty_messages_when_no_tool_calls():
    result = asyncio.run(tool_node.tool_node({"messages": [AIMessage(content="done")]}))

    assert result == {"messages": []}


def test_tool_node_saves_scratchpad_when_updated(monkeypatch):
    saved = {}

    monkeypatch.setattr(
        tool_node,
        "_handle_write",
        lambda args, current_state, call_id: (
            f"{current_state.get('scratchpad', '')}\n{args['notes']}".strip(),
            ToolMessage(content="ok", tool_call_id=call_id),
        ),
    )

    async def fake_save(content, filepath):
        saved["content"] = content
        saved["filepath"] = filepath

    monkeypatch.setattr(tool_node, "save_scratchpad_async", fake_save)

    state = {
        "messages": [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "WriteToScratchpad",
                        "args": {"notes": "new evidence"},
                        "id": "call-1",
                    }
                ],
            )
        ],
        "scratchpad": "existing",
        "scratchpad_file": "scratchpad_section.md",
        "sources": [],
        "active_csv_path": "",
    }

    result = asyncio.run(tool_node.tool_node(state))

    assert result["scratchpad"] == "existing\nnew evidence"
    assert saved == {
        "content": "existing\nnew evidence",
        "filepath": "scratchpad_section.md",
    }


def test_tools_condition_routes_based_on_pending_calls():
    with_calls = {
        "messages": [
            AIMessage(content="", tool_calls=[{"name": "x", "args": {}, "id": "1"}])
        ]
    }
    without_calls = {"messages": [AIMessage(content="no tools")]}

    assert tool_node.tools_condition(with_calls) == "tools"
    assert tool_node.tools_condition(without_calls) == END
