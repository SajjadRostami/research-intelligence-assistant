# Design Document: Research Intelligence and Benchmarking Assistant

## Overview

The Research Intelligence and Benchmarking Assistant is a Python CLI application that automates the production of structured research reports from a user-supplied topic. The system orchestrates searches against multiple academic and patent sources, ranks and deduplicates results, proposes benchmark metrics via an LLM, walks the user through an interactive validation step, and then generates a local Markdown report.

**Key design goals:**
- Deterministic, reproducible outputs — every intermediate artefact is persisted as JSON so runs can be inspected or replayed.
- Strict separation of concerns — search adapters, ranking logic, LLM integration, report generation, and CLI presentation are all independent modules.
- Resilience — each external source is treated as independently failable; the pipeline continues with the results it has.
- Extensibility — adding a new search source or export format requires only a new adapter/renderer implementing a known interface.

**Technology stack:**
- Python 3.11+
- `openai` SDK (OpenAI-compatible, targeting Claude models via the `claude-opus` alias)
- `python-dotenv` for configuration
- `aiohttp` / `httpx` for async HTTP calls to search APIs
- `pydantic` v2 for schema validation and serialisation
- `rich` for CLI presentation (tables, progress spinners)
- `hypothesis` for property-based testing

---

## Architecture

The system follows a **pipeline architecture** with five sequential stages, separated by well-defined data contracts (Pydantic models serialised to JSON):

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLI Entry Point                             │
│                         main.py / cli.py                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  topic: str
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 1 – Search Orchestrator                                      │
│  • Dispatches queries to patent + academic adapters (async)         │
│  • Back-off / retry logic per adapter                               │
│  • Persists raw results → workspace/raw_results.json                │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  List[RawSourceItem]
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 2 – Ranking & Deduplication                                  │
│  • Dedup by title / URL / DOI / patent number                       │
│  • LLM-assisted relevance scoring (0.0–1.0)                         │
│  • Selects top 3 papers + top 3 patents                             │
│  • Persists ranked results → workspace/ranked_results.json          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  RankedResults
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 3 – Benchmark Metric Generation                              │
│  • LLM generates metrics from topic + source summaries              │
│  • Persists proposals → workspace/metrics.json                      │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  List[BenchmarkMetric]
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 4 – Validation Step (Interactive CLI)                        │
│  • Displays sources + metrics; accepts edits                        │
│  • Awaits explicit "confirm" command                                 │
│  • Persists approved state → workspace/approved_state.json          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │  ApprovedState
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 5 – Report Generation                                        │
│  • Scores each source against each metric via LLM                   │
│  • Renders Executive Summary, Benchmark Table, References           │
│  • Saves → workspace/report_<slug>_YYYY_MM_DD.md                    │
│  • Updates workspace history → ~/.ria/history.json                  │
└─────────────────────────────────────────────────────────────────────┘
```

### Directory Layout

```
research-intelligence-assistant/
├── main.py                   # CLI entry point
├── ria/
│   ├── __init__.py
│   ├── cli.py                # Rich-based prompts and menus
│   ├── orchestrator.py       # Stage 1: search orchestration
│   ├── ranking.py            # Stage 2: dedup + scoring
│   ├── metrics.py            # Stage 3: benchmark metric generation
│   ├── validation.py         # Stage 4: interactive validation loop
│   ├── report.py             # Stage 5: report renderer
│   ├── workspace.py          # Workspace + history management
│   ├── models.py             # All Pydantic data models
│   ├── llm.py                # LLM client wrapper
│   └── adapters/
│       ├── base.py           # Abstract SearchAdapter
│       ├── google_patents.py
│       ├── semantic_scholar.py
│       ├── openalex.py
│       ├── arxiv.py
│       ├── pubmed.py
│       └── crossref.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── property/
├── .env.example
├── pyproject.toml
└── requirements.txt
```

---

## Components and Interfaces

### SearchAdapter (Abstract Base)

```python
from abc import ABC, abstractmethod
from ria.models import RawSourceItem, SearchQuery

