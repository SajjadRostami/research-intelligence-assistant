# MVP End-to-End Test - Complete Documentation

## Overview

This directory contains a complete end-to-end test for the Research Intelligence Assistant MVP. The test demonstrates all core functionality of the system.

## Files Created

| File | Purpose | Size |
|------|---------|------|
| `test_mvp_e2e.py` | Main test script (executable) | 13 KB |
| `RUN_TEST.sh` | Bash test runner with environment checks | 1.4 KB |
| `TEST_MVP_E2E.md` | Complete test documentation | 6.7 KB |
| `QUICK_START_GUIDE.md` | Quick reference guide | 5.6 KB |
| `MVP_TEST_README.md` | This file - overview and summary | - |

## Quick Start

### Minimal Steps to Run

1. **Configure environment:**
   ```bash
   export OPENAI_API_KEY="your-api-key"
   export OPENAI_BASE_URL="https://your-endpoint.com/v1"
   ```

2. **Run test:**
   ```bash
   ./RUN_TEST.sh
   ```

3. **Review results in terminal and workspace:**
   ```bash
   ls -la ./test_mvp_workspace/xpbd-soft-body-simulation-algorithm/
   ```

## Test Input

**Research Topic:** "XPBD soft body simulation algorithm"

This topic was chosen because:
- It's specific and technical
- It has both academic papers and patents
- It demonstrates relevance scoring across different source types
- XPBD (Extended Position Based Dynamics) is a real research area

## Test Pipeline

The test runs through 4 main stages:

### 1. SearchOrchestrator
- Searches **SemanticScholar** for academic papers
- **Auto-selects patent adapter**:
  - **SerpAPIPatentAdapter** if `SERPAPI_API_KEY` is set (real patents)
  - **MockPatentAdapter** otherwise (synthetic patents for testing)
- Returns ~20 raw results total
- Saves to `orchestrator_result.json`

### 2. WorkspaceManager
- Creates workspace directory with slug-based naming
- Persists all artifacts as JSON files
- Tracks metadata (counts, timestamps)
- Enables future result loading

### 3. RankingEngine
- **Deduplicates** by title, DOI, patent number
- **Scores** each source using LLM (0.0 to 1.0 relevance)
- **Selects** top 3 papers and top 3 patents
- Saves to `ranked_results.json`

### 4. MetricsGenerator
- Analyzes top sources
- Generates 5-10 benchmark metrics using LLM
- Categories: performance, accuracy, efficiency, usability, etc.
- Saves to `metrics.json`

## Expected Output

The test prints:

```
✓ Number of patents found
✓ Number of papers found  
✓ Top 3 patents with scores, metadata, and reasoning
✓ Top 3 papers with scores, metadata, and reasoning
✓ 5-10 generated benchmark metrics with descriptions
✓ List of saved workspace artifacts
```

## Workspace Structure

After running, the workspace contains:

```
./test_mvp_workspace/
└── xpbd-soft-body-simulation-algorithm/
    ├── metadata.json              # Workspace info, counts, timestamps
    ├── orchestrator_result.json   # Raw results from all adapters
    ├── ranked_results.json        # Top 3 papers + top 3 patents
    └── metrics.json               # Generated benchmark metrics
```

### File Sizes (Approximate)

- `metadata.json`: ~500 bytes
- `orchestrator_result.json`: ~20-50 KB (depends on abstracts)
- `ranked_results.json`: ~5-15 KB
- `metrics.json`: ~1-3 KB

## Key Features Demonstrated

✅ **Concurrent searching** across multiple adapters  
✅ **Automatic adapter selection** based on environment  
✅ **Workspace persistence** with JSON serialization  
✅ **Deduplication** across different sources  
✅ **LLM-based scoring** for relevance ranking  
✅ **Top-N selection** (configurable, defaults to 3)  
✅ **Metrics generation** using LLM analysis  
✅ **Artifact storage** for future use  
✅ **Error handling** for adapter failures  

## What's NOT Included

The following components are **intentionally excluded** from this test:

❌ **Report Generation** - Will be implemented separately  
❌ **Benchmark Table Creation** - Requires report module  
❌ **PDF/Markdown Export** - Future feature  
❌ **Multi-topic Comparison** - Future feature  
❌ **User Interface** - CLI/API only for MVP  

## Environment Variables

### Required

```bash
OPENAI_API_KEY      # API key for LLM access
OPENAI_BASE_URL     # Base URL for OpenAI-compatible endpoint
```

### Optional

```bash
LLM_MODEL           # Model name (default: claude-haiku)
LLM_TIMEOUT         # Request timeout in seconds (default: 60)
LLM_MAX_RETRIES     # Max retries for LLM calls (default: 3)
SERPAPI_API_KEY     # For real patent searches (uses MockPatent if not set)
```

## Performance Notes

