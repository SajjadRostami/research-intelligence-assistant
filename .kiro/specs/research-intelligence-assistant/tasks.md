# Implementation Plan: Research Intelligence and Benchmarking Assistant

## Overview

Implement a Python 3.11+ CLI pipeline that accepts a research topic, orchestrates searches across patent and academic sources, ranks and deduplicates results, generates benchmark metrics via LLM, drives an interactive validation step, and renders a structured Markdown report. The implementation follows the five-stage pipeline architecture defined in the design document, using Pydantic v2, `openai` SDK, `aiohttp`/`httpx`, `rich`, and `hypothesis`.

---

## Tasks

- [ ] 1. Project scaffolding and core data models
  - [ ] 1.1 Initialise project structure and configuration
    - Create `pyproject.toml` with dependencies: `openai`, `python-dotenv`, `aiohttp`, `httpx`, `pydantic>=2`, `rich`, `hypothesis`
    - Create `requirements.txt` (pinned versions)
    - Create `.env.example` with `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `MODEL_NAME`
    - Create package skeleton: `ria/__init__.py`, `ria/adapters/__init__.py`, `main.py`
    - Create `tests/unit/`, `tests/integration/`, `tests/property/` directories with `__init__.py` stubs
    - _Requirements: 1.1_

  - [ ] 1.2 Implement all Pydantic v2 data models in `ria/models.py`
    - Define enums: `SourceType`, `ConfidenceLevel`, `CoverageValue`
    - Define models: `SearchQuery`, `RawSourceItem`, `ScoredSourceItem`, `RankedResults`, `BenchmarkMetric`, `CoverageCell`, `BenchmarkScores`, `ApprovedState`, `HistoryEntry`, `OrchestratorResult`
    - Implement `BenchmarkScores.final_score()` method
    - _Requirements: 1.6, 1.7, 1.8, 2.1, 3.3, 3.4, 16.1, 16.2_

  - [ ]* 1.3 Write property test for Source Item Serialisation Round-Trip (Property 1)
    - **Property 1: Source Item Serialisation Round-Trip**
    - Use `source_item_strategy()` generating `RawSourceItem` with all field combinations including `None` optionals
    - Serialise with `model_dump_json()`, deserialise with `model_validate_json()`, assert equality
    - Tag: `# Feature: research-intelligence-assistant, Property 1: Source Item Serialisation Round-Trip`
    - Module: `tests/property/test_serialisation.py`
    - **Validates: Requirements 16.2**

- [ ] 2. LLM client wrapper
  - [ ] 2.1 Implement `LLMClient` in `ria/llm.py`
    - Wrap `openai.OpenAI` targeting Claude model via env-configured alias
    - Implement `chat(messages, *, response_format)` and `chat_json(messages)` methods
    - `chat_json` enforces JSON mode, retries once on malformed JSON with a correction prompt, raises `LLMTimeoutError` on timeout
    - Load model name and base URL from environment via `python-dotenv`
    - _Requirements: 1.9 (LLM integration), 3.1_

  - [ ]* 2.2 Write unit tests for `LLMClient`
    - Mock `openai.OpenAI` responses
    - Test: valid JSON response, malformed JSON triggers single retry, timeout raises `LLMTimeoutError`
    - Module: `tests/unit/test_llm_client.py`
    - _Requirements: (error handling)_

