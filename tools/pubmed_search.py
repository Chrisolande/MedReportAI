import os
import sys
import threading
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool
from loguru import logger

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.pubmed_scraper import PubMedScraper

_DATA_DIR = Path("data")

# Module-level lock for concurrent CSV writes within a single process
_csv_write_lock = threading.Lock()


def _safe_slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.lower())
    return "_".join(part for part in cleaned.split("_") if part)


def _format_pubmed_rows(df) -> list[str]:
    rows: list[str] = []
    for _, row in df.head(8).iterrows():
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


def _deduplicate_csv(path: str) -> None:
    """Deduplicate a CSV file by Pmid, keeping the first occurrence."""
    import pandas as pd

    try:
        df = pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        logger.warning(f"Could not read CSV for dedup ({path}): {exc}")
        return
    pmid_col = next((c for c in df.columns if c.lower() == "pmid"), None)
    if pmid_col:
        df.drop_duplicates(subset=[pmid_col], keep="first", inplace=True)
        df.to_csv(path, index=False)


def _resolve_output_file(search_query: str, csv_path: str) -> str:
    if csv_path:
        return csv_path
    return str(
        _DATA_DIR / f"pubmed_live_{(_safe_slug(search_query)[:40] or 'pubmed')}.csv"
    )


async def _run_scraper(search_query, start_date, end_date, max_results, output_file):
    scraper = PubMedScraper(
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

    with _csv_write_lock:
        _deduplicate_csv(output_file)

    rows = _format_pubmed_rows(df)
    if not rows:
        return "PubMed returned records, but no usable citation fields were extracted."

    return _build_output(search_query, output_file, rows, len(df))


@tool
async def pubmed_scraper_tool(
    search_query: str,
    max_results: int = 25,
    start_date: str = "2018/01/01",
    end_date: str = "",
    csv_path: str = "",
) -> str:
    """Search PubMed live, persist to CSV, and mark that CSV as active for retrieval."""
    if not search_query.strip():
        return "The `search_query` cannot be empty."

    if not os.environ.get("ENTREZ_EMAIL"):
        return "ENTREZ_EMAIL is not configured"

    if not end_date:
        end_date = datetime.now().strftime("%Y/%m/%d")

    output_file = _resolve_output_file(search_query, csv_path)

    try:
        return await _run_scraper(
            search_query, start_date, end_date, max_results, output_file
        )
    except RuntimeError as exc:
        logger.error(f"PubMed scraper exhausted retries: {exc}")
        return f"PubMed scraping failed after retries: {exc}"
    except Exception as exc:
        logger.error(f"Error in pubmed_scraper_tool: {exc}")
        return f"PubMed scraping failed: {exc}"