class SearchAdapter(ABC):
    source_type: str  # "patent" | "paper"

    @abstractmethod
    async def search(self, query: SearchQuery) -> list[RawSourceItem]:
        """Submit query, return raw results. Never raises — returns [] on error."""
        ...
```

Concrete adapters: `GooglePatentsAdapter`, `SemanticScholarAdapter`, `OpenAlexAdapter`, `ArxivAdapter`, `PubMedAdapter`, `CrossrefAdapter`.

Each adapter is responsible for:
1. Building the source-specific query URL/parameters from a `SearchQuery`.
2. Applying back-off/retry on rate-limit (HTTP 429) or transient errors.
3. Logging failures via the standard `logging` module.
4. Returning partial results rather than raising.

### SearchOrchestrator

```python
class SearchOrchestrator:
    def __init__(self, patent_adapter: SearchAdapter, paper_adapters: list[SearchAdapter]): ...

    async def run(self, topic: str) -> OrchestratorResult:
        """Dispatch parallel searches, collect results, persist raw_results.json."""
        ...
```

Dispatches the patent adapter and all paper adapters concurrently using `asyncio.gather`.

### RankingEngine

```python
class RankingEngine:
    def __init__(self, llm_client: LLMClient): ...

    def deduplicate(self, items: list[RawSourceItem]) -> list[RawSourceItem]: ...
    def score(self, items: list[RawSourceItem], topic: str) -> list[ScoredSourceItem]: ...
    def select_top(self, scored: list[ScoredSourceItem]) -> RankedResults: ...
```

Deduplication compares normalised titles, URLs, DOIs, and patent numbers (lowercased, stripped). Scoring calls the LLM with a structured prompt asking for a JSON `{"relevance_score": float, "explanation": str, "confidence_level": str}` for each item.

### MetricsGenerator

```python
class MetricsGenerator:
    def __init__(self, llm_client: LLMClient): ...

    def generate(self, topic: str, sources: list[ScoredSourceItem]) -> list[BenchmarkMetric]: ...
```

Sends a single prompt to the LLM with the topic and source summaries, receiving a JSON list of metric names.

### ValidationController

Drives the interactive CLI loop. Accepts commands: `approve` / `confirm`, `remove <type> <n>`, `add <type> <url>`, `edit metric <n>`, `remove metric <n>`, `add metric`. Returns an `ApprovedState` on confirmation.

### ReportRenderer

```python
class ReportRenderer:
    def render(self, state: ApprovedState, scores: BenchmarkScores) -> str: ...
```

Pure function: given approved state and coverage scores, produces the full Markdown string. Scoring (`CoverageValue` assignment per cell) is done via a batch LLM call before rendering.

### LLMClient

```python
class LLMClient:
    def __init__(self, model: str = "claude-opus"): ...

    def chat(self, messages: list[dict], *, response_format: str = "text") -> str: ...
    def chat_json(self, messages: list[dict]) -> dict: ...
```

Thin wrapper around the `openai.OpenAI` client. `chat_json` enforces JSON mode and performs schema validation on the response.

### WorkspaceManager

```python
class WorkspaceManager:
    def create(self, topic: str) -> Path: ...
    def save(self, workspace: Path, stage: str, data: BaseModel) -> None: ...
    def load(self, workspace: Path, stage: str, model_class: type[T]) -> T: ...
    def update_history(self, entry: HistoryEntry) -> None: ...
    def list_history(self) -> list[HistoryEntry]: ...
