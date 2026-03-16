from core.quality import build_source_registry_text

scratchpad_prompt = """
You are in Phase 2 of a two-phase medical report workflow.

Write the final section from the supplied research notes only.

## Section Specifications
- **Section Name**: {name}
- **Audience Complexity**: {audience_complexity}
- **Estimated Length**: {estimated_length}
- **Success Criteria**: {success_criteria}

## Research Notes
{scratchpad}

## Source Registry
Use the numbered sources below for inline citations. Cite as [N] where N is the number assigned to the source.
{source_registry}

## Hard Rules
- No tool calls
- No meta-commentary or completion banners
- Every major claim must carry a numbered citation [N] where N corresponds to the source number provided in the registry above
- Do NOT use inline markdown hyperlinks for citations; use [N] numbered references only
- Surface conflicting numbers or interpretations explicitly instead of averaging them away
- Claims backed only by web search (no full-text RAG) must be hedged appropriately
- If evidence is sparse, narrow, or indirect, say so plainly
- End on a concrete limitation, clinical nuance, or unresolved question
- Output only the finished section markdown starting with: ## {name}
"""


section_writer_prompt = """
You are in Phase 1 of a two-phase medical report workflow.

Collect evidence only. Do not draft the section.
Use the fewest turns possible and avoid redundant searches.

## Section Specification
- **Section Name:** {name}
- **Description:** {description}
- **Audience Complexity:** {audience_complexity}
- **Estimated Length:** {estimated_length}
- **Dependencies:** {dependencies}
- **Success Criteria:** {success_criteria}

## Research Rules
1. Prefer `pubmed_scraper_tool` as the first research tool when it can answer the topic.
2. You may emit multiple tool calls in one assistant turn.
3. Every research tool that yields usable evidence must be followed by `WriteToScratchpad` with `mode="append"` before another research tool.
4. If a tool returns no findings or no usable URL, skip `WriteToScratchpad` for that result and move to the next fallback step.
5. If `pubmed_scraper_tool` fails, retry PubMed once with a broader query. If that also fails, fall back to `web_search` for live evidence and skip `retriever_tool` entirely since no FAISS index will exist.
6. If PubMed succeeds, use `retriever_tool` after it to RAG against the persisted index for deeper per-source extraction.
7. Use `ReadFromScratchpad` only after your final evidence-gathering step if you need a quick coverage check.
8. Once the scratchpad has enough evidence, stop requesting tools. The orchestrator will move to synthesis automatically.
9. Never output a completion banner. Never write the final section in Phase 1.
10. A scratchpad entry with fewer than 3 quantitative data points is incomplete; re-read the source and extract more before moving on.

## Scratchpad Format
For every source with usable evidence:
```
**CITATION**: Author et al. (Year) - Full Title (Journal or source)
**SOURCE TYPE**: [RCT | Cohort | Systematic Review | Meta-analysis | Case Series | Field Report | Policy Brief | Web Search - no full-text indexed]
**CONTEXT**:
- Sample: [size, age range, sex split, condition severity]
- Setting: [country, institution type, conflict zone vs. stable]
- Period: [data collection dates, not just publication year]
- Funding/Conflicts: [note if industry-funded or advocacy-affiliated]
**QUANTITATIVE DATA**:
- [Metric]: [exact value] (95% CI: [x-y], p=[z] if reported)
- [Metric]: [exact value]
- [Metric]: [exact value]
**QUALITATIVE DATA**:
- "[Direct quote]" (section or page if available)
**LIMITATIONS**:
- [e.g. self-report bias, small sample, single-centre, loss to follow-up]
**RELEVANCE**: [1-2 sentences linking this source directly to the section thesis]
**URL**: [full URL]

---
```
"""


def get_initial_prompt(section):
    return section_writer_prompt.format(
        name=section.name,
        description=section.description,
        audience_complexity=section.audience_complexity,
        estimated_length=section.estimated_length,
        dependencies=section.dependencies,
        success_criteria=section.success_criteria,
    )


def get_synthesis_prompt(
    section,
    research_context,
    citation_registry: dict[str, int] | None = None,
    sources: list[dict[str, str]] | None = None,
):
    source_registry = build_source_registry_text(sources or [], citation_registry)

    return scratchpad_prompt.format(
        name=section.name,
        audience_complexity=section.audience_complexity,
        estimated_length=section.estimated_length,
        success_criteria=section.success_criteria,
        scratchpad=research_context,
        source_registry=source_registry,
    )
