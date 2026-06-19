#!/usr/bin/env python3
"""
Quick test script for the FastAPI application.

This script demonstrates how to use the Research Intelligence Assistant API.
"""

import asyncio
import httpx


async def test_api():
    """Test the FastAPI endpoints."""
    base_url = "http://localhost:8000"

    print("=" * 80)
    print("Testing Research Intelligence Assistant API")
    print("=" * 80)
    print()

    async with httpx.AsyncClient(timeout=300.0) as client:
        # Test 1: Health check
        print("Test 1: Health Check (GET /)")
        response = await client.get(f"{base_url}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        # Test 2: Detailed health check
        print("Test 2: Detailed Health Check (GET /health)")
        response = await client.get(f"{base_url}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print()

        # Test 3: Generate report (small example)
        print("Test 3: Generate Report (POST /generate)")
        print("Topic: 'machine learning optimization'")
        print("This will take a few minutes...")
        print()

        response = await client.post(
            f"{base_url}/generate",
            json={
                "topic": "machine learning optimization",
                "max_results_per_adapter": 5,  # Small number for quick test
            },
        )

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"Success: {result['success']}")
            print(f"Message: {result['message']}")
            print(f"Report Path: {result['report_path']}")
            print(f"Workspace: {result['workspace_dir']}")
            print()
            print("Statistics:")
            for key, value in result['stats'].items():
                print(f"  {key}: {value}")
            print()
            print("Report preview (first 500 chars):")
            print("-" * 80)
            print(result['report_content'][:500] + "...")
            print("-" * 80)
        else:
            print(f"Error: {response.text}")

        print()
        print("=" * 80)
        print("API Test Complete")
        print("=" * 80)


if __name__ == "__main__":
    print()
    print("Make sure the API server is running:")
    print("  uvicorn app:app --reload --host 0.0.0.0 --port 8000")
    print()
    input("Press Enter to start the test...")
    print()

    asyncio.run(test_api())
