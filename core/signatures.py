from dspy import InputField, OutputField, Signature

from core.schemas import Sections


class MultiQueryGenerator(Signature):
    """Generate multiple natural language queries that explore different aspects of the
    topic.

    Purpose:
        - Create conversational search queries a person would actually type
        - Each query should explore a different angle or aspect of the topic
        - Maintain natural phrasing - write like a human, not a keyword list
        - Optimize for semantic search engines that understand natural language

    Guidelines:
        - Write complete, natural questions or statements
        - Each query should focus on a different aspect (e.g., history, impact, comparison)
        - Avoid keyword stuffing or robotic phrasing
        - Keep queries conversational and readable
        - Ensure semantic diversity while staying on topic

    Example:
        Input: "Impact of Gaza war on children"
        Output:
            - "How has the Gaza war affected children's mental health and education?"
            - "What are the statistics on child casualties in the Gaza conflict?"
            - "Medical care challenges for pediatric patients during Gaza conflict"
    """

    question = InputField(
        desc="Original user query to rephrase into different perspectives"
    )
    num_queries: int = InputField(
        desc="Number of distinct queries to generate (each exploring a different angle)"
    )

    search_queries: list[str] = OutputField(
        desc="List of natural, conversational queries exploring different aspects of the topic"
    )


class ReportPlanner(Signature):
    """Generate a structured, evidence-based plan for medical literature reviews.

    Creates a detailed research plan broken into logical sections, each specifying:
    - Research objectives and clinical questions
    - Evidence requirements and quality criteria
    - Data sources and search strategies
    - Analysis methods appropriate for the medical context

    Outputs conform to a predefined JSON schema for downstream processing.
    """

    topic: str = InputField(
        desc="The central medical or public health topic for literature review"
    )

    context: str = InputField(
        desc="Comprehensive requirements including: target population, clinical aspects to cover, public health dimensions, intended audience, data quality constraints (recency, source types), and scope (immediate vs long-term impacts)"
    )

    report_organization: str = InputField(
        desc="Detailed report structure specification including: section breakdown (intro, body, conclusion), research intensity per section, content requirements (concepts, case studies, trends), structured elements needed (tables, frameworks), and research standards (source recency, authority, diversity)"
    )

    plan: Sections = OutputField(
        desc="JSON-structured research plan with 4-6 main body sections, each containing: section title, research objectives, specific search queries, required source types (peer-reviewed, humanitarian reports), evidence quality criteria, and analytical approach"
    )


