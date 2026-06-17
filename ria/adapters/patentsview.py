"""
PatentsView API adapter.

This adapter queries the PatentsView API (https://patentsview.org/apis/api-query-language)
for US patent data. PatentsView provides free, JSON-based REST API access to USPTO data.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from ria.adapters.base import SearchAdapter
from ria.models import ConfidenceLevel, RawSourceItem, SourceType

logger = logging.getLogger(__name__)


class PatentsViewAdapter(SearchAdapter):
    """
    Adapter for searching US patents via PatentsView API.

    PatentsView provides a free REST API for querying USPTO patent data.
    The API supports text search across patent titles and abstracts.

    Attributes:
        source_type: Always SourceType.PATENT
        base_url: PatentsView API endpoint
    """

    source_type = SourceType.PATENT

    def __init__(self, base_url: str = "https://api.patentsview.org/patents/query"):
        """
        Initialize the PatentsView adapter.

        Args:
            base_url: PatentsView API query endpoint
        """
        self.base_url = base_url

    def _build_query_params(self, query: str, max_results: int) -> dict[str, Any]:
        """
        Build PatentsView API query parameters.

        PatentsView uses a JSON query language. This method constructs a
        text search query that searches patent titles and abstracts.

        Args:
            query: The search query string
            max_results: Maximum number of results to return

        Returns:
            Dictionary with 'q', 'f', and 'o' parameters for the API
        """
        # Query format: search in patent_title and patent_abstract
        # Use _text_any to search for any word in the query
        query_json = {
            "_or": [
                {"_text_any": {"patent_title": query}},
                {"_text_any": {"patent_abstract": query}},
            ]
        }

        # Fields to return
        fields = [
            "patent_id",
            "patent_number",
            "patent_title",
            "patent_date",
            "assignee_organization",
            "assignee_first_name",
            "assignee_last_name",
        ]

        # Options: sort by date (newest first), limit results
        options = {"per_page": max_results, "sort": [{"patent_date": "desc"}]}

        return {"q": query_json, "f": fields, "o": options}

    def _parse_response(self, data: dict[str, Any], query: str) -> list[RawSourceItem]:
        """
        Parse PatentsView API JSON response into RawSourceItem objects.

        Args:
            data: JSON response from PatentsView API
            query: Original query string (used for logging)

        Returns:
            List of RawSourceItem objects, one per patent
        """
        results = []

        # Check if response has patents
        patents = data.get("patents", [])
        if not patents:
            logger.info(f"No patents found for query: {query}")
            return []

        for patent in patents:
            try:
                # Extract required fields
                patent_id = patent.get("patent_id")
                patent_number = patent.get("patent_number")
                title = patent.get("patent_title", "").strip()

                if not title or not patent_number:
                    continue

                # Build patent URL (Google Patents format for compatibility)
                source_url = f"https://patents.google.com/patent/{patent_number}"

                # Extract publication date
                publication_date = patent.get("patent_date")

                # Extract assignee (patent holder)
                # Assignees can be organizations or individuals
                assignees = patent.get("assignees", [])
                assignee = None
                if assignees:
                    first_assignee = assignees[0]
                    org = first_assignee.get("assignee_organization")
                    if org:
                        assignee = org
                    else:
                        # Individual assignee
                        first_name = first_assignee.get("assignee_first_name", "")
                        last_name = first_assignee.get("assignee_last_name", "")
                        assignee = f"{first_name} {last_name}".strip()

                # Create RawSourceItem
                item = RawSourceItem(
                    title=title,
                    source_type=SourceType.PATENT,
                    source_url=source_url,
                    publication_date=publication_date,
                    author_or_assignee=assignee,
                    patent_number=patent_number,
                    confidence_level=ConfidenceLevel.HIGH,  # Direct from API
                    raw_adapter_source="patentsview",
                )

                results.append(item)

            except Exception as e:
                logger.warning(f"Failed to parse patent result: {e}")
                continue

        logger.info(f"Extracted {len(results)} patents from PatentsView")
        return results

    async def search(self, query: str, max_results: int = 10) -> list[RawSourceItem]:
        """
        Execute a search query against PatentsView API.

        This method:
        1. Builds PatentsView API query parameters
        2. Makes an HTTP POST request to the API
        3. Parses the JSON response into RawSourceItem objects
        4. Returns up to max_results patent items

        Args:
            query: Search query string (natural language)
            max_results: Maximum number of results to return (default: 10)

        Returns:
            List of RawSourceItem objects representing US patent search results.
            Returns empty list if no results found or on error.

        Raises:
            httpx.HTTPStatusError: For HTTP errors
            httpx.RequestError: For network-level errors
        """
        try:
            params = self._build_query_params(query, max_results)
            logger.info(f"Searching PatentsView API: {query}")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, json=params)
                response.raise_for_status()
                data = response.json()

                results = self._parse_response(data, query)
                return results[:max_results]

        except Exception as e:
            logger.error(f"PatentsView search failed for query '{query}': {e}")
            return []
