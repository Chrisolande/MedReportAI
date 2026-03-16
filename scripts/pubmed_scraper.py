"""PubMed scraper - refactored with pymed + pydantic-settings."""

import asyncio
import os
import time
from pathlib import Path
from typing import Any, Literal

import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from loguru import logger
from pydantic import BaseModel, Field
from pymed import PubMed

from prompts.scraper import pubmed_parser_prompt

_ = load_dotenv()

MAX_RETRIES = 4
BACKOFF_BASE = 2.0
_DEFAULT_FILENAME = "data/pubmed_results.csv"


class ArticleQuery(BaseModel):
    pubmed_query: str = Field(
        description=(
            "A ready-to-use PubMed query string with proper field tags "
            "(e.g. '[Title/Abstract]', '[Author]', date filters via mindate/maxdate)."
        )
    )
    start_date: str = Field(
        default="",
        description="Start date in YYYY/MM/DD format. Leave empty if not specified.",
    )
    end_date: str = Field(
        default="2026/12/31",
        description="End date in YYYY/MM/DD format. Default to '2026/12/31' if not specified.",
    )
    max_results: int = Field(
        default=25,
        description="Number of results to fetch. Translate qualitative text to integers: 'many'=100, 'some'=25, 'few'=10.",
    )
    filename: str = Field(
        default=_DEFAULT_FILENAME,
        description="Descriptive filename for the output. Must be lowercase, use underscores, start with 'data/', end with '.csv', and be under 60 characters.",
    )


def _get_affiliations(xml: Any) -> list[str]:
    """Extract unique affiliation strings from XML."""
    affs = []
    for aff in xml.findall(".//Affiliation"):
        if aff.text:
            affs.append(aff.text.strip())
    return list(dict.fromkeys(affs))


def _get_references(xml: Any, limit: int = 5) -> list[str]:
    """Extract first N references with optional PMID links."""
    refs = []
    for ref in xml.findall(".//Reference")[:limit]:
        citation = getattr(ref.find("Citation"), "text", "") or ""
        pmid_el = ref.find(".//ArticleId[@IdType='pubmed']")
        if pmid_el is not None and pmid_el.text:
            citation += f" https://pubmed.ncbi.nlm.nih.gov/{pmid_el.text.strip()}"
        if citation.strip():
            refs.append(citation.strip())
    return refs


def _extract_extras(article: Any) -> dict[str, str]:
    """Pull affiliations and references from raw XML (fields pymed omits)."""
    try:
        xml = article.xml
        return {
            "affiliations": "; ".join(_get_affiliations(xml)),
            "references": " | ".join(_get_references(xml)),
        }
    except Exception as exc:
        logger.debug(f"Extra-field extraction skipped: {exc}")
        return {"affiliations": "", "references": ""}


def _parse_authors(article: Any) -> str:
    authors = [
        f"{a.get('lastname', '')} {a.get('firstname', '')}".strip()
        for a in (article.authors or [])
    ]
    return ", ".join(authors)


def _parse_keywords(article: Any) -> str:
    return ", ".join(str(k) for k in (article.keywords or []) if k)


def _build_article_row(article: Any) -> dict:
    pmid = str(article.pubmed_id or "").split("\n")[0].strip()
    pub_date = str(article.publication_date) if article.publication_date else ""
    row = {
        "pmid": pmid,
        "title": article.title or "",
        "abstract": article.abstract or "",
        "authors": _parse_authors(article),
        "journal": article.journal or "",
        "keywords": _parse_keywords(article),
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}" if pmid else "",
        "publication_date": pub_date,
    }
    row.update(_extract_extras(article))
    return row


def _article_to_dict(article: Any) -> dict | None:
    """Convert a pymed PubMedArticle to a flat dict."""
    try:
        return _build_article_row(article)
    except Exception as exc:
        logger.warning(f"Article parse error: {exc}")
        return None


def _query_with_backoff(pubmed: PubMed, query: str, max_results: int) -> list:
    """Run a PubMed query with exponential backoff on rate limit errors."""
    for attempt in range(MAX_RETRIES):
        try:
            return list(pubmed.query(query, max_results=max_results))
        except Exception as exc:
            if "429" in str(exc) or "Too Many Requests" in str(exc):
                wait = BACKOFF_BASE**attempt
                logger.warning(
                    f"Rate limited (attempt {attempt + 1}/{MAX_RETRIES}), "
                    f"retrying in {wait:.1f}s"
                )
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"PubMed query failed after {MAX_RETRIES} attempts")


