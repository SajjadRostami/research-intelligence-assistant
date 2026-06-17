#!/usr/bin/env python3
"""
Test script for MockPatentAdapter (MVP version).

This script demonstrates the patent adapter interface using MockPatentAdapter,
which returns synthetic data for testing purposes.

Note:
- GooglePatentsAdapter: Deprecated (requires JavaScript rendering)
- PatentsViewAdapter: Deprecated (API shut down)
- MockPatentAdapter: Current MVP solution (returns synthetic data)
- Future: Replace with Google Patents BigQuery or Lens.org API
"""

import asyncio
import sys

from ria.adapters import MockPatentAdapter


async def main():
    """
    Main test function for MockPatentAdapter.

    This function:
    1. Creates a MockPatentAdapter instance
    2. Executes a search query for "XPBD soft body simulation algorithm"
    3. Requests 5 results
    4. Displays title, patent number, assignee, and URL for each result
    5. Handles errors gracefully with helpful error messages

    Note: This returns synthetic data for MVP testing.
    """
    print("=" * 80)
    print("Mock Patent Adapter Test (MVP)")
    print("=" * 80)
    print()
    print("⚠ WARNING: This adapter returns SYNTHETIC DATA for testing purposes.")
    print("   Replace with a real patent API (BigQuery, Lens.org) for production.")
    print()

    # Step 1: Create a MockPatentAdapter instance
    # Returns synthetic patent data for MVP testing
    adapter = MockPatentAdapter()
    print("✓ Created MockPatentAdapter instance")
    print()

    # Step 2: Define the search parameters
    query = "XPBD soft body simulation algorithm"
    max_results = 5

    print(f"Search Query: '{query}'")
    print(f"Max Results: {max_results}")
    print()
    print("Searching... (this may take a few seconds)")
    print()

    try:
        # Step 3: Execute the search (async operation)
        # The mock adapter will:
        #   - Generate synthetic patent data based on the query
        #   - Return up to max_results patent items with plausible titles
        #   - Mark results with LOW confidence (synthetic data)
        results = await adapter.search(query=query, max_results=max_results)

        # Step 4: Check if we got any results
        if not results:
            print("⚠ No results found for this query.")
            print()
            print("Possible reasons:")
            print("  - The query returned no matches in the USPTO database")
            print("  - Network connectivity issues")
            print("  - PatentsView API may be temporarily unavailable")
            print()
            print("Try running the script again or try a different query.")
            return

        # Step 5: Display the results
        print(f"✓ Found {len(results)} result(s)")
        print("=" * 80)
        print()

        # Loop through each result and print the requested fields
        for i, result in enumerate(results, start=1):
            print(f"Result #{i}")
            print("-" * 80)

            # Print title (always available)
            print(f"Title:         {result.title}")

            # Print patent number (may be None if not found in HTML)
            patent_num = result.patent_number if result.patent_number else "N/A"
            print(f"Patent Number: {patent_num}")

            # Print assignee (may be None if not found in HTML)
            assignee = result.author_or_assignee if result.author_or_assignee else "N/A"
            print(f"Assignee:      {assignee}")

            # Print URL (always available)
            print(f"URL:           {result.source_url}")

            # Optional: Print additional metadata for debugging
            if result.publication_date:
                print(f"Published:     {result.publication_date}")
            if result.confidence_level:
                print(f"Confidence:    {result.confidence_level.value}")

            print()

        print("=" * 80)
        print(f"✓ Test completed successfully! Retrieved {len(results)} patent(s).")

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        print("\n\n⚠ Test interrupted by user (Ctrl+C)")
        sys.exit(130)

    except Exception as e:
        # Handle any errors that occur during the search
        print(f"✗ Error occurred during search: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        print()
        print("Common reasons why the test might fail:")
        print()
        print("1. Network Issues")
        print("   - No internet connection")
        print("   - Firewall blocking outbound HTTPS requests")
        print("   - DNS resolution failure for api.patentsview.org")
        print()
        print("2. API Unavailable (HTTP 503)")
        print("   - PatentsView API may be temporarily down")
        print("   - Solution: Check https://patentsview.org/ status")
        print()
        print("3. Invalid Query Format")
        print("   - Query may contain special characters that break the API")
        print("   - Solution: Try a simpler query with basic keywords")
        print()
        print("4. API Rate Limiting")
        print("   - PatentsView has usage limits (unlikely for normal use)")
        print("   - Solution: Wait and retry")
        print()
        print("5. Missing Dependencies")
        print("   - Required package (httpx) not installed")
        print("   - Solution: pip install httpx")
        print()
        print("Troubleshooting steps:")
        print("  - Verify internet connectivity: ping api.patentsview.org")
        print("  - Check API status: https://patentsview.org/apis")
        print("  - Try a simpler query like 'artificial intelligence'")
        print("  - Check the logs for detailed error messages")

        # Exit with error code
        sys.exit(1)


if __name__ == "__main__":
    # Run the async main function
    # asyncio.run() creates an event loop, runs the coroutine, and cleans up
    asyncio.run(main())
