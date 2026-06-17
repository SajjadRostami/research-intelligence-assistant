# MetricsGenerator Integration Guide

## Pipeline Integration

The MetricsGenerator fits into the overall research pipeline after the ranking stage:

```
┌─────────────────────────────────────────────────────────────────┐
│                     Research Pipeline                            │
└─────────────────────────────────────────────────────────────────┘

1. User Input
   └─> Research Topic
       │
       ▼
2. Search Orchestration (orchestrator.py)
   └─> Queries multiple adapters
       └─> Returns OrchestratorResult (raw_items)
       │
       ▼
3. Ranking Engine (ranking.py)
   └─> Deduplicate sources
   └─> Score for relevance
   └─> Select top 3 papers + top 3 patents
       └─> Returns RankedResults
       │
       ▼
4. MetricsGenerator (metrics.py) ⭐ NEW - Task 7.1
   └─> Analyze topic and sources
   └─> Generate 5-10 benchmark metrics
       └─> Returns list[BenchmarkMetric]
       │
       ▼
5. User Validation (FUTURE - Task 7.2)
   └─> User reviews metrics
   └─> Approves/edits/removes metrics
       └─> Returns ApprovedState
       │
       ▼
6. Benchmark Scoring (FUTURE - Task 8)
   └─> Score each source against each metric
       └─> Returns BenchmarkScores
       │
       ▼
7. Report Generation (FUTURE - Task 9)
   └─> Generate formatted report
       └─> Returns final report document
```

## Data Flow

```
┌──────────────────┐
│  Research Topic  │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────┐
│  RankedResults           │
│  - papers (top 3)        │
│  - patents (top 3)       │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  MetricsGenerator        │
│  .generate()             │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  list[BenchmarkMetric]   │
│  - name                  │
│  - description           │
│  - category              │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  WorkspaceManager        │
│  .save_artifact()        │
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  metrics.json            │
│  (persisted)             │
└──────────────────────────┘
```

## Example Usage in Pipeline

### Standalone Usage (as in test_metrics.py)

```python
from ria.llm import LLMClient
from ria.metrics import MetricsGenerator
from ria.workspace import WorkspaceManager
from ria.models import RankedResults

# Initialize
llm = LLMClient()
generator = MetricsGenerator(llm)
workspace_mgr = WorkspaceManager()

# Load ranked results
workspace = workspace_mgr.get_workspace_by_topic(topic)
ranked_data = workspace_mgr.load_artifact(workspace, "ranked_results.json")
ranked = RankedResults.model_validate(ranked_data)

# Generate metrics
metrics = generator.generate(
    topic=topic,
    papers=ranked.papers,
    patents=ranked.patents,
)

# Save metrics
generator.save_metrics(workspace, metrics, workspace_mgr)

print(f"Generated {len(metrics)} metrics:")
for metric in metrics:
    print(f"  - {metric.name} ({metric.category})")
```

### Integrated Pipeline Usage (future)

```python
from ria.orchestrator import SearchOrchestrator
from ria.ranking import RankingEngine
from ria.metrics import MetricsGenerator
from ria.workspace import WorkspaceManager
from ria.llm import LLMClient

def run_full_pipeline(topic: str):
    # Setup
    llm = LLMClient()
    workspace_mgr = WorkspaceManager()
    workspace = workspace_mgr.create(topic)
    
    # Stage 1: Search
    orchestrator = SearchOrchestrator()
    orch_result = orchestrator.search(topic)
    workspace_mgr.save_orchestrator_result(workspace, orch_result)
    
    # Stage 2: Rank
    ranking = RankingEngine(llm)
    deduplicated = ranking.deduplicate(orch_result.raw_items)
    scored = ranking.score(deduplicated, topic)
    top_papers, top_patents = ranking.select_top(scored)
    
    ranked_results = RankedResults(papers=top_papers, patents=top_patents)
    workspace_mgr.save_artifact(workspace, "ranked_results.json",
                                ranked_results.model_dump())
    
    # Stage 3: Generate Metrics ⭐ NEW
    metrics_gen = MetricsGenerator(llm)
    metrics = metrics_gen.generate(topic, top_papers, top_patents)
    metrics_gen.save_metrics(workspace, metrics, workspace_mgr)
    
    # Stage 4: User Validation (TODO)
    # approved = validate_with_user(ranked_results, metrics)
    
    # Stage 5: Benchmark Scoring (TODO)
    # scores = score_benchmark(approved)
    
    # Stage 6: Report Generation (TODO)
    # report = generate_report(scores)
    
    return metrics
```