```

All persistence uses `model.model_dump_json()` (Pydantic v2) for serialisation and `Model.model_validate_json()` for deserialisation, guaranteeing the round-trip property.

---

## Data Models

All models are defined in `ria/models.py` using Pydantic v2.

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl
from typing import Literal

class SourceType(str, Enum):
    PATENT = "patent"
    PAPER = "paper"

class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class CoverageValue(float, Enum):
    COVERED = 1.0
    PARTIAL = 0.5
    NOT_COVERED = 0.0

class SearchQuery(BaseModel):
    query_string: str
    source: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class RawSourceItem(BaseModel):
    title: str
    source_type: SourceType
    source_url: str
    publication_date: str | None = None
    author_or_assignee: str | None = None
    relevance_explanation: str | None = None
    confidence_level: ConfidenceLevel | None = None
    doi: str | None = None
    patent_number: str | None = None
    raw_adapter_source: str  # which adapter produced this

class ScoredSourceItem(RawSourceItem):
    relevance_score: float = Field(ge=0.0, le=1.0)

class RankedResults(BaseModel):
    papers: list[ScoredSourceItem]   # exactly 3 after selection
    patents: list[ScoredSourceItem]  # exactly 3 after selection

class BenchmarkMetric(BaseModel):
    name: str
    description: str | None = None

class CoverageCell(BaseModel):
    source_item_title: str
    metric_name: str
    value: CoverageValue
    rationale: str | None = None

class BenchmarkScores(BaseModel):
    cells: list[CoverageCell]

    def final_score(self, source_title: str, metrics: list[BenchmarkMetric]) -> float:
        values = [
            c.value for c in self.cells
            if c.source_item_title == source_title
        ]
        return round(sum(values) / len(metrics), 2) if metrics else 0.0

class ApprovedState(BaseModel):
    topic: str
    papers: list[ScoredSourceItem]
    patents: list[ScoredSourceItem]
    metrics: list[BenchmarkMetric]
    confirmed_at: datetime = Field(default_factory=datetime.utcnow)

class HistoryEntry(BaseModel):
    topic: str
    creation_date: datetime
    last_updated: datetime
    report_version: int = 1
    paper_count: int
    patent_count: int
    report_file_path: str
    workspace_dir: str

class OrchestratorResult(BaseModel):
    topic: str
    queries: list[SearchQuery]
    raw_items: list[RawSourceItem]
```

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Source Item Serialisation Round-Trip

*For any* valid `RawSourceItem` record — including all field combinations with optional fields set to `None` — serialising it to JSON using `model_dump_json()` and then deserialising it back with `model_validate_json()` SHALL produce a record that compares equal to the original.

**Validates: Requirements 16.2**

---

### Property 2: Empty and Whitespace-Only Topics Are Rejected

*For any* string composed entirely of Unicode whitespace characters (including the empty string, single space, tab, mixed whitespace), submitting it as a topic SHALL cause the CLI input handler to reject it, display an error message, and re-prompt without altering any pipeline state.

**Validates: Requirements 1.3**

---

### Property 3: Relevance Score Bounds

*For any* source item processed by the ranking engine (with the LLM mocked to return scores), the assigned `Relevance_Score` SHALL always be a floating-point value in the closed interval `[0.0, 1.0]`. No value below 0.0 or above 1.0 shall ever be stored on a `ScoredSourceItem`.

**Validates: Requirements 2.1**

---

### Property 4: Final Score Computation Formula and Coverage Value Domain

*For any* non-empty list of `CoverageCell` values belonging to a source item, where each coverage value is drawn from `{0.0, 0.5, 1.0}`, and *for any* positive integer `n` (number of approved metrics), the computed `Final_Score` SHALL equal `round(sum(coverage_values) / n, 2)`. No `CoverageCell` shall ever carry a value outside `{0.0, 0.5, 1.0}`.

**Validates: Requirements 3.3, 3.4, 8.2, 8.3**

---

### Property 5: Deduplication Idempotence

*For any* list of `RawSourceItem` records (including lists with exact duplicates, same-DOI items, same-URL items, and lists with no duplicates at all), applying the deduplication function twice SHALL produce the same result as applying it once — the second application SHALL not remove any additional items.

**Validates: Requirements 2.2**

---

### Property 6: Source Items Are Sorted Descending by Score

*For any* non-empty list of `ScoredSourceItem` records, after ranking within a category (papers or patents), the items SHALL appear in descending order of `Relevance_Score`. Equivalently, for all consecutive pairs `(a, b)` in the output list, `a.relevance_score >= b.relevance_score`. The same descending order SHALL apply to rows in the Benchmark Table (by `Final_Score`) and to items within each category in the Executive Summary.

