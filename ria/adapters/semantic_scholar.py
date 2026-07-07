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

    def _expand_query(self, query: str) -> list[str]:
        """
        Expand query with common variations and full forms.

        For short acronyms, generates expanded technical phrases to improve recall.

        Args:
            query: Original search query

        Returns:
            List of query strings to search (including the original)
        """
        queries = [query]

        # Query expansion for known acronyms
        query_lower = query.lower().strip()

        if query_lower == "xpbd" or "xpbd" in query_lower.split():
            queries.extend([
                "Extended Position Based Dynamics",
                "XPBD position based dynamics",
                "Position Based Dynamics compliant constraints",
                "real-time simulation XPBD",
            ])

        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            if q.lower() not in seen:
                seen.add(q.lower())
                unique_queries.append(q)

        return unique_queries

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
            "fields": "paperId,title,authors,abstract,year,venue,url,citationCount,externalIds,openAccessPdf,isOpenAccess,tldr",
        }

    def _parse_paper_result(self, paper: dict[str, Any]) -> dict[str, Any] | None:
        """
        Parse a single paper result from Semantic Scholar API.

        Extracts metadata from the API response and creates a dictionary with
        paper data including open access information.
        Returns None if the paper is missing required fields (title or URL).

        Args:
            paper: Dictionary containing paper data from API response

        Returns:
            Dictionary with paper data if parsing succeeds, None if required fields missing
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

            # Extract open access information
            is_open_access = paper.get("isOpenAccess", False)
            open_access_pdf = paper.get("openAccessPdf")
            pdf_url = None
            if open_access_pdf and isinstance(open_access_pdf, dict):
                pdf_url = open_access_pdf.get("url")

            # Extract additional fields
            venue = paper.get("venue")
            citation_count = paper.get("citationCount", 0)
            tldr_data = paper.get("tldr")
            tldr_text = None
            if tldr_data and isinstance(tldr_data, dict):
                tldr_text = tldr_data.get("text")

            # Create relevance explanation from abstract or TLDR
            relevance_explanation = None
            if abstract:
                # Use first 200 characters of abstract as snippet
                relevance_explanation = abstract[:200]
                if len(abstract) > 200:
                    relevance_explanation += "..."
            elif tldr_text:
                relevance_explanation = tldr_text

            # Return parsed data with metadata
            return {
                "title": title,
                "paper_id": paper_id,
                "source_url": paper_url,
                "publication_date": publication_date,
                "authors": authors if authors else None,
                "doi": doi,
                "venue": venue,
                "citation_count": citation_count,
                "is_open_access": is_open_access,
                "pdf_url": pdf_url,
                "relevance_explanation": relevance_explanation,
            }

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

    def _deduplicate_papers(self, papers: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Deduplicate papers by paperId, DOI, or normalized title.

        Args:
            papers: List of parsed paper dictionaries

        Returns:
            Deduplicated list of papers
        """
        seen_ids = set()
        seen_dois = set()
        seen_titles = set()
        unique_papers = []

        for paper in papers:
            # Check paperId
            paper_id = paper.get("paper_id")
            if paper_id and paper_id in seen_ids:
                continue

            # Check DOI
            doi = paper.get("doi")
            if doi and doi in seen_dois:
                continue

            # Check normalized title (case-insensitive, whitespace-normalized)
            title = paper.get("title", "")
            normalized_title = " ".join(title.lower().split())
            if normalized_title in seen_titles:
                continue

            # Add to seen sets
            if paper_id:
                seen_ids.add(paper_id)
            if doi:
                seen_dois.add(doi)
            if normalized_title:
                seen_titles.add(normalized_title)

            unique_papers.append(paper)

        return unique_papers

    async def search(self, query: str, max_results: int = 10) -> list[RawSourceItem]:
        """
        Execute a search query against Semantic Scholar API with query expansion.

        This method:
        1. Expands query with common variations (e.g., "XPBD" -> "Extended Position Based Dynamics")
        2. Builds query parameters for the API
        3. Makes HTTP GET requests to the paper search endpoint for each query variant
        4. Implements exponential backoff retry for rate limits (HTTP 429)
        5. Parses the JSON response
        6. Filters for open-access papers when available
        7. Deduplicates by paperId, DOI, or title
        8. Extracts paper metadata into RawSourceItem objects
        9. Returns up to max_results papers

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
        # Expand query for better recall
        queries = self._expand_query(query)
        logger.info(f"Searching Semantic Scholar with {len(queries)} query variant(s): {queries}")

        all_parsed_papers = []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for query_variant in queries:
                    try:
                        # Build search URL and parameters
                        search_url = f"{self.base_url}/paper/search"
                        params = self._build_search_params(query_variant, max_results)

                        logger.info(f"Semantic Scholar request URL: {search_url}")
                        logger.info(f"Semantic Scholar query params: {params}")

                        # Make API request with retry logic
                        response = await self._make_request_with_retry(client, search_url, params)

                        logger.info(f"Semantic Scholar response status: {response.status_code}")

                        # Parse JSON response
                        data = response.json()

                        # Extract papers from response
                        papers = data.get("data", [])
                        logger.info(f"Semantic Scholar raw results for '{query_variant}': {len(papers)} papers")

                        if not papers:
                            continue

                        # Parse each paper result
                        for paper in papers:
                            parsed = self._parse_paper_result(paper)
                            if parsed:
                                all_parsed_papers.append(parsed)

                    except httpx.HTTPStatusError as e:
                        logger.error(
                            f"Semantic Scholar API error for query '{query_variant}' "
                            f"(HTTP {e.response.status_code}): {e}"
                        )
                        if e.response.status_code == 429:
                            logger.warning(
                                "Rate limit exceeded. Consider using an API key or reducing request frequency."
                            )
                        continue

                    except httpx.RequestError as e:
                        logger.error(f"Semantic Scholar request failed for query '{query_variant}': {e}")
                        continue

            # Deduplicate papers
            unique_papers = self._deduplicate_papers(all_parsed_papers)
            logger.info(f"After deduplication: {len(unique_papers)} unique papers")

            # Separate open access and non-open access papers
            open_access_papers = [
                p for p in unique_papers
                if p.get("is_open_access") or p.get("pdf_url")
            ]
            other_papers = [
                p for p in unique_papers
                if not (p.get("is_open_access") or p.get("pdf_url"))
            ]

            logger.info(f"Open access papers found: {len(open_access_papers)}")
            logger.info(f"Non-open access papers: {len(other_papers)}")

            # Prefer open access papers, but include others if needed
            selected_papers = open_access_papers[:max_results]
            if len(selected_papers) < max_results:
                remaining = max_results - len(selected_papers)
                selected_papers.extend(other_papers[:remaining])

            # Convert to RawSourceItem objects
            results = []
            for paper in selected_papers:
                item = RawSourceItem(
                    title=paper["title"],
                    source_type=SourceType.PAPER,
                    source_url=paper["source_url"],
                    publication_date=paper["publication_date"],
                    author_or_assignee=paper["authors"],
                    doi=paper["doi"],
                    venue=paper["venue"],
                    citation_count=paper["citation_count"],
                    is_open_access=paper["is_open_access"],
                    pdf_url=paper["pdf_url"],
                    relevance_explanation=paper["relevance_explanation"],
                    confidence_level=ConfidenceLevel.HIGH,
                    raw_adapter_source="semantic_scholar",
                )
                results.append(item)

            logger.info(
                f"Semantic Scholar final results: {len(results)} papers "
                f"({len([r for r in results if r.is_open_access or r.pdf_url])} open access)"
            )

            if not results:
                logger.warning(
                    f"No papers found for query: {query}. This may indicate API issues or "
                    "overly specific search terms."
                )

            return results

        except Exception as e:
            logger.error(f"Semantic Scholar search failed for query '{query}': {e}", exc_info=True)
            return []
