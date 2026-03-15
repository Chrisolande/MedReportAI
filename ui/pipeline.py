"""LangGraph streaming runner + Streamlit pipeline UI."""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from queue import Empty, Queue
from typing import Any, cast

import streamlit as st
from langchain_core.runnables import RunnableConfig

NODE_PHASE_MAP: dict[str, tuple[str, str]] = {
    "generate_report_plan": ("01", "Planning"),
    "build_section_with_tools": ("02", "Research"),
    "write_final_sections": ("03", "Synthesis"),
    "compile_final_report": ("04", "Assembly"),
    "__end__": ("05", "Complete"),
}

PHASES = [
    ("01", "\N{MICROSCOPE}", "Planning", "Parsing topic, drafting section outline"),
    ("02", "\N{SATELLITE ANTENNA}", "Research", "Parallel agents searching literature"),
    ("03", "\N{DNA DOUBLE HELIX}", "Synthesis", "Drafting sections with evidence"),
    ("04", "\N{LINK SYMBOL}", "Assembly", "Merging sections, resolving refs"),
    ("05", "\N{CHECK MARK}", "Complete", "Report finalised"),
]

_NODE_PHASE_LOOKUP: dict[str, tuple[str, str]] = dict(NODE_PHASE_MAP)


@st.cache_resource(show_spinner=False)
def _load_graph():
    from app import graph  # noqa: PLC0415

    return graph


def _node_to_phase(node_name: str) -> tuple[str, str] | None:
    return next(
        (
            phase
            for fragment, phase in _NODE_PHASE_LOOKUP.items()
            if fragment in node_name
        ),
        None,
    )


# Event handlers - one per chain event kind, uniform signature


def _on_chain_start(ev: dict, q: Queue, _result: dict) -> None:
    name = ev.get("name", "")
    q.put({"type": "log", "msg": "starting node", "node": name})
    if phase := _node_to_phase(name):
        q.put(
            {
                "type": "phase",
                "phase_id": phase[0],
                "phase_label": phase[1],
                "node": name,
            }
        )


def _on_chain_end(ev: dict, q: Queue, final_result: dict) -> None:
    q.put({"type": "log", "msg": "node complete", "node": ev.get("name", "")})
    if (output := ev.get("data", {}).get("output", {})) and isinstance(output, dict):
        final_result.update(output)


def _on_chain_error(ev: dict, q: Queue, _result: dict) -> None:
    q.put({"type": "error", "msg": str(ev.get("data", {}).get("error", "unknown"))})


_EVENT_HANDLERS = {
    "on_chain_start": _on_chain_start,
    "on_chain_end": _on_chain_end,
    "on_chain_error": _on_chain_error,
}


# Stream worker


def _stream_worker(
    topic: str,
    context: str,
    report_organization: str,
    sections: list[dict] | None,
    q: Queue,
) -> None:
    async def _run() -> None:
        g = _load_graph()
        graph_input: dict[str, Any] = {"topic": topic}
        if sections:
            graph_input["sections"] = sections

        final_result: dict = {}
        async for ev in g.astream_events(
            cast(dict, graph_input),
            config=cast(
                RunnableConfig,
                {
                    "configurable": {
                        "context": context,
                        "report_organization": report_organization,
                    }
                },
            ),
            version="v2",
        ):
            if handler := _EVENT_HANDLERS.get(ev.get("event", "")):
                handler(ev, q, final_result)

        q.put({"type": "result", "data": final_result})

    try:
        asyncio.run(_run())
    except Exception as exc:
        q.put({"type": "error", "msg": str(exc)})


# HTML rendering


def _render_pipeline_html(active_phase_id: str | None, done_phase_ids: set[str]) -> str:
    def _node_html(pid: str, icon: str, label: str) -> str:
        cls = "phase-node"
        if pid == active_phase_id:
            cls += " active"
        if pid in done_phase_ids:
            cls += " done"
        fill = (
            '<div class="phase-bar-fill"></div>'
            if (pid == active_phase_id or pid in done_phase_ids)
            else ""
        )
        return (
            f'<div class="{cls}">'
            f'<div class="phase-num">{pid}</div>'
            f'<div class="phase-icon-lg">{icon}</div>'
            f'<div class="phase-label">{label}</div>'
            f'<div class="phase-bar">{fill}</div>'
            f"</div>"
        )

    nodes = "".join(_node_html(pid, icon, label) for pid, icon, label, _ in PHASES)
    return f'<div class="pipeline-track">{nodes}</div>'


# Main UI runner


def run_with_ui(
    topic: str,
    context: str,
    report_organization: str,
    sections: list[dict] | None = None,
) -> dict | None:
    q: Queue = Queue()
    threading.Thread(
        target=_stream_worker,
        args=(topic, context, report_organization, sections, q),
        daemon=True,
    ).start()

    pipeline_ph = st.empty()
    log_ph = st.empty()
    active_phase: str | None = "01"
    done_phases: set[str] = set()
    log_lines: list[dict] = []
    result: dict | None = None
    error_msg: str | None = None

    def _log(ts: str, kind: str, node: str, msg: str) -> None:
        log_lines.append({"ts": ts, "kind": kind, "node": node, "msg": msg})

    def _refresh(status_msg: str = "") -> None:
        pipeline_ph.markdown(
            f'<div class="pipeline-wrap fade-in">'
            f"{_render_pipeline_html(active_phase, done_phases)}"
            f'<div class="pipeline-log"><span class="log-prefix">►</span>{status_msg}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        if log_lines:
            lines_html = "".join(
                f'<div class="log-line">'
                f'<span class="log-time">{e["ts"]}</span>'
                f'<span class="log-type-{e["kind"]}">[{e["kind"].upper()}]</span>'
                f' <span class="log-node">{e["node"]}</span> - {e["msg"]}'
                f"</div>"
                for e in log_lines[-18:]
            )
            log_ph.markdown(
                f'<div class="event-log-wrap">{lines_html}</div>',
                unsafe_allow_html=True,
            )

    _refresh("Initialising pipeline…")

    while True:
        try:
            ev = q.get(timeout=0.15)
        except Empty:
            if not threading.main_thread().is_alive():
                break
            continue

        ts = datetime.now().strftime("%H:%M")
        etype = ev["type"]

        if etype == "phase":
            pid, label = ev["phase_id"], ev["phase_label"]
            if active_phase and active_phase < pid:
                done_phases.add(active_phase)
            active_phase = pid
            _log(ts, "start", ev["node"], f"entered phase {label}")
            _refresh(f"Phase {pid} - {label}")

        elif etype == "log":
            _log(ts, "start", ev["node"], ev["msg"])
            _refresh(f'<span class="log-node">{ev["node"]}</span> - {ev["msg"]}')

        elif etype == "result":
            result = ev["data"]
            done_phases = {p[0] for p in PHASES}
            active_phase = None
            _log(ts, "end", "__end__", "graph completed successfully")
            _refresh("Pipeline complete \N{CHECK MARK}")
            break

        elif etype == "error":
            error_msg = ev["msg"]
            _log(ts, "err", "-", str(error_msg))
            _refresh(f"ERROR: {error_msg}")
            break

    if error_msg:
        st.error(f"Pipeline error: {error_msg}")
        return None
    return result
