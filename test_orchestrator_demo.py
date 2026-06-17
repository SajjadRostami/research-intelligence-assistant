#!/usr/bin/env python3
"""
Demo test script for SearchOrchestrator with mock adapters.

This test uses only mock adapters to demonstrate the orchestrator
functionality without requiring API keys or making external calls.

Searches for "XPBD soft body simulation algorithm" and prints:
- Number of patents found
- Number of papers found
- First 3 patent titles
- First 3 paper titles
"""

import asyncio
import logging

from ria.adapters.base import SearchAdapter
from ria.adapters.mock_patent import MockPatentAdapter
from ria.models import ConfidenceLevel, RawSourceItem, SourceType
from ria.orchestrator import SearchOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class MockPaperAdapter(SearchAdapter):
    """Mock adapter for paper search - for testing purposes only."""

    source_type = SourceType.PAPER

    async def search(self, query: str, max_results: int = 10) -> list[RawSourceItem]:
        """Return synthetic paper results."""
        logger.info(f"Generating {max_results} mock papers for query: {query}")

        # Extract key terms from query
        terms = query.lower().split()
        key_terms = [t for t in terms if len(t) > 3][:3]

        results = []
        for i in range(max_results):
            title_variants = [
                f"A Survey of {' '.join(key_terms).upper()} Techniques",
                f"{' '.join(key_terms).title()}: Methods and Applications",
                f"Efficient {' '.join(key_terms).title()} for Real-Time Systems",
                f"Novel Approach to {' '.join(key_terms).title()}",
                f"{' '.join(key_terms).title()} in Computer Graphics: A Review",
            ]
            title = title_variants[i % len(title_variants)]

            authors_list = [
                "Smith, J., Johnson, A.",
                "Zhang, L., Wang, Y., Chen, X.",
                "Brown, M., Davis, K.",
                "Garcia, R., Martinez, P.",
                "Lee, S., Kim, H.",
            ]
            authors = authors_list[i % len(authors_list)]

            item = RawSourceItem(
                title=title,
                source_type=SourceType.PAPER,
                source_url=f"https://example.com/paper/{i+1}",
                publication_date=f"{2020 + (i % 5)}-01-15",
                author_or_assignee=authors,
                doi=f"10.1234/example.{i+1}",
                confidence_level=ConfidenceLevel.LOW,
                raw_adapter_source="mock_paper",
                relevance_explanation=f"Mock paper about {' '.join(key_terms)}...",
            )
            results.append(item)

        return results


async def main():
    """Execute orchestrated search and print results."""
    print("\n" + "=" * 60)
    print("SearchOrchestrator Demo Test")
    print("=" * 60 + "\n")

    # Initialize mock adapters
    patent_adapter = MockPatentAdapter()
    paper_adapter = MockPaperAdapter()

    # Create orchestrator
    orchestrator = SearchOrchestrator(adapters=[patent_adapter, paper_adapter])

    # Execute search
    topic = "XPBD soft body simulation algorithm"
    print(f"Searching for: {topic}\n")

    result = await orchestrator.search(topic, max_results_per_adapter=10)

    # Separate patents and papers
    patents = [item for item in result.raw_items if item.source_type == SourceType.PATENT]
    papers = [item for item in result.raw_items if item.source_type == SourceType.PAPER]

    # Print summary
    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Number of patents found: {len(patents)}")
    print(f"Number of papers found: {len(papers)}")
    print(f"Total queries executed: {len(result.queries)}")

    # Print first 3 patent titles
    print(f"\n{'='*60}")
    print("FIRST 3 PATENT TITLES")
    print(f"{'='*60}")
    for i, patent in enumerate(patents[:3], 1):
        print(f"{i}. {patent.title}")
        print(f"   Patent Number: {patent.patent_number}")
        print(f"   Assignee: {patent.author_or_assignee}")
        print(f"   Date: {patent.publication_date}")
        print()

    # Print first 3 paper titles
    print(f"{'='*60}")
    print("FIRST 3 PAPER TITLES")
    print(f"{'='*60}")
    for i, paper in enumerate(papers[:3], 1):
        print(f"{i}. {paper.title}")
        print(f"   Authors: {paper.author_or_assignee}")
        print(f"   Date: {paper.publication_date}")
        print(f"   DOI: {paper.doi}")
        print()

    # Print adapter execution info
    print(f"{'='*60}")
    print("ADAPTER EXECUTION")
    print(f"{'='*60}")
    for query in result.queries:
        print(f"✓ {query.source}: {query.query_string}")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
