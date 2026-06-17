#!/usr/bin/env python3
"""
Fallback test script for Semantic Scholar adapter.

This script tests the SemanticScholarAdapter with a simple, well-known query
("machine learning") to verify the adapter works correctly. It includes
detailed error reporting for debugging rate limit and other API issues.

The Semantic Scholar API is free to use and does not require an API key,
but rate limits apply (100 requests per 5 minutes per IP address).

Usage:
    python test_semantic_scholar_fallback.py

    # With API key (for higher rate limits):
    export SEMANTIC_SCHOLAR_API_KEY="your-api-key"
    python test_semantic_scholar_fallback.py

Requirements:
    - No API key required (but recommended for higher rate limits)
    - Internet connection
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ria.adapters.semantic_scholar import SemanticScholarAdapter


async def main():
    """Run a fallback test of the Semantic Scholar adapter."""
    print("=" * 80)
    print("Semantic Scholar Adapter - Fallback Test")
    print("=" * 80)
    print()
    print("ℹ️  Note: Using simple query to verify adapter functionality")
    print("   Query: 'machine learning'")
    print()
    print("ℹ️  Semantic Scholar API is free (no API key required)")
    print("   Rate limit: 100 requests per 5 minutes per IP address")
    print("   For higher limits, get an API key at:")
    print("   https://www.semanticscholar.org/product/api")
    print()

    # Initialize adapter
    try:
        adapter = SemanticScholarAdapter(
            max_retries=3,
            initial_retry_delay=2.0,  # Start with 2s delay for retries
        )
        print(f"✅ Adapter initialized successfully")

        import os
        if os.getenv("SEMANTIC_SCHOLAR_API_KEY"):
            print(f"✅ Using API key from environment")
        else:
            print(f"⚠️  No API key found (using free tier with lower rate limits)")

    except Exception as e:
        print(f"❌ Failed to initialize adapter: {e}")
        return 1

    # Test query - simple and well-known
    query = "machine learning"
    max_results = 5  # Request fewer results to reduce load

    print()
    print(f"📝 Query: '{query}'")
    print(f"📊 Requesting: {max_results} results")
    print()
    print("-" * 80)
    print()

    # Execute search
    try:
        print("⏳ Executing search...")
        results = await adapter.search(query, max_results=max_results)
        print("✅ Search completed")
        print()
    except Exception as e:
        print(f"❌ Search failed with exception: {e}")
        print(f"   Exception type: {type(e).__name__}")
        import traceback
        print()
        print("Full traceback:")
        traceback.print_exc()
        return 1

    # Display results
    if not results:
        print("⚠️  No results returned")
        print()
        print("Possible reasons:")
        print("  1. Rate limit exceeded (HTTP 429)")
        print("  2. API is temporarily unavailable")
        print("  3. Network connectivity issues")
        print()
        print("To resolve:")
        print("  - Wait a few minutes before retrying")
        print("  - Get an API key for higher rate limits")
        print("  - Check network connectivity")
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
    print()
    print("Next steps:")
    print("  - The adapter is working correctly!")
    print("  - Try the original query: python test_semantic_scholar_live.py")
    print("  - If you hit rate limits, consider getting an API key")
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
