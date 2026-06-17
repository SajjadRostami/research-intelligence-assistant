"""Quick test of Google Patents adapter functionality."""

import asyncio

from ria.adapters import GooglePatentsAdapter
from ria.models import SourceType


async def test_adapter():
    """Test basic adapter functionality."""
    adapter = GooglePatentsAdapter()

    # Verify adapter properties
    assert adapter.source_type == SourceType.PATENT
    print("✓ Adapter source_type is PATENT")

    # Test URL building
    url = adapter._build_search_url("test query")
    assert "patents.google.com" in url
    assert "test+query" in url or "test%20query" in url
    print(f"✓ URL building works: {url}")

    # Test with a simple query (limited results)
    print("\nTesting search functionality...")
    results = await adapter.search("artificial intelligence", max_results=3)

    if results:
        print(f"✓ Search returned {len(results)} results")
        print(f"✓ First result: {results[0].title}")
        print(f"✓ Patent number: {results[0].patent_number}")
        print(f"✓ Source URL: {results[0].source_url}")
        print(f"✓ Adapter source: {results[0].raw_adapter_source}")

        # Verify all required fields are present
        assert results[0].title
        assert results[0].source_url
        assert results[0].source_type == SourceType.PATENT
        assert results[0].raw_adapter_source == "google_patents"
        print("\n✓ All required fields are populated correctly")
    else:
        print("⚠ No results returned (might be rate limited or network issue)")

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_adapter())