- [ ] 3. Search adapters
  - [ ] 3.1 Implement `SearchAdapter` abstract base in `ria/adapters/base.py`
    - Define abstract `search(query: SearchQuery) -> list[RawSourceItem]` — never raises, returns `[]` on error
    - Define `source_type: str` class attribute
    - _Requirements: 1.4, 1.9_

  - [ ] 3.2 Implement `GooglePatentsAdapter` in `ria/adapters/google_patents.py`
    - Build query URL, make async HTTP request via `aiohttp`/`httpx`
    - Apply exponential back-off (1s, 2s, 4s, max 3 retries) on HTTP 429 or transient errors
    - Extract fields: title, source URL, publication date, assignee, patent number
    - Return partial results on error; log failures
    - _Requirements: 1.4, 1.7, 1.9, 1.10_

  - [ ] 3.3 Implement academic paper adapters: `SemanticScholarAdapter`, `OpenAlexAdapter`, `ArxivAdapter`, `PubMedAdapter`, `CrossrefAdapter`
    - One file per adapter in `ria/adapters/`
    - Each applies the same back-off/retry/partial-result pattern as `GooglePatentsAdapter`
    - Extract common fields into `RawSourceItem`; set `raw_adapter_source` to adapter name
    - _Requirements: 1.4, 1.5, 1.7, 1.9, 1.10_

  - [ ]* 3.4 Write unit tests for search adapters
    - Mock HTTP responses (success, 429, 5xx) for each adapter
    - Verify correct `RawSourceItem` field extraction and back-off behaviour
    - Module: `tests/unit/test_adapters.py`
    - _Requirements: 1.7, 1.9, 1.10_

- [ ] 4. Search orchestrator (Stage 1)
  - [ ] 4.1 Implement `SearchOrchestrator` in `ria/orchestrator.py`
    - Accept one patent adapter and a list of paper adapters
    - Dispatch all adapters concurrently with `asyncio.gather`
    - Collect `RawSourceItem` lists; record `SearchQuery` per adapter with timestamp
    - Return `OrchestratorResult`
    - _Requirements: 1.4, 1.5, 1.6, 1.9_

  - [ ] 4.2 Implement workspace persistence in `ria/workspace.py`
    - `WorkspaceManager.create(topic)` creates per-topic directory
    - `save(workspace, stage, data)` writes `data.model_dump_json()` to `{stage}.json`
    - `load(workspace, stage, model_class)` reads and validates with `model_class.model_validate_json()`
    - `update_history(entry)` appends to `~/.ria/history.json`; re-initialises on corrupt/missing file
    - `list_history()` reads and returns all entries
    - _Requirements: 1.6, 14.1, 14.3, 16.1, 16.2, 16.3, 16.4_

  - [ ]* 4.3 Write unit tests for `WorkspaceManager`
    - Test: workspace creation, save/load round-trip, history append, history list, corrupt history recovery
    - Module: `tests/unit/test_workspace.py`
    - _Requirements: 14.1, 14.3, 16.2_

- [ ] 5. Checkpoint — wire Stage 1
  - Ensure `main.py` can invoke `SearchOrchestrator`, persist `OrchestratorResult` via `WorkspaceManager`, and print a summary to stdout. All tests pass.

- [ ] 6. Ranking and deduplication (Stage 2)
  - [ ] 6.1 Implement `RankingEngine` in `ria/ranking.py`
    - `deduplicate(items)`: normalise (lowercase, strip) titles, URLs, DOIs, patent numbers; remove duplicates
    - `score(items, topic)`: call LLM per item with structured prompt; parse `{"relevance_score": float, "explanation": str, "confidence_level": str}`; clamp score to `[0.0, 1.0]`; fall back to `0.0` on LLM error
    - `select_top(scored)`: return top-3 papers and top-3 patents sorted descending by `relevance_score`
    - Persist `RankedResults` to `ranked_results.json`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 6.2 Write property test for Relevance Score Bounds (Property 3)
    - **Property 3: Relevance Score Bounds**
    - Generate lists of `RawSourceItem` via `st.lists(source_item_strategy(), min_size=1)`; mock LLM to return arbitrary floats
    - Assert every `ScoredSourceItem.relevance_score` in `[0.0, 1.0]`
    - Module: `tests/property/test_ranking.py`
    - **Validates: Requirements 2.1**

  - [ ]* 6.3 Write property test for Deduplication Idempotence (Property 5)
    - **Property 5: Deduplication Idempotence**
    - Generate lists with injected exact duplicates, same-DOI, same-URL items
    - Assert `deduplicate(deduplicate(items)) == deduplicate(items)`
    - Module: `tests/property/test_ranking.py`
    - **Validates: Requirements 2.2**

  - [ ]* 6.4 Write property test for Descending Sort by Score (Property 6)
    - **Property 6: Source Items Are Sorted Descending by Score**
    - Generate lists via `st.lists(scored_item_strategy(), min_size=1)`
    - Assert each consecutive pair `(a, b)` satisfies `a.relevance_score >= b.relevance_score`
    - Module: `tests/property/test_ranking.py`
    - **Validates: Requirements 2.6, 7.4, 8.4**

  - [ ]* 6.5 Write unit tests for deduplication
    - Test specific cases: exact-duplicate titles, same DOI different URL, same URL different title
    - Module: `tests/unit/test_deduplication.py`
    - _Requirements: 2.2_

