#!/usr/bin/env python3
"""
Verification script for ria/models.py

Demonstrates:
1. All models can be instantiated
2. Round-trip serialization works correctly
3. Model relationships and data flow
"""

from datetime import datetime
from ria.models import (
    SourceType,
    ConfidenceLevel,
    CoverageValue,
    SearchQuery,
    RawSourceItem,
    ScoredSourceItem,
    RankedResults,
    BenchmarkMetric,
    CoverageCell,
    BenchmarkScores,
    ApprovedState,
    HistoryEntry,
    OrchestratorResult,
)


def test_enums():
    """Test all enum types."""
    print("=" * 60)
    print("Testing Enums")
    print("=" * 60)

    print("\n1. SourceType:")
    print(f"   - PATENT: {SourceType.PATENT.value}")
    print(f"   - PAPER: {SourceType.PAPER.value}")

    print("\n2. ConfidenceLevel:")
    print(f"   - HIGH: {ConfidenceLevel.HIGH.value}")
    print(f"   - MEDIUM: {ConfidenceLevel.MEDIUM.value}")
    print(f"   - LOW: {ConfidenceLevel.LOW.value}")

    print("\n3. CoverageValue:")
    print(f"   - COVERED: {CoverageValue.COVERED.value}")
    print(f"   - PARTIAL: {CoverageValue.PARTIAL.value}")
    print(f"   - NOT_COVERED: {CoverageValue.NOT_COVERED.value}")


def test_search_query():
    """Test SearchQuery model."""
    print("\n" + "=" * 60)
    print("Testing SearchQuery")
    print("=" * 60)

    query = SearchQuery(
        query_string="AI-Based Debriefing in VR Medical Training",
        source="google_patents"
    )
    print(f"\nCreated SearchQuery:")
    print(f"   Query: {query.query_string}")
    print(f"   Source: {query.source}")
    print(f"   Timestamp: {query.timestamp}")

    # Test serialization round-trip
    json_str = query.model_dump_json()
    query_restored = SearchQuery.model_validate_json(json_str)
    assert query == query_restored, "Round-trip failed!"
    print("   ✓ Round-trip serialization successful")


def test_raw_source_item():
    """Test RawSourceItem model."""
    print("\n" + "=" * 60)
    print("Testing RawSourceItem")
    print("=" * 60)

    paper = RawSourceItem(
        title="AI-based automated feedback for VR surgical training",
        source_type=SourceType.PAPER,
        source_url="https://example.com/paper/123",
        publication_date="2023-05-15",
        author_or_assignee="Smith, J. et al.",
        relevance_explanation="Directly addresses AI debriefing in VR surgical simulation",
        confidence_level=ConfidenceLevel.HIGH,
        doi="10.1234/example.doi",
        patent_number=None,
        raw_adapter_source="semantic_scholar"
    )

    print(f"\nCreated RawSourceItem (Paper):")
    print(f"   Title: {paper.title}")
    print(f"   Type: {paper.source_type.value}")
    print(f"   Confidence: {paper.confidence_level.value if paper.confidence_level else 'N/A'}")
    print(f"   Adapter: {paper.raw_adapter_source}")

    # Test serialization round-trip
    json_str = paper.model_dump_json()
    paper_restored = RawSourceItem.model_validate_json(json_str)
    assert paper == paper_restored, "Round-trip failed!"
    print("   ✓ Round-trip serialization successful")


def test_scored_source_item():
    """Test ScoredSourceItem model (inherits from RawSourceItem)."""
    print("\n" + "=" * 60)
    print("Testing ScoredSourceItem")
    print("=" * 60)

    scored_paper = ScoredSourceItem(
        title="AI-based automated feedback for VR surgical training",
        source_type=SourceType.PAPER,
        source_url="https://example.com/paper/123",
        publication_date="2023-05-15",
        author_or_assignee="Smith, J. et al.",
        relevance_explanation="Directly addresses AI debriefing in VR surgical simulation",
        confidence_level=ConfidenceLevel.HIGH,
        doi="10.1234/example.doi",
        patent_number=None,
        raw_adapter_source="semantic_scholar",
        relevance_score=0.95
    )

    print(f"\nCreated ScoredSourceItem:")
    print(f"   Title: {scored_paper.title}")
    print(f"   Relevance Score: {scored_paper.relevance_score}")
    print(f"   Score Range Valid: {0.0 <= scored_paper.relevance_score <= 1.0}")

    # Test serialization round-trip
    json_str = scored_paper.model_dump_json()
    scored_paper_restored = ScoredSourceItem.model_validate_json(json_str)
    assert scored_paper == scored_paper_restored, "Round-trip failed!"
    print("   ✓ Round-trip serialization successful")


