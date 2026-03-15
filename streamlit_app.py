"""MedReportAI Studio entry point."""

import asyncio

import streamlit as st
from dspy import Predict

from config import config
from core.signatures import ReportPlanner
from ui import history as hist
from ui.exports import render_exports
from ui.pipeline import run_with_ui
from ui.sidebar import render as render_sidebar
from ui.styles import inject_styles

st.set_page_config(
    page_title="MedReportAI",
    layout="wide",
    initial_sidebar_state="expanded",
)

_SESSION_DEFAULTS = {
    "report_result": None,
    "report_topic": None,
    "viewing_history": None,
    "selected_history_id": None,
    "pending_plan": None,
    "pending_plan_topic": None,
    "pending_plan_context": None,
    "pending_plan_org": None,
}


@st.cache_resource(show_spinner=False)
def _ensure_dspy_lm_initialized():
    return config.initialize_dspy()


def _generate_plan_preview(
    topic: str, context: str, report_organization: str
) -> list[dict]:
    _ensure_dspy_lm_initialized()

    async def _run() -> list[dict]:
        result = await asyncio.to_thread(
            Predict(ReportPlanner),
            topic=topic,
            context=context,
            report_organization=report_organization,
        )
        return [
            s.model_dump() if hasattr(s, "model_dump") else dict(s)
            for s in result.plan.sections
        ]

    with st.spinner("Generating research plan…"):
        return asyncio.run(_run())


def _clear_pending_plan() -> None:
    for key in (
        "pending_plan",
        "pending_plan_topic",
        "pending_plan_context",
        "pending_plan_org",
    ):
        st.session_state[key] = None


def _render_plan_hitl() -> list[dict]:
    plan_sections = st.session_state.get("pending_plan") or []
    if not plan_sections:
        return []

    st.markdown('<div class="report-shell fade-in">', unsafe_allow_html=True)
    st.subheader("Plan Review (HITL)")
    st.caption(
        "Review the generated plan, edit any section details, then approve to run research."
    )

    edited: list[dict] = []
    for idx, section in enumerate(plan_sections):
        with st.expander(
            f"Section {idx + 1}: {section.get('name', 'Untitled')}", expanded=idx == 0
        ):
            updated = dict(section) | {
                "name": st.text_input(
                    "Title", value=section.get("name", ""), key=f"plan_name_{idx}"
                ),
                "description": st.text_area(
                    "Description",
                    value=section.get("description", ""),
                    height=100,
                    key=f"plan_desc_{idx}",
                ),
                "research": st.checkbox(
                    "Requires research",
                    value=bool(section.get("research", True)),
                    key=f"plan_research_{idx}",
                ),
                "content": st.text_area(
                    "Writing guidance",
                    value=section.get("content", ""),
                    height=120,
                    key=f"plan_content_{idx}",
                ),
            }
            edited.append(updated)

    st.markdown("</div>", unsafe_allow_html=True)
    return edited


def _plan_action_buttons() -> tuple[bool, bool, bool]:
    col_approve, col_regen, col_decline = st.columns([2, 1, 1])
    with col_approve:
        approve = st.button(
            "Approve Plan & Run",
            type="primary",
            use_container_width=True,
            key="approve_plan_run",
        )
    with col_regen:
        regen = st.button("Regenerate", use_container_width=True, key="regenerate_plan")
    with col_decline:
        decline = st.button("Decline", use_container_width=True, key="decline_plan")
    return approve, regen, decline


