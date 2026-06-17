# ReportRenderer - Research Intelligence Report Generation

## Quick Start

Generate a Markdown report from your research workspace:

```python
from pathlib import Path
from ria.models import BenchmarkMetric, RankedResults
from ria.report import ReportRenderer
from ria.workspace import WorkspaceManager

# Load workspace
manager = WorkspaceManager(base_dir="./workspaces")
workspace = manager.get_workspace_by_topic("Your Research Topic")

# Load artifacts
ranked_results = RankedResults.model_validate(
    manager.load_artifact(workspace, "ranked_results.json")
)
metrics = [
    BenchmarkMetric.model_validate(m) 
    for m in manager.load_artifact(workspace, "metrics.json")
]

# Generate report
renderer = ReportRenderer()
report_path = renderer.generate(
    topic="Your Research Topic",
    ranked_results=ranked_results,
    metrics=metrics,
    workspace_dir=workspace,
)

print(f"Report saved to: {report_path}")
```

## Test the Implementation

```bash
# Test with MVP workspace
python test_report_generation.py

# Test with synthetic data (papers + patents)
python test_report_with_papers.py

# Test integration with WorkspaceManager
python test_report_integration.py

# Run all verification tests
./verify_report_implementation.sh
```

## Generated Report Structure

```markdown
# Research Intelligence Report: {topic}

**Generated:** {timestamp} UTC

---

## Executive Summary
- Overview of sources analyzed
- Key findings
- Top-ranked sources highlighted

## Top Patents
- Patent details with metadata
- Relevance scores and analysis
- Direct links to patent documents

## Top Papers
- Paper details with authors and DOI
- Relevance scores and analysis
- Direct links to papers

## Benchmark Metrics
- Metrics organized by category
- Detailed descriptions

## References
- Properly formatted citations
- Separate sections for patents and papers
```

## Output Location

Reports are saved as `report.md` in the workspace directory:

```
workspaces/
└── your-research-topic/
    ├── ranked_results.json
    ├── metrics.json
    ├── metadata.json
    └── report.md          ← Generated report
```

## Features

✓ Handles patents only, papers only, or both  
✓ Gracefully handles missing optional fields  
✓ Organizes metrics by category  
✓ Generates proper citations  
✓ UTF-8 encoded Markdown output  
✓ GitHub-flavored Markdown compatible  
✓ Clickable URLs for all sources  

## Example Reports

- `test_mvp_workspace/xpbd-soft-body-simulation-algorithm/report.md`
- `test_report_output/report.md`

See `REPORT_IMPLEMENTATION.md` for detailed documentation.
