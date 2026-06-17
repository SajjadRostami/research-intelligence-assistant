# MetricsGenerator - Quick Start Guide

## 30-Second Start

```bash
# 1. Set environment
export OPENAI_API_KEY="your-key"
export OPENAI_BASE_URL="https://endpoint/v1"
export LLM_MODEL="claude-haiku"

# 2. Run test
python test_metrics.py

# 3. Check output
cat workspaces/*/metrics.json
```

## 5-Minute Integration

```python
from ria.llm import LLMClient
from ria.metrics import MetricsGenerator
from ria.workspace import WorkspaceManager
from ria.models import RankedResults

# Initialize
llm = LLMClient()
generator = MetricsGenerator(llm)
workspace_mgr = WorkspaceManager()

# Load your ranked results
workspace = workspace_mgr.get_workspace_by_topic("Your Topic")
ranked_data = workspace_mgr.load_artifact(workspace, "ranked_results.json")
ranked = RankedResults.model_validate(ranked_data)

# Generate metrics
metrics = generator.generate(
    topic="Your Topic",
    papers=ranked.papers,
    patents=ranked.patents,
)

# Save
generator.save_metrics(workspace, metrics, workspace_mgr)

# Use
for metric in metrics:
    print(f"{metric.name} ({metric.category}): {metric.description}")
```

## What You Get

```json
[
  {
    "name": "Simulation Stability",
    "description": "Measures ability to maintain stable physics...",
    "category": "performance"
  },
  {
    "name": "Constraint Accuracy", 
    "description": "Evaluates precision of constraint satisfaction...",
    "category": "accuracy"
  }
]
```

## Files

- **Implementation**: `ria/metrics.py`
- **Test**: `test_metrics.py`
- **Output**: `workspaces/[topic]/metrics.json`
- **Docs**: `TEST_METRICS_README.md`

## Common Issues

**"OPENAI_API_KEY must be set"**
→ Set the environment variable

**LLM timeout**
→ `export LLM_TIMEOUT=120`

**Wrong model**
→ Check `LLM_MODEL` is valid for your endpoint

## Next Steps

1. Run test to verify setup
2. Integrate into your pipeline after ranking
3. Use metrics for benchmark scoring (Task 8)
4. Generate final report (Task 9)

## More Info

- Full guide: `TEST_METRICS_README.md`
- Integration: `METRICS_INTEGRATION.md`
- Summary: `TASK_7_1_SUMMARY.md`
