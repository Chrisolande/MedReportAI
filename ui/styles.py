"""CSS injection for MedReportAI Studio."""

from pathlib import Path

import streamlit as st

_CSS = Path("ui/styles.css").read_text()


def inject_styles() -> None:
    # CHANGE: Replaced st.markdown with st.html to bypass the markdown parser entirely
    st.html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        f"<style>{_CSS}</style>"
    )