**Validates: Requirements 2.6, 7.4, 8.4**

---

### Property 7: Confirmation Gate — No Report Generation Without Explicit Confirmation

*For any* sequence of zero or more validation commands that does not include an explicit confirmation command (`"confirm"` or `"yes"`), the `ValidationController` SHALL NOT set `ApprovedState.confirmed_at` nor trigger report generation. The pipeline state after any such sequence SHALL be observably identical to what it would be if only the non-confirmation commands had been applied.

**Validates: Requirements 3.5, 4.9**

---

### Property 8: Report Filename Slug Format

*For any* research topic string (including strings with spaces, punctuation, Unicode characters, and edge cases like all-punctuation or all-whitespace after stripping), the filename generated by `WorkspaceManager` SHALL match the regular expression `^report_[a-z0-9][a-z0-9\-]*_\d{4}_\d{2}_\d{2}\.md$`. No spaces, uppercase letters, or special characters (other than hyphens) shall appear in the slug portion.

**Validates: Requirements 6.5**

---

### Property 9: Report Structure Completeness — Sections, Sources, and References

*For any* `ApprovedState` containing at least one approved source item and at least one benchmark metric, the rendered Markdown report SHALL:
- Contain exactly three top-level sections appearing in this order: Executive Summary, Benchmark Table, References.
- Include a row in the Benchmark Table for every approved source item.
- Include a column in the Benchmark Table for every approved benchmark metric.
- Include a reference entry for every approved source item, with all IEEE-required fields present: reference number, title, author/inventor/organisation, year or publication date, URL, and access date.

**Validates: Requirements 6.1, 8.1, 10.1, 10.2**

---

### Property 10: Reference Numbering Integrity

*For any* rendered report containing `k` approved source items (`k >= 1`), the reference numbers in the References section SHALL form a contiguous sequence `1, 2, ..., k` with no gaps, no duplicates, and each number assigned to exactly one source item.

**Validates: Requirements 10.3, 10.4**

---

### Property 11: Declining a Confirmation Prompt Preserves State

*For any* application state at a confirmation gate (before report creation, before overwriting an existing report), when the user declines the confirmation prompt, the application state observable to the user SHALL be identical to the state before the prompt was shown — no files are written, no records are modified.

**Validates: Requirements 15.2**

---

### Property 12: Source Item Display Completeness

*For any* `ScoredSourceItem`, the string rendered for display in the validation step SHALL contain the item's sequential number, title, source (adapter name or URL), and `Relevance_Score`. No approved source item shall be silently omitted from the display.

**Validates: Requirements 4.2**

---

## Error Handling

| Scenario | Behaviour |
|---|---|
| Search adapter HTTP error (4xx / 5xx) | Log error with source name and status code; continue with remaining adapters |
| Rate limit (HTTP 429) | Exponential back-off: 1s, 2s, 4s (max 3 retries); mark source unavailable after exhaustion |
| LLM returns malformed JSON | Retry once with an explicit JSON correction prompt; if still invalid, fall back to empty/default values and log warning |
| LLM call times out | Raise `LLMTimeoutError`; surface to CLI as an actionable message |
| Schema validation failure on deserialise | Log the invalid record's raw content at DEBUG level; skip the record; continue |
| User enters invalid command at validation prompt | Display usage hint and re-prompt; do not alter state |
| Report write fails (permissions, disk full) | Surface `IOError` to the CLI with the target path; do not corrupt existing files |
| Workspace history file missing or corrupted | Re-initialise the history file with an empty list after warning the user |

**Retry Policy:**
- HTTP requests: exponential back-off with jitter, max 3 retries per adapter call.
- LLM calls: single retry on malformed JSON; no retry on timeout (surfaces immediately).

**Logging:**
- All log output goes to `ria.log` in the workspace directory (file handler) and to stderr at WARNING+ (console handler).
- Structured logging via Python's `logging` module with `%(asctime)s %(levelname)s %(name)s: %(message)s` format.

---

## Testing Strategy

### Dual Testing Approach