## Workspace Structure

After running the MetricsGenerator, the workspace directory structure:

```
workspaces/
└── extended-position-based-dynamics-xpbd-for-physics-simulation/
    ├── metadata.json              # Workspace metadata
    ├── orchestrator_result.json   # Raw search results
    ├── ranked_results.json        # Top 3 papers + 3 patents
    └── metrics.json               # Generated benchmark metrics ⭐ NEW
```

### metrics.json Format

```json
[
  {
    "name": "Simulation Stability",
    "description": "Measures how well the simulation maintains...",
    "category": "performance"
  },
  {
    "name": "Constraint Accuracy",
    "description": "Evaluates the precision of constraint satisfaction...",
    "category": "accuracy"
  },
  ...
]
```

## Dependencies

### Direct Dependencies
- `ria.llm.LLMClient` - For LLM interaction
- `ria.models.BenchmarkMetric` - Data model
- `ria.models.ScoredSourceItem` - Input data
- `ria.workspace.WorkspaceManager` - Persistence

### Indirect Dependencies
- OpenAI-compatible LLM endpoint
- Environment variables (OPENAI_API_KEY, OPENAI_BASE_URL)

## Error Handling

The MetricsGenerator handles several error cases:

1. **LLM API Failures**: Retries via LLMClient's built-in retry logic
2. **Invalid Response Format**: Raises ValueError with details
3. **Schema Validation Errors**: Pydantic validates 5-10 metrics constraint
4. **Empty Results**: Raises ValueError if no metrics generated

Example:
```python
try:
    metrics = generator.generate(topic, papers, patents)
except ValueError as e:
    print(f"Metric generation failed: {e}")
    # Handle error (retry, use defaults, notify user, etc.)
```

## Performance Considerations

- **LLM Call**: Single LLM call per generation (10-30 seconds typical)
- **Token Usage**: Approximately 1,000-2,000 tokens per request
- **Caching**: Results are cached in metrics.json for reuse
- **Regeneration**: Can regenerate metrics by calling generate() again

## Testing Strategy

### Unit Tests (future)
```python
def test_generate_metrics():
    # Test with mock LLM responses
    # Verify 5-10 metrics returned
    # Verify all fields populated
    
def test_save_load_metrics():
    # Test round-trip serialization
    # Verify data integrity
```

### Integration Tests
- `test_metrics.py` - Full end-to-end test with sample data
- Tests actual LLM integration
- Verifies workspace persistence

## Future Enhancements

1. **Metric Templates**: Pre-defined metric templates per research domain
2. **User Customization**: Allow users to add/edit metrics manually
3. **Metric Validation**: Validate metric applicability to sources
4. **Metric Scoring**: Pre-score metrics for importance/relevance
5. **Batch Generation**: Generate metrics for multiple topics at once

## Troubleshooting

### Issue: Metrics not relevant to topic
- Check that papers/patents have good relevance_explanation fields
- Try a more capable LLM model
- Adjust temperature (currently 0.7)

### Issue: Wrong number of metrics
- Pydantic enforces 5-10 via schema
- LLM will retry if constraint violated
- Check LLM logs for validation errors

### Issue: Duplicate metrics
- LLM should generate unique metrics
- If duplicates occur, manually deduplicate or regenerate

## API Summary

```python
class MetricsGenerator:
    def __init__(self, llm_client: LLMClient)
    
    def generate(
        topic: str,
        papers: list[ScoredSourceItem],
        patents: list[ScoredSourceItem],
    ) -> list[BenchmarkMetric]
    
    def save_metrics(
        workspace: Path,
        metrics: list[BenchmarkMetric],
        workspace_manager: WorkspaceManager,
    ) -> Path
    
    def load_metrics(
        workspace: Path,
        workspace_manager: WorkspaceManager,
    ) -> list[BenchmarkMetric]
```

## Related Components

- **orchestrator.py**: Generates raw search results
- **ranking.py**: Produces RankedResults input for MetricsGenerator
- **workspace.py**: Provides persistence layer
- **llm.py**: Provides LLM interface
- **models.py**: Defines all data structures
