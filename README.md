# Research Intelligence Assistant

A Python-based assistant that generates structured benchmark reports from a research topic by collecting papers, patents, metrics, comparison matrices, analytics, and exportable reports.

**[Live Project Page](https://sajjadrostami.github.io/research-intelligence-assistant/)** | **[GitHub Repository](https://github.com/SajjadRostami/research-intelligence-assistant)**

---

## Key Features

- Scientific paper and patent retrieval
- Topic-aware metric suggestions that adapt based on research topic and learn from user behavior (selected, custom-added, and ignored metrics)
- Source ranking and comparison matrix generation
- Agent-based matrix validation (Metric Bank Agent + Comparison Agent)
- PDF report export with visual heatmaps
- LangSmith analytics and tracing (optional)
- Local web UI with step-by-step workflow

---

## Architecture Overview

The application uses a two-agent structure:

- **Metric Bank Agent**: Provides topic-aware metric suggestions using ChromaDB as the base metric bank, dynamically adapting to the current research topic and learning from selected, custom-added, and ignored metrics
- **Comparison Agent**: Validates and improves comparison matrix cells using rule-based and LLM validation

The pipeline coordinates search, ranking, matrix generation, validation, analytics tracking, and PDF export.

**Core Components:**
- `app.py`: FastAPI REST API with browser UI
- `ria/adapters/`: SerpAPI patents, Semantic Scholar papers
- `ria/metrics_bank.py`: ChromaDB metric storage with adaptive learning
- `ria/research_cache.py`: ChromaDB research cache
- `ria/comparison_matrix.py`: Initial matrix generation
- `ria/agents/comparison_agent.py`: Matrix validation layer
- `ria/report.py`: Markdown + HTML report renderer
- `ria/pdf_export.py`: PDF generation for reports and analytics
- `ria/analytics.py`: LLM usage and cost tracking

---

## Installation

**Prerequisites:** Python 3.10+

1. Clone the repository:
   ```bash
   git clone https://github.com/SajjadRostami/research-intelligence-assistant.git
   cd research-intelligence-assistant
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root:
   ```bash
   # Required
   OPENAI_API_KEY=your_openai_key_here
   SERPAPI_API_KEY=your_serpapi_key_here
   
   # Optional
   OPENAI_BASE_URL=your_custom_endpoint  # For OpenAI-compatible endpoints
   LLM_MODEL=claude-haiku                 # Default model
   SEMANTIC_SCHOLAR_API_KEY=your_key      # For higher rate limits
   
   # LangSmith (optional, for LLM observability)
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=lsv2_pt_your_key_here
   LANGSMITH_PROJECT=research-intelligence-assistant
   ```

   **Note:** Do not commit `.env` with real keys. The app works normally without LangSmith.

---

## Running the Application

Start the FastAPI server:

```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:

```
http://127.0.0.1:8000/ui
```

**UI Workflow:**

1. Enter a research topic and set max results per adapter
2. Choose research mode (cached vs. fresh)
3. Click **Suggest Metrics**
4. Review and select metrics (or add custom ones)
5. Click **Generate Report**
6. View the report with comparison matrix, analytics, and export options

---

## Using LangSmith

LangSmith provides optional LLM tracing and observability. When enabled:

- Every LLM call is traced with a unique `report_id`
- Analytics are retrieved from LangSmith API (with fallback to local tracker)
- Trace URLs are available in the UI for debugging
- Token counts and costs come directly from LLM API responses

To enable LangSmith, add these variables to your `.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_your_key_here
LANGSMITH_PROJECT=research-intelligence-assistant
```

After generating a report, check that the UI shows **"Analytics Source: LangSmith"** instead of "Local tracker".

To disable: set `LANGSMITH_TRACING=false` or remove the variables entirely.


---

## Tests

Run all tests:

```bash
pytest -q
```

---

## Output Files

Generated reports and runtime data are stored locally:

- **PDF Exports**: `pdf_exports/` (research reports and analytics)
- **Workspaces**: `workspaces/<topic>/` (Markdown reports, JSON data, analytics)
- **ChromaDB**: `chroma_db/metrics/` and `chroma_db/research/` (metric bank and research cache)
- **Metric Bank Usage**: `data/metric_bank_usage.json` (adaptive learning data)

**Note:** These directories are excluded from Git via `.gitignore`, along with `.env` files.

---

## Project Structure

```
research-intelligence-assistant/
├── app.py                          # FastAPI application
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (not committed)
├── ria/                            # Core package
│   ├── adapters/                   # SerpAPI patents, Semantic Scholar papers
│   ├── agents/                     # Comparison Agent (validation layer)
│   ├── metrics_bank.py             # ChromaDB metric bank with adaptive learning
│   ├── research_cache.py           # ChromaDB research cache
│   ├── comparison_matrix.py        # Matrix generation
│   ├── llm.py                      # LLM client wrapper
│   ├── report.py                   # Report renderer
│   ├── pdf_export.py               # PDF generation
│   ├── analytics.py                # Execution analytics tracker
│   ├── langsmith_analytics.py      # LangSmith trace retrieval
│   └── ui_template.html            # Browser UI template
├── tests/                          # Test suite
├── chroma_db/                      # ChromaDB data (not committed)
├── workspaces/                     # Generated reports (not committed)
└── pdf_exports/                    # Generated PDFs (not committed)
```

---

## Author

**Sajjad Rostami**  
PhD in Computer Science / XR / AI Systems

Developed as part of an AI Engineering Bootcamp project focused on LLMs, RAG systems, agent-based architectures, and intelligent research automation.

---

## License

This project is open-source. See [LICENSE](LICENSE) for details.
