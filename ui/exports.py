"""PDF conversion and download button rendering."""

from __future__ import annotations

from datetime import datetime

import streamlit as st


def markdown_to_pdf_bytes(md_text: str) -> bytes | None:
    try:
        import markdown as md_lib
        from weasyprint import HTML

        html_body = md_lib.markdown(md_text, extensions=["tables", "fenced_code"])
        full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Syne:wght@400;600&family=Syne+Mono&display=swap" rel="stylesheet">
<style>
  body {{ font-family: 'Syne', sans-serif; font-size: 10.5pt; line-height: 1.8;
          color: #1a2018; max-width: 680px; margin: 0 auto; padding: 2cm 1.5cm; }}
  h1, h2, h3 {{ font-family: 'DM Serif Display', serif; page-break-after: avoid; }}
  h1 {{ font-size: 22pt; font-style: italic; border-bottom: 2px solid #22c55e; padding-bottom: 6pt; }}
  h2 {{ font-size: 13pt; color: #15803d; text-transform: uppercase; letter-spacing: 0.06em; }}
  h3 {{ font-size: 11pt; color: #0d9488; font-family: 'Syne Mono', monospace; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th {{ background: #f0fdf4; color: #15803d; font-family: 'Syne Mono', monospace;
       font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.06em;
       border: 1px solid #d1fae5; padding: 5pt 8pt; }}
  td {{ border: 1px solid #d1fae5; padding: 4pt 8pt; }}
  code {{ font-family: 'Syne Mono', monospace; background: #f0fdf4; padding: 1pt 4pt; border-radius: 3pt; font-size: 0.85em; }}
  blockquote {{ border-left: 3px solid #22c55e; margin-left: 0; padding-left: 1rem; color: #4a5e48; }}
  @page {{ margin: 2cm 1.5cm; }}
</style></head><body>{html_body}</body></html>"""
        return HTML(string=full_html).write_pdf()
    except ImportError:
        return None


def render_exports(final_report: str, topic: str) -> None:
    st.markdown('<p class="export-label">Export report as</p>', unsafe_allow_html=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = topic[:30].replace(" ", "_").lower()

    c1, c2, c3, _ = st.columns([1, 1, 1, 2])
    with c1:
        st.download_button(
            "\U0001f4e5 Markdown",
            data=final_report.encode(),
            file_name=f"report_{slug}_{timestamp}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with c2:
        pdf = markdown_to_pdf_bytes(final_report)
        if pdf:
            st.download_button(
                "\U0001f4e5 PDF",
                data=pdf,
                file_name=f"report_{slug}_{timestamp}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.button(
                "\U0001f4e5 PDF",
                disabled=True,
                use_container_width=True,
                help="pip install weasyprint markdown",
            )
    with c3:
        st.download_button(
            "\U0001f4e5 Plain Text",
            data=final_report.encode(),
            file_name=f"report_{slug}_{timestamp}.txt",
            mime="text/plain",
            use_container_width=True,
        )
