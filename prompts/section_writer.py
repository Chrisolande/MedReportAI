scratchpad_prompt = """
You have completed Phase 1 (Research & Extraction). Now execute Phase 2 (Synthesis & Writing).

**PHASE 2 DIRECTIVE: WRITE ONLY - NO MORE TOOL CALLS**

Your task is to synthesize your scratchpad notes into the final report section that meets ALL specifications below.

---
## Original Section Specifications

- **Section Name**: {name}
- **Audience Complexity**: {audience_complexity}
- **Estimated Length**: {estimated_length}
- **Success Criteria**: {success_criteria}

---
## Your Research Notes (Scratchpad)

{scratchpad}

---
## Instructions for Final Writing

1. **Review** all scratchpad notes above
2. **Select** the most critical findings that meet the success criteria
3. **Synthesize** into a coherent narrative for {audience_complexity} audience
4. **Adhere strictly** to the {estimated_length} length constraint
5. **Output ONLY** the final markdown section content - no meta-commentary

**CRITICAL RULES:**
- DO NOT call any tools (no WriteToScratchpad, no web_search, no retriever_tool)
- DO NOT say "I need more information" - work with what you have
- DO NOT output anything except the final section markdown
- START your response with the section heading: # {name}
- STOP when you finish the section content

Begin writing the final section now:
"""


section_writer_prompt = """
---
### Primary Directive
Your mission is to execute a two-phase protocol to produce a technical report section.

**Phase 1 (Extraction):** Gather and structure raw data (3-4 searches maximum)
**Phase 2 (Synthesis):** Write the final section using scratchpad notes

**CRITICAL**: You have a MAXIMUM research budget of 3-4 tool calls. Use them strategically.

---

### Phase 1: Extraction Protocol (CURRENT PHASE)

**Tool Usage Rules (NON-NEGOTIABLE):**
1. Every `retriever_tool` call MUST be immediately followed by `WriteToScratchpad`
2. Every `web_search` call MUST be immediately followed by `WriteToScratchpad`
3. After 3 research queries, you MUST transition to Phase 2
4. Never call research tools without writing findings to scratchpad

**Research Execution Flow:**
```
SEARCH 1 → retriever_tool("query 1") → WriteToScratchpad(notes="[structured notes]", mode="append")
SEARCH 2 → retriever_tool("query 2") → WriteToScratchpad(notes="[structured notes]", mode="append")
SEARCH 3 → web_search("query 3") → WriteToScratchpad(notes="[structured notes]", mode="append")
REVIEW → ReadFromScratchpad() → Assess if sufficient
DECISION → Either: (a) One final search if critical gap, then STOP, OR (b) Signal Phase 2 ready
```

**Note-Taking Format (for WriteToScratchpad):**
For **every** source, create a structured entry:
```
**CITATION**: Author et al. (Year) - Title
**CONTEXT**:
- Sample: [size, demographics]
- Setting: [location, conditions]
- Period: [timeframe]
**DATA**:
- [Exact statistic 1]: **[value]**
- [Direct quote]: "[quote]"
- [Exact statistic 2]: **[value]**
**URL**: [full URL]

---
```

**Example Scratchpad Entry:**
```
**CITATION**: Veronese et al. (2018) - Quality of life in Palestinian children
**CONTEXT**:
- Sample: 1,276 children, ages 10-17
- Setting: Nablus & Tulkarem refugee camps
- Period: Post-2012 Gaza War
**DATA**:
- PTSD prevalence: **32.8%**
- "Resilience was a significant mediator between trauma exposure and quality of life"
- QoL mean: **38.4 (SD = 7.1)**
**URL**: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5852959/

---
```

**Critical Prohibitions:**
- Do not write prose or analysis in Phase 1
- Do not skip WriteToScratchpad after searches
- Do not exceed 4 research tool calls
- Do not merge or paraphrase sources

**Termination Signal:**
After completing your research (3-4 searches with scratchpad entries), respond with:
"Phase 1 extraction complete. Scratchpad contains [X] sources. Ready for Phase 2 synthesis."

---

### Phase 2: Synthesis & Writing (TRIGGERED SEPARATELY)
This phase begins only after Phase 1 completion or after 4 tool calls.
- Review scratchpad contents
- Write the section using ONLY extracted data
- Match section specifications exactly

**Final Output Requirements:**
- Title with Markdown `##`
- Begin with bold declarative sentence
- End with `### Sources` section
- Match `{estimated_length}` and `{audience_complexity}`

---

**YOU ARE CURRENTLY IN PHASE 1. Begin extraction now.**
"""

initial_research_prompt = """
You are now beginning Phase 1 (Extraction).

**YOUR RESEARCH BUDGET: MAXIMUM 3-4 SEARCHES**

Your mission is to build a detailed, evidence-based scratchpad for the following report section using this exact protocol:

---
### Section Specification
- **Section Name:** {name}
- **Description:** {description}
- **Audience Complexity:** {audience_complexity}
- **Estimated Length:** {estimated_length}
- **Dependencies:** {dependencies}
- **Success Criteria:** {success_criteria}

---
### EXACT WORKFLOW (FOLLOW PRECISELY):

**Round 1:**
1. Identify the 2-3 MOST CRITICAL research queries for this section
2. Call `retriever_tool` OR `web_search` with your first query
3. **IMMEDIATELY call `WriteToScratchpad`** with structured notes from that search using this format:
```
**CITATION**: [Author/Source (Year) - Title]
**CONTEXT**: [Sample/Setting/Period]
**DATA**: [Exact statistics, quotes]
**URL**: [Full URL]
```

**Round 2:**
4. Call your second research tool
5. **IMMEDIATELY call `WriteToScratchpad`** (mode: "append") with findings

**Round 3 (if needed):**
6. ONE more search for critical gaps only
7. **IMMEDIATELY call `WriteToScratchpad`** (mode: "append")

**Phase Transition:**
8. After 2-3 searches, call `ReadFromScratchpad` to review your notes
9. If you have sufficient evidence, **STOP calling tools** and respond with: "Phase 1 complete. Ready for synthesis."
10. If critical gaps remain, do ONE final search, then STOP

---
**CRITICAL RULES:**
- You MUST call `WriteToScratchpad` after EVERY `retriever_tool` or `web_search` call
- Maximum 3-4 research queries total
- After 3 queries, you MUST stop researching and prepare for writing
- Your scratchpad is your only Phase 2 input - make it comprehensive

Begin research now. Execute search → WriteToScratchpad → search → WriteToScratchpad.
"""


def get_initial_prompt(section):
    return initial_research_prompt.format(
        name=section.name,
        description=section.description,
        content=section.content,
        audience_complexity=section.audience_complexity,
        estimated_length=section.estimated_length,
        dependencies=section.dependencies,
        success_criteria=section.success_criteria,
    )


def get_synthesis_prompt(section, research_context):
    return scratchpad_prompt.format(
        name=section.name,
        audience_complexity=section.audience_complexity,
        estimated_length=section.estimated_length,
        success_criteria=section.success_criteria,
        scratchpad=research_context,
    )
