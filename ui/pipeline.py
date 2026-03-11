"""LangGraph streaming runner + Streamlit pipeline UI."""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime
from queue import Empty, Queue

import streamlit as st

# node -> phase mapping - edit to match your graph node names
NODE_PHASE_MAP: dict[str, tuple[str, str]] = {
    "generate_report_plan": ("01", "Planning"),
    "build_section_with_tools": ("02", "Research"),
    "write_final_sections": ("03", "Synthesis"),
    "compile_final_report": ("04", "Assembly"),
    "__end__": ("05", "Complete"),
}

PHASES = [
    ("01", ":microscope:", "Planning", "Parsing topic, drafting section outline"),
    ("02", ":satellite:", "Research", "Parallel agents searching literature"),
    ("03", ":dna:", "Synthesis", "Drafting sections with evidence"),
    ("04", ":link:", "Assembly", "Merging sections, resolving refs"),
    ("05", ":white_checkmark:", "Complete", "Report finalised"),
]


@st.cache_resource(show_spinner=False)
def _load_graph():
    from app import graph  # noqa: PLC0415

    return graph


def _node_to_phase(node_name: str) -> tuple[str, str] | None:
    for fragment, phase in NODE_PHASE_MAP.items():
        if fragment in node_name:
            return phase
    return None


def _stream_worker(
    topic: str,
    context: str,
    report_organization: str,
    q: Queue,
) -> None:
    """Background thread: runs astream_events and pushes events onto q."""

    async def _run() -> None:
        g = _load_graph()
        run_config = {
            "configurable": {
                "context": context,
                "report_organization": report_organization,
            }
        }
        final_result: dict = {}
        async for ev in g.astream_events(
            {"topic": topic}, config=run_config, version="v2"
        ):
            kind = ev.get("event", "")
            name = ev.get("name", "")

            if kind == "on_chain_start":
                q.put({"type": "log", "msg": "starting node", "node": name})
                phase = _node_to_phase(name)
                if phase:
                    q.put(
                        {
                            "type": "phase",
                            "phase_id": phase[0],
                            "phase_label": phase[1],
                            "node": name,
                        }
                    )

            elif kind == "on_chain_end":
                q.put({"type": "log", "msg": "node complete", "node": name})
                output = ev.get("data", {}).get("output", {})
                if isinstance(output, dict) and output:
                    final_result.update(output)

            elif kind == "on_chain_error":
                q.put(
                    {
                        "type": "error",
                        "msg": str(ev.get("data", {}).get("error", "unknown")),
                    }
                )

        q.put({"type": "result", "data": final_result})

    try:
        asyncio.run(_run())
    except Exception as exc:
        q.put({"type": "error", "msg": str(exc)})


def _render_pipeline_html(active_phase_id: str | None, done_phase_ids: set[str]) -> str:
    nodes = []
    for pid, icon, label, _ in PHASES:
        cls = "phase-node"
        if pid == active_phase_id:
            cls += " active"
        if pid in done_phase_ids:
            cls += " done"
        bar_fill = (
            '<div class="phase-bar-fill"></div>'
            if (pid == active_phase_id or pid in done_phase_ids)
            else ""
        )
        nodes.append(
            f'<div class="{cls}">'
            f'<div class="phase-num">{pid}</div>'
            f'<div class="phase-icon-lg">{icon}</div>'
            f'<div class="phase-label">{label}</div>'
            f'<div class="phase-bar">{bar_fill}</div>'
            f"</div>"
        )
    return '<div class="pipeline-track">' + "".join(nodes) + "</div>"


def run_with_ui(topic: str, context: str, report_organization: str) -> dict | None:
    """Start the streaming worker and drive the Streamlit progress UI."""
    q: Queue = Queue()
    thread = threading.Thread(
        target=_stream_worker,
        args=(topic, context, report_organization, q),
        daemon=True,
    )
    thread.start()

    pipeline_ph = st.empty()
    log_ph = st.empty()

    active_phase: str | None = "01"
    done_phases: set[str] = set()
    log_lines: list[dict] = []
    result: dict | None = None
    error_msg: str | None = None

    def _refresh(status_msg: str = "") -> None:
        track_html = _render_pipeline_html(active_phase, done_phases)
        pipeline_ph.markdown(
            f'<div class="pipeline-wrap fade-in">'
            f"{track_html}"
            f'<div class="pipeline-log">'
            f'<span class="log-prefix">►</span>{status_msg}'
            f"</div></div>",
            unsafe_allow_html=True,
        )
        if log_lines:
            lines_html = "".join(
                f'<div class="log-line">'
                f'<span class="log-time">{entry["ts"]}</span>'
                f'<span class="log-type-{entry["kind"]}">[{entry["kind"].upper()}]</span>'
                f'<span class="log-msg"> <span class="log-node">{entry["node"]}</span> — {entry["msg"]}</span>'
                f"</div>"
                for entry in log_lines[-18:]
            )
            log_ph.markdown(
                f'<div class="event-log-wrap">{lines_html}</div>',
                unsafe_allow_html=True,
            )

    _refresh("Initialising pipeline…")

    while thread.is_alive() or not q.empty():
        try:
            ev = q.get(timeout=0.15)
        except Empty:
            continue

        ts = datetime.now().strftime("%H:%M")
        etype = ev["type"]

        if etype == "phase":
            pid, label = ev["phase_id"], ev["phase_label"]
            if active_phase and active_phase < pid:
                done_phases.add(active_phase)
            active_phase = pid
            log_lines.append(
                {
                    "ts": ts,
                    "kind": "start",
                    "node": ev["node"],
                    "msg": f"entered phase {label}",
                }
            )
            _refresh(f"Phase {pid} - {label}")

        elif etype == "log":
            log_lines.append(
                {"ts": ts, "kind": "start", "node": ev["node"], "msg": ev["msg"]}
            )
            _refresh(f'<span class="log-node">{ev["node"]}</span> - {ev["msg"]}')

        elif etype == "result":
            result = ev["data"]
            done_phases = {p[0] for p in PHASES}
            active_phase = None
            log_lines.append(
                {
                    "ts": ts,
                    "kind": "end",
                    "node": "__end__",
                    "msg": "graph completed successfully",
                }
            )
            _refresh("Pipeline complete :white_check_mark:")
            break

        elif etype == "error":
            error_msg = ev["msg"]
            log_lines.append({"ts": ts, "kind": "err", "node": "-", "msg": error_msg})
            _refresh(f"ERROR: {error_msg}")
            break

    thread.join(timeout=5)

    if error_msg:
        st.error(f"Pipeline error: {error_msg}")
        return None
    return result