- [ ] 7. Benchmark metric generation (Stage 3)
  - [ ] 7.1 Implement `MetricsGenerator` in `ria/metrics.py`
    - Send single LLM prompt with topic + source summaries
    - Parse JSON list of `{"name": str, "description": str}` objects into `list[BenchmarkMetric]`
    - Persist `list[BenchmarkMetric]` to `metrics.json`
    - _Requirements: 3.1, 3.2_

- [ ] 8. Interactive validation step (Stage 4)
  - [ ] 8.1 Implement `ValidationController` in `ria/validation.py`
    - Display numbered lists of papers, patents, and metrics using `rich`
    - Accept commands: `approve`/`confirm`, `remove <type> <n>`, `add <type> <url>`, `edit metric <n>`, `remove metric <n>`, `add metric`
    - Re-display updated lists after each mutating command
    - Only set `ApprovedState.confirmed_at` and return `ApprovedState` when `confirm`/`yes` is typed
    - Persist `ApprovedState` to `approved_state.json`
    - Display usage hint on unrecognised command; do not alter state
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 3.5_

  - [ ]* 8.2 Write property test for Confirmation Gate (Property 7)
    - **Property 7: Confirmation Gate — No Report Generation Without Explicit Confirmation**
    - Generate command sequences via `st.lists(command_strategy(exclude={"confirm", "yes"}))`
    - Assert `ApprovedState.confirmed_at` is never set and report generation is never triggered
    - Module: `tests/property/test_validation.py`
    - **Validates: Requirements 3.5, 4.9**

  - [ ]* 8.3 Write property test for Declining Confirmation Preserves State (Property 11)
    - **Property 11: Declining a Confirmation Prompt Preserves State**
    - Generate an `ApprovedState` via `approved_state_strategy()`; simulate user declining the confirmation prompt
    - Assert no files are written and observable state is identical to pre-prompt state
    - Module: `tests/property/test_validation.py`
    - **Validates: Requirements 15.2**

  - [ ]* 8.4 Write property test for Source Item Display Completeness (Property 12)
    - **Property 12: Source Item Display Completeness**
    - Generate lists via `st.lists(scored_item_strategy(), min_size=1)`
    - Assert the rendered string contains each item's sequential number, title, source, and `relevance_score`
    - Module: `tests/property/test_validation.py`
    - **Validates: Requirements 4.2**

  - [ ]* 8.5 Write unit tests for `ValidationController`
    - Test each command type: remove, add, edit metric, remove metric, add metric
    - Module: `tests/unit/test_validation.py`
    - _Requirements: 4.4–4.8_

- [ ] 9. Checkpoint — wire Stages 1–4
  - Ensure pipeline runs from topic input through to `approved_state.json` being written. Run all property and unit tests; ensure all pass.

