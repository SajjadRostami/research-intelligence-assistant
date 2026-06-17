"""
Mock patent adapter for MVP/testing purposes.

This adapter returns synthetic patent data to allow the pipeline to continue
without relying on external APIs. Replace with a real adapter (BigQuery, Lens.org)
for production use.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from ria.adapters.base import SearchAdapter
from ria.models import ConfidenceLevel, RawSourceItem, SourceType

logger = logging.getLogger(__name__)


class MockPatentAdapter(SearchAdapter):
    """
    Mock adapter that returns synthetic patent data.

    This adapter is intended for MVP development and testing when real patent
    APIs are unavailable. It generates plausible-looking patent results based
    on the query terms.

    WARNING: This adapter returns fake data. Replace with a real adapter
    (Google Patents BigQuery, Lens.org API) for production use.

    Attributes:
        source_type: Always SourceType.PATENT
    """

    source_type = SourceType.PATENT

    def _generate_mock_patents(
        self, query: str, max_results: int
    ) -> list[RawSourceItem]:
        """
        Generate synthetic patent results based on query terms.

        Args:
            query: Search query string
            max_results: Number of results to generate

        Returns:
            List of synthetic RawSourceItem objects
        """
        results = []
        base_date = datetime(2024, 1, 1)

        # Extract key terms from query for title generation
        terms = query.lower().split()
        key_terms = [t for t in terms if len(t) > 3][:3]  # Up to 3 key terms

        for i in range(max_results):
            # Generate synthetic patent number (US format)
            patent_number = f"US{10000000 + i * 12345}B2"

            # Generate title with query terms
            title_variants = [
                f"Method and system for {' and '.join(key_terms)}",
                f"Apparatus for {' '.join(key_terms)} processing",
                f"System and method for improved {' '.join(key_terms)}",
                f"Device for {' '.join(key_terms)} optimization",
                f"Method of {' '.join(key_terms)} using machine learning",
            ]
            title = title_variants[i % len(title_variants)]

            # Generate publication date (spread over past 3 years)
            pub_date = base_date - timedelta(days=i * 120)

            # Generate assignee (company name)
            companies = [
                "Acme Corporation",
                "TechnoSoft Inc.",
                "Innovation Labs LLC",
                "Advanced Systems Corp.",
                "Digital Solutions Inc.",
            ]
            assignee = companies[i % len(companies)]

            # Build source URL
            source_url = f"https://patents.google.com/patent/{patent_number}"

            item = RawSourceItem(
                title=title,
                source_type=SourceType.PATENT,
                source_url=source_url,
                publication_date=pub_date.strftime("%Y-%m-%d"),
                author_or_assignee=assignee,
                patent_number=patent_number,
                confidence_level=ConfidenceLevel.LOW,  # Mock data = low confidence
                raw_adapter_source="mock_patent",
            )

            results.append(item)

        return results

    async def search(self, query: str, max_results: int = 10) -> list[RawSourceItem]:
        """
        Return synthetic patent results for testing.

        Args:
            query: Search query string (used to generate relevant-looking titles)
            max_results: Number of results to return (default: 10)

        Returns:
            List of synthetic RawSourceItem objects
        """
        logger.warning(
            "MockPatentAdapter is returning synthetic data - "
            "replace with real adapter for production"
        )

        results = self._generate_mock_patents(query, max_results)
        logger.info(f"Generated {len(results)} mock patents for query: {query}")

        return results
