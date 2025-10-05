from collections import defaultdict
from datetime import datetime


class RetrieverReportGenerator:
    """Generates structured reports from retriever results."""

    def __init__(self, report_title: str = "Research Findings Report"):
        self.report_title = report_title

    def _process_retriever_results(self, results):
        grouped_docs = defaultdict(list)

        for i, result in enumerate(results, 1):
            title = result.metadata.get("Title", f"Document: {i}")
            url = result.metadata.get("Url", "No URL Available")
            doc_key = url if url != "No URL Available" else title
            relevance_score = result.metadata.get("relevance_score", "Unknown")

            grouped_docs[doc_key].append(
                {
                    "chunk_id": i,
                    "title": title,
                    "url": url,
                    "authors": result.metadata.get("Authors", ""),
                    "pub_date": result.metadata.get("Publication Date", ""),
                    "references": result.metadata.get("References", ""),
                    "content": result.page_content,
                    "relevance_score": relevance_score,
                }
            )

        return grouped_docs

    def _generate_summary_stats(self, grouped_docs):
        total_docs = len(grouped_docs)
        total_chunks = sum(len(chunks) for chunks in grouped_docs.values())
        multichunk_docs = [
            (doc_key, len(chunks))
            for doc_key, chunks in grouped_docs.items()
            if len(chunks) > 1
        ]

        return {
            "total_docs": total_docs,
            "total_chunks": total_chunks,
            "multichunk_docs": multichunk_docs,
        }

    def _generate_markdown_report(self, grouped_docs):
        markdown = (
            f"# {self.report_title}\n"
            f"*Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n\n"
            f"**Summary:**\n"
            f"- Total unique documents: {len(grouped_docs)}\n"
            f"- Total chunks processed: {sum(len(chunks) for chunks in grouped_docs.values())}\n\n"
            "---\n\n"
        )

        for doc_num, (_, chunks) in enumerate(grouped_docs.items(), 1):
            first_chunk = chunks[0]
            markdown += (
                f"## {doc_num}. {first_chunk['title']}\n"
                f"**Authors:** {first_chunk['authors'] or 'Not Specified'}  \n"
                f"**Publication Date:** {first_chunk['pub_date'] or 'Not specified'}  \n"
                f"**URL:** {first_chunk['url']}  \n"
                f"**References:** {first_chunk['references'] or 'Not available'}  \n"
                f"**Chunks found:** {len(chunks)}\n\n"
                f"### Content:\n\n"
            )

            for chunk in chunks:
                if len(chunks) > 1:
                    markdown += f"**Chunk {chunk['chunk_id']} (Score: {chunk['relevance_score']}):**\n\n"
                else:
                    markdown += f"**Relevance Score:** {chunk['relevance_score']}\n\n"
                markdown += f"{chunk['content']}\n\n"
                if len(chunks) > 1:
                    markdown += "---\n\n"

            markdown += "\n"

        return markdown

    def create_report(self, results):
        grouped_docs = self._process_retriever_results(results)
        stats = self._generate_summary_stats(grouped_docs)
        markdown_report = self._generate_markdown_report(grouped_docs)

        stats_section = (
            "## Report Statistics\n\n"
            f"- **Total Documents:** {stats['total_docs']}\n"
            f"- **Total Chunks:** {stats['total_chunks']}\n\n"
            "### Documents with Multiple Chunks:\n"
        )

        if stats["multichunk_docs"]:
            for doc_key, chunk_count in stats["multichunk_docs"]:
                display_key = doc_key[:60] + "..." if len(doc_key) > 60 else doc_key
                stats_section += f"- {display_key}: {chunk_count} chunks\n"
        else:
            stats_section += "- None (all documents had single chunks)\n"

        # Insert stats right after the summary
        markdown_report = markdown_report.replace("---\n", f"{stats_section}\n---\n", 1)

        return {"markdown": markdown_report, "documents": grouped_docs, "stats": stats}
