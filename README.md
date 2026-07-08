# Research Intelligence Assistant

A FastAPI-based research and benchmarking assistant that searches for scientific papers and patents, suggests comparison metrics, validates evaluations using an agent-based validation layer, and generates structured reports with professional PDF exports.

---

## What It Does

Research Intelligence Assistant automates the research discovery and benchmarking process:

1. **Searches** for relevant patents and scientific papers based on a research topic
2. **Suggests** domain-relevant comparison metrics using a ChromaDB-backed metric bank
3. **Evaluates** sources against selected metrics using LLM-powered analysis
4. **Validates** the comparison matrix using the Comparison Agent with rule-based and LLM validation
5. **Generates** a structured Markdown report with:
   - Executive summary with validation insights
   - Top-ranked papers and patents
   - Validated comparison matrix with visual heatmap
   - Open-access paper detection and links
6. **Exports** professional PDFs for research reports and LLM execution analytics
7. **Tracks** LLM usage, token counts, estimated costs, and execution analytics

---

## Key Features

### Browser UI
- Clean, step-by-step web interface at `/ui`
- Metric suggestion workflow
- Custom metric support
- Research mode selection (cached vs. fresh)
- Real-time statistics and report rendering
- PDF export buttons for research reports and analytics

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

### Comparison Agent (Validation Layer)
- **Agent-based matrix validation**: Reviews each cell in the comparison matrix before final report generation
- **Rule-based validation**: Applies deterministic rules for well-defined metrics (Open Access, XPBD Support, Patent/IP, VR/HMD, Haptic Support, AI Support)
- **LLM-based validation**: Used for ambiguous cases when rule-based validation is insufficient
- **Evidence verification**: Ensures YES/PART/NO values are justified by source metadata (title, abstract, relevance analysis, source type)
- **Change tracking**: Logs corrections with explanations of what changed and why
- **Confidence scoring**: Provides validation confidence for each cell and overall matrix
- **Fallback safety**: If validation fails, uses original matrix without blocking report generation
- **No hallucination**: Agent is instructed to prefer PART or NO when evidence is weak or missing

### Executive Summary Comparison Matrix
- Row-based heatmap coloring by overall source coverage
- **✅ Fully Matched**, **⚠️ Partially Covered**, **❌ Not Covered** status badges (validated by Comparison Agent)
- Linked source labels (Paper 1, Patent 1, etc.) jump to full citations
- Metric coverage row shows column-wise average scores
- Evidence tooltips on hover
- Optional validation summary in executive summary

### Report Rendering
- Markdown + embedded HTML for rich formatting
- Uses validated comparison matrix from Comparison Agent
- Includes ranked sources, metadata, and validation insights
- Displays cache status and open-access paper counts

### PDF Export
- **Research Report PDF**: Compact professional design with title, comparison matrix, top papers/patents, and references
- **LLM Usage Analytics PDF**: Execution summary, token usage, estimated costs, step breakdown, and workflow visualization
- **No secrets exposed**: API keys, prompts, and credentials are never included in PDFs
- **Cost disclaimer**: All costs are clearly labeled as estimates, not official invoices
- Clean, presentation-ready output for sharing research findings

### LLM Observability and Analytics
- **Token Usage Tracking**: Monitors prompt tokens, completion tokens, and total tokens for all LLM calls
- **Cost Estimation**: Calculates estimated costs based on model pricing (labeled as estimates)
- **Execution Timing**: Tracks duration for each pipeline step (including Comparison Agent validation)
- **LangSmith Tracing** (optional): Integration with LangSmith for detailed trace analysis
- **Workflow Visualization**: Shows the complete pipeline execution flow in the UI
- **Interactive Charts**: Duration by step, cost by step, token distribution, prompt vs completion tokens
- **Validation Metrics**: Tracks cells reviewed, cells changed, and validation confidence from Comparison Agent

---

## Architecture

### Multi-Agent Workflow

