"""
Unit tests for SerpAPI patent adapter.

Tests the SerpAPIPatentAdapter with mocked HTTP responses to verify
parsing logic without making real API calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from ria.adapters.serpapi_patents import SerpAPIPatentAdapter
from ria.models import ConfidenceLevel, SourceType


@pytest.fixture
def mock_serpapi_response():
    """Mock SerpAPI response with sample patent results."""
    return {
        "search_metadata": {
            "status": "Success",
        },
        "organic_results": [
            {
                "title": "Position based dynamics",
                "patent_id": "US8620641B1",
                "assignee": "Google Inc",
                "publication_date": "2013-12-31",
                "snippet": "A method for simulating soft body physics using position-based dynamics",
                "pdf": "https://patents.google.com/patent/US8620641B1/en?oq=XPBD",
            },
            {
                "title": "Extended position based dynamics for soft body simulation",
                "patent_id": "US9999999A",
                "assignee": "MIT",
                "publication_date": "2020-05-15",
                "snippet": "An extension of XPBD algorithm for real-time simulation",
                "pdf": "https://patents.google.com/patent/US9999999A/en",
            },
            {
                "title": "Physics simulation method",
                "patent_id": "US1111111B2",
                "assignee": None,  # Missing assignee
                "publication_date": None,  # Missing date
                "snippet": "Generic physics simulation method",
                # No PDF provided - should construct URL from patent_id
            },
        ],
    }


@pytest.fixture
def mock_empty_response():
    """Mock SerpAPI response with no results."""
    return {
        "search_metadata": {
            "status": "Success",
        },
        "organic_results": [],
    }


@pytest.fixture
def mock_error_response():
    """Mock SerpAPI response with an error."""
    return {
        "error": "Invalid API key provided",
    }


class TestSerpAPIPatentAdapter:
    """Test suite for SerpAPIPatentAdapter."""

    def test_initialization_with_api_key(self):
        """Test adapter initialization with explicit API key."""
        adapter = SerpAPIPatentAdapter(api_key="test_key_12345")
        assert adapter.api_key == "test_key_12345"
        assert adapter.source_type == SourceType.PATENT

    def test_initialization_without_api_key(self):
        """Test adapter initialization fails without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="SERPAPI_API_KEY must be set"):
                SerpAPIPatentAdapter()

    def test_initialization_from_env(self):
        """Test adapter initialization from environment variable."""
        with patch.dict("os.environ", {"SERPAPI_API_KEY": "env_key_123"}):
            adapter = SerpAPIPatentAdapter()
            assert adapter.api_key == "env_key_123"

    def test_build_search_params(self):
        """Test query parameter construction."""
        adapter = SerpAPIPatentAdapter(api_key="test_key")
        params = adapter._build_search_params("XPBD algorithm", 50)

        assert params["engine"] == "google_patents"
        assert params["q"] == "XPBD algorithm"
        assert params["num"] == 50
        assert params["api_key"] == "test_key"

    def test_build_search_params_min_limit(self):
        """Test query parameter construction respects SerpAPI min limit."""
        adapter = SerpAPIPatentAdapter(api_key="test_key")
        params = adapter._build_search_params("test", 5)

        # Should be clamped to 10 (SerpAPI min)
        assert params["num"] == 10

    def test_build_search_params_max_limit(self):
        """Test query parameter construction respects SerpAPI max limit."""
        adapter = SerpAPIPatentAdapter(api_key="test_key")
        params = adapter._build_search_params("test", 150)

        # Should be capped at 100 (SerpAPI max)
        assert params["num"] == 100

    @pytest.mark.asyncio
    async def test_search_success(self, mock_serpapi_response):
        """Test successful patent search with mocked response."""
        adapter = SerpAPIPatentAdapter(api_key="test_key")

        # Mock the HTTP client
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Mock the response - json() is synchronous in httpx
            mock_response = Mock()
            mock_response.json = Mock(return_value=mock_serpapi_response)
            mock_response.raise_for_status = Mock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)

            # Execute search
            results = await adapter.search("XPBD algorithm", max_results=10)

            # Verify results
            assert len(results) == 3

            # Check first result
            assert results[0].title == "Position based dynamics"
            assert results[0].patent_number == "US8620641B1"
            assert results[0].author_or_assignee == "Google Inc"
            assert results[0].publication_date == "2013-12-31"
            assert results[0].source_url == "https://patents.google.com/patent/US8620641B1/en?oq=XPBD"
            assert results[0].source_type == SourceType.PATENT
            assert results[0].raw_adapter_source == "serpapi_patents"
            assert results[0].confidence_level == ConfidenceLevel.HIGH
            assert "position-based dynamics" in results[0].relevance_explanation

            # Check second result
            assert results[1].patent_number == "US9999999A"
            assert results[1].author_or_assignee == "MIT"

            # Check third result (missing fields)
            assert results[2].patent_number == "US1111111B2"
            assert results[2].author_or_assignee is None
            assert results[2].publication_date is None
            # URL should be constructed from patent_id
            assert results[2].source_url == "https://patents.google.com/patent/US1111111B2"

    @pytest.mark.asyncio
    async def test_search_empty_results(self, mock_empty_response):
        """Test search with no results."""
        adapter = SerpAPIPatentAdapter(api_key="test_key")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.json = Mock(return_value=mock_empty_response)
            mock_response.raise_for_status = Mock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)

            results = await adapter.search("nonexistent patent", max_results=10)

            assert results == []

    @pytest.mark.asyncio
    async def test_search_api_error(self, mock_error_response):
        """Test search with API error response."""
        adapter = SerpAPIPatentAdapter(api_key="invalid_key")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.json = Mock(return_value=mock_error_response)
            mock_response.raise_for_status = Mock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)

            results = await adapter.search("test query", max_results=10)

            assert results == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        """Test search with HTTP error."""
        adapter = SerpAPIPatentAdapter(api_key="test_key")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Simulate HTTP 500 error
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.raise_for_status = Mock(side_effect=httpx.HTTPStatusError(
                "Server error", request=Mock(), response=mock_response
            ))
            mock_client.get = AsyncMock(return_value=mock_response)

            results = await adapter.search("test query", max_results=10)

            assert results == []

    @pytest.mark.asyncio
    async def test_search_network_error(self):
        """Test search with network error."""
        adapter = SerpAPIPatentAdapter(api_key="test_key")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            # Simulate network error
            mock_client.get = AsyncMock(side_effect=httpx.RequestError("Connection timeout"))

            results = await adapter.search("test query", max_results=10)

            assert results == []

    @pytest.mark.asyncio
    async def test_search_max_results_limit(self, mock_serpapi_response):
        """Test that max_results correctly limits returned items."""
        adapter = SerpAPIPatentAdapter(api_key="test_key")

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client

            mock_response = Mock()
            mock_response.json = Mock(return_value=mock_serpapi_response)
            mock_response.raise_for_status = Mock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)

            # Request only 2 results
            results = await adapter.search("test", max_results=2)

            assert len(results) == 2

    def test_parse_patent_result_missing_title(self):
        """Test parsing skips results with no title."""
        adapter = SerpAPIPatentAdapter(api_key="test_key")

        result = {
            "patent_id": "US1234567A",
            # Missing title
        }

        item = adapter._parse_patent_result(result)
        assert item is None

    def test_parse_patent_result_missing_url(self):
        """Test parsing skips results with no URL or patent_id."""
        adapter = SerpAPIPatentAdapter(api_key="test_key")

        result = {
            "title": "Test Patent",
            # Missing both pdf and patent_id
        }

        item = adapter._parse_patent_result(result)
        assert item is None