def test_ranked_results():
    """Test RankedResults model."""
    print("\n" + "=" * 60)
    print("Testing RankedResults")
    print("=" * 60)

    papers = [
        ScoredSourceItem(
            title=f"Paper {i+1}",
            source_type=SourceType.PAPER,
            source_url=f"https://example.com/paper/{i+1}",
            raw_adapter_source="test_adapter",
            relevance_score=0.9 - i*0.1
        )
        for i in range(3)
    ]

    patents = [
        ScoredSourceItem(
            title=f"Patent {i+1}",
            source_type=SourceType.PATENT,
            source_url=f"https://patents.google.com/patent/{i+1}",
            raw_adapter_source="google_patents",
            patent_number=f"US{10000+i}",
            relevance_score=0.85 - i*0.1
        )
        for i in range(3)
    ]

    results = RankedResults(papers=papers, patents=patents)

    print(f"\nCreated RankedResults:")
    print(f"   Papers: {len(results.papers)}")
    print(f"   Patents: {len(results.patents)}")
    print(f"   Paper Scores: {[p.relevance_score for p in results.papers]}")
    print(f"   Patent Scores: {[p.relevance_score for p in results.patents]}")

    # Test serialization round-trip
    json_str = results.model_dump_json()
    results_restored = RankedResults.model_validate_json(json_str)
    assert results == results_restored, "Round-trip failed!"
    print("   ✓ Round-trip serialization successful")


def test_benchmark_metric():
    """Test BenchmarkMetric model."""
    print("\n" + "=" * 60)
    print("Testing BenchmarkMetric")
    print("=" * 60)

    metric = BenchmarkMetric(
        name="Real-time Feedback",
        description="Provides automated feedback during or immediately after simulation"
    )

    print(f"\nCreated BenchmarkMetric:")
    print(f"   Name: {metric.name}")
    print(f"   Description: {metric.description}")

    # Test serialization round-trip
    json_str = metric.model_dump_json()
    metric_restored = BenchmarkMetric.model_validate_json(json_str)
    assert metric == metric_restored, "Round-trip failed!"
    print("   ✓ Round-trip serialization successful")


def test_benchmark_scores():
    """Test BenchmarkScores model and final_score calculation."""
    print("\n" + "=" * 60)
    print("Testing BenchmarkScores")
    print("=" * 60)

    cells = [
        CoverageCell(
            source_item_title="Paper 1",
            metric_name="Real-time Feedback",
            value=CoverageValue.COVERED,
            rationale="Explicitly describes real-time feedback mechanism"
        ),
        CoverageCell(
            source_item_title="Paper 1",
            metric_name="VR Integration",
            value=CoverageValue.COVERED,
            rationale="Native VR platform integration"
        ),
        CoverageCell(
            source_item_title="Paper 1",
            metric_name="AI-Driven Analysis",
            value=CoverageValue.PARTIAL,
            rationale="Uses rule-based AI, not deep learning"
        ),
    ]

    scores = BenchmarkScores(cells=cells)
    metrics = [
        BenchmarkMetric(name="Real-time Feedback"),
        BenchmarkMetric(name="VR Integration"),
        BenchmarkMetric(name="AI-Driven Analysis"),
    ]

    final_score = scores.final_score("Paper 1", metrics)
    expected_score = round((1.0 + 1.0 + 0.5) / 3, 2)

    print(f"\nCreated BenchmarkScores:")
    print(f"   Total Cells: {len(scores.cells)}")
    print(f"   Coverage Values: {[c.value.value for c in cells]}")
    print(f"   Final Score for 'Paper 1': {final_score}")
    print(f"   Expected Score: {expected_score}")
    print(f"   ✓ Calculation correct: {final_score == expected_score}")

    # Test serialization round-trip
    json_str = scores.model_dump_json()
    scores_restored = BenchmarkScores.model_validate_json(json_str)
    assert scores == scores_restored, "Round-trip failed!"
    print("   ✓ Round-trip serialization successful")


def test_approved_state():
    """Test ApprovedState model."""
    print("\n" + "=" * 60)
    print("Testing ApprovedState")
    print("=" * 60)

    papers = [
        ScoredSourceItem(
            title="AI-based VR training",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper/1",
            raw_adapter_source="test",
            relevance_score=0.9
        )
    ]

    patents = [
        ScoredSourceItem(
            title="VR surgical simulator",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/1",
            raw_adapter_source="google_patents",
            patent_number="US10001",
            relevance_score=0.85
        )
    ]

    metrics = [
        BenchmarkMetric(name="Real-time Feedback"),
        BenchmarkMetric(name="VR Integration"),
    ]

    approved = ApprovedState(
        topic="AI-Based Debriefing in VR Medical Training",
        papers=papers,
        patents=patents,
        metrics=metrics
    )

    print(f"\nCreated ApprovedState:")
    print(f"   Topic: {approved.topic}")
    print(f"   Papers: {len(approved.papers)}")
    print(f"   Patents: {len(approved.patents)}")
    print(f"   Metrics: {len(approved.metrics)}")
    print(f"   Confirmed At: {approved.confirmed_at}")

    # Test serialization round-trip
    json_str = approved.model_dump_json()
    approved_restored = ApprovedState.model_validate_json(json_str)
    assert approved == approved_restored, "Round-trip failed!"
    print("   ✓ Round-trip serialization successful")