```
User Input (Browser UI)
    │
    ▼
FastAPI Backend
    │
    ├── /suggest-metrics → MetricsBank (ChromaDB)
    ├── /cache/status    → ResearchCache (ChromaDB)
    ├── /generate        → Pipeline:
    │       │
    │       ├── ResearchCache (lookup or fetch)
    │       ├── SearchOrchestrator (patents + papers)
    │       ├── RankingEngine (LLM scoring + deduplication)
    │       ├── MetricsBank (selected + custom metrics)
    │       ├── ComparisonMatrixGenerator (initial LLM evaluation)
    │       ├── ComparisonAgent (validation layer) ← AGENT VALIDATION
    │       └── ReportRenderer (Markdown + HTML with validated matrix)
    │
    ├── /export-research-pdf → PDFExporter (research report)
    └── /export-usage-pdf    → PDFExporter (analytics report)
```

**Comparison Agent Validation Flow:**

```
Initial Matrix (from ComparisonMatrixGenerator)
    │
    ▼
For each cell (source × metric):
    │
    ├── Rule-Based Validation
    │   ├── Open Access metric → Check is_open_access / pdf_url
    │   ├── XPBD Support → Keyword matching (XPBD, PBD, position-based)
    │   ├── Patent/IP → Source type validation
    │   ├── VR/HMD → Keyword matching (VR, HMD, virtual reality)
    │   ├── Haptic Support → Keyword matching (haptic device, force feedback)
    │   └── AI Support → Keyword matching (AI, ML, deep learning)
    │
    ├── LLM-Based Validation (if rule-based insufficient)
    │   └── Validate ambiguous cells with structured LLM call
    │
    └── Change Tracking
        ├── Log corrections (old status → new status)
        ├── Record reason for change
        └── Track confidence score
    │
    ▼
Validated Matrix
    │
    └── Used in Report + PDF Export
```

The **Comparison Agent** is a controlled validation agent, not a fully autonomous multi-agent system. It acts as a critic that reviews the initial matrix and corrects unsupported evaluations before report generation.

### Core Components

- **FastAPI app** (`app.py`): REST API with `/ui`, `/generate`, `/suggest-metrics`, `/cache/status`, `/export-research-pdf`, `/export-usage-pdf` endpoints
- **Adapters** (`ria/adapters/`): SerpAPI patents, Semantic Scholar papers
- **ChromaDB Metric Bank** (`ria/metrics_bank.py`): Persistent metric storage
- **ChromaDB Research Cache** (`ria/research_cache.py`): Caches fetched papers/patents
- **Comparison Matrix Generator** (`ria/comparison_matrix.py`): LLM-based source evaluation (initial matrix)
- **Comparison Agent** (`ria/agents/comparison_agent.py`): Validates matrix cells with rule-based and LLM validation
- **Report Renderer** (`ria/report.py`): Markdown + HTML report generation (uses validated matrix)
- **PDF Exporter** (`ria/pdf_export.py`): Professional PDF generation for reports and analytics
- **Analytics Tracker** (`ria/analytics.py`): Tracks LLM usage, costs, and execution metrics
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

   **LangSmith Tracing** (optional, for LLM observability):
   ```bash
   LANGSMITH_TRACING=true
   LANGSMITH_API_KEY=lsv2_pt_your_key_here
   LANGSMITH_PROJECT=your-project-name
   ```

   **Note**: The app works normally without LangSmith. If these variables are not set or tracing is disabled, local analytics tracking will still function. Legacy `LANGCHAIN_*` variables are also supported for backward compatibility.

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

- **Statistics panel** shows:
  - Total items found
  - Patents/papers breakdown
  - Open-access paper count
  - Cache status

- **Research Report** includes:
  - Executive summary
  - Top-ranked papers (with open-access links)
  - Top-ranked patents
  - **Comparison Matrix** with heatmap coloring
  - Metric coverage summary

- **LLM Execution Summary** displays:
  - Total execution time
  - Total LLM calls (including Comparison Agent validation calls)
  - Token usage (prompt, completion, total)
  - Estimated cost (labeled as estimate)
  - Cache status
  - Papers found
  - Validation metrics (cells reviewed, cells changed, confidence score)

