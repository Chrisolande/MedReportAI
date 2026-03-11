import asyncio
import os
from dataclasses import dataclass
from typing import Any, Literal

import pandas as pd
from Bio import Entrez
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_deepseek import ChatDeepSeek
from loguru import logger
from pydantic import BaseModel, Field

from prompts.scraper import pubmed_parser_prompt

_ = load_dotenv()


class ArticleQuery(BaseModel):
    authors: list[str] = Field(default_factory=list)
    topics: list[str] = Field(description="Research topics/keywords")
    start_date: str = Field(default="", description="YYYY/MM/DD format")
    end_date: str = Field(default="", description="YYYY/MM/DD format")
    max_results: int = Field(default=10)
    filename: str = Field(default="pubmed_results.csv", description="Output file name")


@dataclass
class PubMedScraper:
    email: str
    authors: list[str] | None = None
    topics: list[str] | None = None
    start_date: str = "2012/01/01"
    end_date: str = "2025/08/27"
    max_results: int = 10
    delay: float = 0.34
    output_file: str = "data/pubmed_results.csv"
    model: Literal["deepseek-chat", "deepseek-reasoner"] = "deepseek-chat"
    temperature: float = 1.3

    def __post_init__(self):
        Entrez.email = self.email
        self.llm = ChatDeepSeek(
            model=self.model,
            temperature=self.temperature,
            max_tokens=500,  # type: ignore
        )
        self.authors = self.authors or []
        self.topics = self.topics or []

    def parse_query(self, query: str) -> dict:
        """Parse natural language query into search parameters."""
        structured_llm = self.llm.with_structured_output(ArticleQuery)
        result = structured_llm.invoke(
            [SystemMessage(content=pubmed_parser_prompt), HumanMessage(content=query)]
        )
        parsed = result.model_dump()  # type: ignore
        logger.info(f"Parsed query: {parsed}")
        return parsed

    def build_query(self) -> str:
        """Build PubMed search query."""
        queries = []
        date_range = (
            f'("{self.start_date}"[Date - Create] : "{self.end_date}"[Date - Create])'
        )

        if self.authors:
            author_q = (
                "(" + " OR ".join(f"{author}[Author]" for author in self.authors) + ")"
            )
            queries.append(author_q)

        if self.topics:
            topic_q = (
                "("
                + " OR ".join(f"{topic}[Title/Abstract]" for topic in self.topics)
                + ")"
            )
            queries.append(topic_q)

        return " AND ".join(queries + [date_range]) if queries else date_range

    def search_pubmed(self) -> list[str]:
        """Search PubMed and return PMIDs."""
        query = self.build_query()
        try:
            logger.info(f"Searching: {query}")
            with Entrez.esearch(
                db="pubmed", retmax=self.max_results, term=query
            ) as handle:
                record = Entrez.read(handle)
            logger.info(f"Found {len(record['IdList'])} articles")  # type: ignore
            return record["IdList"]  # type: ignore
        except Exception as e:
            logger.warning(f"Search error: {e}")
            return []

    def extract_article_data(self, record: dict) -> Any:
        """Extract article information from PubMed record."""
        try:
            medline = record["MedlineCitation"]
            article = medline["Article"]
            pmid = str(medline["PMID"])

            # Basic info
            title = str(article.get("ArticleTitle", ""))
            journal = str(article.get("Journal", {}).get("Title", ""))

            # Abstract
            abstract = ""
            if "Abstract" in article and "AbstractText" in article["Abstract"]:
                abstract_parts = article["Abstract"]["AbstractText"]
                abstract = (
                    " ".join(str(part) for part in abstract_parts)
                    if isinstance(abstract_parts, list)
                    else str(abstract_parts)
                )

            # Authors and affiliations
            authors, affiliations = [], []
            for author in article.get("AuthorList", []):
                last_name = author.get("LastName", "")
                fore_name = author.get("ForeName", "")
                if last_name:
                    authors.append(f"{last_name} {fore_name}".strip())

                for affil_info in author.get("AffiliationInfo", []):
                    if "Affiliation" in affil_info:
                        affiliations.append(affil_info["Affiliation"])

            # Keywords (MeSH terms)
            keywords = [
                str(mesh["DescriptorName"])
                for mesh in medline.get("MeshHeadingList", [])
                if "DescriptorName" in mesh
            ]

            # Publication date
            pub_date = (
                article.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
            )
            date_parts = [
                str(pub_date.get(part, ""))
                for part in ["Year", "Month", "Day"]
                if pub_date.get(part)
            ]
            publication_date = "-".join(date_parts)

            # References (first 5) with PMID links
            references = []
            try:
                ref_list = record.get("PubmedData", {}).get("ReferenceList", [])
                for ref_group in ref_list:
                    for ref in ref_group.get("Reference", []):
                        citation = ref.get("Citation", "").strip()
                        if citation:
                            # Extract PMID from ArticleIdList
                            pmid_found = None
                            for article_id in ref.get("ArticleIdList", []):
                                # Check if it's a dictionary with IdType
                                if (
                                    isinstance(article_id, dict)
                                    and article_id.get("IdType") == "pubmed"
                                ):
                                    pmid_found = str(article_id.get("content", ""))
                                # Check if it's an object with attributes
                                elif (
                                    hasattr(article_id, "attributes")
                                    and article_id.attributes.get("IdType") == "pubmed"  # type: ignore
                                ):
                                    pmid_found = str(article_id)
                                # Direct string check (fallback)
                                elif str(article_id).isdigit():
                                    pmid_found = str(article_id)

                                if pmid_found:
                                    break

                            # Append PMID link if found
                            if pmid_found:
                                citation += (
                                    f" https://pubmed.ncbi.nlm.nih.gov/{pmid_found}"
                                )

                            references.append(citation)
                        if len(references) >= 5:
                            break
                    if len(references) >= 5:
                        break
            except Exception:
                pass

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract,
                "authors": ", ".join(authors),
                "journal": journal,
                "keywords": ", ".join(keywords),
                "url": f"https://www.ncbi.nlm.nih.gov/pubmed/{pmid}",
                "affiliations": "; ".join(dict.fromkeys(affiliations)),
                "publication_date": publication_date,
                "references": " | ".join(references),
            }
        except Exception as e:
            logger.warning(f"Extraction error: {e}")
            return None  # type: ignore

    def fetch_details(self, pmids: list[str]) -> list[dict]:
        """Synchronous wrapper around async detail fetching.

        Use ``fetch_details_async`` when called inside an async runtime.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.fetch_details_async(pmids))

        raise RuntimeError(
            "fetch_details() was called while an event loop is running. "
            "Use await fetch_details_async(...) in async contexts."
        )

    async def fetch_details_async(self, pmids: list[str]) -> list[dict]:
        """Fetch detailed article information."""
        articles = []
        batch_size = 10

        for i in range(0, len(pmids), batch_size):
            batch = pmids[i : i + batch_size]
            try:
                logger.info(
                    f"Fetching batch {i // batch_size + 1}/{(len(pmids) + batch_size - 1) // batch_size}"
                )
                records = await asyncio.to_thread(self._fetch_batch_records, batch)

                for record in records["PubmedArticle"]:  # type: ignore
                    article_data = self.extract_article_data(record)
                    if article_data:
                        articles.append(article_data)

                if i + batch_size < len(pmids) and self.delay > 0:
                    await asyncio.sleep(self.delay)

            except Exception as e:
                logger.warning(f"Batch {i // batch_size + 1} fetch error: {e}")
                continue

        return articles

    @staticmethod
    def _fetch_batch_records(batch: list[str]) -> Any:
        with Entrez.efetch(db="pubmed", id=",".join(batch), retmode="xml") as handle:
            return Entrez.read(handle)

    def scrape(self) -> pd.DataFrame:
        """Synchronous wrapper around async scraping.

        Use ``scrape_async`` when called inside an async runtime.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.scrape_async())

        raise RuntimeError(
            "scrape() was called while an event loop is running. "
            "Use await scrape_async() in async contexts."
        )

    async def scrape_async(self) -> pd.DataFrame:
        """Main scraping method."""
        pmids = await asyncio.to_thread(self.search_pubmed)
        if not pmids:
            return pd.DataFrame()

        articles = await self.fetch_details_async(pmids)
        if not articles:
            return pd.DataFrame()

        df = pd.DataFrame(articles)
        df.columns = [col.replace("_", " ").title() for col in df.columns]

        try:
            if not os.path.exists("data"):
                os.makedirs("data")
            await asyncio.to_thread(df.to_csv, self.output_file, index=False)
            logger.info(f"Results saved to {self.output_file}")
        except Exception as e:
            logger.warning(f"Save error: {e}")

        return df

    def search_with_llm(self, query: str) -> pd.DataFrame:
        """Synchronous wrapper around async LLM search.

        Use ``search_with_llm_async`` when called inside an async runtime.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.search_with_llm_async(query))

        raise RuntimeError(
            "search_with_llm() was called while an event loop is running. "
            "Use await search_with_llm_async(query) in async contexts."
        )

    async def search_with_llm_async(self, query: str) -> pd.DataFrame:
        """Search using natural language query."""
        try:
            params = await asyncio.to_thread(self.parse_query, query)

            # Update instance attributes
            self.authors = params.get("authors", [])
            self.topics = params.get("topics", [])
            self.start_date = params.get("start_date") or self.start_date
            self.end_date = params.get("end_date") or self.end_date
            self.max_results = params.get("max_results", self.max_results)
            self.output_file = params.get("filename") or self.output_file

            logger.info(f"Searching with: authors={self.authors}, topics={self.topics}")
            return await self.scrape_async()

        except Exception as e:
            logger.warning(f"LLM search error: {e}")
            return pd.DataFrame()
