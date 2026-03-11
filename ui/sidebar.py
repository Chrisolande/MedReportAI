"""Sidebar: pipeline config + report archive."""

import textwrap

import streamlit as st

from prompts.planner import context as DEFAULT_CONTEXT
from prompts.planner import report_organization as DEFAULT_REPORT_ORG
from ui import history as hist


def render() -> tuple[str, str]:
    """Render sidebar and return (context, report_organization)."""
    with st.sidebar:
        st.markdown(
            '<h3 style="margin:0 0 0.3rem;font-size:1rem;">:dna: MedReportAI</h3>'
            "<p style=\"font-family:'Syne Mono',monospace;font-size:0.62rem;"
            'color:#3a5a40;letter-spacing:0.12em;margin:0 0 1.2rem;">',
            unsafe_allow_html=True,
        )

        with st.expander(":gear: Pipeline Config", expanded=False):
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
            "letter-spacing:0.14em;text-transform:uppercase;color:#3a5a40;"
            'margin:1.2rem 0 0.6rem;">// Report Archive</p>',
            unsafe_allow_html=True,
        )

        history = hist.load()
        if not history:
            st.markdown(
                "<p style=\"font-family:'Syne Mono',monospace;font-size:0.72rem;"
                'color:#3a5a40;font-style:italic;">No archived reports.</p>',
                unsafe_allow_html=True,
            )
        else:
            selected_id = st.session_state.get("selected_history_id")
            for item in history:
                prefix = ":arrow_forward: " if item["id"] == selected_id else "  "
                title = textwrap.shorten(item["topic"], width=34, placeholder="…")
                if st.button(
                    f"{prefix}{title}\n{item['created_at']}",
                    key=f"hist_{item['id']}",
                    use_container_width=True,
                ):
                    st.session_state["selected_history_id"] = item["id"]
                    st.session_state["viewing_history"] = item
                    st.rerun()

            if st.button(":wastebasket: Clear archive", use_container_width=True):
                hist.clear()
                st.session_state.pop("selected_history_id", None)
                st.session_state.pop("viewing_history", None)
                st.rerun()

    return (
        st.session_state.get("sb_context", DEFAULT_CONTEXT),
        st.session_state.get("sb_org", DEFAULT_REPORT_ORG),
    )