- **Execution Analytics Charts**:
  - Duration by Step (bar chart, includes Comparison Agent step)
  - Cost by Step (bar chart, estimated, includes validation costs)
  - Token Distribution by Step (doughnut chart)
  - Prompt vs Completion Tokens (stacked bar chart)

- **Workflow Pipeline** shows:
  - Visual timeline of all executed steps (including validation)
  - Duration, tokens, cost per step
  - Status indicators

- **Export Buttons**:
  - Export Research Report PDF (with validated matrix)
  - Export LLM Usage Analytics PDF

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

## Comparison Agent

### Overview

The **Comparison Agent** is a validation layer that reviews the comparison matrix before the final report is generated. It acts as a critic that verifies whether each YES/PART/NO evaluation is justified by the available evidence.

### Responsibility

The Comparison Agent:
- Reviews the initial source comparison matrix generated by `ComparisonMatrixGenerator`
- Checks each source against each selected metric
- Validates whether each YES / PART / NO value is supported by evidence
- Corrects unsupported or incorrect values
- Logs what changed and why
- Provides a confidence score for the validation

### Evaluation Definitions

- **YES (✅ / full)**: Clear and explicit evidence supports the metric in the source metadata
- **PART (⚠️ / partial)**: Partial, indirect, or related evidence supports the metric
- **NO (❌ / none)**: No clear evidence supports the metric

### Evidence Sources

The Comparison Agent bases its validation on:
- Source title
- Source abstract or summary
- Relevance analysis explanation
- Source type (paper vs. patent)
- Metadata (DOI, patent number, venue, authors, publication date)
- Flags (is_open_access, pdf_url)
- Selected metric definitions

The agent **does not hallucinate** and is instructed to prefer **PART** or **NO** when evidence is weak or missing.

### Rule-Based Validation

The Comparison Agent includes deterministic rule-based validation for well-defined metrics:

#### Open Access
- **YES**: if `is_open_access` flag is true OR `pdf_url` exists
- **NO**: if neither flag is set

#### XPBD Support
- **YES**: if title or relevance analysis explicitly mentions "XPBD" or "Extended Position Based Dynamics"
- **PART**: if mentions "position-based dynamics", "PBD", or "constraint-based simulation"
- **NO**: otherwise

#### Patent / IP Coverage
- **YES**: if source type is patent
- **PART**: if paper discusses patents or IP
- **NO**: otherwise

#### VR HMD Integration
- **YES**: if mentions "VR", "HMD", "head-mounted display", "virtual reality", "Oculus", or "HTC Vive"
- **PART**: if mentions "simulation", "training", or "immersive" (context-dependent)
- **NO**: otherwise

#### Haptic Robot Support
- **YES**: if mentions "haptic device", "haptic robot", "force feedback device", "haptic interface", or "robotic haptics"
- **PART**: if mentions "haptic feedback", "haptic", "force feedback", or "tactile"
- **NO**: otherwise

#### AI Support
- **YES**: if mentions "AI", "machine learning", "deep learning", "neural network", "learning-based", or "ML"
- **PART**: if mentions "optimization", "automated", "intelligent", or "adaptive" (context-dependent)
- **NO**: otherwise

### LLM-Based Validation

When rule-based validation is insufficient or unavailable for a metric, the Comparison Agent can use LLM-based validation:

- **Input**: Source context, metric name, current status, current evidence, metric description
- **Output**: Structured JSON with validated status, confidence, evidence, and reason for change
- **Safety**: Falls back to original evaluation if LLM call fails
- **Temperature**: 0.2 (low temperature for consistency)
- **Instructions**: "Do not hallucinate. Base your decision ONLY on the provided evidence."

LLM-based validation does not replace rule-based validation—it complements it for ambiguous cases.

### Validation Output

Validation results include:

- **validated_matrix**: List of `SourceMetricEvaluation` objects with corrected status values
- **changes**: List of `ValidationChange` objects with old status, new status, and reason
- **validation_summary**: Human-readable summary of validation results
- **confidence_score**: Overall confidence score (0.0 to 1.0)
- **cells_reviewed**: Total number of matrix cells reviewed
- **cells_changed**: Total number of matrix cells corrected