- [ ] 10. Report renderer and scoring (Stage 5)
  - [ ] 10.1 Implement coverage scoring in `ria/report.py`
    - Send batch LLM prompt with `ApprovedState` sources × metrics
    - Parse response into `BenchmarkScores` (list of `CoverageCell`)
    - Validate all `CoverageValue` values are in `{0.0, 0.5, 1.0}`
    - _Requirements: 8.2, 8.3_

  - [ ] 10.2 Implement `ReportRenderer.render()` in `ria/report.py`
    - Pure function: `render(state: ApprovedState, scores: BenchmarkScores) -> str`
    - Render three sections in order: `# 1. Executive Summary`, `# 2. Benchmark Table`, `# 3. References`
    - Executive Summary: one-to-two sentence summary per source, grouped by category (papers first, then patents), sorted descending by `relevance_score`
    - Benchmark Table: rows = sources (sorted descending by `final_score`), columns = metrics, last column = `Final_Score` (2 d.p.); include legend
    - References: IEEE format, sequentially numbered; include inline `[N]` citations in Executive Summary
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 7.1, 7.2, 7.3, 7.4, 8.1, 8.2, 8.3, 8.4, 8.5, 10.1, 10.2, 10.3, 10.4_

  - [ ]* 10.3 Write property test for Final Score Formula and Coverage Domain (Property 4)
    - **Property 4: Final Score Computation Formula and Coverage Value Domain**
    - Generate coverage value lists via `st.lists(st.sampled_from([0.0, 0.5, 1.0]), min_size=1)` and metric counts via `st.integers(min_value=1, max_value=20)`
    - Assert `final_score == round(sum(values) / n, 2)` and no `CoverageCell` holds a value outside `{0.0, 0.5, 1.0}`
    - Module: `tests/property/test_scoring.py`
    - **Validates: Requirements 3.3, 3.4, 8.2, 8.3**

  - [ ]* 10.4 Write property test for Report Filename Slug Format (Property 8)
    - **Property 8: Report Filename Slug Format**
    - Generate arbitrary topic strings via `st.text(min_size=1)`
    - Assert generated filename matches `^report_[a-z0-9][a-z0-9\-]*_\d{4}_\d{2}_\d{2}\.md$`
    - Module: `tests/property/test_report.py`
    - **Validates: Requirements 6.5**

  - [ ]* 10.5 Write property test for Report Structure Completeness (Property 9)
    - **Property 9: Report Structure Completeness — Sections, Sources, and References**
    - Generate `ApprovedState` via `approved_state_strategy()` (at least one source, one metric)
    - Assert rendered Markdown contains exactly three top-level sections in order; every source has a table row; every metric has a table column; every source has a reference entry with all IEEE-required fields
    - Module: `tests/property/test_report.py`
    - **Validates: Requirements 6.1, 8.1, 10.1, 10.2**

  - [ ]* 10.6 Write property test for Reference Numbering Integrity (Property 10)
    - **Property 10: Reference Numbering Integrity**
    - Generate `ApprovedState` via `approved_state_strategy(min_sources=1)`
    - Assert reference numbers form a contiguous sequence `1..k` with no gaps, no duplicates
    - Module: `tests/property/test_report.py`
    - **Validates: Requirements 10.3, 10.4**

  - [ ]* 10.7 Write unit tests for `ReportRenderer`
    - Snapshot tests for specific `ApprovedState` inputs; verify section order, heading format, table structure, legend presence
    - Module: `tests/unit/test_report_renderer.py`
    - _Requirements: 6.1, 6.2, 8.5, 10.1_

