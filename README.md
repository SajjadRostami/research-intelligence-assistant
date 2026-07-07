# Research Intelligence Assistant

A FastAPI-based research assistant that searches for scientific papers and patents, suggests comparison metrics, and generates structured benchmark reports with interactive comparison matrices.

---

## What It Does

Research Intelligence Assistant automates the research discovery and benchmarking process:

1. **Searches** for relevant patents and scientific papers based on a research topic
2. **Suggests** domain-relevant comparison metrics using a ChromaDB-backed metric bank
3. **Evaluates** sources against selected metrics using LLM-powered analysis
4. **Generates** a structured Markdown report with:
   - Executive summary
   - Top-ranked papers and patents
   - Interactive comparison matrix with visual heatmap
   - Open-access paper detection and links

---

## Key Features

### Browser UI
- Clean, step-by-step web interface at `/ui`
- Metric suggestion workflow
- Custom metric support
- Research mode selection (cached vs. fresh)
- Real-time statistics and report rendering

### Data Sources
- **Patents**: SerpAPI Patent Search (or mock adapter for testing)
- **Papers**: Semantic Scholar with open-access detection
- Automatic deduplication and ranking

### ChromaDB Metric Bank
- Persistent storage of comparison metrics with embeddings
- Similarity-based metric suggestions
- Default metrics for common domains (AI, GPU, VR/AR, Medical, Performance, etc.)
- Custom metric storage with usage tracking

### ChromaDB Research Cache
- Caches fetched papers and patents to avoid repeated API calls
- Topic normalization and exact match lookup
- "Research from scratch" mode to bypass cache
- Cache status endpoint

### Executive Summary Comparison Matrix
- Row-based heatmap coloring by overall source coverage
- **✅ Fully Matched**, **⚠️ Partially Covered**, **❌ Not Covered** status badges
- Linked source labels (Paper 1, Patent 1, etc.) jump to full citations
- Metric coverage row shows column-wise average scores
- Evidence tooltips on hover

### Report Rendering
- Markdown + embedded HTML for rich formatting
- Includes comparison matrix, ranked sources, and metadata
- Displays cache status and open-access paper counts

---

## Architecture

```
User Input (Browser UI)
    │
    ▼
FastAPI Backend
    │
    ├── /suggest-metrics → MetricsBank (ChromaDB)
    ├── /cache/status    → ResearchCache (ChromaDB)
    └── /generate        → Pipeline:
            │
            ├── ResearchCache (lookup or fetch)
            ├── SearchOrchestrator (patents + papers)
            ├── RankingEngine (LLM scoring + deduplication)
            ├── MetricsBank (selected + custom metrics)
            ├── ComparisonMatrixGenerator (LLM evaluation)
            └── ReportRenderer (Markdown + HTML)
```

### Core Components

- **FastAPI app** (`app.py`): REST API with `/ui`, `/generate`, `/suggest-metrics`, `/cache/status` endpoints
- **Adapters** (`ria/adapters/`): SerpAPI patents, Semantic Scholar papers
- **ChromaDB Metric Bank** (`ria/metrics_bank.py`): Persistent metric storage
- **ChromaDB Research Cache** (`ria/research_cache.py`): Caches fetched papers/patents
- **Comparison Matrix Generator** (`ria/comparison_matrix.py`): LLM-based source evaluation
- **Report Renderer** (`ria/report.py`): Markdown + HTML report generation
- **UI Template** (`ria/ui_template.html`): Interactive browser interface

---

## Installation

### Prerequisites

- Python 3.10+
- Virtual environment (recommended)

### Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/SajjadRostami/research-intelligence-assistant.git
   cd research-intelligence-assistant
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment variables**:

   Create a `.env` file in the project root:

   ```bash
   # .env
   OPENAI_API_KEY=your_openai_key_here
   SERPAPI_API_KEY=your_serpapi_key_here
   ```

   **Note**: Do not commit `.env` with real keys. Use `.env.example` for templates.

   Optional environment variables:
   - `OPENAI_BASE_URL`: Custom OpenAI-compatible endpoint (default: OpenAI)
   - `LLM_MODEL`: Model to use (default: `claude-haiku`)
   - `SEMANTIC_SCHOLAR_API_KEY`: For higher Semantic Scholar rate limits

---

## Running the Application

### Start the FastAPI Server

