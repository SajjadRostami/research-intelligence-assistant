"""
SerpAPI patent search adapter.

This adapter queries the Google Patents database through SerpAPI's
structured API. It provides reliable patent search results without
web scraping, using SerpAPI's google_patents search engine.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from ria.adapters.base import SearchAdapter
from ria.models import ConfidenceLevel, RawSourceItem, SourceType

logger = logging.getLogger(__name__)


class SerpAPIPatentAdapter(SearchAdapter):
    """
    Adapter for searching patents using SerpAPI's Google Patents engine.

    This adapter uses SerpAPI to query the Google Patents database and returns
    structured patent results. It requires a valid SERPAPI_API_KEY from environment
    variables.

    Attributes:
        source_type: Always SourceType.PATENT
        api_key: SerpAPI authentication key
        base_url: SerpAPI base URL
    """

    source_type = SourceType.PATENT

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://serpapi.com/search",
    ):
        """
        Initialize the SerpAPI patent adapter.

        Args:
            api_key: SerpAPI API key. If None, reads from SERPAPI_API_KEY env var
            base_url: SerpAPI base URL (default: https://serpapi.com/search)

        Raises:
            ValueError: If no API key is provided or found in environment
        """
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "SERPAPI_API_KEY must be set in environment or passed to constructor"
            )
        self.base_url = base_url

    def _build_search_params(self, query: str, num_results: int) -> dict[str, Any]:
        """
        Build SerpAPI query parameters for Google Patents search.

        Args:
            query: The search query string
            num_results: Number of results to request

        Returns:
            Dictionary of query parameters for SerpAPI
        """
        # SerpAPI requires num to be between 10 and 100 for google_patents
        num_clamped = max(10, min(num_results, 100))

        return {
            "engine": "google_patents",
            "q": query,
            "num": num_clamped,
            "api_key": self.api_key,
        }

    def _parse_patent_result(self, result: dict[str, Any]) -> RawSourceItem | None:
        """
        Parse a single patent result from SerpAPI response.

        Extracts all available fields from the SerpAPI result structure:
        - title
        - patent_id (patent number)
        - assignee
        - publication_date
        - snippet (abstract/description)
        - pdf (URL to patent document)

        Args:
            result: Single patent result dictionary from SerpAPI

        Returns:
            RawSourceItem if parsing succeeds, None otherwise
        """
        try:
            title = result.get("title", "").strip()
            if not title:
                logger.warning("Skipping result with no title")
                return None

            # Extract patent number (e.g., "US1234567A")
            patent_number = result.get("patent_id", "").strip()

            # Extract assignee (patent holder)
            assignee_raw = result.get("assignee")
            assignee = assignee_raw.strip() if assignee_raw else None

            # Extract publication date
            pub_date_raw = result.get("publication_date")
            publication_date = pub_date_raw.strip() if pub_date_raw else None

            # Extract abstract/snippet
            snippet_raw = result.get("snippet")
            snippet = snippet_raw.strip() if snippet_raw else None

            # Build patent URL - SerpAPI provides a PDF link or we can construct from patent_id
            pdf_url = result.get("pdf")
            if pdf_url:
                source_url = pdf_url
            elif patent_number:
                # Construct Google Patents URL
                source_url = f"https://patents.google.com/patent/{patent_number}"
            else:
                logger.warning(f"No URL available for patent: {title}")
                return None

            return RawSourceItem(
                title=title,
                source_type=SourceType.PATENT,
                source_url=source_url,
                publication_date=publication_date,
                author_or_assignee=assignee,
                patent_number=patent_number,
                relevance_explanation=snippet,
                confidence_level=ConfidenceLevel.HIGH,  # Structured API data
                raw_adapter_source="serpapi_patents",
            )

        except Exception as e:
            logger.warning(f"Failed to parse patent result: {e}", exc_info=True)
            return None

    async def search(self, query: str, max_results: int = 10) -> list[RawSourceItem]:
        """
        Execute a patent search query via SerpAPI.

        This method:
        1. Constructs SerpAPI query parameters for Google Patents
        2. Makes an async HTTP request to SerpAPI
        3. Parses the JSON response and extracts patent metadata
        4. Returns up to max_results patent items

        Args:
            query: Search query string (natural language or structured)
            max_results: Maximum number of results to return (default: 10)

        Returns:
            List of RawSourceItem objects representing patent search results.
            Returns empty list if no results found or on error.
        """
        try:
            params = self._build_search_params(query, max_results)
            logger.info(f"Searching SerpAPI Google Patents: query='{query}', num={max_results}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()

            # Check for API errors
            error = data.get("error")
            if error:
                logger.error(f"SerpAPI error: {error}")
                print(f"❌ SerpAPI error: {error}")
                return []

            # Extract organic results (the main patent results)
            organic_results = data.get("organic_results", [])

            if not organic_results:
                logger.info(f"No patent results found for query: {query}")
                print(f"ℹ️  No patent results found for query: '{query}'")
                return []

            # Parse each result
            items = []
            for result in organic_results:
                item = self._parse_patent_result(result)
                if item:
                    items.append(item)

            logger.info(f"Successfully extracted {len(items)} patents from SerpAPI")
            print(f"✅ Found {len(items)} patent(s) via SerpAPI")

            return items[:max_results]

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error during SerpAPI request: {e.response.status_code}")
            print(f"❌ HTTP error {e.response.status_code}: {e}")
            return []

        except httpx.RequestError as e:
            logger.error(f"Network error during SerpAPI request: {e}")
            print(f"❌ Network error: {e}")
            return []

        except Exception as e:
            logger.error(f"Unexpected error during SerpAPI search: {e}", exc_info=True)
            print(f"❌ Unexpected error: {e}")
            return []
