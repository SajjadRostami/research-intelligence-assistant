"""
Example usage of the GooglePatentsAdapter.

This script demonstrates how to use the Google Patents adapter to search
for patents related to a research topic.
"""

import asyncio
import json

from ria.adapters import GooglePatentsAdapter


async def main():
    """Run example patent search."""
    # Initialize the adapter
    adapter = GooglePatentsAdapter()

    # Example query: search for quantum computing patents
    query = "quantum computing algorithm"
    max_results = 5

    print(f"Searching Google Patents for: '{query}'")
    print(f"Max results: {max_results}\n")

    # Execute the search
    results = await adapter.search(query, max_results=max_results)

    # Display results
    print(f"Found {len(results)} patent(s):\n")

    for i, item in enumerate(results, 1):
        print(f"Patent {i}:")
        print(f"  Title: {item.title}")
        print(f"  Patent Number: {item.patent_number}")
        print(f"  Assignee: {item.author_or_assignee or 'N/A'}")
        print(f"  Publication Date: {item.publication_date or 'N/A'}")
        print(f"  URL: {item.source_url}")
        print(f"  Confidence: {item.confidence_level}")
        print(f"  Source: {item.raw_adapter_source}")
        print()

    # Example: Convert to JSON for serialization
    if results:
        print("\nExample JSON serialization of first result:")
        print(json.dumps(results[0].model_dump(), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