### Workspace Artifacts

Validation generates the following workspace files:

- `comparison_evaluations_initial.json`: Initial matrix before validation
- `comparison_evaluations.json`: Validated matrix after Comparison Agent
- `comparison_validation.json`: Validation result with changes and summary

**Note**: These are local generated files and should not be committed to git.

### Fallback Behavior

If Comparison Agent validation fails for any reason:
- The original matrix from `ComparisonMatrixGenerator` is used
- Report generation continues without blocking
- A warning is logged but the pipeline completes successfully

---

## LLM Observability and Analytics

The Research Intelligence Assistant includes comprehensive LLM execution tracking and observability features.

### Features

#### 1. Token Usage Tracking
- Tracks **prompt tokens**, **completion tokens**, and **total tokens** for every LLM call
- Per-step breakdown showing token usage across the pipeline
- Extracted directly from OpenAI-compatible API responses

#### 2. Cost Estimation
- Calculates estimated costs based on model pricing
- Supports multiple models: Claude (Haiku, Sonnet, Opus), GPT-4, GPT-3.5, etc.
- Per-step cost breakdown
- **Note**: Costs are estimates based on approximate pricing and should not be used for billing

#### 3. Execution Timing
- Tracks duration for each pipeline step
- Total execution time from start to finish
- Helps identify performance bottlenecks

#### 4. LangSmith Analytics Integration (Optional)

**Two Analytics Sources:**

1. **LangSmith (Primary)**: When LangSmith tracing is enabled, usage analytics are retrieved directly from LangSmith traces after report generation. This provides authoritative token counts, costs, and timing based on actual LLM API calls.

2. **Internal Tracker (Fallback)**: When LangSmith is unavailable or disabled, the internal analytics tracker monitors LLM calls locally. This ensures analytics are always available.

**The analytics source is clearly indicated in:**
- UI execution summary (highlighted when using LangSmith)
- Analytics JSON files (`analytics_source` field)
- PDF analytics reports

