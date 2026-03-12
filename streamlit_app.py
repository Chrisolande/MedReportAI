"""MedReportAI Studio entry point."""

import streamlit as st

from prompts.planner import context as DEFAULT_CONTEXT
from prompts.planner import report_organization as DEFAULT_REPORT_ORG
from ui import history as hist
from ui.exports import render_exports
from ui.pipeline import run_with_ui
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
}


def render_sidebar() -> tuple[str, str]:
    with st.sidebar:
        with st.expander("Pipeline Config", expanded=False, icon=None):
            context = st.text_area(
                "Context / Persona",
                value=DEFAULT_CONTEXT,
                height=95,
                help="System persona for planner prompts.",
                key="sb_context",
            )
            report_organization = st.text_area(
                "Report Structure",
                value=DEFAULT_REPORT_ORG,
                height=105,
                help="Structure guidance for the planner.",
                key="sb_org",
            )

        st.markdown(
            "<p style=\"font-family:'Syne Mono',monospace;font-size:0.60rem;"
            "color:#5a7060;letter-spacing:0.18em;text-transform:uppercase;"
            "margin:1.4rem 0 0.5rem;padding-bottom:0.4rem;"
            'border-bottom:1px solid rgba(74,222,128,0.12);">// Report Archive</p>',
            unsafe_allow_html=True,
        )

        history = hist.load()
        if not history:
            st.caption("No archived reports.")
        else:
            selected_id = st.session_state.get("selected_history_id")
            for item in history:
                active = item["id"] == selected_id
                label = f"{'>\u25b6 ' if active else '   '}{item['topic'][:42]}\n\u2014 {item['created_at']}"
                if st.button(label, key=f"hist_{item['id']}", use_container_width=True):
                    st.session_state["selected_history_id"] = item["id"]
                    st.session_state["viewing_history"] = item
                    st.rerun()

            if st.button("\u2715  Clear archive", use_container_width=True):
                hist.clear()
                st.session_state.pop("selected_history_id", None)
                st.session_state.pop("viewing_history", None)
                st.rerun()

    return (
        st.session_state.get("sb_context", DEFAULT_CONTEXT),
        st.session_state.get("sb_org", DEFAULT_REPORT_ORG),
    )


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
                <span class="status-badge online">
                    <span class="dot"></span>System Online
                </span>
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

    viewing = st.session_state.get("viewing_history")
    if viewing and not run_clicked:
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
            result = run_with_ui(topic.strip(), context, report_organization)
            if result is not None:
                st.session_state["report_result"] = result
                st.session_state["report_topic"] = topic.strip()
                final = result.get("final_report", "")
                if final:
                    hist.add(topic.strip(), final)
                st.rerun()

    result = st.session_state.get("report_result")
    if not result:
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
