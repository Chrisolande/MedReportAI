from dspy import InputField, OutputField, Signature

from core.schemas import Sections
from utils.dspy_bootstrap import ensure_dspy_cache_dir

ensure_dspy_cache_dir()


class MultiQueryGenerator(Signature):
    """Generate multiple natural language queries exploring different aspects of a
    topic.

    - Write complete, natural questions or statements, not keyword lists
    - Each query must focus on a distinct angle (history, impact, mechanisms, policy, etc.)
    - Ensure semantic diversity while staying on topic

    Example:
        Input: "Impact of Gaza war on children"
        Output:
            - "How has the Gaza war affected children's mental health and education?"
            - "What are the statistics on child casualties in the Gaza conflict?"
            - "Medical care challenges for pediatric patients during Gaza conflict"
    """

    question: str = InputField(
        desc="Original query to rephrase into different perspectives"
    )
    num_queries: int = InputField(desc="Number of distinct queries to generate")
    search_queries: list[str] = OutputField(
        desc="Natural queries each exploring a different aspect of the topic"
    )


class ReportPlanner(Signature):
    """Plan a structured medical literature review broken into logical sections.

    A good section has a single, clear research question with defined boundaries.
    Sections must not overlap - if two candidate sections would cite the same sources,
    merge them. Prefer fewer, deeper sections over many shallow ones. Each section's
    search queries should be specific enough to return targeted results in 10-25
    articles.
    """

    topic: str = InputField(desc="Central medical or public health topic")
    context: str = InputField(
        desc="Target population, clinical aspects, intended audience, data quality "
        "constraints, and scope"
    )
    report_organization: str = InputField(
        desc="Section breakdown, research intensity, content requirements, and research standards"
    )
    plan: Sections = OutputField(
        desc="Research plan with 4-6 body sections. Each section must have: title, research "
        "objective, 2-3 specific search queries, required source types, and analytical approach. "
        "Sections must have non-overlapping scope."
    )


class FinalInstructions(Signature):
    """Write introduction or conclusion sections for a research report.

    INTRODUCTION RULES
    - Heading: ## {section_title}
    - Length: 50-100 words, prose only, no lists, tables, or bullets
    - Content: hook (core problem or gap) → stakes (why it matters now) → scope signal
    - Do not preview findings or summarize sections
    - First sentence must earn attention; avoid "This report examines..."

    CONCLUSION RULES
    - Heading: ## {section_title}
    - Length: 100-150 words
    - Synthesize cross-cutting insights, do not restate section headings
    - ONE optional structural element if it genuinely clarifies:
        * Comparison table (2-4 cols, 3-5 rows): only for comparative reports
        * Priority list (3-5 items): only when recommendations have clear rank order
        * Insights table (2-3 rows): only when themes cluster meaningfully
    - End with clear directionality: next steps, decision criteria, or future outlook

    EVIDENCE GRADING IN BOTH SECTIONS
    - Reference specific data and findings from the report, no generic claims
    - Do not introduce new claims not evidenced in the provided context

    DO NOT:
    - Exceed word limits
    - Use structural elements in introductions
    - Use more than one structural element in conclusions
    - Begin with "This section will..." or "In conclusion..."
    - Include word counts or meta-commentary in output
    - Use vague language: "various factors", "multiple approaches", "recent studies"
    """

    section_title: str = InputField(
        desc="Exact title for this section (used in Markdown heading)"
    )
    section_topic: str = InputField(
        desc="Section type ('Introduction' or 'Conclusion') and brief topic context. "
        "For conclusions, note whether the report is comparative."
    )
    context: str = InputField(
        desc="Complete report content - all sections, findings, data, examples. "
        "Sole source material for synthesis."
    )
    section_content: str = OutputField(
        desc="Publication-ready section starting with Markdown heading. "
        "No preamble, no word counts, no process notes."
    )