**To enable LangSmith analytics**, add to `.env`:
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt_your_key_here
LANGSMITH_PROJECT=your-project-name
```

**Legacy variables** (also supported for backward compatibility):
```bash
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_your_key_here
LANGCHAIN_PROJECT=your-project-name
```

**How it works:**
- Each report generation is tagged with a unique `report_id`
- All LLM calls are traced to LangSmith with this `report_id` metadata
- After generation, the system queries LangSmith for usage data
- If LangSmith is unavailable, it falls back to internal tracker automatically

**Benefits of LangSmith integration:**
- Authoritative usage data from LLM API responses
- Detailed trace URLs for debugging
- Centralized observability across all runs
- No manual token counting required

If tracing is disabled or variables are missing, the app continues with local analytics only.

#### 5. Analytics Data Storage
- Analytics data saved to workspace as `analytics.json`
- Includes: analytics source, execution time, token counts, costs, cache status, step breakdown
- LangSmith trace IDs and URLs when available
- Available for later analysis or export

#### 6. UI Visualization
After generating a report, the UI displays:

**LLM Execution Summary:**
- Total duration, LLM calls, tokens, estimated cost
- Cache status and data counts

**Interactive Charts:**
- **Duration by Step**: Horizontal bar chart showing time spent per pipeline step
- **Cost by Step**: Horizontal bar chart showing estimated cost per step
- **Token Distribution**: Doughnut chart showing token usage across steps
- **Prompt vs Completion Tokens**: Stacked bar chart comparing input vs output tokens

**Workflow Pipeline:**
- Visual timeline showing all executed steps
- Status indicators, duration, token counts, and costs per step

### Tracked Pipeline Steps

1. **Initialize Components** - Setup LLM client, cache, workspace
2. **Check Cache** - Look up cached results
3. **Fetch Research** - SearchOrchestrator (if cache miss)
4. **Deduplicate Sources** - Remove duplicate papers/patents
5. **Score Sources** - LLM-based relevance scoring (multiple calls)
6. **Select Top Sources** - Select top N papers and patents
7. **Generate Metrics** - Auto-generate comparison metrics (if not selected)
8. **Evaluate Comparison Matrix** - LLM evaluation of sources against metrics (multiple calls)
9. **Validate Comparison Matrix** - Comparison Agent validates each cell (rule-based + optional LLM)
10. **Generate Report** - Render final Markdown report with validated matrix

### Cost Estimation Models

The system uses approximate pricing per 1,000 tokens:

| Model | Prompt Tokens | Completion Tokens |
|-------|---------------|-------------------|
| Claude Haiku | $0.00025 | $0.00125 |
| Claude Sonnet | $0.003 | $0.015 |
| Claude Opus | $0.015 | $0.075 |
| GPT-4o-mini | $0.00015 | $0.0006 |
| GPT-4o | $0.01 | $0.03 |
| GPT-4 | $0.03 | $0.06 |
| GPT-3.5 | $0.0005 | $0.0015 |

**Important**: These are estimates. Actual costs may vary. Do not use for billing purposes.

### Privacy and Security

- **No API keys exposed**: API keys are never sent to the frontend or included in logs/PDFs
- **No prompts logged**: User prompts and LLM responses are not stored in analytics (only metadata)
- **Local tracking**: All analytics data stored locally in workspace directories
- **Optional tracing**: LangSmith integration is completely optional

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

### `POST /export-research-pdf`

Export research report as a professional PDF.

**Request Body**:
```json
{
  "topic": "XPBD soft body simulation",
  "report_content": "... Markdown content ...",
  "stats": { ... },
  "analytics": { ... },
  "comparison_evaluations": [ ... ],
  "metric_names": ["XPBD Support", "GPU Support"],
  "ranked_papers": [ ... ],
  "ranked_patents": [ ... ]
}
```

**Response**: PDF file download

**Features**:
- Compact professional header with topic and date
- Validated comparison matrix with color-coded cells
- Top papers section with citations
- Top patents section with assignees
- Full references
- Does not expose API keys or secrets

### `POST /export-usage-pdf`

Export LLM usage analytics as a professional PDF.

**Request Body**:
```json
{
  "topic": "XPBD soft body simulation",
  "analytics": {
    "total_duration_seconds": 12.5,
    "total_llm_calls": 15,
    "total_tokens": 12000,
    "estimated_total_cost": 0.0456,
    "steps": [ ... ]
  }
}
```

**Response**: PDF file download

**Features**:
- Execution summary with timing and token counts
- Estimated costs (clearly labeled as estimates)
- Per-step breakdown
- Workflow pipeline visualization
- LangSmith trace information (if available)
- Does not expose API keys or prompts

---

## Testing

### Run All Tests

```bash
python -m pytest
```

**Expected Result**: 120 tests passing (as of 2026-07-07)

### Run Specific Tests

```bash
# Unit tests
python -m pytest tests/unit/ -v

# Comparison Agent tests
python -m pytest test_comparison_agent.py -v
python -m pytest test_comparison_agent_integration.py -v

# PDF export tests
python -m pytest tests/unit/test_pdf_export.py tests/unit/test_research_pdf_fixes.py -v

# Semantic Scholar adapter
python -m pytest tests/unit/test_semantic_scholar.py -v
```

### Comparison Agent Tests

```bash
# Rule-based validation tests
python -m pytest test_comparison_agent.py::TestComparisonAgentRuleBased -v

# LLM-based validation tests (requires OPENAI_API_KEY)
python -m pytest test_comparison_agent.py::TestComparisonAgentLLMBased -v

# Integration tests (full pipeline with validation)
python -m pytest test_comparison_agent_integration.py -v
```

### Manual Testing

```bash
# Test full pipeline with Comparison Agent
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

# Workspaces and generated artifacts
workspaces/

# PDF exports
pdf_exports/
sample_pdf_exports/

