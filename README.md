<div align="center">

# &#x1F9EC; MedReportAI

**AI-powered biomedical research report generator**

*Parallel LangGraph agents that plan → retrieve → synthesise → compile evidence-based medical reports from PubMed and the web.*

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-pipeline-1C3C3C?logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![DSPy](https://img.shields.io/badge/DSPy-prompts-FF6F00)](https://dspy-docs.vercel.app/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-LLM-4A90D9)](https://www.deepseek.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<!-- SCREENSHOT: Add a hero screenshot of the Streamlit UI here -->
<!-- ![MedReportAI Screenshot](docs/images/screenshot.png) -->

</div>

---

## &#x2728; Features

| Feature | Description |
|---|---|
| &#x1F52C; **Automated Report Planning** | DSPy-driven planner generates structured section outlines from a single research query |
| &#x1F4E1; **Triple-Source Retrieval** | Live PubMed search via BioPython Entrez, local PubMed FAISS index, and Tavily web search |
| &#x1F9E0; **Parallel Agent Architecture** | LangGraph orchestrates multiple section-writing agents concurrently with tool access |
| &#x1F4DD; **Scratchpad Protocol** | Agents follow a disciplined extract → note → synthesise workflow for traceable research |
| &#x1F504; **Hybrid Retrieval (BM25 + Dense)** | Ensemble retriever with cross-encoder reranking for high-precision document retrieval |
| &#x1F50E; **Live PubMed Search** | On-demand querying of PubMed with automatic CSV persistence and active-source switching |
| &#x1F4CA; **Real-Time Pipeline UI** | Streamlit dashboard with live phase tracking: Planning → Research → Synthesis → Assembly |
| &#x1F4E5; **Multi-Format Export** | Download final reports as Markdown, PDF, or plain text |
| &#x1F5C2; **Report History** | Browse and revisit previously generated reports from the sidebar archive |

---

## &#x1F3D7; Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit UI                          │
│  ┌─────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Sidebar  │  │ Query Input  │  │ Pipeline Tracker  │  │
│  └─────────┘  └──────┬───────┘  └───────────────────┘  │
└──────────────────────┼──────────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────────┐
│                  LangGraph Pipeline                       │
│                                                          │
│  ┌──────────────┐    ┌─────────────────────────────┐     │
│  │ Plan Report  │───▶│ Build Sections (parallel)   │     │
│  │  (DSPy)      │    │  ┌─────────┐  ┌─────────┐  │     │
│  └──────────────┘    │  │ Agent 1 │  │ Agent N │  │     │
│                      │  │ write → │  │ write → │  │     │
│                      │  │ tools → │  │ tools → │  │     │
│                      │  │ scratch │  │ scratch │  │     │
│                      │  └─────────┘  └─────────┘  │     │
│                      └────────────┬────────────────┘     ��
│                                   ▼                      │
│  ┌──────────────┐    ┌─────────────────────────────┐     │
│  │ Compile      │◀───│ Write Final Sections        │     │
│  │ Final Report │    │ (intro, conclusion)          │     │
│  └──────────────┘    └─────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼               ▼               ▼
┌────────────┐  ┌────────────┐  ┌────────────┐
│ PubMed RAG │  │ Live       │  │ Tavily     │
│ (FAISS +   │  │ PubMed     │  │ Web        │
│  BM25)     │  │ Search     │  │ Search     │
└────────────┘  └────────────┘  └────────────┘
       │               │               │
       └───────────────┼───────────────┘
                       ▼
                ┌────────────┐
                │ Scratchpad │
                │ Memory     │
                └────────────┘
```

---

## &#x1F4C1; Project Structure

```
MedReportAI/
├── app.py                  # LangGraph pipeline definition & entry point
├── streamlit_app.py        # Streamlit web application
├── config.py               # Model, retriever, and path configuration
├── langgraph.json          # LangGraph deployment config
├── pyproject.toml          # Project metadata & dependencies
├── report_history.json     # Persisted report archive
│
├── .streamlit/
│   └── config.toml         # Streamlit theme (dark + green accents)
│
├── agents/                 # High-level agent logic
│   └── planner.py          # Report plan generation & final section writing (DSPy)
│
├── core/                   # Pipeline internals
│   ├── nodes.py            # Graph node functions (compile, gather, initiate)
│   ├── schemas.py          # Pydantic schemas (scratchpad operations, state models)
│   ├── signatures.py       # DSPy signatures (ReportPlanner, SectionWriter, etc.)
│   ├── states.py           # LangGraph state definitions with reducer annotations
│   └── tool_node.py        # Tool execution node with routing logic
│
├── rag/                    # Retrieval-Augmented Generation
│   ├── chain.py            # RAG chain construction
│   ├── embeddings.py       # FastEmbed wrapper for LangChain
│   ├── retrieval_builder.py # Ensemble retriever + cross-encoder reranker
│   ├── retrieval_formatter.py # Structured report from retriever results
│   └── source_formatter.py # Web search result formatting & deduplication
│
├── tools/                  # LangChain tools available to agents
│   ├── pubmed_search.py    # Live PubMed search with CSV persistence & active-source switching
│   ├── retrieval.py        # PubMed FAISS retriever tool
│   ├── web_search.py       # Tavily web search tool
│   ├── scratchpad.py       # Read/write/clear scratchpad operations
│   └── query_generator.py  # DSPy multi-query generator
│
├── prompts/                # Prompt engineering
│   ├── planner.py          # Context persona & report structure prompts
│   ├── section_writer.py   # Two-phase section writing protocol
│   └── scraper.py          # PubMed query parsing prompt
│
├── scripts/                # Standalone utilities
│   └── pubmed_scraper.py   # PubMed article scraper (BioPython Entrez + DeepSeek)
│
├── ui/                     # Streamlit UI components
│   ├── exports.py          # PDF/Markdown/text export functionality
│   ├── history.py          # Report archive (JSON persistence)
│   ├── pipeline.py         # Async streaming runner + phase tracker
│   ├── sidebar.py          # Config panel & report archive browser
│   └── styles.py           # Custom CSS (dark theme with green accents)
│
├── utils/                  # Shared utilities
│   ├── data_processing.py  # CSV loading, semantic chunking, FAISS indexing
│   ├── formatting.py       # Rich console formatters
│   └── helpers.py          # Environment setup, logging, file helpers
│
├── outputs/                # Generated scratchpads & FAISS indexes
│   └── scratchpads/        # Per-section scratchpad markdown files
│
└── downloaded_docs/        # Downloaded research PDF documents
```

---

## &#x1F680; Getting Started

### Prerequisites

- **Python 3.12+**
- A [DeepSeek API key](https://platform.deepseek.com/)
- A [Tavily API key](https://tavily.com/) (for web search)
- *(Optional)* An email for [NCBI Entrez](https://www.ncbi.nlm.nih.gov/account/) (for live PubMed search)

### Installation

```bash
# Clone the repository
git clone https://github.com/Chrisolande/MedReportAI.git
cd MedReportAI

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Install dev dependencies (optional)
pip install -e ".[dev]"
```

### Environment Variables

Create a `.env` file in the project root:

```env
DEEPSEEK_API_KEY=your_deepseek_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
ENTREZ_EMAIL=your_email@example.com  # Optional: for live PubMed search
```

### Prepare Data

You can either use the **live PubMed search tool** (which fetches articles on-demand during pipeline runs) or pre-populate your data using the built-in scraper:

```python
from scripts.pubmed_scraper import PubMedScraper

scraper = PubMedScraper(
    email="your_email@example.com",
    topics=["pediatric health outcomes in conflict settings"],
)
df = await scraper.scrape_async()
```

This fetches articles from PubMed and saves them to `data/pubmed_results.csv`. The retrieval system will automatically build and cache a FAISS vector index from the CSV data on first run.

---

## &#x1F5A5; Usage

### Streamlit Web App

```bash
streamlit run streamlit_app.py
```

<!-- SCREENSHOT: Add a screenshot of the running Streamlit app here -->

1. Enter a research query (e.g., *"Long-term pediatric health outcomes in conflict settings"*)
2. Optionally customize the **Context/Persona** and **Report Structure** in the sidebar
3. Click **▶ Run Pipeline** and watch real-time progress through each phase
4. Export the final report as **Markdown**, **PDF**, or **Text**
5. Browse past reports from the **Report Archive** in the sidebar

### LangGraph API

The pipeline is also exposed as a LangGraph-compatible graph:

```python
from app import graph

result = await graph.ainvoke(
    {"topic": "Impact of malnutrition on child neurodevelopment"},
    config={
        "configurable": {
            "context": "You are a pediatric nutrition researcher...",
            "report_organization": "Structure the report with..."
        }
    }
)

print(result["final_report"])
```

---

## &#x2699; Configuration

All settings are centralized in `config.py` using dataclass-based configs:

### Model Configuration

| Setting | Default | Description |
|---|---|---|
| `deepseek_model` | `deepseek-chat` | LLM model (`deepseek-chat` or `deepseek-reasoner`) |
| `deepseek_temperature` | `1.3` | Generation temperature |
| `max_tokens` | `512` | Maximum tokens per LLM call |
| `embedding_model` | `sentence-transformers/all-MiniLM-L6-v2` | Sentence embedding model (FastEmbed) |

### Retriever Configuration

| Setting | Default | Description |
|---|---|---|
| `k` | `15` | Number of documents to retrieve |
| `sparse_weight` | `0.65` | BM25 weight in ensemble retriever |
| `dense_weight` | `0.35` | Dense retrieval weight in ensemble |
| `similarity_threshold` | `0.6` | Minimum similarity for document inclusion |
| `redundancy_threshold` | `0.95` | Maximum similarity before deduplication |
| `top_n` | `5` | Documents retained after reranking |
| `reranker_model` | `Xenova/ms-marco-miniLM-L-6-v2` | Cross-encoder reranker model |

### Report Configuration

The pipeline's persona and report structure are fully customizable at runtime via the Streamlit sidebar or programmatically through `RunnableConfig`:

```python
config = {
    "configurable": {
        "context": "Your custom persona prompt...",
        "report_organization": "Your custom report structure..."
    }
}
```

---

## &#x1F6E0; Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | [LangGraph](https://github.com/langchain-ai/langgraph)  -  stateful multi-agent pipeline with parallel branches |
| **Prompt Framework** | [DSPy](https://dspy-docs.vercel.app/)  -  structured signatures for planning, writing & query generation |
| **LLM** | [DeepSeek](https://www.deepseek.com/)  -  `deepseek-chat` / `deepseek-reasoner` |
| **Retrieval** | FAISS + BM25 ensemble with FastEmbed cross-encoder reranking |
| **Live Search** | [BioPython Entrez](https://biopython.org/)  -  real-time PubMed querying with CSV persistence |
| **Web Search** | [Tavily](https://tavily.com/)  -  real-time web search with raw content extraction |
| **Frontend** | [Streamlit](https://streamlit.io/)  -  custom dark theme with live pipeline tracking |
| **PDF Export** | WeasyPrint  -  styled PDF generation from Markdown |
| **Logging** | [Loguru](https://github.com/Delgan/loguru)  -  structured logging with file rotation |
| **Tracing** | [LangSmith](https://smith.langchain.com/)  -  optional observability for tool calls |

---

## &#x1F9EA; Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linters & formatters
ruff check .
black .
isort .
mypy .

# Pre-commit hooks (configured in .pre-commit-config.yaml)
pre-commit install
pre-commit run --all-files
```

The project uses a comprehensive pre-commit configuration including:

- **Black** (line length 88, Python 3.12 target)
- **isort** (Black-compatible profile)
- **autoflake** (remove unused imports/variables)
- **Ruff** (fast Python linter)
- **mypy** (static type checking)
- **nbqa** (notebook linting)

---

## &#x1F4C4; License

This project is licensed under the [MIT License](LICENSE).

---

## &#x1F91D; Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

<div align="center">

**Built with &#x1F9EC; by [@Chrisolande](https://github.com/Chrisolande)**

</div>
