# MetricsGenerator Test Guide

## Overview

This guide explains how to test the `MetricsGenerator` implementation (Task 7.1).

## What Was Implemented

### 1. MetricsGenerator Class (`ria/metrics.py`)

The MetricsGenerator creates 5-10 relevant benchmark metrics for a research topic using:

- **Input**: Research topic, top-ranked papers, and top-ranked patents
- **Processing**: Uses LLMClient to analyze sources and generate metrics
- **Output**: List of BenchmarkMetric objects with name, description, and category
- **Persistence**: Saves metrics to `metrics.json` via WorkspaceManager

### 2. Features

✓ Generates 5-10 metrics relevant to the research topic  
✓ Each metric includes:
  - Name (concise identifier)
  - Description (detailed explanation)
  - Category (performance, accuracy, usability, hardware, efficiency, etc.)

✓ Uses existing LLMClient for generation  
✓ Saves results to workspace using WorkspaceManager  
✓ Loads saved metrics from workspace  

### 3. Test Script (`test_metrics.py`)

Comprehensive test that:
- Creates sample ranked results for "XPBD physics simulation"
- Generates metrics using MetricsGenerator
- Saves metrics to workspace
- Prints all generated metrics with details

## Prerequisites

Ensure you have:

1. **Python environment** with dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables** configured:
   ```bash
   export OPENAI_API_KEY="your-api-key"
   export OPENAI_BASE_URL="https://your-llm-endpoint.com/v1"
   export LLM_MODEL="claude-haiku"  # or your preferred model
   ```

   Optional environment variables:
   ```bash
   export LLM_TIMEOUT=60          # Request timeout in seconds
   export LLM_MAX_RETRIES=3       # Maximum retry attempts
   ```

## How to Run the Test

### Quick Start

```bash
python test_metrics.py
```

### What the Test Does

1. **Initialization** - Creates LLM client, workspace manager, and metrics generator
2. **Sample Data** - Generates sample ranked results (3 papers + 3 patents on XPBD)
3. **Workspace Creation** - Creates a workspace for the research topic
4. **Metric Generation** - Calls the LLM to generate 5-10 relevant metrics
5. **Persistence** - Saves metrics to `workspaces/[topic-slug]/metrics.json`
6. **Output** - Prints all metrics with names, descriptions, and categories

### Expected Output

```
================================================================================
MetricsGenerator Test Script
================================================================================

1. Initializing components...
   ✓ LLM client initialized
   ✓ Workspace manager initialized
   ✓ Metrics generator initialized

2. Loading ranked results...
   ✓ Topic: Extended Position Based Dynamics (XPBD) for physics simulation
   ✓ Papers: 3
   ✓ Patents: 3

3. Creating workspace...
   ✓ Workspace created at: workspaces/extended-position-based-dynamics-xpbd-for-physics-simulation

4. Saving ranked results to workspace...
   ✓ Ranked results saved

5. Generating benchmark metrics...
   (This may take 10-30 seconds depending on LLM response time)
   ✓ Generated 7 metrics

6. Saving metrics to workspace...
   ✓ Metrics saved to: workspaces/.../metrics.json

7. Generated Metrics:
================================================================================

Metric 1: Simulation Stability
--------------------------------------------------------------------------------
Description: Measures how well the simulation maintains stability across different timesteps...
Category: performance

Metric 2: Constraint Accuracy
--------------------------------------------------------------------------------
Description: Evaluates the precision of constraint satisfaction in the physics solver...
Category: accuracy

[... more metrics ...]

================================================================================
Test completed successfully!

Next steps:
  - Metrics are saved in workspace/metrics.json
  - Use these metrics for benchmark scoring in the next phase
  - Implement report generation to visualize results
================================================================================
```

## Testing with Real Data

To test with actual ranked results from the pipeline:

```python
from pathlib import Path
from ria.workspace import WorkspaceManager
from ria.models import RankedResults

# Load existing workspace
workspace_manager = WorkspaceManager()
workspace = Path("workspaces/your-topic-slug")

# Load ranked results
ranked_data = workspace_manager.load_artifact(workspace, "ranked_results.json")
ranked_results = RankedResults.model_validate(ranked_data)

# Generate metrics
from ria.llm import LLMClient
from ria.metrics import MetricsGenerator

llm = LLMClient()
generator = MetricsGenerator(llm)

metrics = generator.generate(
    topic="Your research topic",
    papers=ranked_results.papers,
    patents=ranked_results.patents,
)

# Save metrics
generator.save_metrics(workspace, metrics, workspace_manager)
```

## Troubleshooting

### Issue: "OPENAI_API_KEY must be set"

**Solution**: Set the required environment variables:
```bash
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://your-endpoint.com/v1"
```

### Issue: LLM timeout or API errors

**Solution**: Increase timeout or retries:
```bash
export LLM_TIMEOUT=120
export LLM_MAX_RETRIES=5
```

### Issue: Generated metrics are not relevant

**Solution**: The LLM analyzes the topic and sources. Try:
- Ensuring papers and patents have good `relevance_explanation` fields
- Using a more capable model (e.g., GPT-4 instead of GPT-3.5)
- Adjusting temperature in `metrics.py` (currently 0.7)

### Issue: Less than 5 or more than 10 metrics generated

**Solution**: The Pydantic schema enforces 5-10 metrics via `min_length` and `max_length`. If the LLM violates this, it will retry. If issues persist, check the LLM response format.

## File Locations

- **Implementation**: `ria/metrics.py`
- **Test Script**: `test_metrics.py`
- **Models**: `ria/models.py` (BenchmarkMetric defined here)
- **Output**: `workspaces/[topic-slug]/metrics.json`

## Next Steps

After Task 7.1 is complete:

1. **Task 7.2**: Implement user validation UI for metrics
2. **Task 8**: Implement report generation using approved metrics
3. **Integration**: Connect metrics generation to the main pipeline

## API Reference

### MetricsGenerator

```python
class MetricsGenerator:
    def __init__(self, llm_client: LLMClient)
    
    def generate(
        self,
        topic: str,
        papers: list[ScoredSourceItem],
        patents: list[ScoredSourceItem],
    ) -> list[BenchmarkMetric]
    
    def save_metrics(
        self,
        workspace: Path,
        metrics: list[BenchmarkMetric],
        workspace_manager: WorkspaceManager,
    ) -> Path
    
    def load_metrics(
        self,
        workspace: Path,
        workspace_manager: WorkspaceManager,
    ) -> list[BenchmarkMetric]
```

### BenchmarkMetric

```python
class BenchmarkMetric(BaseModel):
    name: str
    description: str | None = None
```

Note: The description field contains both the metric description and category in the format:
`"{description} (Category: {category})"`
