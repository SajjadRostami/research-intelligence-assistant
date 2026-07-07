"""
Tests for the Comparison Agent.

These tests verify that the Comparison Agent correctly validates
comparison matrix cells using rule-based and LLM-based validation.
"""

import pytest
from unittest.mock import Mock, MagicMock

from ria.agents.comparison_agent import ComparisonAgent, ValidationResult
from ria.comparison_matrix import MetricEvaluation, SourceMetricEvaluation
from ria.models import ScoredSourceItem, SourceType, ConfidenceLevel


def create_test_paper(
    title: str = "Test Paper",
    relevance_explanation: str = "",
    is_open_access: bool = False,
    pdf_url: str | None = None,
) -> ScoredSourceItem:
    """Helper to create a test paper."""
    return ScoredSourceItem(
        title=title,
        source_type=SourceType.PAPER,
        source_url="https://example.com/paper",
        publication_date="2024-01-01",
        author_or_assignee="Test Author",
        relevance_explanation=relevance_explanation,
        confidence_level=ConfidenceLevel.HIGH,
        doi="10.1234/test",
        raw_adapter_source="test",
        relevance_score=0.9,
        is_open_access=is_open_access,
        pdf_url=pdf_url,
    )


def create_test_patent(
    title: str = "Test Patent",
    relevance_explanation: str = "",
    patent_number: str = "US12345678",
) -> ScoredSourceItem:
    """Helper to create a test patent."""
    return ScoredSourceItem(
        title=title,
        source_type=SourceType.PATENT,
        source_url="https://patents.google.com/patent/US12345678",
        publication_date="2024-01-01",
        author_or_assignee="Test Assignee",
        relevance_explanation=relevance_explanation,
        confidence_level=ConfidenceLevel.HIGH,
        patent_number=patent_number,
        raw_adapter_source="test",
        relevance_score=0.9,
    )


def create_test_evaluation(
    source: ScoredSourceItem,
    metric_name: str,
    status: str = "full",
) -> SourceMetricEvaluation:
    """Helper to create a test evaluation."""
    symbol = "✅" if status == "full" else "⚠️" if status == "partial" else "❌"
    score = 1.0 if status == "full" else 0.5 if status == "partial" else 0.0

    metric_eval = MetricEvaluation(
        metric_name=metric_name,
        status=status,
        symbol=symbol,
        score=score,
        evidence="Initial evaluation",
        confidence="medium",
    )

    source_id = source.doi if source.doi else source.patent_number if source.patent_number else source.title[:50]

    return SourceMetricEvaluation(
        source_id=source_id,
        source_title=source.title,
        source_type=source.source_type.value,
        metric_evaluations=[metric_eval],
        overall_score=score,
    )


