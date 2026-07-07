"""
Integration test for Comparison Agent in the full pipeline.

This test verifies that the Comparison Agent integrates correctly
with the comparison matrix generation and report rendering.
"""

import pytest
from unittest.mock import Mock

from ria.agents.comparison_agent import ComparisonAgent
from ria.comparison_matrix import ComparisonMatrixGenerator, MetricEvaluation, SourceMetricEvaluation
from ria.models import ScoredSourceItem, SourceType, ConfidenceLevel
from ria.llm import LLMClient


def create_test_paper_with_xpbd() -> ScoredSourceItem:
    """Create a test paper with XPBD in title."""
    return ScoredSourceItem(
        title="Extended Position Based Dynamics for Soft Body Simulation",
        source_type=SourceType.PAPER,
        source_url="https://arxiv.org/abs/1234.5678",
        publication_date="2024-01-15",
        author_or_assignee="Smith, J. and Doe, A.",
        relevance_explanation="This paper presents a novel XPBD method for deformable objects.",
        confidence_level=ConfidenceLevel.HIGH,
        doi="10.1234/arxiv.1234.5678",
        raw_adapter_source="semantic_scholar",
        relevance_score=0.95,
        is_open_access=True,
        pdf_url="https://arxiv.org/pdf/1234.5678.pdf",
        venue="SIGGRAPH 2024",
        citation_count=42,
    )


def create_test_paper_without_xpbd() -> ScoredSourceItem:
    """Create a test paper without XPBD."""
    return ScoredSourceItem(
        title="Traditional Mass-Spring Systems for Cloth Simulation",
        source_type=SourceType.PAPER,
        source_url="https://example.com/paper",
        publication_date="2023-06-10",
        author_or_assignee="Brown, K.",
        relevance_explanation="Classic mass-spring approach for cloth dynamics.",
        confidence_level=ConfidenceLevel.MEDIUM,
        doi="10.1234/example.9876",
        raw_adapter_source="semantic_scholar",
        relevance_score=0.65,
        is_open_access=False,
        pdf_url=None,
        venue="Computer Graphics Forum",
        citation_count=15,
    )


def create_test_patent() -> ScoredSourceItem:
    """Create a test patent."""
    return ScoredSourceItem(
        title="Method and System for Real-Time Soft Body Deformation",
        source_type=SourceType.PATENT,
        source_url="https://patents.google.com/patent/US12345678",
        publication_date="2022-03-20",
        author_or_assignee="TechCorp Inc.",
        relevance_explanation="Patent for soft body simulation in VR training.",
        confidence_level=ConfidenceLevel.HIGH,
        patent_number="US12345678B2",
        raw_adapter_source="serpapi",
        relevance_score=0.88,
    )


