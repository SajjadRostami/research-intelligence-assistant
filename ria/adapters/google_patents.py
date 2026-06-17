"""
Google Patents search adapter.

This adapter queries Google Patents via web scraping and extracts patent
information from the search results page. It implements retry logic with
exponential backoff for rate limiting (HTTP 429).
"""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from ria.adapters.base import SearchAdapter
from ria.models import ConfidenceLevel, RawSourceItem, SourceType

logger = logging.getLogger(__name__)


class GooglePatentsAdapter(SearchAdapter):
    """
    Adapter for searching Google Patents.

    This adapter constructs search URLs for Google Patents, makes async HTTP
    requests, and extracts patent metadata from the HTML response. It handles
    rate limiting with exponential backoff and parses results into RawSourceItem
    objects.

    Attributes:
        source_type: Always SourceType.PATENT
        base_url: Google Patents search base URL
        max_retries: Maximum number of retry attempts for rate limiting
        initial_backoff: Initial backoff delay in seconds (doubles each retry)
    """

    source_type = SourceType.PATENT

    def __init__(
        self,
        base_url: str = "https://patents.google.com/",
        max_retries: int = 3,
        initial_backoff: float = 1.0,
    ):
        """
        Initialize the Google Patents adapter.

        Args:
            base_url: Base URL for Google Patents (default: https://patents.google.com/)
            max_retries: Maximum retry attempts for HTTP 429 errors (default: 3)
            initial_backoff: Initial backoff delay in seconds (default: 1.0)
        """
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff

    def _build_search_url(self, query: str) -> str:
        """
        Build a Google Patents search URL from a query string.

        Args:
            query: The search query (will be URL-encoded)

        Returns:
            Complete search URL for Google Patents
        """
        encoded_query = quote_plus(query)
        return f"{self.base_url}/?q={encoded_query}"

    async def _fetch_with_backoff(self, url: str) -> str:
        """
        Fetch URL content with exponential backoff on HTTP 429.

        Implements retry logic with exponential backoff specifically for rate
        limiting errors (HTTP 429). Other HTTP errors are raised immediately.
        Uses browser-like headers to avoid anti-scraping blocks.

        Args:
            url: The URL to fetch

        Returns:
            HTML content as a string

        Raises:
            httpx.HTTPStatusError: For non-429 HTTP errors or after max retries
            httpx.RequestError: For network-level errors
        """
        backoff = self.initial_backoff

        # Use browser-like headers to avoid anti-scraping blocks
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

        async with httpx.AsyncClient(
            timeout=30.0, follow_redirects=True, headers=headers
        ) as client:
            for attempt in range(self.max_retries + 1):
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    return response.text

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        if attempt < self.max_retries:
                            logger.warning(
                                f"Rate limited (429). Retrying in {backoff}s "
                                f"(attempt {attempt + 1}/{self.max_retries})"
                            )
                            await asyncio.sleep(backoff)
                            backoff *= 2  # Exponential backoff
                            continue
                        else:
                            logger.error(
                                f"Max retries ({self.max_retries}) exceeded for 429 error"
                            )
                            raise
                    else:
                        # Non-429 errors are raised immediately
                        logger.error(f"HTTP error {e.response.status_code}: {e}")
                        raise

        # Should never reach here, but satisfy type checker
        raise httpx.RequestError("Unexpected error in fetch_with_backoff")

    def _parse_results(self, html: str, query: str) -> list[RawSourceItem]:
        """
        Parse Google Patents HTML and extract patent information.

        Extracts the following fields from each search result:
        - Title
        - Patent number
        - Publication date
        - Assignee (patent holder)
        - URL to the patent detail page

        Args:
            html: HTML content from Google Patents search results page
            query: Original query string (used for logging)

        Returns:
            List of RawSourceItem objects, one per patent result
        """
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Google Patents search results are in <search-result> elements
        search_results = soup.find_all("search-result")

        if not search_results:
            logger.info(f"No search results found for query: {query}")
            return []

        for result in search_results:
            try:
                # Extract title
                title_elem = result.find("h3", class_="result-title")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)

                # Extract patent number and build URL
                patent_id_elem = result.find("span", {"data-result": "patent_number"})
                patent_number = (
                    patent_id_elem.get_text(strip=True) if patent_id_elem else None
                )

                # Build patent URL (format: /patent/{patent_number})
                if patent_number:
                    source_url = f"{self.base_url}/patent/{patent_number}"
                else:
                    # Fallback: try to extract from link
                    link_elem = result.find("a")
                    if link_elem and link_elem.get("href"):
                        href = link_elem["href"]
                        source_url = (
                            f"{self.base_url}{href}"
                            if href.startswith("/")
                            else href
                        )
                    else:
                        logger.warning(f"No URL found for patent: {title}")
                        continue

                # Extract publication date
                date_elem = result.find("span", {"data-result": "publication_date"})
                publication_date = date_elem.get_text(strip=True) if date_elem else None

                # Extract assignee (patent holder)
                assignee_elem = result.find("span", {"data-result": "assignee"})
                assignee = assignee_elem.get_text(strip=True) if assignee_elem else None

                # Create RawSourceItem
                item = RawSourceItem(
                    title=title,
                    source_type=SourceType.PATENT,
                    source_url=source_url,
                    publication_date=publication_date,
                    author_or_assignee=assignee,
                    patent_number=patent_number,
                    confidence_level=ConfidenceLevel.HIGH,  # Direct from source
                    raw_adapter_source="google_patents",
                )

                results.append(item)

            except Exception as e:
                logger.warning(f"Failed to parse patent result: {e}")
                continue

        logger.info(f"Extracted {len(results)} patents from Google Patents")
        return results

    async def search(self, query: str, max_results: int = 10) -> list[RawSourceItem]:
        """
        Execute a search query against Google Patents.

        This method:
        1. Builds a Google Patents search URL from the query
        2. Fetches the search results page with exponential backoff on 429
        3. Parses the HTML to extract patent metadata
        4. Returns up to max_results patent items

        Args:
            query: Search query string (natural language or structured)
            max_results: Maximum number of results to return (default: 10)

        Returns:
            List of RawSourceItem objects representing patent search results.
            Returns empty list if no results found or on error.

        Raises:
            httpx.HTTPStatusError: For HTTP errors (after retries for 429)
            httpx.RequestError: For network-level errors
        """
        try:
            url = self._build_search_url(query)
            logger.info(f"Searching Google Patents: {url}")

            html = await self._fetch_with_backoff(url)
            results = self._parse_results(html, query)

            # Limit to max_results
            return results[:max_results]

        except Exception as e:
            logger.error(f"Google Patents search failed for query '{query}': {e}")
            return []