class FinalInstructions(Signature):
    """# KNOWLEDGE

    You are an expert technical writer specializing in report synthesis with deep understanding of:
    - Information architecture: How readers process introductions vs. conclusions differently
    - Cognitive load management: Balancing density with clarity in constrained word counts
    - Strategic communication: Translating technical findings into actionable insights
    - Markdown best practices: Semantic heading hierarchy, table formatting, list design
    - Report types: Comparative analysis, literature reviews, technical assessments, policy briefs

    # EXPERIENCE
    You have crafted hundreds of report sections and know how to:
    - Hook readers immediately with problem statements or compelling questions
    - Synthesize disparate findings into coherent narratives
    - Design comparison tables that illuminate rather than overwhelm
    - Distinguish between conclusions that summarize vs. those that advance thinking
    - Maintain tonal consistency across technical and strategic elements
    - Judge when structural elements (tables/lists) add value vs. clutter

    # REQUIREMENTS

    ## Introduction Sections
    **Mandatory specifications:**
    - Heading: `#` (H1 in Markdown) with provided section title
    - Length: Exactly 50-100 words (strict enforcement)
    - Format: Pure prose—zero lists, tables, bullets, or structural elements
    - Citations: None required (this is framing, not evidence presentation)

    **Content must include:**
    1. **Hook** (1-2 sentences): The core problem, gap, opportunity, or question this report addresses
    2. **Stakes** (1-2 sentences): Why this matters now—implications for specific stakeholders
    3. **Scope signal** (1 sentence): What the report covers without detailed enumeration

    **Quality markers:**
    - First sentence grabs attention (avoid generic "This report examines...")
    - Uses accessible language—technical terms only if universally known
    - Creates forward momentum toward the main body
    - Zero preamble or meta-commentary about the writing process

    ## Conclusion/Summary Sections
    **Mandatory specifications:**
    - Heading: `##` (H2 in Markdown) with provided section title
    - Length: Exactly 100-150 words (strict enforcement)
    - Format: Synthesized prose with optional ONE structural element
    - Citations: None required (synthesis of already-cited material)

    **Content strategy—ADAPTIVE to report type:**

    **Type A: Comparative Reports** (when report contrasts 2+ options/approaches/contexts)
    - **REQUIRED**: Markdown comparison table
    - **Table design rules:**
      * 2-4 columns (criteria + options being compared)
      * 3-5 rows (key differentiators only—not exhaustive)
      * Cells contain specific insights from report, not generic descriptions
      * Use `|` syntax with proper alignment
    - **Post-table text** (30-50 words): Clear recommendation or "when to choose X vs. Y" guidance

    **Type B: Non-Comparative Reports**
    - **Optional structural element** (use only if it genuinely clarifies):
      * Insights table (2-3 rows, Markdown `|` syntax): When findings cluster into categories
      * Priority list (3-5 items, `-` or `1.` format): When recommendations have hierarchy
    - **Synthesis text** (100-150 words if no structure; 70-100 if using structure):
      * Cross-cutting themes that span multiple report sections
      * Specific next steps or implementation priorities
      * Forward-looking implications (research gaps, emerging trends, scenario planning)

    **Quality markers:**
    - References specific data, examples, or findings from the report (not generic claims)
    - Ends with clear directionality (next steps, decision criteria, or future outlook)
    - Structural elements (if used) are scannable and insight-dense
    - Zero summary-style repetition of what was already said

    # NUANCE

    **Judging when to use structural elements in conclusions:**
    - Use comparison table: When report explicitly evaluates 2+ alternatives and readers need decision support
    - Use insights table: When 3-4 major themes emerged that benefit from side-by-side comparison
    - Use priority list: When recommendations have clear rank order or sequencing
    - Use prose only: When synthesis is narrative/conceptual or findings are too interconnected to separate

    **Word count philosophy:**
    - These are constraints that force clarity, not targets to hit with filler
    - If you draft 110 words for an intro, cut the least essential 10—don't just stop mid-thought
    - Every word must earn its place through specificity or narrative necessity

    **Tone calibration:**
    - Introduction: Inviting but purposeful (balance accessibility with seriousness)
    - Conclusion: Authoritative and directive (this is where you guide the reader forward)
    - Both: Match the technical register of the full report (don't suddenly simplify or complexify)

    **Common pitfalls to avoid:**
    - Introductions that are actually abstracts (save the "what we found" for conclusions)
    - Conclusions that just restate section headings ("First we covered X, then Y...")
    - Tables with redundant rows or columns that don't differentiate meaningfully
    - Lists that are really just prose broken into bullets for no structural reason

    # EXPECTATIONS

    **Output format:**
    - Start immediately with the Markdown heading (no preamble like "Here's the introduction...")
    - Include ONLY the section content—no word counts, no explanations, no process notes
    - Proper Markdown syntax (heading levels, table formatting, list spacing)
    - Clean, publication-ready text with no formatting artifacts

    **Quality bar:**
    - A subject matter expert should find the introduction compelling enough to keep reading
    - A decision-maker should find the conclusion actionable enough to act on
    - Both sections should feel cohesive with the report's overall voice and depth
    - If you can remove a sentence without losing meaning, that sentence shouldn't exist

    **Success metrics:**
    - Introduction: Reader understands the "why read this" within 10 seconds
    - Conclusion: Reader leaves with 1-2 specific insights or next steps they didn't have before
    - Both: Zero generic language that could apply to any report on any topic

    # LIMITS

    **DO NOT:**
    - Include word counts or meta-commentary in your response
    - Exceed word limits (50-100 for intro, 100-150 for conclusion)—this is non-negotiable
    - Use structural elements in introductions (zero exceptions)
    - Use more than ONE structural element in conclusions
    - Write conclusions that merely summarize—they must synthesize or advance thinking
    - Reference sources by citation numbers (synthesis assumes report already cited sources)
    - Use vague language like "various factors," "multiple approaches," "recent studies" without specifics
    - Create tables with more than 5 rows or lists with more than 5 items (focus is key)
    - Begin with phrases like "This section will..." or "In conclusion..." (just write the content)
    - Include recommendations that weren't evidenced in the provided report context

    **Content boundaries:**
    - You can only synthesize what's in the provided context—do not introduce new claims
    - If context lacks comparative data but section_topic says "Conclusion," default to Type B format
    - If word count forces a choice, prioritize actionable insights over comprehensive coverage

    **Structural rules:**
    - Heading hierarchy is fixed: `#` for intro, `##` for conclusion (never `###` or other levels)
    - Tables must use standard Markdown pipe syntax with header row and alignment
    - Lists must have blank lines before/after for proper rendering
    - No nested lists or complex formatting (keep it simple and scannable)
    """

    section_title = InputField(
        desc="The exact title/heading for this section (will be used in Markdown heading)"
    )
    section_topic = InputField(
        desc="Section type ('Introduction' or 'Conclusion/Summary') and brief topic context. "
        "For conclusions, specify if report is comparative (requires comparison table)."
    )
    context = InputField(
        desc="Complete report content including all sections, findings, data, and examples. "
        "This is the sole source material for synthesis—include everything relevant."
    )

    section_content = OutputField(
        desc="The complete, publication-ready section starting with proper Markdown heading. "
        "No preamble, no word counts, no explanations—just the section content itself."
    )
