#!/usr/bin/env python3
"""
Live test script for SerpAPI patent adapter.

This script demonstrates the SerpAPIPatentAdapter by searching for patents
related to "XPBD soft body simulation algorithm" and displaying the results.

Usage:
    python test_serpapi_patents_live.py

Requirements:
    - SERPAPI_API_KEY must be set in .env or environment variables
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

from ria.adapters.serpapi_patents import SerpAPIPatentAdapter


async def main():
    """Run a live test of the SerpAPI patent adapter."""
    # Load environment variables
    load_dotenv()

    # Check for API key
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key or api_key == "your_serpapi_key_here":
        print("❌ Error: SERPAPI_API_KEY not set in environment")
        print("   Please set it in .env file or export it:")
        print("   export SERPAPI_API_KEY=your_actual_key_here")
        return 1

    print("=" * 80)
    print("SerpAPI Patent Adapter - Live Test")
    print("=" * 80)
    print()

    # Initialize adapter
    try:
        adapter = SerpAPIPatentAdapter()
        print(f"✅ Adapter initialized successfully")
    except ValueError as e:
        print(f"❌ Failed to initialize adapter: {e}")
        return 1

    # Test query
    query = "XPBD soft body simulation algorithm"
    max_results = 10  # SerpAPI requires minimum of 10 for google_patents

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

    print(f"Found {len(results)} patent(s):")
    print()

    for i, item in enumerate(results, 1):
        print(f"{'=' * 80}")
        print(f"Result #{i}")
        print(f"{'=' * 80}")
        print(f"Title:            {item.title}")
        print(f"Patent Number:    {item.patent_number or 'N/A'}")
        print(f"Assignee:         {item.author_or_assignee or 'N/A'}")
        print(f"Publication Date: {item.publication_date or 'N/A'}")
        print(f"URL:              {item.source_url}")
        print(f"Source Type:      {item.source_type.value}")
        print(f"Adapter:          {item.raw_adapter_source}")
        print(f"Confidence:       {item.confidence_level.value if item.confidence_level else 'N/A'}")

        if item.relevance_explanation:
            snippet = item.relevance_explanation[:200]
            if len(item.relevance_explanation) > 200:
                snippet += "..."
            print(f"Snippet:          {snippet}")

        print()

    print(f"{'=' * 80}")
    print(f"✅ Test completed successfully!")
    print(f"{'=' * 80}")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
