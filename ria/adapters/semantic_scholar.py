"""
Semantic Scholar API adapter.

This adapter queries the Semantic Scholar Academic Graph API to search for
scientific papers. It implements the SearchAdapter interface and returns
structured paper metadata.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

from ria.adapters.base import SearchAdapter
from ria.models import ConfidenceLevel, RawSourceItem, SourceType

logger = logging.getLogger(__name__)


class SemanticScholarAdapter(SearchAdapter):
    """
    Adapter for searching Semantic Scholar papers.

    This adapter uses the Semantic Scholar Academic Graph API to search for
    scientific papers. It handles HTTP requests, parses JSON responses, and
    extracts paper metadata into RawSourceItem objects.

    The API is free to use and does not require authentication, but rate
    limits apply (100 requests per 5 minutes per IP address).

    API Documentation: https://api.semanticscholar.org/

    Attributes:
        source_type: Always SourceType.PAPER
        base_url: Semantic Scholar API base URL
        timeout: Request timeout in seconds
    """

    source_type = SourceType.PAPER

    def __init__(
        self,
        base_url: str = "https://api.semanticscholar.org/graph/v1",
        timeout: float = 30.0,
        api_key: str | None = None,
        max_retries: int = 3,
        initial_retry_delay: float = 1.0,
    ):
        """
        Initialize the Semantic Scholar adapter.

        Args:
            base_url: Base URL for Semantic Scholar API
            timeout: Request timeout in seconds (default: 30.0)
            api_key: Optional Semantic Scholar API key for higher rate limits.
                    Can also be set via SEMANTIC_SCHOLAR_API_KEY environment variable.
            max_retries: Maximum number of retry attempts for rate limit errors (default: 3)
            initial_retry_delay: Initial retry delay in seconds, doubled for each retry (default: 1.0)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay

    def _build_search_params(self, query: str, max_results: int) -> dict[str, Any]:
        """
        Build query parameters for Semantic Scholar API.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            Dictionary of query parameters for the API request
        """
        # Semantic Scholar API supports up to 100 results per request
        limit = min(max_results, 100)

        return {
            "query": query,
            "limit": limit,
            "fields": "title,authors,abstract,year,publicationDate,externalIds,url",
        }

    def _parse_paper_result(self, paper: dict[str, Any]) -> RawSourceItem | None:
        """
        Parse a single paper result from Semantic Scholar API.

        Extracts metadata from the API response and creates a RawSourceItem.
        Returns None if the paper is missing required fields (title or URL).

        Args:
            paper: Dictionary containing paper data from API response

        Returns:
            RawSourceItem if parsing succeeds, None if required fields missing
        """
        try:
            # Required fields
            title = paper.get("title")
            paper_id = paper.get("paperId")

            if not title or not paper_id:
                logger.warning("Skipping paper with missing title or paperId")
                return None

            # Construct paper URL
            paper_url = paper.get("url")
            if not paper_url:
                # Fallback: construct URL from paper ID
                paper_url = f"https://www.semanticscholar.org/paper/{paper_id}"

            # Extract authors
            authors_data = paper.get("authors", [])
            authors = ", ".join(
                author.get("name", "Unknown")
                for author in authors_data
                if author.get("name")
            )

            # Extract abstract
            abstract = paper.get("abstract")

            # Extract publication date
            publication_date = paper.get("publicationDate") or str(paper.get("year", ""))

            # Extract DOI from externalIds
            external_ids = paper.get("externalIds") or {}
            doi = external_ids.get("DOI")

            # Create relevance explanation from abstract snippet
            relevance_explanation = None
            if abstract:
                # Use first 200 characters of abstract as snippet
                relevance_explanation = abstract[:200]
                if len(abstract) > 200:
                    relevance_explanation += "..."

            # Create RawSourceItem
            return RawSourceItem(
                title=title,
                source_type=SourceType.PAPER,
                source_url=paper_url,
                publication_date=publication_date,
                author_or_assignee=authors if authors else None,
                doi=doi,
                relevance_explanation=relevance_explanation,
                confidence_level=ConfidenceLevel.HIGH,
                raw_adapter_source="semantic_scholar",
            )

        except Exception as e:
            logger.warning(f"Failed to parse paper result: {e}")
            return None

    def _build_headers(self) -> dict[str, str]:
        """
        Build HTTP headers for Semantic Scholar API requests.

        Returns:
            Dictionary of HTTP headers including User-Agent and optional API key
        """
        headers = {
            "User-Agent": "research-intelligence-assistant/1.0 (https://github.com/yourusername/research-intelligence-assistant)",
        }

        if self.api_key:
            headers["x-api-key"] = self.api_key

        return headers

    async def _make_request_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, Any],
    ) -> httpx.Response:
        """
        Make an HTTP request with exponential backoff retry logic for rate limits.

        Args:
            client: HTTPX async client
            url: Request URL
            params: Query parameters

        Returns:
            HTTP response

        Raises:
            httpx.HTTPStatusError: If request fails after all retries
        """
        headers = self._build_headers()

        for attempt in range(self.max_retries + 1):
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response

            except httpx.HTTPStatusError as e:
                # Handle rate limiting (HTTP 429)
                if e.response.status_code == 429:
                    if attempt < self.max_retries:
                        # Calculate exponential backoff delay
                        delay = self.initial_retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Rate limited (HTTP 429). Retrying in {delay}s "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(
                            f"Rate limited (HTTP 429) after {self.max_retries} retries. "
                            "Consider using an API key for higher rate limits."
                        )
                        raise

                # For other HTTP errors, don't retry
                raise

        # Should never reach here
        raise RuntimeError("Unexpected state in retry logic")

    async def search(self, query: str, max_results: int = 10) -> list[RawSourceItem]:
        """
        Execute a search query against Semantic Scholar API.

        This method:
        1. Builds query parameters for the API
        2. Makes an HTTP GET request to the paper search endpoint
        3. Implements exponential backoff retry for rate limits (HTTP 429)
        4. Parses the JSON response
        5. Extracts paper metadata into RawSourceItem objects
        6. Returns up to max_results papers

        Args:
            query: Search query string (natural language or keywords)
            max_results: Maximum number of results to return (default: 10)

        Returns:
            List of RawSourceItem objects representing paper search results.
            Returns empty list if no results found or on error.

        Note:
            The Semantic Scholar API has rate limits:
            - Without API key: 100 requests per 5 minutes per IP
            - With API key: Higher limits available

            This adapter implements exponential backoff retry for HTTP 429 errors.
            To get an API key, visit: https://www.semanticscholar.org/product/api
        """
        try:
            # Build search URL and parameters
            search_url = f"{self.base_url}/paper/search"
            params = self._build_search_params(query, max_results)

            logger.info(f"Searching Semantic Scholar: {query}")

            # Make API request with retry logic
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await self._make_request_with_retry(client, search_url, params)

                # Parse JSON response
                data = response.json()

                # Extract papers from response
                papers = data.get("data", [])

                if not papers:
                    logger.info(f"No papers found for query: {query}")
                    return []

                # Parse each paper result
                results = []
                for paper in papers:
                    item = self._parse_paper_result(paper)
                    if item:
                        results.append(item)

                logger.info(f"Extracted {len(results)} papers from Semantic Scholar")
                return results

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Semantic Scholar API error (HTTP {e.response.status_code}): {e}"
            )
            return []

        except httpx.RequestError as e:
            logger.error(f"Semantic Scholar request failed: {e}")
            return []

        except Exception as e:
            logger.error(f"Semantic Scholar search failed for query '{query}': {e}")
            return []