class TestComparisonAgentRuleBased:
    """Test rule-based validation logic."""

    def test_open_access_yes_with_pdf_url(self):
        """Test Open Access metric: YES when PDF URL exists."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="Open Access Paper",
            pdf_url="https://arxiv.org/pdf/1234.5678.pdf",
        )

        initial_matrix = [create_test_evaluation(paper, "Open Access", status="none")]

        result = agent.validate_matrix(
            topic="test",
            sources=[paper],
            selected_metrics=["Open Access"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        assert len(result.changes) == 1
        assert result.changes[0].new_status == "YES"
        assert "open access" in result.changes[0].reason.lower()

    def test_open_access_no_without_pdf(self):
        """Test Open Access metric: NO when no PDF and not open access."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="Closed Access Paper",
            is_open_access=False,
            pdf_url=None,
        )

        initial_matrix = [create_test_evaluation(paper, "Open Access", status="full")]

        result = agent.validate_matrix(
            topic="test",
            sources=[paper],
            selected_metrics=["Open Access"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        assert len(result.changes) == 1
        assert result.changes[0].new_status == "NO"

    def test_xpbd_support_yes_explicit_mention(self):
        """Test XPBD Support: YES when explicitly mentioned."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="Extended Position Based Dynamics for Soft Bodies",
            relevance_explanation="This paper presents a novel XPBD approach.",
        )

        initial_matrix = [create_test_evaluation(paper, "XPBD Support", status="none")]

        result = agent.validate_matrix(
            topic="XPBD simulation",
            sources=[paper],
            selected_metrics=["XPBD Support"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        assert result.changes[0].new_status == "YES"

    def test_xpbd_support_part_for_pbd(self):
        """Test XPBD Support: PART when PBD mentioned but not XPBD."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="Position-Based Dynamics for Cloth Simulation",
            relevance_explanation="Uses position-based constraints.",
        )

        initial_matrix = [create_test_evaluation(paper, "XPBD Support", status="full")]

        result = agent.validate_matrix(
            topic="XPBD simulation",
            sources=[paper],
            selected_metrics=["XPBD Support"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        assert result.changes[0].new_status == "PART"

    def test_haptic_robot_support_no_for_no_mention(self):
        """Test Haptic Robot Support: NO when not mentioned (should be PART for simulation context)."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="Soft Body Simulation",
            relevance_explanation="A simulation paper without haptics.",
        )

        initial_matrix = [create_test_evaluation(paper, "Haptic Robot Support", status="full")]

        result = agent.validate_matrix(
            topic="haptic simulation",
            sources=[paper],
            selected_metrics=["Haptic Robot Support"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        # Should be PART because "simulation" keyword suggests possible VR/haptic context
        assert result.changes[0].new_status == "PART"

    def test_haptic_robot_support_yes_explicit(self):
        """Test Haptic Robot Support: YES when explicit."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="Haptic Device Integration for Surgical Simulation",
            relevance_explanation="Uses a haptic robot for force feedback.",
        )

        initial_matrix = [create_test_evaluation(paper, "Haptic Robot Support", status="none")]

        result = agent.validate_matrix(
            topic="haptic simulation",
            sources=[paper],
            selected_metrics=["Haptic Robot Support"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        assert result.changes[0].new_status == "YES"

    def test_ai_support_no_for_no_mention(self):
        """Test AI Support: NO when AI/ML not mentioned."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="Traditional Physics Simulation",
            relevance_explanation="Uses classical mechanics.",
        )

        initial_matrix = [create_test_evaluation(paper, "AI Support", status="full")]

        result = agent.validate_matrix(
            topic="AI simulation",
            sources=[paper],
            selected_metrics=["AI Support"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        assert result.changes[0].new_status == "NO"

    def test_ai_support_yes_for_ml_mention(self):
        """Test AI Support: YES when ML mentioned."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="Machine Learning for Soft Body Simulation",
            relevance_explanation="Uses deep learning to predict deformations.",
        )

        initial_matrix = [create_test_evaluation(paper, "AI Support", status="none")]

        result = agent.validate_matrix(
            topic="AI simulation",
            sources=[paper],
            selected_metrics=["AI Support"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        assert result.changes[0].new_status == "YES"

    def test_patent_metric_yes_for_patents(self):
        """Test Patent metric: YES for patent sources."""
        agent = ComparisonAgent()

        patent = create_test_patent(
            title="Soft Body Simulation Patent",
            patent_number="US12345678",
        )

        initial_matrix = [create_test_evaluation(patent, "Patent", status="none")]

        result = agent.validate_matrix(
            topic="test",
            sources=[patent],
            selected_metrics=["Patent"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        assert result.changes[0].new_status == "YES"

    def test_vr_hmd_yes_for_explicit_mention(self):
        """Test VR HMD Integration: YES when explicit."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="VR Surgical Training with HMD",
            relevance_explanation="Uses Oculus VR headset.",
        )

        initial_matrix = [create_test_evaluation(paper, "VR HMD Integration", status="none")]

        result = agent.validate_matrix(
            topic="VR simulation",
            sources=[paper],
            selected_metrics=["VR HMD Integration"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        assert result.changes[0].new_status == "YES"


class TestComparisonAgentValidation:
    """Test overall validation logic."""

    def test_no_changes_when_all_correct(self):
        """Test that validation makes no changes when matrix is correct."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="Open Access Paper",
            pdf_url="https://arxiv.org/pdf/1234.pdf",
        )

        initial_matrix = [create_test_evaluation(paper, "Open Access", status="full")]

        result = agent.validate_matrix(
            topic="test",
            sources=[paper],
            selected_metrics=["Open Access"],
            initial_matrix=initial_matrix,
        )

        assert result.cells_reviewed == 1
        assert result.cells_changed == 0
        assert len(result.changes) == 0

    def test_multiple_sources_multiple_metrics(self):
        """Test validation with multiple sources and metrics."""
        agent = ComparisonAgent()

        # Use different DOIs to avoid confusion
        paper1 = ScoredSourceItem(
            title="XPBD Paper",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper1",
            publication_date="2024-01-01",
            author_or_assignee="Author 1",
            relevance_explanation="Uses XPBD for simulation.",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1234/paper1",
            raw_adapter_source="test",
            relevance_score=0.9,
            is_open_access=True,
            pdf_url="https://arxiv.org/pdf/1234.pdf",
        )

        paper2 = ScoredSourceItem(
            title="Closed Paper",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper2",
            publication_date="2024-01-01",
            author_or_assignee="Author 2",
            relevance_explanation="No XPBD mentioned.",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1234/paper2",
            raw_adapter_source="test",
            relevance_score=0.8,
            is_open_access=False,
            pdf_url=None,
        )

        # Create matrix with some incorrect values
        eval1 = SourceMetricEvaluation(
            source_id="10.1234/paper1",
            source_title="XPBD Paper",
            source_type="paper",
            metric_evaluations=[
                MetricEvaluation(
                    metric_name="XPBD Support",
                    status="none",  # Should be full
                    symbol="❌",
                    score=0.0,
                    evidence="Initial",
                    confidence="medium",
                ),
                MetricEvaluation(
                    metric_name="Open Access",
                    status="full",  # Correct
                    symbol="✅",
                    score=1.0,
                    evidence="Initial",
                    confidence="high",
                ),
            ],
            overall_score=0.5,
        )

        eval2 = SourceMetricEvaluation(
            source_id="10.1234/paper2",
            source_title="Closed Paper",
            source_type="paper",
            metric_evaluations=[
                MetricEvaluation(
                    metric_name="XPBD Support",
                    status="none",  # Correct
                    symbol="❌",
                    score=0.0,
                    evidence="Initial",
                    confidence="medium",
                ),
                MetricEvaluation(
                    metric_name="Open Access",
                    status="full",  # Should be none
                    symbol="✅",
                    score=1.0,
                    evidence="Initial",
                    confidence="high",
                ),
            ],
            overall_score=0.5,
        )

        result = agent.validate_matrix(
            topic="XPBD simulation",
            sources=[paper1, paper2],
            selected_metrics=["XPBD Support", "Open Access"],
            initial_matrix=[eval1, eval2],
        )

        # Should find 3 changes (paper1 XPBD: none->full, paper2 XPBD: none->full, paper2 Open Access: full->none)
        # Paper 1's Open Access stays full (correct)
        assert result.cells_reviewed == 4
        assert result.cells_changed == 3
        assert len(result.changes) == 3

    def test_confidence_score_calculation(self):
        """Test that confidence score is calculated correctly."""
        agent = ComparisonAgent()

        paper = create_test_paper(
            title="Test Paper",
            pdf_url="https://arxiv.org/pdf/1234.pdf",
        )

        initial_matrix = [create_test_evaluation(paper, "Open Access", status="none")]

        result = agent.validate_matrix(
            topic="test",
            sources=[paper],
            selected_metrics=["Open Access"],
            initial_matrix=initial_matrix,
        )

        # Confidence should be high (1.0) for rule-based Open Access validation
        assert result.confidence_score == 1.0

    def test_fallback_on_missing_source(self):
        """Test that validation handles sources not in the lookup."""
        agent = ComparisonAgent()

        # Create papers with different DOIs
        paper1 = ScoredSourceItem(
            title="Paper 1",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper1",
            publication_date="2024-01-01",
            author_or_assignee="Author 1",
            relevance_explanation="Test",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1234/paper1",
            raw_adapter_source="test",
            relevance_score=0.9,
        )

        paper2 = ScoredSourceItem(
            title="Paper 2",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper2",
            publication_date="2024-01-01",
            author_or_assignee="Author 2",
            relevance_explanation="Test",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1234/paper2",
            raw_adapter_source="test",
            relevance_score=0.8,
        )

        # Create evaluation for paper2 with correct source_id
        eval2 = SourceMetricEvaluation(
            source_id="10.1234/paper2",
            source_title="Paper 2",
            source_type="paper",
            metric_evaluations=[
                MetricEvaluation(
                    metric_name="Open Access",
                    status="full",
                    symbol="✅",
                    score=1.0,
                    evidence="Initial",
                    confidence="high",
                )
            ],
            overall_score=1.0,
        )

        result = agent.validate_matrix(
            topic="test",
            sources=[paper1],  # Only paper1, paper2 missing
            selected_metrics=["Open Access"],
            initial_matrix=[eval2],
        )

        # Source not in lookup should be skipped (not reviewed or changed)
        # The agent correctly keeps the original evaluation but doesn't process it
        assert len(result.validated_matrix) == 1
        assert result.validated_matrix[0].source_id == "10.1234/paper2"


class TestComparisonAgentLLMValidation:
    """Test LLM-based validation (when rules don't apply)."""

    def test_llm_validation_with_mock(self):
        """Test LLM validation with a mock LLM client."""
        # Create mock LLM
        mock_llm = Mock()
        mock_llm.last_call_metadata = {
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        }

        # Mock response
        from pydantic import BaseModel, Field
        from typing import Optional, Literal

        class ValidationResponse(BaseModel):
            validated_status: Literal["full", "partial", "none"]
            confidence: Literal["high", "medium", "low"]
            evidence: str
            changed: bool
            reason_for_change: Optional[str]

        mock_response = ValidationResponse(
            validated_status="partial",
            confidence="medium",
            evidence="Metric is partially supported.",
            changed=True,
            reason_for_change="LLM review found partial support.",
        )

        mock_llm.chat_json = Mock(return_value=mock_response)

        agent = ComparisonAgent(llm_client=mock_llm)

        paper = create_test_paper(
            title="Custom Metric Paper",
            relevance_explanation="Some custom content.",
        )

        initial_matrix = [create_test_evaluation(paper, "Custom Metric", status="full")]

        result = agent.validate_matrix(
            topic="test",
            sources=[paper],
            selected_metrics=["Custom Metric"],
            initial_matrix=initial_matrix,
        )

        # Should use LLM for custom metric
        assert mock_llm.chat_json.called
        assert result.cells_reviewed == 1
        assert result.cells_changed == 1
        assert result.changes[0].new_status == "PART"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