def test_comparison_agent_pipeline_integration():
    """
    Test the full pipeline: Matrix Generation → Validation → Report.

    This simulates what happens in app.py during report generation.
    """
    # Mock LLM client (we'll use rule-based validation only)
    mock_llm = Mock(spec=LLMClient)
    mock_llm.last_call_metadata = {
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }
    }

    # Create test sources
    sources = [
        create_test_paper_with_xpbd(),
        create_test_paper_without_xpbd(),
        create_test_patent(),
    ]

    # Define test metrics
    metric_names = [
        "XPBD Support",
        "Open Access",
        "Patent",
    ]

    metric_descriptions = {
        "XPBD Support": "Does the source use Extended Position Based Dynamics?",
        "Open Access": "Is the source freely available?",
        "Patent": "Is the source a patent or discusses patents?",
    }

    # Step 1: Generate initial comparison matrix
    # Mock the matrix generator to create a matrix with some intentional errors
    initial_evaluations = []

    # Paper 1: XPBD paper (open access) - mark XPBD as NO (should be YES)
    initial_evaluations.append(SourceMetricEvaluation(
        source_id=sources[0].doi,
        source_title=sources[0].title,
        source_type=sources[0].source_type.value,
        metric_evaluations=[
            MetricEvaluation(
                metric_name="XPBD Support",
                status="none",  # WRONG! Should be full
                symbol="❌",
                score=0.0,
                evidence="Initial evaluation",
                confidence="low",
            ),
            MetricEvaluation(
                metric_name="Open Access",
                status="full",  # CORRECT
                symbol="✅",
                score=1.0,
                evidence="Initial evaluation",
                confidence="high",
            ),
            MetricEvaluation(
                metric_name="Patent",
                status="none",  # CORRECT (it's a paper, not a patent)
                symbol="❌",
                score=0.0,
                evidence="Initial evaluation",
                confidence="high",
            ),
        ],
        overall_score=0.33,
    ))

    # Paper 2: Non-XPBD paper (closed access) - mark as open access (should be NO)
    initial_evaluations.append(SourceMetricEvaluation(
        source_id=sources[1].doi,
        source_title=sources[1].title,
        source_type=sources[1].source_type.value,
        metric_evaluations=[
            MetricEvaluation(
                metric_name="XPBD Support",
                status="none",  # CORRECT
                symbol="❌",
                score=0.0,
                evidence="Initial evaluation",
                confidence="high",
            ),
            MetricEvaluation(
                metric_name="Open Access",
                status="full",  # WRONG! Should be none
                symbol="✅",
                score=1.0,
                evidence="Initial evaluation",
                confidence="low",
            ),
            MetricEvaluation(
                metric_name="Patent",
                status="none",  # CORRECT
                symbol="❌",
                score=0.0,
                evidence="Initial evaluation",
                confidence="high",
            ),
        ],
        overall_score=0.33,
    ))

    # Patent - mark as not a patent (should be YES)
    initial_evaluations.append(SourceMetricEvaluation(
        source_id=sources[2].patent_number,
        source_title=sources[2].title,
        source_type=sources[2].source_type.value,
        metric_evaluations=[
            MetricEvaluation(
                metric_name="XPBD Support",
                status="none",  # CORRECT (patent doesn't mention XPBD)
                symbol="❌",
                score=0.0,
                evidence="Initial evaluation",
                confidence="medium",
            ),
            MetricEvaluation(
                metric_name="Open Access",
                status="none",  # CORRECT (patents aren't typically open access in same way)
                symbol="❌",
                score=0.0,
                evidence="Initial evaluation",
                confidence="high",
            ),
            MetricEvaluation(
                metric_name="Patent",
                status="none",  # WRONG! Should be full
                symbol="❌",
                score=0.0,
                evidence="Initial evaluation",
                confidence="low",
            ),
        ],
        overall_score=0.0,
    ))

    # Step 2: Validate with Comparison Agent
    agent = ComparisonAgent(llm_client=None)  # No LLM, rule-based only

    validation_result = agent.validate_matrix(
        topic="XPBD soft body simulation",
        sources=sources,
        selected_metrics=metric_names,
        initial_matrix=initial_evaluations,
        metric_descriptions=metric_descriptions,
    )

    # Step 3: Verify corrections
    assert validation_result.cells_reviewed == 9  # 3 sources × 3 metrics
    assert validation_result.cells_changed == 3  # 3 intentional errors

    # Verify specific corrections
    print(f"\nChanges detected: {len(validation_result.changes)}")
    for change in validation_result.changes:
        print(f"  - {change.source_label} / {change.metric}: {change.old_status} → {change.new_status}")

    # Find changes by metric name
    xpbd_changes = [c for c in validation_result.changes if c.metric == "XPBD Support"]
    open_access_changes = [c for c in validation_result.changes if c.metric == "Open Access"]
    patent_changes = [c for c in validation_result.changes if c.metric == "Patent"]

    # Check XPBD Support correction
    assert len(xpbd_changes) == 1
    xpbd_change = xpbd_changes[0]
    assert xpbd_change.old_status == "NO"
    assert xpbd_change.new_status == "YES"

    # Check Open Access correction
    assert len(open_access_changes) == 1
    open_access_change = open_access_changes[0]
    assert open_access_change.old_status == "YES"
    assert open_access_change.new_status == "NO"

    # Check Patent correction
    assert len(patent_changes) == 1
    patent_change = patent_changes[0]
    assert patent_change.old_status == "NO"
    assert patent_change.new_status == "YES"

    # Step 4: Verify validation summary
    assert "3 cells were corrected" in validation_result.validation_summary
    assert validation_result.confidence_score > 0.8  # Rule-based = high confidence

    # Step 5: Verify validated matrix has correct values
    validated_matrix = {
        eval.source_id: eval
        for eval in validation_result.validated_matrix
    }

    # XPBD paper should now have XPBD Support = full
    xpbd_paper = validated_matrix[sources[0].doi]
    xpbd_metric = next(m for m in xpbd_paper.metric_evaluations if m.metric_name == "XPBD Support")
    assert xpbd_metric.status == "full"
    assert xpbd_metric.symbol == "✅"

    # Non-XPBD paper should now have Open Access = none
    non_xpbd_paper = validated_matrix[sources[1].doi]
    oa_metric = next(m for m in non_xpbd_paper.metric_evaluations if m.metric_name == "Open Access")
    assert oa_metric.status == "none"
    assert oa_metric.symbol == "❌"

    # Patent should now have Patent = full
    patent = validated_matrix[sources[2].patent_number]
    patent_metric = next(m for m in patent.metric_evaluations if m.metric_name == "Patent")
    assert patent_metric.status == "full"
    assert patent_metric.symbol == "✅"

    print("✓ Integration test passed!")
    print(f"  - Reviewed {validation_result.cells_reviewed} cells")
    print(f"  - Corrected {validation_result.cells_changed} errors")
    print(f"  - Confidence: {validation_result.confidence_score:.2%}")


def test_agent_fallback_on_failure():
    """Test that the pipeline continues if validation fails."""

    # Create a source
    source = create_test_paper_with_xpbd()

    # Create initial matrix
    initial_eval = SourceMetricEvaluation(
        source_id=source.doi,
        source_title=source.title,
        source_type=source.source_type.value,
        metric_evaluations=[
            MetricEvaluation(
                metric_name="Test Metric",
                status="full",
                symbol="✅",
                score=1.0,
                evidence="Test",
                confidence="high",
            ),
        ],
        overall_score=1.0,
    )

    # Simulate validation failure by passing invalid data
    agent = ComparisonAgent()

    # This should handle gracefully (source not in sources list)
    result = agent.validate_matrix(
        topic="test",
        sources=[],  # Empty sources
        selected_metrics=["Test Metric"],
        initial_matrix=[initial_eval],
    )

    # Should return the original matrix unchanged
    assert len(result.validated_matrix) == 1
    assert result.cells_changed == 0

    print("✓ Fallback test passed!")


if __name__ == "__main__":
    test_comparison_agent_pipeline_integration()
    test_agent_fallback_on_failure()
    print("\n✓ All integration tests passed!")
