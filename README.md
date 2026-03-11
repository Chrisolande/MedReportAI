<div align="center">

# 🧬 MedReportAI

**AI-powered biomedical research report generator**

*Parallel LangGraph agents that plan → retrieve → synthesise → compile evidence-based medical reports from PubMed and the web.*

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-pipeline-1C3C3C?logo=langchain&logoColor=white)](https://github.com/langchain-ai/langgraph)
[![DSPy](https://img.shields.io/badge/DSPy-prompts-FF6F00)](https://dspy-docs.vercel.app/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-LLM-4A90D9)](https://www.deepseek.com/)

<!-- SCREENSHOT: Add a hero screenshot of the Streamlit UI here -->
<!-- ![MedReportAI Screenshot](docs/images/screenshot.png) -->

</div>

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔬 **Automated Report Planning** | DSPy-driven planner generates structured section outlines from a single research query |
| 📡 **Dual-Source Retrieval** | Searches both a local PubMed FAISS index and the live web (via Tavily) for comprehensive evidence |
| 🧠 **Parallel Agent Architecture** | LangGraph orchestrates multiple section-writing agents concurrently with tool access |
| 📝 **Scratchpad Protocol** | Agents follow a disciplined extract → note → synthesise workflow for traceable research |
| 🔄 **Hybrid Retrieval (BM25 + Dense)** | Ensemble retriever with cross-encoder reranking for high-precision document retrieval |
| 📊 **Real-Time Pipeline UI** | Streamlit dashboard with live phase tracking: Planning → Research → Synthesis → Assembly |
| 📥 **Multi-Format Export** | Download final reports as Markdown, PDF, or plain text |
| 🗂️ **Report History** | Browse and revisit previously generated reports from the sidebar archive |

---

## 🏗️ Architecture

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
│  └──────────────┘    │  �� Agent 1 │  │ Agent N │  │     │
│                      │  │ write → │  │ write → │  │     │
│                      │  │ tools → │  │ tools → │  │     │
│                      │  │ scratch │  │ scratch │  │     │
│                      │  └─────────┘  └─────────┘  │     │
│                      └────────────┬────────────────┘     │
│                                   ▼                      │
│  ┌──────────────┐    ┌─────────────────────────────┐     │
│  │ Compile      │◀───│ Write Final Sections        │     │
│  │ Final Report │    │ (intro, conclusion)          │     │
│  └──────────────┘    └─────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌────────────┐ ┌─────────┐ ┌──────────┐
   │ PubMed RAG │ │ Tavily  │ │ Scratch  │
   │ (FAISS +   │ │ Web     │ │ pad      │
   │  BM25)     │ │ Search  │ │ Memory   │
   └────────────┘ └─────────┘ └──────────┘
```

---

## 📁 Project Structure

```
MedReportAI/
├── app.py                  # LangGraph pipeline definition & entry point
├── streamlit_app.py        # Streamlit web application
├── config.py               # Model, retriever, and path configuration
├── langgraph.json          # LangGraph deployment config
├── pyproject.toml          # Project metadata & dependencies
│
├── agents/                 # High-level agent logic
│   └── planner.py          # Report plan generation & final section writing (DSPy)
│
├── core/                   # Pipeline internals
│   ├── nodes.py            # Graph node functions (compile, gather, initiate)
│   ├── schemas.py          # Pydantic schemas (scratchpad operations, etc.)
│   ├── signatures.py       # DSPy signatures (ReportPlanner, SectionWriter, etc.)
│   ├── states.py           # LangGraph state definitions
│   └── tool_node.py        # Tool execution node with routing logic
│
├── rag/                    # Retrieval-Augmented Generation
│   ├── chain.py            # RAG chain construction
│   ├── embeddings.py       # FastEmbed wrapper for LangChain
│   ├── retrieval_builder.py # Ensemble retriever + cross-encoder reranker
│   ├── retrieval_formatter.py # Structured report from retriever results
│   └── source_formatter.py # Web search result formatting
│
├── tools/                  # LangChain tools available to agents
│   ├── retrieval.py        # PubMed retriever tool
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
│   └── pubmed_scraper.py   # PubMed article scraper (BioPython + DeepSeek)
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
├── data/                   # Datasets & scraped articles
├── outputs/                # Generated FAISS indexes & scratchpad files
└── downloaded_docs/        # Downloaded research documents
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+**
- A [DeepSeek API key](https://platform.deepseek.com/)
- A [Tavily API key](https://tavily.com/) (for web search)

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
```

### Prepare Data

Before running the pipeline, you'll need PubMed article data. Use the built-in scraper:

```python
from scripts.pubmed_scraper import PubMedScraper

scraper = PubMedScraper(email="your_email@example.com")
scraper.run("pediatric health outcomes in conflict settings")
```

This will fetch articles from PubMed and save them to `data/pubmed_results.csv`.

### Build the FAISS Index

The retrieval system will automatically build and cache a FAISS vector index on first run from the CSV data in `data/`.

---

## 🖥️ Usage

### Streamlit Web App

```bash
streamlit run streamlit_app.py
```

<!-- SCREENSHOT: Add a screenshot of the running Streamlit app here -->

1. Enter a research query (e.g., *"Long-term pediatric health outcomes in conflict settings"*)
2. Optionally customize the **Context/Persona** and **Report Structure** in the sidebar
3. Click **▶ Run Pipeline** and watch real-time progress through each phase
4. Export the final report as **Markdown**, **PDF**, or **Text**

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

## ⚙️ Configuration

All settings are centralized in `config.py`:

| Setting | Default | Description |
|---|---|---|
| `deepseek_model` | `deepseek-chat` | LLM model (`deepseek-chat` or `deepseek-reasoner`) |
| `deepseek_temperature` | `1.3` | Generation temperature |
| `embedding_model` | `all-MiniLM-L6-v2` | Sentence embedding model (FastEmbed) |
| `reranker_model` | `ms-marco-miniLM-L-6-v2` | Cross-encoder reranker |
| `k` | `15` | Number of documents to retrieve |
| `sparse_weight` | `0.65` | BM25 weight in ensemble |
| `dense_weight` | `0.35` | Dense retrieval weight in ensemble |
| `top_n` | `5` | Documents after reranking |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | [LangGraph](https://github.com/langchain-ai/langgraph) — stateful multi-agent pipeline |
| **Prompt Framework** | [DSPy](https://dspy-docs.vercel.app/) — structured signatures for planning & writing |
| **LLM** | [DeepSeek](https://www.deepseek.com/) — `deepseek-chat` / `deepseek-reasoner` |
| **Retrieval** | FAISS + BM25 ensemble with FastEmbed cross-encoder reranking |
| **Web Search** | [Tavily](https://tavily.com/) — real-time web search with raw content |
| **Data Source** | [PubMed](https://pubmed.ncbi.nlm.nih.gov/) via BioPython Entrez API |
| **Frontend** | [Streamlit](https://streamlit.io/) — custom dark theme with live pipeline tracking |
| **PDF Export** | WeasyPrint — styled PDF generation from Markdown |

---

## 🧪 Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run linters & formatters
ruff check .
black .
isort .
mypy .

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

---

## 📄 License

This project does not currently specify a license. Please contact the author for usage terms.

---

## 🤝 Contributing

Contributions are welcome! Please open an issue first to discuss what you'd like to change.

---

<div align="center">

**Built with 🧬 by [@Chrisolande](https://github.com/Chrisolande)**

</div>