def _run_async(coro):
    """Run a coroutine safely when no event loop is running."""
    try:
        asyncio.get_running_loop()
        raise RuntimeError(
            "Called a sync wrapper from inside an async context. "
            "Use the _async variant instead."
        )
    except RuntimeError as exc:
        if "sync wrapper" in str(exc):
            raise
    return asyncio.run(coro)


class PubMedScraper:
    def __init__(
        self,
        *,
        email: str | None = None,
        pubmed_query: str = "",
        start_date: str = "2012/01/01",
        end_date: str = "2025/08/27",
        max_results: int = 25,
        delay: float = 0.1,
        output_file: str = _DEFAULT_FILENAME,
        model: Literal["deepseek-chat", "deepseek-reasoner"] = "deepseek-chat",
        temperature: float = 1.3,
    ):
        self.pubmed_query = pubmed_query
        self.start_date = start_date
        self.end_date = end_date
        self.max_results = max_results
        self.delay = delay
        self.output_file = output_file

        self._pubmed = PubMed(
            tool="MedReportAI",
            email=os.getenv("ENTREZ_EMAIL", email or ""),
        )
        api_key = os.getenv("NCBI_API_KEY")
        if api_key:
            self._pubmed.parameters["api_key"] = api_key
            logger.info("NCBI API key loaded")
        else:
            logger.warning("No NCBI_API_KEY found, limited to 3 req/s")

        self._llm = ChatDeepSeek(
            model=model,
            temperature=temperature,
            max_tokens=2048,  # type: ignore
        )

    def parse_query(self, natural_language: str) -> ArticleQuery:
        """Convert a free-text request into a structured PubMed query via LLM."""
        structured_llm = self._llm.with_structured_output(ArticleQuery)
        result = structured_llm.invoke(
            [
                SystemMessage(content=pubmed_parser_prompt),
                HumanMessage(content=natural_language),
            ]
        )
        logger.info(f"Parsed query: {result}")
        return result  # type: ignore

    def _build_query_with_dates(self) -> str:
        query = self.pubmed_query
        if self.start_date or self.end_date:
            start = self.start_date or "1900/01/01"
            end = self.end_date or "3000/12/31"
            query += (
                f' AND ("{start}"[Date - Publication] : "{end}"[Date - Publication])'
            )
        return query

    async def _merge_existing_csv(self, df: pd.DataFrame) -> pd.DataFrame:
        existing_path = Path(self.output_file)
        if not existing_path.exists():
            return df
        try:
            existing_df = pd.read_csv(self.output_file)
            df = pd.concat([existing_df, df], ignore_index=True)
            pmid_col = next((c for c in df.columns if c.lower() == "pmid"), None)
            if pmid_col:
                df.drop_duplicates(subset=[pmid_col], keep="first", inplace=True)
        except Exception as exc:
            logger.warning(f"Could not merge with existing CSV: {exc}")
        return df

    async def scrape_async(self) -> pd.DataFrame:
        """Fetch articles matching self.pubmed_query and return a DataFrame."""
        if not self.pubmed_query:
            logger.warning("No query set – returning empty DataFrame")
            return pd.DataFrame()

        query = self._build_query_with_dates()
        logger.info(f"Querying PubMed: {query!r}  max={self.max_results}")
        rows = await asyncio.to_thread(self._query_rows_blocking, query)

        if not rows:
            logger.warning("No articles retrieved")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df.columns = [c.replace("_", " ").title() for c in df.columns]

        output_dir = Path(self.output_file).parent
        await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)

        df = await self._merge_existing_csv(df)

        await asyncio.to_thread(df.to_csv, self.output_file, index=False)
        logger.info(f"Saved {len(df)} articles -> {self.output_file}")
        return df

    def _query_rows_blocking(self, query: str) -> list[dict]:
        """Run synchronous PubMed query + iteration outside the event loop."""
        articles_raw = _query_with_backoff(self._pubmed, query, self.max_results)
        rows: list[dict] = []

        for idx, article in enumerate(articles_raw, start=1):
            row = _article_to_dict(article)
            if row:
                rows.append(row)
            if self.delay > 0 and idx % 10 == 0:
                time.sleep(self.delay)

        return rows

    async def search_with_llm_async(self, natural_language: str) -> pd.DataFrame:
        """Parse a natural-language request, then scrape."""
        params = await asyncio.to_thread(self.parse_query, natural_language)
        self.pubmed_query = params.pubmed_query
        self.start_date = params.start_date or self.start_date
        self.end_date = params.end_date or self.end_date
        return await self.scrape_async()

    def scrape(self) -> pd.DataFrame:
        return _run_async(self.scrape_async())

    def search_with_llm(self, natural_language: str) -> pd.DataFrame:
        return _run_async(self.search_with_llm_async(natural_language))