```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

### Open the Browser UI

Navigate to:

```
http://127.0.0.1:8000/ui
```

---

## UI Workflow

### Step 1: Enter Research Topic

1. Enter a research topic (e.g., "XPBD soft body simulation")
2. Set max results per adapter (default: 3)
3. Choose research mode:
   - **Use cached results if available**: Reuses cached data from previous searches
   - **Research from scratch**: Fetches fresh data and updates cache
4. Click **Suggest Metrics**

### Step 2: Select Comparison Metrics

1. Review suggested metrics from the metric bank
2. Click metrics to select/deselect
3. Add custom metrics via the input field
4. Click **Generate Report**

### Step 3: View Report

- Statistics panel shows:
  - Total items found
  - Patents/papers breakdown
  - Open-access paper count
  - Cache status
- Report includes:
  - Executive summary
  - Top-ranked papers (with open-access links)
  - Top-ranked patents
  - **Comparison Matrix** with heatmap coloring
  - Metric coverage summary

---

## Cache Behavior

### First Search for a Topic

- Fetches fresh papers and patents from APIs
- Saves metadata to ChromaDB (`chroma_db/research/`)
- Report generated from fetched results

### Repeated Search (Same Topic)

- **Cached mode**: Loads cached metadata instantly (no API calls)
- **Fresh mode**: Fetches new results and updates cache

### ChromaDB Directories

- `chroma_db/metrics/`: Metric bank storage
- `chroma_db/research/`: Research cache storage

**Note**: These directories contain local generated data. Add to `.gitignore`.

---

## API Endpoints

### `GET /`

Health check endpoint.

**Response**:
```json
{
  "status": "running",
  "message": "Research Intelligence Assistant is running",
  "version": "0.1.0"
}
```

### `GET /health`

Detailed health check with API key status.

**Response**:
```json
{
  "status": "healthy",
  "api_keys": {
    "serpapi": true,
    "openai": true
  },
  "llm_model": "claude-haiku",
  "base_url": "default"
}
```

### `GET /ui`

Browser-based UI for the research assistant.

### `POST /generate`

Generate a research report.

**Request Body**:
```json
{
  "topic": "XPBD soft body simulation",
  "max_results_per_adapter": 10,
  "selected_metrics": ["AI Support", "GPU Support", "Real-Time Performance"],
  "custom_metrics": ["Custom Feature"],
  "use_cache": true,
  "force_fresh_research": false
}
```

**Response**:
```json
{
  "success": true,
  "message": "Report generated successfully",
  "report_content": "... Markdown content ...",
  "workspace_dir": "./workspaces/xpbd-soft-body-simulation",
  "stats": {
    "total_raw_items": 20,
    "patents_found": 10,
    "papers_found": 10,
    "open_access_papers_found": 5,
    "ranked_patents": 5,
    "ranked_papers": 5,
    "metrics_generated": 3,
    "cache_status": "Cached results"
  }
}
```

### `POST /suggest-metrics`

Suggest metrics for a research topic.

**Request Body**:
```json
{
  "topic": "XPBD soft body simulation",
  "max_metrics": 10
}
```

**Response**:
```json
{
  "success": true,
  "suggested_metrics": [
    {
      "metric_id": "xpbd_support",
      "name": "XPBD Support",
      "description": "Whether the source uses Extended Position Based Dynamics",
      "category": "Algorithm",
      "usage_count": 5,
      "reason": "Relevant to 'XPBD soft body simulation' (similarity score: 0.95)"
    }
  ]
}
```

### `POST /cache/status`

Get cache status for a topic.

**Request Body**:
```json
{
  "topic": "XPBD soft body simulation"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "topic": "XPBD soft body simulation",
    "cached": true,
    "patents_count": 5,
    "papers_count": 5,
    "open_access_papers_count": 3,
    "last_fetched_at": "2026-07-07T12:34:56",
    "total_items": 10
  }
}
```

---

## Testing

### Run All Tests

```bash
python -m pytest
```

### Run Specific Tests

```bash
# Unit tests
python -m pytest tests/unit/

# Test new features
python test_new_features.py
```

### Manual Testing

```bash
# Test Semantic Scholar adapter
python -m pytest tests/unit/test_semantic_scholar.py -v

# Test full pipeline
python test_mvp_e2e.py
```

---

## Git and Security Notes

### Do NOT Commit

Add these to `.gitignore`:

```
# Environment variables
.env