def test_history_entry():
    """Test HistoryEntry model."""
    print("\n" + "=" * 60)
    print("Testing HistoryEntry")
    print("=" * 60)

    now = datetime.utcnow()
    entry = HistoryEntry(
        topic="AI-Based Debriefing in VR Medical Training",
        creation_date=now,
        last_updated=now,
        report_version=1,
        paper_count=3,
        patent_count=3,
        report_file_path="/path/to/report_ai-based-debriefing_2024_06_17.md",
        workspace_dir="/path/to/workspace"
    )

    print(f"\nCreated HistoryEntry:")
    print(f"   Topic: {entry.topic}")
    print(f"   Version: {entry.report_version}")
    print(f"   Paper Count: {entry.paper_count}")
    print(f"   Patent Count: {entry.patent_count}")
    print(f"   Report Path: {entry.report_file_path}")

    # Test serialization round-trip
    json_str = entry.model_dump_json()
    entry_restored = HistoryEntry.model_validate_json(json_str)
    assert entry == entry_restored, "Round-trip failed!"
    print("   ✓ Round-trip serialization successful")


def test_orchestrator_result():
    """Test OrchestratorResult model."""
    print("\n" + "=" * 60)
    print("Testing OrchestratorResult")
    print("=" * 60)

    queries = [
        SearchQuery(query_string="VR medical training", source="google_patents"),
        SearchQuery(query_string="AI debriefing simulation", source="semantic_scholar"),
    ]

    items = [
        RawSourceItem(
            title="Example Paper",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper/1",
            raw_adapter_source="semantic_scholar"
        ),
        RawSourceItem(
            title="Example Patent",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/1",
            patent_number="US10001",
            raw_adapter_source="google_patents"
        ),
    ]

    result = OrchestratorResult(
        topic="AI-Based Debriefing in VR Medical Training",
        queries=queries,
        raw_items=items
    )

    print(f"\nCreated OrchestratorResult:")
    print(f"   Topic: {result.topic}")
    print(f"   Queries: {len(result.queries)}")
    print(f"   Raw Items: {len(result.raw_items)}")
    print(f"   Query Sources: {[q.source for q in result.queries]}")
    print(f"   Item Types: {[item.source_type.value for item in result.raw_items]}")

    # Test serialization round-trip
    json_str = result.model_dump_json()
    result_restored = OrchestratorResult.model_validate_json(json_str)
    assert result == result_restored, "Round-trip failed!"
    print("   ✓ Round-trip serialization successful")


def show_model_relationships():
    """Display how models relate to each other in the pipeline."""
    print("\n" + "=" * 60)
    print("Model Relationships and Data Flow")
    print("=" * 60)

    print("""
Stage 1: Search Orchestration
    Input: topic (str)
    ├─ SearchQuery → tracks each search executed
    ├─ RawSourceItem → collected from each adapter
    └─ OrchestratorResult → bundles topic, queries, and raw items

Stage 2: Ranking & Deduplication
    Input: OrchestratorResult
    ├─ RawSourceItem → deduplicated and scored
    ├─ ScoredSourceItem → extends RawSourceItem with relevance_score
    └─ RankedResults → top 3 papers + top 3 patents

Stage 3: Benchmark Metric Generation
    Input: RankedResults
    └─ BenchmarkMetric → LLM-generated evaluation criteria

Stage 4: Validation (Interactive)
    Input: RankedResults + list[BenchmarkMetric]
    └─ ApprovedState → user-confirmed sources and metrics

Stage 5: Report Generation
    Input: ApprovedState
    ├─ CoverageCell → scoring for each source × metric pair
    ├─ BenchmarkScores → complete scoring matrix
    └─ Output: Markdown report + HistoryEntry

Workspace Management:
    HistoryEntry → tracks all generated reports for reuse/update
    """)


def main():
    """Run all verification tests."""
    print("\n" + "=" * 60)
    print("RIA Models Verification Script")
    print("=" * 60)

    test_enums()
    test_search_query()
    test_raw_source_item()
    test_scored_source_item()
    test_ranked_results()
    test_benchmark_metric()
    test_benchmark_scores()
    test_approved_state()
    test_history_entry()
    test_orchestrator_result()
    show_model_relationships()

    print("\n" + "=" * 60)
    print("✓ All models verified successfully!")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
