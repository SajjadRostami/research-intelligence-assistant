# Ranking Engine Test Guide

This guide explains how to test the RankingEngine implementation (Task 6.1).

## Overview

The RankingEngine provides three core operations:

1. **Deduplication**: Removes duplicate sources by title, DOI, and patent number
2. **Scoring**: Uses LLM to score each source's relevance to a research topic (0.0 to 1.0)
3. **Selection**: Selects the top 3 papers and top 3 patents by score

## Prerequisites

Make sure your environment has the required API credentials configured:

```bash
export OPENAI_API_KEY=your-api-key
export OPENAI_BASE_URL=https://api.openai.com/v1
```

Or for OpenRouter (Claude models):
```bash
export OPENAI_API_KEY=your-openrouter-key
export OPENAI_BASE_URL=https://openrouter.ai/api/v1
export LLM_MODEL=anthropic/claude-3.5-sonnet
```

## Test Scripts

### Option 1: Standalone Test (Recommended for Quick Testing)

Uses mock data - doesn't require an existing workspace.

```bash
python test_ranking_standalone.py
```

**What it does:**
- Creates 9 mock source items (4 papers, 4 patents, plus 2 duplicates)
- Demonstrates deduplication (removes 2 duplicates)
- Scores each item using the LLM
- Selects and displays the top 3 papers and top 3 patents

**Expected output:**
```
================================================================================
Ranking Engine Standalone Test
================================================================================
Research Topic: XPBD soft body simulation algorithm

Creating mock data...
Created 9 raw items

Initializing LLM client and ranking engine...
Using model: claude-haiku

Step 1: Deduplicating...
  Before: 9 items
  After:  7 items
  Removed: 2 duplicates

Step 2: Scoring items for relevance...
  (This may take a moment as each item is scored by the LLM)
  Scored 7 items

Step 3: Selecting top results...
  Selected 4 papers
  Selected 3 patents

================================================================================
TOP PAPERS
================================================================================

[1] Score: 0.95
    Title: XPBD: Extended Position Based Dynamics for Fast Simulation
    Type: paper
    Date: 2023-08-20
    Author: Alice Johnson, Bob Williams
    DOI: 10.1234/example.2023.002
    Reasoning: Directly addresses XPBD algorithm for soft body simulation...

[2] Score: 0.85
    Title: Position Based Dynamics for Soft Body Simulation
    ...

[3] Score: 0.60
    Title: Physics-Based Animation of Deformable Objects
    ...

================================================================================
TOP PATENTS
================================================================================

[1] Score: 0.75
    Title: System and Method for Real-Time Soft Body Deformation
    ...
```

### Option 2: Workspace Test (For Integration Testing)

Uses actual workspace data from the search orchestrator.

```bash
python test_ranking.py
```

**Requirements:**
- A workspace must exist in `./workspaces/` with `orchestrator_result.json`
- You can create a workspace by running the search orchestrator first

**What it does:**
- Loads raw items from an existing workspace
- Deduplicates the real search results
- Scores them using the LLM
- Saves the ranked results back to the workspace as `ranked_results.json`

## Implementation Details

### Deduplication Logic

The `deduplicate()` method removes duplicates using three criteria:

1. **Normalized title matching**: Case-insensitive, whitespace-normalized
   - "XPBD  Algorithm" matches "xpbd algorithm"

2. **DOI matching**: Case-insensitive, whitespace-trimmed
   - Only for items with DOI field populated

3. **Patent number matching**: Case-insensitive, whitespace-trimmed
   - Only for items with patent_number field populated

First occurrence is kept when duplicates are found.

### Scoring Logic

The `score()` method uses the LLM to evaluate relevance:

- **Input**: Research topic + source metadata (title, abstract, date, author)
- **Output**: Score (0.0-1.0) + reasoning
- **Temperature**: 0.3 (lower for consistent scoring)
- **Scoring scale**:
  - 1.0 = Highly relevant, directly addresses the topic
  - 0.5 = Moderately relevant, tangentially related
  - 0.0 = Not relevant at all

### Selection Logic

The `select_top()` method:

1. Separates items by source type (paper vs patent)
2. Sorts each list by relevance_score descending
3. Returns the top N from each list (default: 3)

## Troubleshooting

### "OPENAI_API_KEY must be set"
Set the required environment variables before running the test.

### "Workspace not found"
For `test_ranking.py`, make sure you've run the search orchestrator first to create a workspace, or use the standalone test instead.

### Scoring failures
If individual items fail to score, they're assigned a score of 0.0 and a warning is printed. The test continues with remaining items.

## Next Steps

After Task 6.1 is complete, the following features will be added:

- **Task 6.2**: Benchmark metric generation
- **Task 6.3**: Report generation with scored tables

The RankingEngine is now ready to be integrated into the main research pipeline.
