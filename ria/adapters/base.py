"""
Base adapter interface for search data sources.

This module defines the abstract base class that all search adapters
(patent databases, scientific paper APIs, etc.) must implement.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ria.models import RawSourceItem, SourceType


class SearchAdapter(ABC):
    """
    Abstract base class for search adapters.

    All concrete adapters (e.g., PatentAdapter, PubMedAdapter) must inherit
    from this class and implement the search() method. Each adapter is
    responsible for:

    - Querying a specific data source (API, database, web scraping, etc.)
    - Parsing the response into RawSourceItem objects
    - Handling authentication, rate limiting, and error handling
    - Populating the raw_adapter_source field with its identifier

    Attributes:
        source_type: The type of sources this adapter returns (PATENT or PAPER)
    """

    source_type: SourceType

    @abstractmethod
    async def search(self, query: str, max_results: int = 10) -> list[RawSourceItem]:
        """
        Execute a search query against the adapter's data source.

        This method must be implemented by all concrete adapters. It should:
        1. Send the query to the underlying data source
        2. Parse the response into structured data
        3. Convert each result into a RawSourceItem
        4. Return a list of results, up to max_results items

        Args:
            query: The search query string (natural language or structured)
            max_results: Maximum number of results to return (default: 10)

        Returns:
            A list of RawSourceItem objects representing search results.
            Returns an empty list if no results are found or an error occurs.

        Raises:
            Exception: Concrete implementations may raise adapter-specific
                      exceptions for network errors, authentication failures,
                      or invalid queries. Callers should handle these appropriately.
        """
        ...
