import os
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool
from loguru import logger

from scripts.pubmed_scraper import PubMedScraper

ACTIVE_CSV_POINTER = Path("data/.active_pubmed_csv.txt")


def _safe_slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.lower())
    return "_".join(part for part in cleaned.split("_") if part)


@tool
async def pubmed_scraper_tool(
    search_query: str,
    max_results: int = 10,
    start_date: str = "2018/01/01",
    end_date: str = "",
) -> str:
    """Search PubMed live, persist to CSV, and mark that CSV as active for retrieval."""
    if not search_query.strip():
        return "The `search_query` cannot be empty."

    entrez_email = os.getenv("ENTREZ_EMAIL")
    if not entrez_email:
        return "ENTREZ_EMAIL is not configured. Set it in your environment to use PubMed scraping."

    if not end_date:
        end_date = datetime.now().strftime("%Y/%m/%d")

    capped_max_results = max(1, min(max_results, 25))

    try:
        output_slug = _safe_slug(search_query)[:40] or "pubmed"
        output_file = f"data/pubmed_live_{output_slug}.csv"

        scraper = PubMedScraper(
            email=entrez_email,
            topics=[search_query],
            start_date=start_date,
            end_date=end_date,
            max_results=capped_max_results,
            output_file=output_file,
            temperature=0.1,
        )

        df = await scraper.scrape_async()
        if df.empty:
            return "No PubMed studies found for the provided query and date range."

        # Mark this dataset as the active retrieval source for retriever_tool.
        ACTIVE_CSV_POINTER.parent.mkdir(parents=True, exist_ok=True)
        ACTIVE_CSV_POINTER.write_text(output_file, encoding="utf-8")

        rows = []
        for _, row in df.head(8).iterrows():
            title = str(row.get("Title", "")).strip()
            journal = str(row.get("Journal", "")).strip()
            pub_date = str(row.get("Publication Date", "")).strip()
            url = str(row.get("Url", "")).strip()
            if title and url:
                rows.append(f"- **{title}** ({journal}, {pub_date})\\n  - {url}")
            elif title:
                rows.append(f"- **{title}** ({journal}, {pub_date})")

        if not rows:
            return (
                "PubMed returned records, but no usable citation fields were extracted."
            )

        return (
            f"PubMed direct search results for: **{search_query}** "
            f"(showing {min(len(rows), 8)} of {len(df)})\\n"
            f"Dataset persisted to: `{output_file}` and set as active retrieval source.\\n\\n"
            + "\\n".join(rows)
        )
    except Exception as exc:
        logger.error(f"Error in pubmed_scraper_tool: {exc}")
        return f"PubMed scraping failed: {exc}"
