#!/usr/bin/env python3
"""
Test script for SearchOrchestrator.

Searches for "XPBD soft body simulation algorithm" and prints:
- Number of patents found
- Number of papers found
- First 3 patent titles
- First 3 paper titles
"""

import asyncio
import logging
import os

from ria.adapters.mock_patent import MockPatentAdapter
from ria.adapters.semantic_scholar import SemanticScholarAdapter
from ria.adapters.serpapi_patents import SerpAPIPatentAdapter
from ria.models import SourceType
from ria.orchestrator import SearchOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    """Execute orchestrated search and print results."""
    # Initialize patent adapter - use SerpAPI if key available, otherwise use mock
    if os.getenv("SERPAPI_API_KEY"):
        print("Using SerpAPI for patent search")
        patent_adapter = SerpAPIPatentAdapter()
    else:
        print("SERPAPI_API_KEY not found - using MockPatentAdapter")
        patent_adapter = MockPatentAdapter()

    # Initialize paper adapter
    paper_adapter = SemanticScholarAdapter()

    # Create orchestrator
    orchestrator = SearchOrchestrator(
        adapters=[patent_adapter, paper_adapter]
    )

    # Execute search
    topic = "XPBD soft body simulation algorithm"
    print(f"\n{'='*60}")
    print(f"Searching for: {topic}")
    print(f"{'='*60}\n")

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

    # Print first 3 patent titles
    print(f"\n{'='*60}")
    print("FIRST 3 PATENT TITLES")
    print(f"{'='*60}")
    for i, patent in enumerate(patents[:3], 1):
        print(f"{i}. {patent.title}")
        if patent.patent_number:
            print(f"   Patent Number: {patent.patent_number}")
        print()

    if len(patents) == 0:
        print("No patents found.\n")

    # Print first 3 paper titles
    print(f"{'='*60}")
    print("FIRST 3 PAPER TITLES")
    print(f"{'='*60}")
    for i, paper in enumerate(papers[:3], 1):
        print(f"{i}. {paper.title}")
        if paper.author_or_assignee:
            print(f"   Authors: {paper.author_or_assignee}")
        print()

    if len(papers) == 0:
        print("No papers found.\n")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
