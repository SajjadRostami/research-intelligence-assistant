"""
Search orchestrator for coordinating multiple data source adapters.

The SearchOrchestrator runs searches across multiple adapters concurrently
and aggregates results into a single OrchestratorResult.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Sequence

from ria.adapters.base import SearchAdapter
from ria.models import OrchestratorResult, RawSourceItem, SearchQuery

logger = logging.getLogger(__name__)


class SearchOrchestrator:
    """
    Orchestrates concurrent searches across multiple adapters.

    The orchestrator accepts a research topic and runs all configured adapters
    in parallel using asyncio. It collects results from all adapters and
    handles failures gracefully by logging errors and continuing with
    successful results.

    Example:
        orchestrator = SearchOrchestrator(
            adapters=[SerpAPIPatentAdapter(), SemanticScholarAdapter()]
        )
        result = await orchestrator.search("XPBD simulation")
    """

    def __init__(self, adapters: Sequence[SearchAdapter]):
        """
        Initialize the orchestrator with a list of search adapters.

        Args:
            adapters: Sequence of SearchAdapter instances to query concurrently
        """
        self.adapters = adapters

    async def _search_adapter(
        self,
        adapter: SearchAdapter,
        query: str,
        max_results: int,
    ) -> tuple[SearchQuery, list[RawSourceItem]]:
        """
        Execute search on a single adapter with error handling.

        Args:
            adapter: The search adapter to query
            query: Search query string
            max_results: Maximum number of results to request

        Returns:
            Tuple of (SearchQuery, list of RawSourceItem).
            Returns empty list on failure.
        """
        adapter_name = adapter.__class__.__name__
        search_query = SearchQuery(
            query_string=query,
            source=adapter_name,
            timestamp=datetime.utcnow(),
        )

        try:
            logger.info(f"Starting search on {adapter_name}")
            items = await adapter.search(query, max_results=max_results)
            logger.info(f"Completed search on {adapter_name}: {len(items)} results")
            return search_query, items

        except Exception as e:
            logger.error(
                f"Adapter {adapter_name} failed for query '{query}': {e}",
                exc_info=True,
            )
            # Return empty results on failure, but include the search query
            return search_query, []

    async def search(
        self,
        topic: str,
        max_results_per_adapter: int = 10,
    ) -> OrchestratorResult:
        """
        Execute concurrent searches across all adapters.

        Runs all configured adapters in parallel using asyncio.gather(),
        collects results from all successful searches, and aggregates
        them into a single OrchestratorResult.

        Args:
            topic: Research topic string to search for
            max_results_per_adapter: Maximum results per adapter (default: 10)

        Returns:
            OrchestratorResult containing:
            - topic: The research topic
            - queries: List of all SearchQuery objects (one per adapter)
            - raw_items: Aggregated list of all RawSourceItem objects

        Note:
            Adapter failures are logged but do not prevent other adapters
            from completing. If all adapters fail, returns an empty result.
        """
        logger.info(
            f"Starting orchestrated search for topic: '{topic}' "
            f"across {len(self.adapters)} adapter(s)"
        )

        # Execute all adapter searches concurrently
        search_tasks = [
            self._search_adapter(adapter, topic, max_results_per_adapter)
            for adapter in self.adapters
        ]

        # Gather results from all adapters (won't raise on individual failures)
        results = await asyncio.gather(*search_tasks)

        # Aggregate queries and items
        all_queries: list[SearchQuery] = []
        all_items: list[RawSourceItem] = []

        for search_query, items in results:
            all_queries.append(search_query)
            all_items.extend(items)

        logger.info(
            f"Orchestration complete: {len(all_items)} total items from "
            f"{len(all_queries)} adapter(s)"
        )

        return OrchestratorResult(
            topic=topic,
            queries=all_queries,
            raw_items=all_items,
        )