def _handle_pending_plan(topic: str, context: str, report_organization: str) -> None:
    edited_sections = _render_plan_hitl()
    approve, regen, decline = _plan_action_buttons()

    if regen:
        try:
            st.session_state["pending_plan"] = _generate_plan_preview(
                st.session_state.get("pending_plan_topic") or topic,
                st.session_state.get("pending_plan_context") or context,
                st.session_state.get("pending_plan_org") or report_organization,
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Unable to regenerate plan: {exc}")

    if decline:
        _clear_pending_plan()
        st.info("Plan declined. Update your query and run again when ready.")
        st.stop()

    if approve:
        approved_topic = st.session_state.get("pending_plan_topic") or topic
        result = run_with_ui(
            approved_topic,
            st.session_state.get("pending_plan_context") or context,
            st.session_state.get("pending_plan_org") or report_organization,
            sections=edited_sections,
        )
        if result is not None:
            st.session_state["report_result"] = result
            st.session_state["report_topic"] = approved_topic
            if final := result.get("final_report", ""):
                hist.add(approved_topic, final)
        _clear_pending_plan()
        st.rerun()

    st.stop()


def main() -> None:
    inject_styles()

    for k, v in _SESSION_DEFAULTS.items():
        st.session_state.setdefault(k, v)

    context, report_organization = render_sidebar()

    st.markdown(
        """
        <div class="masthead fade-in">
            <div class="masthead-eyebrow">
                Medical Intelligence Platform
                <span class="status-badge online"><span class="dot"></span>System Online</span>
            </div>
            <h1>Med<em>Report</em>AI</h1>
            <p class="masthead-sub">
                Parallel LangGraph agents, plan &rarr; retrieve &rarr; synthesise &rarr; compile.
                Real-time node-level progress.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="input-shell fade-in">', unsafe_allow_html=True)
    topic = st.text_area(
        "Research Query",
        placeholder="e.g. Long-term pediatric health outcomes in conflict settings",
        height=108,
        key="main_topic",
    )
    col_run, col_clear, _ = st.columns([2, 1, 3])
    with col_run:
        run_clicked = st.button(
            "Run Pipeline", type="primary", use_container_width=True
        )
    with col_clear:
        clear_clicked = st.button("Reset", type="secondary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if clear_clicked:
        for k in _SESSION_DEFAULTS:
            st.session_state.pop(k, None)
        st.rerun()

    # Show archived report if one is selected and pipeline isn't running
    if (viewing := st.session_state.get("viewing_history")) and not run_clicked:
        st.markdown(
            f'<div class="archive-shell fade-in">'
            f'<p style="font-family:var(--mono);font-size:0.68rem;color:var(--amber);'
            f'letter-spacing:0.08em;margin:0 0 0.3rem;">{viewing["created_at"]}</p>'
            f'<p style="font-family:var(--serif);font-size:1.1rem;font-style:italic;'
            f'color:var(--ink);margin:0 0 1rem;">{viewing["topic"]}</p>',
            unsafe_allow_html=True,
        )
        st.markdown(viewing["report"])
        render_exports(viewing["report"], viewing["topic"])
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if run_clicked:
        if not topic.strip():
            st.warning("Enter a research query to continue.")
        else:
            try:
                st.session_state.update(
                    {
                        "pending_plan": _generate_plan_preview(
                            topic.strip(), context, report_organization
                        ),
                        "pending_plan_topic": topic.strip(),
                        "pending_plan_context": context,
                        "pending_plan_org": report_organization,
                        "report_result": None,
                        "report_topic": None,
                        "viewing_history": None,
                    }
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Unable to generate plan for review: {exc}")

    if st.session_state.get("pending_plan"):
        _handle_pending_plan(topic, context, report_organization)

    if not (result := st.session_state.get("report_result")):
        return

    final_report = result.get("final_report", "")
    saved_topic = st.session_state.get("report_topic", "report")

    if final_report:
        st.markdown('<div class="report-shell fade-in">', unsafe_allow_html=True)
        st.markdown(final_report)
        st.markdown("<hr>", unsafe_allow_html=True)
        render_exports(final_report, saved_topic)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("Pipeline completed but no `final_report` key found in graph output.")

    with st.expander("Raw graph state"):
        st.json(result)


if __name__ == "__main__":
    main()