- **Total runtime:** 2-5 minutes (depends on API response times)
- **Slowest stage:** RankingEngine scoring (1-2 minutes for 20 sources)
- **API calls:** ~25-30 LLM calls total
  - 1 call per source for scoring (~20 calls)
  - 1 call for metrics generation
  - Retries on failure

## Troubleshooting Guide

### Test Won't Start

```bash
# Check environment
echo $OPENAI_API_KEY
echo $OPENAI_BASE_URL

# Test LLM connection
python3 -c "from ria.llm import LLMClient; print(LLMClient())"
```

### No Results Found

```bash
# Check adapters directly
python3 test_semantic_scholar_live.py

# Check network
curl -I https://api.semanticscholar.org/
```

### Scoring Fails

- Check LLM model supports JSON mode
- Verify API quota/rate limits
- Review logs for specific error messages
- Try reducing `MAX_RESULTS_PER_ADAPTER` in test script

### Import Errors

```bash
# Verify installation
pip install -r requirements.txt

# Check imports
python3 -c "import test_mvp_e2e"
```

## Customization

### Change Research Topic

Edit line 55 in `test_mvp_e2e.py`:

```python
TEST_TOPIC = "Your research topic here"
```

### Change Result Count

Edit line 57:

```python
MAX_RESULTS_PER_ADAPTER = 5  # Reduce for faster testing
```

### Change Top-N Selection

Edit the `select_top()` call (line 241):

```python
top_papers, top_patents = ranking_engine.select_top(
    scored_items=scored_items,
    top_n=5,  # Get top 5 instead of top 3
)
```

### Use Real Patents

The test **automatically detects** which patent adapter to use:

```bash
# For real patents: just set the API key
export SERPAPI_API_KEY="your-serpapi-key"

# Then run the test - it will automatically use SerpAPIPatentAdapter
./test_mvp_e2e.py
```

No code changes needed! The test detects `SERPAPI_API_KEY` and selects the appropriate adapter.

## Loading Saved Artifacts

After the test runs, you can load artifacts programmatically:

```python
from pathlib import Path
from ria.workspace import WorkspaceManager
from ria.metrics import MetricsGenerator
from ria.llm import LLMClient

# Initialize managers
workspace_manager = WorkspaceManager(base_dir="./test_mvp_workspace")
workspace = workspace_manager.get_workspace_by_topic(
    "XPBD soft body simulation algorithm"
)

# Load orchestrator results
orch_result = workspace_manager.load_orchestrator_result(workspace)
print(f"Loaded {len(orch_result.raw_items)} raw items")

# Load ranked results  
ranked = workspace_manager.load_artifact(workspace, "ranked_results.json")
print(f"Top papers: {len(ranked['papers'])}")
print(f"Top patents: {len(ranked['patents'])}")

# Load metrics
llm = LLMClient()
metrics_gen = MetricsGenerator(llm)
metrics = metrics_gen.load_metrics(workspace, workspace_manager)
print(f"Loaded {len(metrics)} metrics")
```

## Next Development Steps

After running this test successfully:

1. **Implement Report Generator** - Use ranked results and metrics to create comparison tables
2. **Add PDF Export** - Convert reports to PDF format
3. **Implement Caching** - Cache LLM scoring results to avoid re-scoring
4. **Add More Adapters** - IEEE Xplore, arXiv, Google Scholar, USPTO
5. **Create CLI Interface** - User-friendly command-line tool
6. **Build Web API** - REST API for remote usage
7. **Add Visualization** - Charts comparing metrics across sources

## Documentation Structure

For different needs, reference:

- **Just want to run it?** → `QUICK_START_GUIDE.md`
- **Need detailed info?** → `TEST_MVP_E2E.md`
- **Want to understand implementation?** → `test_mvp_e2e.py` (well-commented)
- **Quick reference?** → This file (`MVP_TEST_README.md`)

## Success Criteria

The test is successful if:

✅ No exceptions or errors  
✅ Papers found > 0  
✅ Patents found > 0  
✅ All 4 JSON files created in workspace  
✅ Top papers and patents displayed with scores  
✅ 5-10 metrics generated  
✅ All files have valid JSON syntax  

## Contact & Support

For issues or questions:

1. Check `TEST_MVP_E2E.md` troubleshooting section
2. Review component logs in terminal output
3. Inspect workspace JSON files for data issues
4. Test individual components using other test files in repo

## Related Test Files

Other tests in this repository:

- `test_orchestrator.py` - Tests SearchOrchestrator only
- `test_ranking.py` - Tests RankingEngine only  
- `test_metrics.py` - Tests MetricsGenerator only
- `test_workspace.py` - Tests WorkspaceManager only
- `test_semantic_scholar_live.py` - Tests SemanticScholar adapter
- `test_serpapi_patents_live.py` - Tests SerpAPI patent adapter

This end-to-end test (`test_mvp_e2e.py`) integrates all components.

---

**Created:** 2026-06-17  
**Version:** MVP 1.0  
**Status:** Ready for testing
