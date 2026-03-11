"""MedReportAI Studio entry point."""

import streamlit as st

from ui import history as hist
from ui.exports import render_exports
from ui.pipeline import run_with_ui
from ui.sidebar import render as render_sidebar
from ui.styles import inject_styles

st.set_page_config(
    page_title="MedReportAI",
    page_icon=":dna:",
    layout="wide",
    initial_sidebar_state="expanded",
)


_SESSION_DEFAULTS = {
    "report_result": None,
    "report_topic": None,
    "viewing_history": None,
    "selected_history_id": None,
}


def main() -> None:
    inject_styles()

    for k, v in _SESSION_DEFAULTS.items():
        st.session_state.setdefault(k, v)

    context, report_organization = render_sidebar()

    # masthead
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
                Parallel LangGraph agents, plan → retrieve → synthesise → compile.
                Real-time node-level progress.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # input
    st.markdown('<div class="input-shell fade-in">', unsafe_allow_html=True)
    topic = st.text_area(
        "Research Query",
        placeholder="e.g.  Long-term pediatric health outcomes in conflict settings and evidence-backed interventions",
        height=108,
        key="main_topic",
    )
    col_run, col_clear, _ = st.columns([2, 1, 3])
    with col_run:
        run_clicked = st.button(
            ":arrow_forward: Run Pipeline", type="primary", use_container_width=True
        )
    with col_clear:
        clear_clicked = st.button("Reset", type="secondary", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    if clear_clicked:
        for k in _SESSION_DEFAULTS:
            st.session_state.pop(k, None)
        st.rerun()

    # archived report view
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

    # run pipeline
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

    # result display
    result = st.session_state.get("report_result")
    if not result:
        return

    final_report = result.get("final_report", "")
    saved_topic = st.session_state.get("report_topic", "report")

    st.markdown('<div class="report-shell fade-in">', unsafe_allow_html=True)
    if final_report:
        st.markdown(final_report)
        st.markdown("<hr>", unsafe_allow_html=True)
        render_exports(final_report, saved_topic)
    else:
        st.info("Pipeline completed, no `final_report` key in graph output.")
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("// Raw graph state"):
        st.json(result)


if __name__ == "__main__":
    main()
