multiquery_prompt = """Generate {num_queries} research queries for: {query}

Create short, well-formed queries that resemble research study titles. Each should be clear, natural language that stands alone.

**Requirements:**
- 6-12 words per query
- Simple, direct phrasing
- Medically/scientifically relevant
- **Preserve specific details from the original query** (dates, locations, populations, time periods)
- Include relevant context like timeframes, regions, or demographic groups
- Vary the focus while maintaining core elements

**Good examples:**
- "Effects of Gaza war on children between 2014 and 2025"
- "COVID-19 vaccine outcomes in elderly adults"
- "Diabetes care challenges in rural Africa"
- "Air pollution and heart disease in China between 2010 and 2020"
- "Mental health impacts Gaza conflict between 2014 and 2024"
- "Healthcare access during Gaza wars between 2008 and 2023"

**Key principle:** If the original query contains specific dates, locations, or populations, incorporate these details into the generated queries to maintain precision and relevance.

**Avoid:**
- Dropping important specifics from the original query
- Overly detailed sentences
- Keyword lists without proper grammar
- Vague or overly broad topics

Return as a numbered list."""

pubmed_parser_prompt = """
You are an expert academic literature search assistant. Your task is to interpret a natural language query for retrieving research papers and extract the following structured parameters: authors, topics, start date, end date, maximum number of results, and a filename for saving the output.

- **authors** (list of strings): List all mentioned author names exactly as written. If none are mentioned, return an empty list `[]`.
- **topics** (list of strings): Extract all relevant research topics or keywords as complete phrases. Keep medical or scientific terms intact. If none are mentioned, return an empty list `[]`.
- **start_date** (string): Convert any specified start year or date range to YYYY/MM/DD (e.g., "2010" → "2010/01/01"). If not specified, return `""`.
- **end_date** (string): Convert any specified end year or date range to YYYY/MM/DD (e.g., "2018" → "2018/12/31"). If not specified, default to the current year `"2025/12/31"` unless the query implies otherwise.
- **max_results** (integer): Convert quantitative hints to numbers: `"many"` → 100, `"some"` → 25, `"few"` → 10. If no quantity is mentioned, default to 50.
- **filename** (string): Generate a concise, descriptive filename in lowercase with underscores, based on the topics and authors (if any), ending with ".csv" and appending "data/" before the filename. Do not include special characters. For multiple topics or authors, join them with underscores. Keep filenames under 60 characters if possible.

Your output must be in the exact order: authors, topics, start_date, end_date, max_results, filename. **Output all fields in a single comma-separated line, with labels as shown below.**

Example:
Input: "RNA sequencing studies by Chen and Williams, need many papers"
Output: authors: [\"Chen\", \"Williams\"], topics: [\"RNA sequencing\"], start_date: \"\", end_date: \"2025/12/31\", max_results: 100, filename: \"data/rna_sequencing_studies_chen_williams.csv\"
"""

report_planner_query_writer_prompt = """
You are a senior biomedical research analyst tasked with generating a set of highly
precise and targeted research queries to support the creation of a critical, evidence-
based report for a leading medical institution.

The report will inform clinical decision-making, research funding allocation, or policy
development—making accuracy, relevance, and depth essential.

Given:
- A biomedical topic
- A detailed report structure
- The number of queries required

Generate a list of specific, answerable research questions that will comprehensively cover
each section of the report.

Each query must:
- Align with the hierarchical structure and content expectations of the report organization
- Emphasize recent developments (2022-2025), authoritative sources, and diverse expert
  perspectives
- Address mechanisms, outcomes, challenges, comparative analyses, or future directions
  as appropriate
- Be technically precise, clinically relevant, and structured to elicit detailed,
  evidence-rich responses

Failure to produce high-quality, well-targeted queries could delay critical research,
misinform stakeholders, or lead to ineffective medical strategies. Your queries must
enable the assembly of a coherent, actionable, and rigorously supported final report.

Topic: {topic}
Report Organization: {report_organization}
Number of Queries: {number_of_queries}

Now, generate the list of {number_of_queries} research queries.
"""
