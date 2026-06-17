#!/usr/bin/env python3
"""
Live test script for Semantic Scholar adapter.

This script demonstrates the SemanticScholarAdapter by searching for papers
related to "XPBD soft body simulation algorithm" and displaying the results.

The Semantic Scholar API is free to use and does not require an API key,
but rate limits apply (100 requests per 5 minutes per IP address).

Usage:
    python test_semantic_scholar_live.py

Requirements:
    - No API key required
    - Internet connection
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ria.adapters.semantic_scholar import SemanticScholarAdapter


async def main():
    """Run a live test of the Semantic Scholar adapter."""
    print("=" * 80)
    print("Semantic Scholar Adapter - Live Test")
    print("=" * 80)
    print()
    print("ℹ️  Note: Semantic Scholar API is free (no API key required)")
    print("   Rate limit: 100 requests per 5 minutes per IP address")
    print()

    # Initialize adapter
    try:
        adapter = SemanticScholarAdapter()
        print(f"✅ Adapter initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize adapter: {e}")
        return 1

    # Test query
    query = "XPBD soft body simulation algorithm"
    max_results = 10

    print(f"📝 Query: '{query}'")
    print(f"📊 Requesting: {max_results} results")
    print()
    print("-" * 80)
    print()

    # Execute search
    try:
        results = await adapter.search(query, max_results=max_results)
    except Exception as e:
        print(f"❌ Search failed: {e}")
        return 1

    # Display results
    if not results:
        print("⚠️  No results returned")
        return 0

    print(f"Found {len(results)} paper(s):")
    print()

    for i, item in enumerate(results, 1):
        print(f"{'=' * 80}")
        print(f"Result #{i}")
        print(f"{'=' * 80}")
        print(f"Title:            {item.title}")
        print(f"Authors:          {item.author_or_assignee or 'N/A'}")
        print(f"Publication Date: {item.publication_date or 'N/A'}")
        print(f"DOI:              {item.doi or 'N/A'}")
        print(f"URL:              {item.source_url}")
        print(f"Source Type:      {item.source_type.value}")
        print(f"Adapter:          {item.raw_adapter_source}")
        print(f"Confidence:       {item.confidence_level.value if item.confidence_level else 'N/A'}")

        if item.relevance_explanation:
            print(f"Abstract:         {item.relevance_explanation}")

        print()

    print(f"{'=' * 80}")
    print(f"✅ Test completed successfully!")
    print(f"{'=' * 80}")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
