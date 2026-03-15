import os
import sys
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pubmed_scraper import PubMedScraper

_DATA_DIR = Path("data")


def _safe_slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.lower())
    return "_".join(part for part in cleaned.split("_") if part)


def _format_pubmed_rows(df) -> list[str]:
    rows: list[str] = []
    iterator = df.head(8).iterrows() if hasattr(df, "iterrows") else iter(df.head(8))
    for _, row in iterator:
        title = str(row.get("Title", "")).strip()
        if not title:
            continue
        journal = str(row.get("Journal", "")).strip()
        pub_date = str(row.get("Publication Date", "")).strip()
        url = str(row.get("Url", "")).strip()
        line = f"- **{title}** ({journal}, {pub_date})"
        if url:
            line += f"\n  - {url}"
        rows.append(line)
    return rows


def _build_output(
    search_query: str, output_file: str, rows: list[str], total: int
) -> str:
    return (
        f"DATASET_PATH: {output_file}\n"
        f"PubMed direct search results for: **{search_query}** "
        f"(showing {min(len(rows), 8)} of {total})\n"
        f"Dataset persisted to: `{output_file}`.\n\n" + "\n".join(rows)
    )


@tool
async def pubmed_scraper_tool(
    search_query: str,
    max_results: int = 25,
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

    output_slug = _safe_slug(search_query)[:40] or "pubmed"
    output_file = str(_DATA_DIR / f"pubmed_live_{output_slug}.csv")

    try:
        scraper = PubMedScraper(
            email=entrez_email,
            pubmed_query=search_query,
            start_date=start_date,
            end_date=end_date,
            max_results=max(1, min(max_results, 100)),
            output_file=output_file,
            temperature=0.1,
        )

        df = await scraper.scrape_async()

        if df.empty:
            return "No PubMed studies found for the provided query and date range."

        rows = _format_pubmed_rows(df)
        if not rows:
            return (
                "PubMed returned records, but no usable citation fields were extracted."
            )

        return _build_output(search_query, output_file, rows, len(df))

    except Exception as exc:
        logger.error(f"Error in pubmed_scraper_tool: {exc}")
        return f"PubMed scraping failed: {exc}"