- [ ] 11. CLI presentation layer
  - [ ] 11.1 Implement `ria/cli.py` — Rich-based prompts and menus
    - Topic input prompt with non-empty / non-whitespace validation; re-prompts on invalid input
    - `display_sources_and_metrics(papers, patents, metrics)` using `rich.table`
    - Progress spinners for each pipeline stage
    - Confirmation gate prompt (shows action summary, awaits `y`/`n`)
    - History listing view
    - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.2, 4.3, 6.5, 6.6, 14.3, 15.1, 15.3_

  - [ ]* 11.2 Write property test for Empty and Whitespace-Only Topic Rejection (Property 2)
    - **Property 2: Empty and Whitespace-Only Topics Are Rejected**
    - Generate strings via `st.one_of(st.just(""), st.text(alphabet=st.characters(whitelist_categories=("Zs","Cc"))))`
    - Assert CLI input handler rejects, displays error, re-prompts, and no pipeline state is altered
    - Module: `tests/property/test_input_validation.py`
    - **Validates: Requirements 1.3**

- [ ] 12. Wire complete pipeline in `main.py`
  - [ ] 12.1 Connect all five stages end-to-end in `main.py`
    - Stage 1: invoke `SearchOrchestrator`, persist `raw_results.json`
    - Stage 2: invoke `RankingEngine`, persist `ranked_results.json`
    - Stage 3: invoke `MetricsGenerator`, persist `metrics.json`
    - Stage 4: invoke `ValidationController`, persist `approved_state.json`
    - Stage 5: invoke coverage scoring + `ReportRenderer`, save report file, update history
    - Surface all errors to CLI with actionable messages
    - _Requirements: 1.1–1.10, 2.1–2.6, 3.1–3.5, 4.1–4.10, 6.1–6.6, 7.1–7.4, 8.1–8.5, 10.1–10.4, 14.1–14.3, 15.1–15.3_

- [ ] 13. Integration tests
  - [ ]* 13.1 Write end-to-end pipeline integration test
    - Mock all HTTP adapters and LLM client; run full pipeline
    - Assert workspace artefacts written in correct order: `raw_results.json`, `ranked_results.json`, `metrics.json`, `approved_state.json`, `report_*.md`
    - Assert final Markdown file is well-formed and contains all three sections
    - Module: `tests/integration/test_pipeline.py`
    - _Requirements: 6.1, 16.1, 16.2_

  - [ ]* 13.2 Write optional live adapter integration test
    - Gate with `RIA_RUN_LIVE_TESTS=1` environment variable
    - Verify real API connectivity for each adapter; skip gracefully when variable not set
    - Module: `tests/integration/test_adapters_live.py`
    - _Requirements: 1.4, 1.5_

- [ ] 14. Final checkpoint — full test suite
  - Run `pytest tests/ -v` and confirm all property, unit, and integration (mocked) tests pass. Fix any failures before marking complete.

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP; property tests correspond directly to the 12 correctness properties in the design document.
- Each task references specific requirements for traceability.
- Checkpoints at tasks 5, 9, and 14 ensure incremental validation at each pipeline boundary.
- Property tests use `@settings(max_examples=100)` and are tagged with design property numbers as comments.
- The `approved_state_strategy()` and `scored_item_strategy()` Hypothesis strategies should be defined in a shared `tests/property/strategies.py` module and imported by all property test modules.
- All LLM interactions in tests are mocked; live tests are gated by `RIA_RUN_LIVE_TESTS=1`.

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3", "2.1"] },
    { "id": 2, "tasks": ["2.2", "3.1"] },
    { "id": 3, "tasks": ["3.2", "3.3"] },
    { "id": 4, "tasks": ["3.4", "4.1", "4.2"] },
    { "id": 5, "tasks": ["4.3", "6.1"] },
    { "id": 6, "tasks": ["6.2", "6.3", "6.4", "6.5", "7.1"] },
    { "id": 7, "tasks": ["8.1"] },
    { "id": 8, "tasks": ["8.2", "8.3", "8.4", "8.5", "10.1"] },
    { "id": 9, "tasks": ["10.2"] },
    { "id": 10, "tasks": ["10.3", "10.4", "10.5", "10.6", "10.7", "11.1"] },
    { "id": 11, "tasks": ["11.2", "12.1"] },
    { "id": 12, "tasks": ["13.1", "13.2"] }
  ]
}
```