# Backups
*.backup
```

**Important**: Workspace directories (`workspaces/`) contain local generated files such as:
- `comparison_evaluations_initial.json`
- `comparison_evaluations.json`
- `comparison_validation.json`
- `analytics.json`
- `report.md`

These are local artifacts and should never be committed.

### Protect Your API Keys

- Never commit `.env` files with real API keys
- Use `.env.example` as a template
- Store real keys in environment variables or secret managers
- API keys are never exposed in PDFs, logs, or frontend responses

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
│   ├── agents/                 # Agent-based components
│   │   ├── __init__.py
│   │   └── comparison_agent.py # Comparison matrix validator
│   ├── metrics_bank.py         # ChromaDB metric bank
│   ├── research_cache.py       # ChromaDB research cache
│   ├── comparison_matrix.py    # Matrix generation
│   ├── llm.py                  # LLM client wrapper
│   ├── metrics.py              # Metric generation
│   ├── models.py               # Pydantic models
│   ├── orchestrator.py         # Search orchestration
│   ├── ranking.py              # Ranking engine
│   ├── report.py               # Report renderer
│   ├── pdf_export.py           # PDF generation
│   ├── analytics.py            # Execution analytics tracker
│   ├── workspace.py            # Workspace management
│   └── ui_template.html        # Browser UI template
├── tests/                      # Test suite
│   └── unit/
│       ├── test_pdf_export.py
│       ├── test_research_pdf_fixes.py
│       └── ...
├── test_comparison_agent.py    # Comparison Agent tests
├── test_comparison_agent_integration.py  # Integration tests
├── chroma_db/                  # ChromaDB data (not committed)
│   ├── metrics/
│   └── research/
├── workspaces/                 # Generated reports (not committed)
└── pdf_exports/                # Generated PDFs (not committed)
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
1. **Executive Summary**: High-level overview of research landscape with validation insights
2. **Validated Comparison Matrix**:
   - Reviewed and corrected by Comparison Agent
   - Row-based heatmap coloring (green = high coverage, red = low coverage)
   - Status badges (✅/⚠️/❌) for each metric per source
   - Linked source labels jump to full citations
   - Metric coverage row shows average scores
   - Evidence tooltips on hover
3. **Top Papers**: 5 ranked papers with citation counts, venues, and open-access links
4. **Top Patents**: 5 ranked patents with assignees and publication dates
5. **References**: Full citation details for all sources
6. **Cache Status**: Reports whether results were cached or freshly fetched
7. **Validation Summary**: Shows how many cells were reviewed and corrected by the Comparison Agent

**PDF Exports**:
- **Research Report PDF**: Compact professional design with title, validated matrix, top sources, and references
- **LLM Usage Analytics PDF**: Execution summary, token usage, estimated costs, and workflow visualization

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
- **Comparison Agent with rule-based and LLM validation**
- **Professional PDF exports for research reports and analytics**
- **LLM usage tracking and cost estimation**
- **Validation change logging and confidence scoring**

### In Progress 🚧
- Enhanced metric categorization
- User feedback loop for metric refinement
- Additional rule-based validation patterns

### Planned 🔮
- Additional data sources (ArXiv, Google Patents)
- Commercial solution discovery
- Interactive dashboard with filters
- Multi-source benchmarking
- Fully autonomous multi-agent research system

---

## Project Status

This is a **demo-ready prototype** with production-oriented features, developed as part of an AI Engineering Bootcamp project. It demonstrates:
- Multi-stage LLM pipeline orchestration
- Agent-based validation layer
- ChromaDB-backed caching and similarity search
- Professional PDF generation
- LLM observability and cost tracking

The project is suitable for:
- Research demonstrations
- Educational purposes
- Proof-of-concept for research automation
- Foundation for production-ready systems

**Not recommended for**:
- Production use without further hardening
- Mission-critical research workflows
- Official cost accounting (estimates only)

---

## Author

**Sajjad Rostami**  
PhD in Computer Science / XR / AI Systems

Research Intelligence Assistant was developed as part of an AI Engineering Bootcamp project focused on LLMs, RAG systems, agent-based architectures, and intelligent research automation.

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