# Python cache
__pycache__/
*.pyc
*.pyo

# ChromaDB data
chroma_db/
test_chroma_db/

# Workspaces
workspaces/

# Backups
*.backup
```

### Protect Your API Keys

- Never commit `.env` files
- Use `.env.example` as a template
- Store real keys in environment variables or secret managers

---

## Technology Stack

### Backend
- **FastAPI**: Modern async web framework
- **Pydantic v2**: Data validation and serialization
- **HTTPX**: Async HTTP client for API calls

### AI
- **OpenAI SDK**: LLM integration (Claude via OpenAI-compatible endpoints)
- **Structured Output**: JSON response models with Pydantic

### Storage
- **ChromaDB**: Vector database for metric bank and research cache
- **Embeddings**: Similarity-based search for metrics and papers

### External APIs
- **SerpAPI**: Patent search
- **Semantic Scholar**: Scientific paper search with open-access detection

### Testing
- **Pytest**: Unit and integration tests
- **Hypothesis**: Property-based testing

---

## Project Structure

```
research-intelligence-assistant/
├── app.py                      # FastAPI application
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not committed)
├── .gitignore                  # Git ignore rules
├── ria/                        # Core package
│   ├── __init__.py
│   ├── adapters/               # Search adapters
│   │   ├── base.py
│   │   ├── semantic_scholar.py
│   │   ├── serpapi_patents.py
│   │   └── mock_patent.py
│   ├── metrics_bank.py         # ChromaDB metric bank
│   ├── research_cache.py       # ChromaDB research cache
│   ├── comparison_matrix.py    # Matrix generation
│   ├── llm.py                  # LLM client wrapper
│   ├── metrics.py              # Metric generation
│   ├── models.py               # Pydantic models
│   ├── orchestrator.py         # Search orchestration
│   ├── ranking.py              # Ranking engine
│   ├── report.py               # Report renderer
│   ├── workspace.py            # Workspace management
│   └── ui_template.html        # Browser UI template
├── tests/                      # Test suite
│   └── unit/
├── chroma_db/                  # ChromaDB data (not committed)
│   ├── metrics/
│   └── research/
└── workspaces/                 # Generated reports (not committed)
```

---

## Example Use Case

**Input Topic**:
```
XPBD soft body simulation algorithm
```

**Selected Metrics**:
- XPBD Support
- GPU Support
- Real-Time Performance
- Open Access

**Output**:
1. **Executive Summary**: High-level overview of research landscape
2. **Top Papers**: 5 ranked papers with citation counts, venues, and open-access links
3. **Top Patents**: 5 ranked patents with assignees and publication dates
4. **Comparison Matrix**:
   - Row-based heatmap coloring (green = high coverage, red = low coverage)
   - Status badges for each metric per source
   - Linked source labels jump to full citations
   - Metric coverage row shows average scores
5. **Cache Status**: Reports whether results were cached or freshly fetched

---

## Roadmap

### Completed ✅
- FastAPI REST API with browser UI
- ChromaDB metric bank with similarity search
- ChromaDB research cache with topic normalization
- Comparison matrix with row-based heatmap coloring
- Open-access paper detection and PDF links
- Custom metric support
- Cache status endpoint

### In Progress 🚧
- Enhanced metric categorization
- User feedback loop for metric refinement

### Planned 🔮
- PDF report export
- Additional data sources (ArXiv, Google Patents)
- Commercial solution discovery
- Interactive dashboard with filters
- Multi-source benchmarking

---

## Author

**Sajjad Rostami**  
PhD in Computer Science / XR / AI Systems

Research Intelligence Assistant was developed as part of an AI Engineering Bootcamp project focused on LLMs, RAG systems, and intelligent research automation.

---

## License

This project is open-source. See [LICENSE](LICENSE) for details.

---

## Support

For issues, questions, or contributions:
- Open an issue on [GitHub](https://github.com/SajjadRostami/research-intelligence-assistant/issues)
- Submit a pull request

---

## Acknowledgments

- **Semantic Scholar**: For providing free academic paper search API
- **SerpAPI**: For patent search capabilities
- **ChromaDB**: For vector database and embeddings support
- **FastAPI**: For modern async web framework
- **Anthropic Claude**: For LLM-powered analysis