Both unit/example-based tests and property-based tests are used. Unit tests cover specific concrete scenarios and integration points; property tests verify universal invariants across generated inputs.

### Property-Based Testing

The project uses **Hypothesis** (Python) as the property-based testing library. Each property test is configured to run a minimum of **100 examples** (`@settings(max_examples=100)`).

Each property test is tagged with a comment referencing its design property:

```python
# Feature: research-intelligence-assistant, Property 1: Source Item Serialisation Round-Trip
@given(source_item_strategy())
@settings(max_examples=100)
def test_source_item_round_trip(item: RawSourceItem) -> None:
    serialised = item.model_dump_json()
    deserialised = RawSourceItem.model_validate_json(serialised)
    assert deserialised == item
```

### Property Tests (one per correctness property)

| Property | Test Module | Hypothesis Strategy |
|---|---|---|
| P1: Serialisation round-trip | `tests/property/test_serialisation.py` | `source_item_strategy()` — generates `RawSourceItem` with all field combinations including `None` optionals |
| P2: Empty/whitespace topic rejection | `tests/property/test_input_validation.py` | `st.one_of(st.just(""), st.text(alphabet=st.characters(whitelist_categories=("Zs","Cc"))))` |
| P3: Relevance score bounds | `tests/property/test_ranking.py` | `st.lists(source_item_strategy(), min_size=1)` with mocked LLM |
| P4: Final score formula + coverage domain | `tests/property/test_scoring.py` | `st.lists(st.sampled_from([0.0, 0.5, 1.0]), min_size=1)` + `st.integers(min_value=1, max_value=20)` |
| P5: Deduplication idempotence | `tests/property/test_ranking.py` | `st.lists(source_item_strategy())` with injected duplicates |
| P6: Descending sort by score | `tests/property/test_ranking.py` | `st.lists(scored_item_strategy(), min_size=1)` |
| P7: Confirmation gate | `tests/property/test_validation.py` | `st.lists(command_strategy(exclude={"confirm", "yes"}))` |
| P8: Filename slug format | `tests/property/test_report.py` | `st.text(min_size=1)` |
| P9: Report section completeness | `tests/property/test_report.py` | `approved_state_strategy()` |
| P10: Reference numbering integrity | `tests/property/test_report.py` | `approved_state_strategy(min_sources=1)` |
| P11: Decline preserves state | `tests/property/test_validation.py` | `approved_state_strategy()` |
| P12: Source item display completeness | `tests/property/test_validation.py` | `st.lists(scored_item_strategy(), min_size=1)` |

### Unit Tests

- **`tests/unit/test_deduplication.py`** — Specific examples: exact-duplicate titles, same DOI different URL, same URL different title.
- **`tests/unit/test_adapters.py`** — Mock HTTP responses for each adapter; verify correct `RawSourceItem` extraction.
- **`tests/unit/test_llm_client.py`** — Mock LLM responses; verify JSON parsing, malformed-JSON retry, timeout handling.
- **`tests/unit/test_report_renderer.py`** — Snapshot tests for specific `ApprovedState` inputs; verify section order and heading format.
- **`tests/unit/test_workspace.py`** — Workspace creation, history append, history list.
- **`tests/unit/test_validation.py`** — Each validation command type: remove, add, edit metric, remove metric, add metric.

### Integration Tests

- **`tests/integration/test_pipeline.py`** — End-to-end pipeline run with mocked HTTP and mocked LLM; verifies workspace artefacts are written in the correct order and the final Markdown file is valid.
- **`tests/integration/test_adapters_live.py`** — Optional, gated by `RIA_RUN_LIVE_TESTS=1`; verifies real API connectivity for each adapter.

### Testing Commands

```bash
# Run all tests (property + unit + integration, mocked)
pytest tests/ -v

# Run only property-based tests
pytest tests/property/ -v

# Run with increased Hypothesis examples
pytest tests/property/ --hypothesis-seed=0 -v

# Run live integration tests (requires API keys)
RIA_RUN_LIVE_TESTS=1 pytest tests/integration/test_adapters_live.py -v
```
