"""
Example usage of the LLMClient for both standard chat and structured JSON responses.

Run this script to see the LLM client in action.
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv

from ria.llm import LLMClient
from ria.models import BenchmarkMetric

# Load environment variables
load_dotenv()


def example_chat():
    """Demonstrate basic chat completion."""
    print("=== Example 1: Basic Chat Completion ===\n")

    client = LLMClient()

    messages = [
        {"role": "system", "content": "You are a helpful research assistant."},
        {
            "role": "user",
            "content": "Explain what a patent is in one sentence.",
        },
    ]

    response = client.chat(messages, temperature=0.7)
    print(f"Response: {response}\n")


def example_chat_json():
    """Demonstrate structured JSON response with Pydantic model."""
    print("=== Example 2: Structured JSON Response ===\n")

    client = LLMClient()

    messages = [
        {
            "role": "system",
            "content": "You are an expert at creating benchmark metrics for research evaluation.",
        },
        {
            "role": "user",
            "content": (
                "Create a benchmark metric for evaluating AI models based on accuracy. "
                "Include a name and description."
            ),
        },
    ]

    # The response will be parsed into a BenchmarkMetric object
    metric = client.chat_json(
        messages=messages,
        response_model=BenchmarkMetric,
        temperature=0.5,
    )

    print(f"Metric Name: {metric.name}")
    print(f"Metric Description: {metric.description}\n")

    # Verify it's a proper Pydantic model
    print(f"Type: {type(metric)}")
    print(f"JSON output: {metric.model_dump_json()}\n")


def example_custom_config():
    """Demonstrate using custom configuration."""
    print("=== Example 3: Custom Configuration ===\n")

    # You can override default settings
    client = LLMClient(
        model="claude-sonnet",  # Use a different model
        timeout=30,  # Shorter timeout
        max_retries=2,  # Fewer retries
    )

    messages = [
        {"role": "system", "content": "You are a concise assistant."},
        {"role": "user", "content": "What is 2+2?"},
    ]

    response = client.chat(messages, temperature=0.0)
    print(f"Response: {response}\n")


def example_error_handling():
    """Demonstrate error handling."""
    print("=== Example 4: Error Handling ===\n")

    client = LLMClient()

    # Example with malformed response model expectation
    try:
        messages = [
            {"role": "user", "content": "Just say hello, don't create any metrics"},
        ]

        # This might fail if the LLM doesn't return valid JSON for BenchmarkMetric
        metric = client.chat_json(
            messages=messages,
            response_model=BenchmarkMetric,
            temperature=0.0,
        )
        print(f"Unexpectedly succeeded: {metric}\n")
    except Exception as e:
        print(f"Expected error caught: {type(e).__name__}: {e}\n")


if __name__ == "__main__":
    print("LLMClient Usage Examples\n")
    print("=" * 60)
    print()

    try:
        example_chat()
        example_chat_json()
        example_custom_config()
        # Uncomment to see error handling:
        # example_error_handling()

        print("=" * 60)
        print("\nAll examples completed successfully!")

    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback

        traceback.print_exc()
