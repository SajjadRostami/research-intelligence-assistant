# End-to-End MVP Test

This document explains how to run the complete end-to-end MVP test for the Research Intelligence Assistant.

## Overview

The test runs the complete pipeline with the input query: **"XPBD soft body simulation algorithm"**

### Pipeline Stages

1. **SearchOrchestrator** - Searches for patents and papers across multiple adapters
2. **WorkspaceManager** - Creates workspace and persists all artifacts
3. **RankingEngine** - Deduplicates, scores, and ranks sources by relevance
4. **MetricsGenerator** - Generates benchmark metrics using LLM analysis

### Test Outputs

The test will display:
- Number of patents found
- Number of papers found
- Top 3 patents (ranked by relevance score)
- Top 3 papers (ranked by relevance score)
- Generated benchmark metrics (5-10 metrics)

All artifacts are saved to the workspace for future use.

## Prerequisites

1. **Python environment** with dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables** configured:
   - `OPENAI_API_KEY` - API key for LLM access
   - `OPENAI_BASE_URL` - Base URL for OpenAI-compatible API endpoint
   - `LLM_MODEL` - (Optional) Model name, defaults to `claude-haiku`

   Example `.env` file:
   ```bash
   OPENAI_API_KEY=your-api-key-here
   OPENAI_BASE_URL=https://your-api-endpoint.com/v1
   LLM_MODEL=claude-haiku
   ```

3. **Optional: SerpAPI key** for real patent searches:
   - The test **automatically detects** if `SERPAPI_API_KEY` is set
   - If set: uses `SerpAPIPatentAdapter` (real patent data from SerpAPI)
   - If not set: uses `MockPatentAdapter` (synthetic patent data for testing)
   - To enable real patents: `export SERPAPI_API_KEY=your-serpapi-key`

## Running the Test

### Method 1: Direct Execution

```bash
./test_mvp_e2e.py
```

### Method 2: Python Module

```bash
python test_mvp_e2e.py
```

### Method 3: With Python 3 Explicitly

```bash
python3 test_mvp_e2e.py
```

## Expected Output

The test will print structured output showing:

1. **Initialization** - Components being initialized
2. **Search Results** - Raw counts of papers and patents found
3. **Workspace Creation** - Workspace path and saved files
4. **Ranking Progress** - Deduplication, scoring, and selection
5. **Metrics Generation** - Generated benchmark metrics
6. **Final Results** - Formatted display of top sources and metrics
7. **Artifacts Summary** - List of saved files in workspace

### Sample Output Structure

```
================================================================================
Research Intelligence Assistant - End-to-End MVP Test
================================================================================

Test Configuration:
  Topic: XPBD soft body simulation algorithm
  Workspace: ./test_mvp_workspace
  Max results per adapter: 10

...

================================================================================
Step 6: Final Results
================================================================================

Summary Statistics
--------------------------------------------------------------------------------
Research Topic: XPBD soft body simulation algorithm
Workspace: ./test_mvp_workspace/xpbd-soft-body-simulation-algorithm

Number of patents found: 10
Number of papers found: 10
Total raw sources: 20
After deduplication: 18

Top 3 Patents (Ranked by Relevance)
--------------------------------------------------------------------------------
1. [Patent Title]
   Score: 0.950
   Patent Number: US1234567
   ...

Top 3 Papers (Ranked by Relevance)
--------------------------------------------------------------------------------
1. [Paper Title]
   Score: 0.980
   Author(s): [Authors]
   ...

Generated Benchmark Metrics
--------------------------------------------------------------------------------
Total metrics: 7

1. Simulation Accuracy
   Category: performance
   Description: ...

...
```

## Workspace Artifacts

After running the test, the workspace directory will contain:

```
./test_mvp_workspace/xpbd-soft-body-simulation-algorithm/
├── metadata.json              # Workspace metadata and stats
├── orchestrator_result.json   # Raw search results from all adapters
├── ranked_results.json        # Top 3 papers and top 3 patents with scores
└── metrics.json               # Generated benchmark metrics
```

### Loading Artifacts

You can load saved artifacts programmatically:

```python
from pathlib import Path
from ria.workspace import WorkspaceManager
from ria.metrics import MetricsGenerator
from ria.llm import LLMClient

workspace_manager = WorkspaceManager(base_dir="./test_mvp_workspace")
workspace = Path("./test_mvp_workspace/xpbd-soft-body-simulation-algorithm")

# Load orchestrator results
orchestrator_result = workspace_manager.load_orchestrator_result(workspace)

# Load ranked results
ranked_results = workspace_manager.load_artifact(workspace, "ranked_results.json")

# Load metrics
llm_client = LLMClient()
metrics_generator = MetricsGenerator(llm_client)
metrics = metrics_generator.load_metrics(workspace, workspace_manager)
```

## Cleanup

The test automatically cleans up the workspace before each run. To manually remove test artifacts:

```bash
rm -rf ./test_mvp_workspace
```

## Troubleshooting

### Issue: LLM API Connection Error

**Symptom**: `Connection refused` or `Invalid API key` errors

**Solution**: Check your environment variables:
```bash
echo $OPENAI_API_KEY
echo $OPENAI_BASE_URL
```

### Issue: No Papers Found

**Symptom**: `Number of papers found: 0`

**Solution**: 
- Check internet connectivity
- Semantic Scholar API may be rate-limited (wait a few minutes)
- Try a different test topic

### Issue: Mock Patents Only

**Symptom**: Patents have generic titles like "System and Method for..." or the test output shows "MockPatentAdapter (synthetic patents)"

**Explanation**: The test automatically uses `MockPatentAdapter` when `SERPAPI_API_KEY` is not found in the environment. This generates synthetic patents for testing.

**Solution**: To get real patents:
1. Sign up for SerpAPI: https://serpapi.com/
2. Set environment variable: `export SERPAPI_API_KEY=your-key`
3. Re-run the test - it will automatically use `SerpAPIPatentAdapter`

### Issue: Scoring Takes Too Long

**Symptom**: Step 4.2 (Relevance Scoring) is slow

**Explanation**: The ranking engine scores each source individually using LLM calls. With 20 sources, this can take 1-2 minutes.

**Solution**: 
- Reduce `MAX_RESULTS_PER_ADAPTER` in the test script (line 55)
- Use a faster model by setting `LLM_MODEL` environment variable
- This is expected behavior for the MVP

## Next Steps

After the test completes successfully:

1. **Inspect the workspace** - Review the JSON artifacts
2. **Modify the test** - Try different research topics
3. **Integrate components** - Use the workspace artifacts in your application
4. **Generate reports** - Use the ranked results and metrics to create comparison tables

The test demonstrates all core functionality except report generation, which will be implemented in a separate module.
