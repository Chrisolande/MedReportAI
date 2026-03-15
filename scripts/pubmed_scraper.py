"""PubMed scraper - refactored with pymed + pydantic-settings."""

import os

# Allow imports from project root regardless of script location
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import os
from typing import Any, Literal

import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from loguru import logger
from pydantic import BaseModel, Field
from pymed import PubMed

from prompts.scraper import pubmed_parser_prompt

# Settings


_ = load_dotenv()


# Structured LLM output schema


class ArticleQuery(BaseModel):
    pubmed_query: str = Field(
        description=(
            "A ready-to-use PubMed query string with proper field tags "
            "(e.g. '[Title/Abstract]', '[Author]', date filters via mindate/maxdate)."
        )
    )
    start_date: str = Field(default="", description="YYYY/MM/DD")
    end_date: str = Field(default="", description="YYYY/MM/DD")
    max_results: int = Field(default=25)
    filename: str = Field(default="pubmed_results.csv")


# Helpers


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
        return {
            "affiliations": "",
            "references": "",
        }


def _article_to_dict(article: Any) -> dict | None:
    """Convert a pymed PubMedArticle to a flat dict."""
    try:
        authors = [
            f"{a.get('lastname', '')} {a.get('firstname', '')}".strip()
            for a in (article.authors or [])
        ]
        keywords = [str(k) for k in (article.keywords or []) if k]
        pub_date = str(article.publication_date) if article.publication_date else ""
        pmid = str(article.pubmed_id or "").split("\n")[0].strip()

        row = {
            "pmid": pmid,
            "title": article.title or "",
            "abstract": article.abstract or "",
            "authors": ", ".join(authors),
            "journal": article.journal or "",
            "keywords": ", ".join(keywords),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}" if pmid else "",
            "publication_date": pub_date,
        }
        row.update(_extract_extras(article))
        return row
    except Exception as exc:
        logger.warning(f"Article parse error: {exc}")
        return None


def _run_async(coro):
    """Run a coroutine safely regardless of whether a loop is already running."""
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


# Scraper


class PubMedScraper:
    def __init__(
        self,
        *,
        email: str | None,
        pubmed_query: str = "",
        start_date: str = "2012/01/01",
        end_date: str = "2025/08/27",
        max_results: int = 25,
        delay: float = 0.34,
        output_file: str = "data/pubmed_results.csv",
        model: Literal["deepseek-chat", "deepseek-reasoner"] = "deepseek-chat",
        temperature: float = 1.3,
    ):
        self.pubmed_query = pubmed_query
        self.start_date = start_date
        self.end_date = end_date
        self.max_results = max_results
        self.delay = delay
        self.output_file = output_file

        self._pubmed = PubMed(tool="MedReportAI")
        self._llm = ChatDeepSeek(
            model=model,
            temperature=temperature,
            max_tokens=2048,  # type: ignore
        )

    # LLM query parsing

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

    # Core async pipeline

    async def scrape_async(self) -> pd.DataFrame:
        """Fetch articles matching ``self.pubmed_query`` and return a DataFrame."""
        if not self.pubmed_query:
            logger.warning("No query set – returning empty DataFrame")
            return pd.DataFrame()

        # Append date filter directly into the query string if provided
        query = self.pubmed_query
        if self.start_date or self.end_date:
            start = self.start_date or "1900/01/01"
            end = self.end_date or "3000/12/31"
            query += (
                f' AND ("{start}"[Date - Publication] : "{end}"[Date - Publication])'
            )

        logger.info(f"Querying PubMed: {query!r}  max={self.max_results}")

        articles_raw = await asyncio.to_thread(
            self._pubmed.query, query, max_results=self.max_results
        )

        rows: list[dict] = []
        for article in articles_raw:
            row = _article_to_dict(article)
            if row:
                rows.append(row)
            if self.delay > 0 and len(rows) % 10 == 0 and rows:
                await asyncio.sleep(self.delay)

        if not rows:
            logger.warning("No articles retrieved")
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df.columns = [c.replace("_", " ").title() for c in df.columns]

        os.makedirs(os.path.dirname(self.output_file) or ".", exist_ok=True)
        await asyncio.to_thread(df.to_csv, self.output_file, index=False)
        logger.info(f"Saved {len(df)} articles -> {self.output_file}")
        return df

    async def search_with_llm_async(self, natural_language: str) -> pd.DataFrame:
        """Parse a natural-language request, then scrape."""
        params = await asyncio.to_thread(self.parse_query, natural_language)
        self.pubmed_query = params.pubmed_query
        self.start_date = params.start_date or self.start_date
        self.end_date = params.end_date or self.end_date
        self.max_results = params.max_results
        self.output_file = params.filename or self.output_file
        return await self.scrape_async()

    # Sync convenience wrappers

    def scrape(self) -> pd.DataFrame:
        return _run_async(self.scrape_async())

    def search_with_llm(self, natural_language: str) -> pd.DataFrame:
        return _run_async(self.search_with_llm_async(natural_language))
