"""Unit tests for the RankingEngine."""

import pytest
from unittest.mock import Mock, patch

from ria.models import RawSourceItem, SourceType, ConfidenceLevel, ScoredSourceItem
from ria.ranking import RankingEngine, RelevanceScore


@pytest.fixture
def mock_llm():
    """Create a mock LLM client."""
    return Mock()


@pytest.fixture
def sample_raw_items():
    """Create sample raw items for testing."""
    return [
        RawSourceItem(
            title="XPBD Position Based Dynamics",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper1",
            publication_date="2023-01-15",
            author_or_assignee="John Doe",
            relevance_explanation="Original abstract about XPBD simulation",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1234/example",
            raw_adapter_source="semantic_scholar",
        ),
        RawSourceItem(
            title="Soft Body Physics Patent",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US123456",
            publication_date="2022-06-01",
            author_or_assignee="Tech Corp",
            relevance_explanation="Patent abstract about soft body simulation",
            confidence_level=ConfidenceLevel.MEDIUM,
            patent_number="US123456",
            raw_adapter_source="serpapi_patents",
        ),
    ]


class TestRankingEngine:
    """Tests for the RankingEngine class."""

    def test_deduplicate_by_title(self, mock_llm):
        """Test deduplication by normalized title."""
        engine = RankingEngine(mock_llm)
        items = [
            RawSourceItem(
                title="Test Paper",
                source_type=SourceType.PAPER,
                source_url="url1",
                raw_adapter_source="test",
            ),
            RawSourceItem(
                title="TEST  PAPER",  # Same title, different spacing/case
                source_type=SourceType.PAPER,
                source_url="url2",
                raw_adapter_source="test",
            ),
            RawSourceItem(
                title="Different Paper",
                source_type=SourceType.PAPER,
                source_url="url3",
                raw_adapter_source="test",
            ),
        ]

        result = engine.deduplicate(items)
        assert len(result) == 2
        assert result[0].title == "Test Paper"
        assert result[1].title == "Different Paper"

    def test_deduplicate_by_doi(self, mock_llm):
        """Test deduplication by DOI."""
        engine = RankingEngine(mock_llm)
        items = [
            RawSourceItem(
                title="Paper One",
                source_type=SourceType.PAPER,
                source_url="url1",
                doi="10.1234/test",
                raw_adapter_source="test",
            ),
            RawSourceItem(
                title="Paper Two",  # Different title, same DOI
                source_type=SourceType.PAPER,
                source_url="url2",
                doi="10.1234/TEST",  # Different case
                raw_adapter_source="test",
            ),
        ]

        result = engine.deduplicate(items)
        assert len(result) == 1
        assert result[0].title == "Paper One"

    def test_deduplicate_by_patent_number(self, mock_llm):
        """Test deduplication by patent number."""
        engine = RankingEngine(mock_llm)
        items = [
            RawSourceItem(
                title="Patent One",
                source_type=SourceType.PATENT,
                source_url="url1",
                patent_number="US123456",
                raw_adapter_source="test",
            ),
            RawSourceItem(
                title="Patent Two",  # Different title, same patent number
                source_type=SourceType.PATENT,
                source_url="url2",
                patent_number="us123456",  # Different case
                raw_adapter_source="test",
            ),
        ]

        result = engine.deduplicate(items)
        assert len(result) == 1
        assert result[0].title == "Patent One"

    def test_score_success(self, mock_llm, sample_raw_items):
        """Test successful scoring of items."""
        engine = RankingEngine(mock_llm)

        # Mock LLM to return a relevance score
        mock_llm.chat_json.return_value = RelevanceScore(
            score=0.85,
            reasoning="Highly relevant to XPBD simulation"
        )

        result = engine.score(sample_raw_items, "XPBD simulation")

        assert len(result) == 2
        assert all(isinstance(item, ScoredSourceItem) for item in result)
        assert result[0].relevance_score == 0.85
        assert result[0].relevance_explanation == "Highly relevant to XPBD simulation"
        assert result[1].relevance_score == 0.85
        assert result[1].relevance_explanation == "Highly relevant to XPBD simulation"

    def test_score_with_llm_failure(self, mock_llm, sample_raw_items):
        """Test scoring when LLM fails - should assign default score."""
        engine = RankingEngine(mock_llm)

        # Mock LLM to raise an exception
        mock_llm.chat_json.side_effect = Exception("API rate limit exceeded")

        result = engine.score(sample_raw_items, "XPBD simulation")

        # Should still return scored items with default scores
        assert len(result) == 2
        assert all(isinstance(item, ScoredSourceItem) for item in result)
        assert result[0].relevance_score == 0.0
        assert "Scoring failed" in result[0].relevance_explanation
        assert "API rate limit exceeded" in result[0].relevance_explanation
        assert result[1].relevance_score == 0.0
        assert "Scoring failed" in result[1].relevance_explanation

    def test_score_preserves_original_fields(self, mock_llm, sample_raw_items):
        """Test that scoring preserves all original fields from RawSourceItem."""
        engine = RankingEngine(mock_llm)

        mock_llm.chat_json.return_value = RelevanceScore(
            score=0.75,
            reasoning="New relevance reasoning"
        )

        result = engine.score(sample_raw_items, "test topic")

        # Check that original fields are preserved
        paper = result[0]
        assert paper.title == "XPBD Position Based Dynamics"
        assert paper.source_type == SourceType.PAPER
        assert paper.source_url == "https://example.com/paper1"
        assert paper.publication_date == "2023-01-15"
        assert paper.author_or_assignee == "John Doe"
        assert paper.confidence_level == ConfidenceLevel.HIGH
        assert paper.doi == "10.1234/example"
        assert paper.raw_adapter_source == "semantic_scholar"

        # Check that relevance_explanation is updated (not duplicated)
        assert paper.relevance_explanation == "New relevance reasoning"
        assert paper.relevance_score == 0.75

    def test_select_top_papers_and_patents(self, mock_llm):
        """Test selection of top papers and patents."""
        engine = RankingEngine(mock_llm)

        scored_items = [
            ScoredSourceItem(
                title="Paper A",
                source_type=SourceType.PAPER,
                source_url="url1",
                raw_adapter_source="test",
                relevance_score=0.9,
            ),
            ScoredSourceItem(
                title="Paper B",
                source_type=SourceType.PAPER,
                source_url="url2",
                raw_adapter_source="test",
                relevance_score=0.7,
            ),
            ScoredSourceItem(
                title="Paper C",
                source_type=SourceType.PAPER,
                source_url="url3",
                raw_adapter_source="test",
                relevance_score=0.8,
            ),
            ScoredSourceItem(
                title="Patent X",
                source_type=SourceType.PATENT,
                source_url="url4",
                raw_adapter_source="test",
                relevance_score=0.95,
            ),
            ScoredSourceItem(
                title="Patent Y",
                source_type=SourceType.PATENT,
                source_url="url5",
                raw_adapter_source="test",
                relevance_score=0.6,
            ),
        ]

        top_papers, top_patents = engine.select_top(scored_items, top_n=2)

        # Should select top 2 papers by score
        assert len(top_papers) == 2
        assert top_papers[0].title == "Paper A"
        assert top_papers[0].relevance_score == 0.9
        assert top_papers[1].title == "Paper C"
        assert top_papers[1].relevance_score == 0.8

        # Should select top 2 patents by score (only 2 available)
        assert len(top_patents) == 2
        assert top_patents[0].title == "Patent X"
        assert top_patents[0].relevance_score == 0.95
        assert top_patents[1].title == "Patent Y"
        assert top_patents[1].relevance_score == 0.6

    def test_select_top_with_fewer_items_than_top_n(self, mock_llm):
        """Test selection when there are fewer items than top_n."""
        engine = RankingEngine(mock_llm)

        scored_items = [
            ScoredSourceItem(
                title="Paper A",
                source_type=SourceType.PAPER,
                source_url="url1",
                raw_adapter_source="test",
                relevance_score=0.9,
            ),
        ]

        top_papers, top_patents = engine.select_top(scored_items, top_n=3)

        assert len(top_papers) == 1
        assert len(top_patents) == 0
