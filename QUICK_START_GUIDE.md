# Quick Start Guide - MVP End-to-End Test

## Run the Test (3 Steps)

### 1. Set Environment Variables

```bash
export OPENAI_API_KEY="your-api-key-here"
export OPENAI_BASE_URL="https://your-api-endpoint.com/v1"
export LLM_MODEL="claude-haiku"  # Optional, defaults to claude-haiku
```

### 2. Run the Test

**Option A: Use the test runner (recommended)**
```bash
./RUN_TEST.sh
```

**Option B: Run directly**
```bash
./test_mvp_e2e.py
```

**Option C: Run with Python**
```bash
python3 test_mvp_e2e.py
```

### 3. Review Results

The test will:
- Search for "XPBD soft body simulation algorithm"
- Find and rank patents and papers
- Generate benchmark metrics
- Save all artifacts to `./test_mvp_workspace/`

## What the Test Does

```
Input: "XPBD soft body simulation algorithm"
    ↓
┌─────────────────────────────────────────────┐
│ 1. SearchOrchestrator                       │
│    - Searches SemanticScholar (papers)      │
│    - Auto-selects patent adapter:           │
│      • SerpAPI if SERPAPI_API_KEY set       │
│      • MockPatent otherwise                 │
│    - Returns ~20 raw results                │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ 2. WorkspaceManager                         │
│    - Creates workspace directory            │
│    - Saves orchestrator_result.json         │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ 3. RankingEngine                            │
│    - Deduplicates sources                   │
│    - Scores each source (LLM-based)         │
│    - Selects top 3 papers + top 3 patents   │
│    - Saves ranked_results.json              │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│ 4. MetricsGenerator                         │
│    - Analyzes top sources                   │
│    - Generates 5-10 benchmark metrics       │
│    - Saves metrics.json                     │
└─────────────────────────────────────────────┘
    ↓
Output:
  • Number of patents found
  • Number of papers found
  • Top 3 patents (with scores)
  • Top 3 papers (with scores)
  • Generated metrics
  • All artifacts saved to workspace
```

## Example Output

```
================================================================================
Research Intelligence Assistant - End-to-End MVP Test
================================================================================

Test Configuration:
  Topic: XPBD soft body simulation algorithm
  Workspace: ./test_mvp_workspace
  Max results per adapter: 10

...

Summary Statistics
--------------------------------------------------------------------------------
Number of patents found: 10
Number of papers found: 10
Total raw sources: 20
After deduplication: 18

Top 3 Patents (Ranked by Relevance)
--------------------------------------------------------------------------------
1. Extended Position Based Dynamics Framework
   Score: 0.950
   Patent Number: US123456789
   Assignee: Tech Corp
   ...

Top 3 Papers (Ranked by Relevance)
--------------------------------------------------------------------------------
1. XPBD: Position-Based Simulation of Compliant Constraint Dynamics
   Score: 0.985
   Author(s): John Doe, Jane Smith
   DOI: 10.1234/example
   ...

Generated Benchmark Metrics
--------------------------------------------------------------------------------
1. Simulation Accuracy
   Category: performance
   Description: Measures the accuracy of soft body deformation...

2. Computational Efficiency
   Category: efficiency
   Description: CPU/GPU time per simulation step...

...
```

## Workspace Files

After running, check the workspace:

```
./test_mvp_workspace/xpbd-soft-body-simulation-algorithm/
├── metadata.json              # Workspace metadata
├── orchestrator_result.json   # Raw search results (all sources)
├── ranked_results.json        # Top 3 papers + top 3 patents
└── metrics.json               # Generated benchmark metrics
```

## Troubleshooting

**Problem**: `Connection refused` or API errors  
**Solution**: Check `OPENAI_API_KEY` and `OPENAI_BASE_URL` are set correctly

**Problem**: No papers found  
**Solution**: Check internet connection, Semantic Scholar may be rate-limited

**Problem**: Scoring is slow  
**Solution**: Expected behavior - LLM scores each source individually (~1-2 min)

**Problem**: Generic/fake patents  
**Solution**: The test auto-detects patent adapter. Set `SERPAPI_API_KEY` for real patents. Without it, MockPatent adapter generates synthetic data for testing.

## For More Details

- See `TEST_MVP_E2E.md` for complete documentation
- Check test implementation: `test_mvp_e2e.py`
- Review workspace artifacts after running

## Next Steps

1. Run the test to verify all components work
2. Inspect the workspace JSON files
3. Try different research topics by editing `TEST_TOPIC` in `test_mvp_e2e.py`
4. Integrate components into your application
5. Implement report generation using the artifacts
