"""
Unit tests for Semantic Scholar adapter.

Tests the SemanticScholarAdapter with mocked HTTP responses to verify
parsing logic without making real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from ria.adapters.semantic_scholar import SemanticScholarAdapter
from ria.models import ConfidenceLevel, SourceType


@pytest.fixture
def mock_semantic_scholar_response():
    """Mock Semantic Scholar API response with sample paper results."""
    return {
        "total": 1234,
        "offset": 0,
        "next": 100,
        "data": [
            {
                "paperId": "abc123def456",
                "title": "XPBD: Position-Based Simulation of Compliant Constrained Dynamics",
                "abstract": "We present an extension of Position Based Dynamics (PBD) to simulate compliant constrained dynamics. The method is based on extending constraints with compliance parameters...",
                "authors": [
                    {"authorId": "12345", "name": "Miles Macklin"},
                    {"authorId": "67890", "name": "Matthias Müller"},
                ],
                "year": 2016,
                "publicationDate": "2016-07-01",
                "venue": "ACM SIGGRAPH",
                "citationCount": 245,
                "isOpenAccess": True,
                "openAccessPdf": {
                    "url": "https://dl.acm.org/doi/pdf/10.1145/2994258.2994272",
                    "status": "GOLD",
                },
                "externalIds": {
                    "DOI": "10.1145/2994258.2994272",
                    "ArXiv": "1606.00000",
                },
                "url": "https://www.semanticscholar.org/paper/abc123def456",
                "tldr": {
                    "text": "An extension of Position Based Dynamics for compliant constraints.",
                },
            },
            {
                "paperId": "xyz789uvw012",
                "title": "Position Based Dynamics",
                "abstract": "The most popular approaches for the simulation of dynamic systems in computer graphics are force based. They compute forces acting on each object...",
                "authors": [
                    {"authorId": "11111", "name": "Matthias Müller"},
                    {"authorId": "22222", "name": "Bruno Heidelberger"},
                ],
                "year": 2007,
                "publicationDate": "2007-08-01",
                "venue": "Journal of Visual Communication",
                "citationCount": 892,
                "isOpenAccess": False,
                "openAccessPdf": None,
                "externalIds": {
                    "DOI": "10.1016/j.jvcir.2007.01.005",
                },
                "url": "https://www.semanticscholar.org/paper/xyz789uvw012",
            },
            {
                "paperId": "paper_minimal",
                "title": "Minimal Paper Entry",
                # Missing abstract, authors, year, externalIds
                "url": None,  # Will test URL construction from paperId
                "isOpenAccess": False,
                "citationCount": 0,
            },
        ],
    }


@pytest.fixture
def mock_empty_response():
    """Mock Semantic Scholar API response with no results."""
    return {
        "total": 0,
        "offset": 0,
        "data": [],
    }


class TestSemanticScholarAdapter:
    """Test suite for SemanticScholarAdapter."""

    def test_initialization_defaults(self):
        """Test adapter initialization with default values."""
        adapter = SemanticScholarAdapter()
        assert adapter.base_url == "https://api.semanticscholar.org/graph/v1"
        assert adapter.timeout == 30.0
        assert adapter.source_type == SourceType.PAPER

    def test_initialization_custom(self):
        """Test adapter initialization with custom values."""
        adapter = SemanticScholarAdapter(
            base_url="https://custom.api.com",
            timeout=60.0,
        )
        assert adapter.base_url == "https://custom.api.com"
        assert adapter.timeout == 60.0

    def test_build_search_params(self):
        """Test query parameter construction."""
        adapter = SemanticScholarAdapter()
        params = adapter._build_search_params("XPBD algorithm", 50)

        assert params["query"] == "XPBD algorithm"
        assert params["limit"] == 50
        assert params["fields"] == "paperId,title,authors,abstract,year,venue,url,citationCount,externalIds,openAccessPdf,isOpenAccess,tldr"

    def test_build_search_params_max_limit(self):
        """Test query parameter construction respects API max limit."""
        adapter = SemanticScholarAdapter()
        params = adapter._build_search_params("test", 200)

        # Should be capped at 100 (API max)
        assert params["limit"] == 100

    @pytest.mark.asyncio
    async def test_search_success(self, mock_semantic_scholar_response):
        """Test successful paper search with mocked response."""
        adapter = SemanticScholarAdapter()

        # Mock the HTTP client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock the response
            mock_response = Mock()
            mock_response.json = Mock(return_value=mock_semantic_scholar_response)
            mock_response.raise_for_status = Mock(return_value=None)
            mock_response.status_code = 200
            mock_client.get = AsyncMock(return_value=mock_response)

            # Execute search
            results = await adapter.search("test query", max_results=10)

            # Should prioritize open access papers
            assert len(results) <= 3

            # Find the open access paper (should be first or included)
            open_access_papers = [r for r in results if r.is_open_access or r.pdf_url]
            assert len(open_access_papers) >= 1

            # Check open access paper
            oa_paper = [r for r in results if r.title == "XPBD: Position-Based Simulation of Compliant Constrained Dynamics"]
            if oa_paper:
                paper = oa_paper[0]
                assert paper.author_or_assignee == "Miles Macklin, Matthias Müller"
                assert paper.publication_date == "2016-07-01"
                assert paper.doi == "10.1145/2994258.2994272"
                assert paper.source_url == "https://www.semanticscholar.org/paper/abc123def456"
                assert paper.source_type == SourceType.PAPER
                assert paper.raw_adapter_source == "semantic_scholar"
                assert paper.confidence_level == ConfidenceLevel.HIGH
                assert paper.venue == "ACM SIGGRAPH"
                assert paper.citation_count == 245
                assert paper.is_open_access is True
                assert paper.pdf_url == "https://dl.acm.org/doi/pdf/10.1145/2994258.2994272"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mock_empty_response):
        """Test search with no results."""
        adapter = SemanticScholarAdapter()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.json = Mock(return_value=mock_empty_response)
            mock_response.raise_for_status = Mock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)

            results = await adapter.search("nonexistent paper", max_results=10)

            assert results == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        """Test search with HTTP error."""
        adapter = SemanticScholarAdapter()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Simulate HTTP 500 error
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status = Mock(
                side_effect=httpx.HTTPStatusError(
                    "Server error", request=Mock(), response=mock_response
                )
            )
            mock_client.get = AsyncMock(return_value=mock_response)

            results = await adapter.search("test query", max_results=10)

            assert results == []

    @pytest.mark.asyncio
    async def test_search_network_error(self):
        """Test search with network error."""
        adapter = SemanticScholarAdapter()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Simulate network error
            mock_client.get = AsyncMock(
                side_effect=httpx.RequestError("Connection timeout")
            )

            results = await adapter.search("test query", max_results=10)

            assert results == []

    @pytest.mark.asyncio
    async def test_search_rate_limit_error(self):
        """Test search with rate limit error (HTTP 429)."""
        adapter = SemanticScholarAdapter()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Simulate HTTP 429 error
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.raise_for_status = Mock(
                side_effect=httpx.HTTPStatusError(
                    "Rate limit exceeded", request=Mock(), response=mock_response
                )
            )
            mock_client.get = AsyncMock(return_value=mock_response)

            results = await adapter.search("test query", max_results=10)

            assert results == []

    def test_parse_paper_result_missing_title(self):
        """Test parsing skips results with no title."""
        adapter = SemanticScholarAdapter()

        result = {
            "paperId": "abc123",
            # Missing title
            "url": "https://example.com",
        }

        item = adapter._parse_paper_result(result)
        assert item is None

    def test_parse_paper_result_missing_paper_id(self):
        """Test parsing skips results with no paperId."""
        adapter = SemanticScholarAdapter()

        result = {
            "title": "Test Paper",
            # Missing paperId
            "url": "https://example.com",
        }

        item = adapter._parse_paper_result(result)
        assert item is None

    def test_parse_paper_result_year_only(self):
        """Test parsing handles year without publicationDate."""
        adapter = SemanticScholarAdapter()

        result = {
            "paperId": "abc123",
            "title": "Test Paper",
            "year": 2020,
            # No publicationDate
            "url": "https://example.com",
        }

        item = adapter._parse_paper_result(result)
        assert item is not None
        assert item["publication_date"] == "2020"

    def test_parse_paper_result_long_abstract(self):
        """Test parsing truncates long abstracts in relevance_explanation."""
        adapter = SemanticScholarAdapter()

        long_abstract = "A" * 300  # 300 characters

        result = {
            "paperId": "abc123",
            "title": "Test Paper",
            "abstract": long_abstract,
            "url": "https://example.com",
        }

        item = adapter._parse_paper_result(result)
        assert item is not None
        assert len(item["relevance_explanation"]) == 203  # 200 + "..."
        assert item["relevance_explanation"].endswith("...")

    def test_parse_paper_result_no_authors(self):
        """Test parsing handles missing or empty authors list."""
        adapter = SemanticScholarAdapter()

        result = {
            "paperId": "abc123",
            "title": "Test Paper",
            "authors": [],  # Empty authors list
            "url": "https://example.com",
        }

        item = adapter._parse_paper_result(result)
        assert item is not None
        assert item["authors"] is None

    def test_expand_query_xpbd(self):
        """Test query expansion for XPBD acronym."""
        adapter = SemanticScholarAdapter()

        queries = adapter._expand_query("XPBD")
        assert len(queries) == 5
        assert "XPBD" in queries
        assert "Extended Position Based Dynamics" in queries
        assert "XPBD position based dynamics" in queries
        assert "Position Based Dynamics compliant constraints" in queries
        assert "real-time simulation XPBD" in queries

    def test_expand_query_xpbd_in_phrase(self):
        """Test query expansion when XPBD is in a phrase."""
        adapter = SemanticScholarAdapter()

        queries = adapter._expand_query("XPBD simulation algorithm")
        assert len(queries) == 5
        assert "XPBD simulation algorithm" in queries

    def test_expand_query_no_expansion(self):
        """Test query expansion for non-acronym queries."""
        adapter = SemanticScholarAdapter()

        queries = adapter._expand_query("machine learning")
        assert len(queries) == 1
        assert queries[0] == "machine learning"

    def test_deduplicate_papers_by_paper_id(self):
        """Test deduplication by paperId."""
        adapter = SemanticScholarAdapter()

        papers = [
            {"paper_id": "123", "title": "Paper A", "doi": None},
            {"paper_id": "123", "title": "Paper A Duplicate", "doi": None},
            {"paper_id": "456", "title": "Paper B", "doi": None},
        ]

        unique = adapter._deduplicate_papers(papers)
        assert len(unique) == 2
        assert unique[0]["paper_id"] == "123"
        assert unique[1]["paper_id"] == "456"

    def test_deduplicate_papers_by_doi(self):
        """Test deduplication by DOI."""
        adapter = SemanticScholarAdapter()

        papers = [
            {"paper_id": "123", "title": "Paper A", "doi": "10.1234/test"},
            {"paper_id": "456", "title": "Paper A", "doi": "10.1234/test"},
            {"paper_id": "789", "title": "Paper B", "doi": "10.5678/other"},
        ]

        unique = adapter._deduplicate_papers(papers)
        assert len(unique) == 2
        assert unique[0]["doi"] == "10.1234/test"
        assert unique[1]["doi"] == "10.5678/other"

    def test_deduplicate_papers_by_title(self):
        """Test deduplication by normalized title."""
        adapter = SemanticScholarAdapter()

        papers = [
            {"paper_id": "123", "title": "Machine Learning   for Physics", "doi": None},
            {"paper_id": "456", "title": "machine learning FOR physics", "doi": None},
            {"paper_id": "789", "title": "Deep Learning", "doi": None},
        ]

        unique = adapter._deduplicate_papers(papers)
        assert len(unique) == 2
        # First title should be kept
        assert unique[0]["paper_id"] == "123"
        assert unique[1]["paper_id"] == "789"
