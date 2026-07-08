#!/usr/bin/env python
"""
Verification script for LangSmith analytics integration.

Run this script to verify that LangSmith analytics are properly configured
and working in your Research Intelligence Assistant installation.

Usage:
    python verify_langsmith_analytics.py
"""

import os
import sys
from pathlib import Path


def check_env_vars():
    """Check if LangSmith environment variables are set."""
    print("🔍 Checking environment variables...")

    # Current LangSmith variables (primary)
    langsmith_tracing = (
        os.getenv("LANGSMITH_TRACING", "").lower() or
        os.getenv("LANGCHAIN_TRACING_V2", "").lower()
    )
    langsmith_api_key = (
        os.getenv("LANGSMITH_API_KEY", "").strip() or
        os.getenv("LANGCHAIN_API_KEY", "").strip()
    )
    langsmith_project = (
        os.getenv("LANGSMITH_PROJECT", "").strip() or
        os.getenv("LANGCHAIN_PROJECT", "").strip() or
        "research-intelligence-assistant"
    )

    print(f"  LANGSMITH_TRACING (or LANGCHAIN_TRACING_V2): {langsmith_tracing}")
    print(f"  LANGSMITH_API_KEY (or LANGCHAIN_API_KEY): {'✓ Set' if langsmith_api_key else '✗ Not set'}")
    print(f"  LANGSMITH_PROJECT (or LANGCHAIN_PROJECT): {langsmith_project}")

    if langsmith_tracing == "true" and langsmith_api_key:
        print("✅ LangSmith is enabled and configured\n")
        return True
    elif langsmith_tracing == "false":
        print("⚠️  LangSmith tracing is disabled")
        print("   Analytics will use internal tracker only\n")
        return False
    else:
        print("⚠️  LangSmith is not properly configured")
        print("   Set LANGSMITH_TRACING=true and LANGSMITH_API_KEY to enable\n")
        return False


def check_langsmith_import():
    """Check if langsmith package is installed."""
    print("📦 Checking langsmith package...")

    try:
        import langsmith
        print(f"✅ langsmith package installed (version: {langsmith.__version__})\n")
        return True
    except ImportError:
        print("✗ langsmith package not installed")
        print("  Install with: pip install langsmith\n")
        return False


def check_provider_initialization():
    """Check if LangSmithAnalyticsProvider can be initialized."""
    print("🔧 Checking LangSmithAnalyticsProvider initialization...")

    try:
        from ria.langsmith_analytics import LangSmithAnalyticsProvider

        provider = LangSmithAnalyticsProvider()

        if provider.enabled:
            print("✅ LangSmithAnalyticsProvider is enabled")
            print(f"   Project: {provider.project_name}")
            print(f"   API Key: {'✓ Set' if provider.api_key else '✗ Not set'}\n")
            return True
        else:
            print("⚠️  LangSmithAnalyticsProvider is disabled")
            print("   Will fall back to internal analytics tracker\n")
            return False

    except Exception as e:
        print(f"✗ Error initializing provider: {e}\n")
        return False


def check_llm_client():
    """Check if LLMClient can attach report_id."""
    print("🤖 Checking LLMClient with report_id...")

    try:
        # Check if environment has required LLM config
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL")

        if not api_key or not base_url:
            print("⚠️  OPENAI_API_KEY or OPENAI_BASE_URL not set")
            print("   Cannot test LLMClient initialization")
            print("   Set these variables in .env to test full integration\n")
            return False

        from ria.llm import LLMClient

        client = LLMClient(
            report_id="test-report-123",
            topic="Test Topic",
        )

        print("✅ LLMClient initialized with report_id")
        print(f"   Report ID: {client.report_id}")
        print(f"   Topic: {client.topic}")
        print(f"   LangSmith Enabled: {client.langsmith_enabled}\n")
        return True

    except Exception as e:
        print(f"✗ Error initializing LLMClient: {e}\n")
        return False


def check_recent_workspaces():
    """Check for recent analytics.json files in workspaces."""
    print("📁 Checking recent workspaces for analytics...")

    workspaces_dir = Path("./workspaces")

    if not workspaces_dir.exists():
        print("⚠️  No workspaces directory found")
        print("   Generate a report first to create analytics data\n")
        return False

    # Find most recent analytics.json
    analytics_files = list(workspaces_dir.glob("*/analytics.json"))

    if not analytics_files:
        print("⚠️  No analytics.json files found in workspaces")
        print("   Generate a report first to create analytics data\n")
        return False

    # Get most recent
    latest_analytics = max(analytics_files, key=lambda p: p.stat().st_mtime)

    print(f"📊 Most recent analytics: {latest_analytics}")

    try:
        import json

        with open(latest_analytics) as f:
            data = json.load(f)

        analytics_source = data.get("analytics_source") or data.get("source", "Unknown")
        print(f"   Analytics Source: {analytics_source}")
        print(f"   Total LLM Calls: {data.get('total_llm_calls', 'N/A')}")
        print(f"   Total Tokens: {data.get('total_tokens', 'N/A')}")
        print(f"   Estimated Cost: ${data.get('estimated_total_cost', 0):.4f}")

        if "LangSmith" in analytics_source:
            print("✅ Analytics are being sourced from LangSmith!\n")
            return True
        else:
            print("⚠️  Analytics are using internal tracker")
            print(f"   Reason: {analytics_source}\n")
            return False

    except Exception as e:
        print(f"✗ Error reading analytics file: {e}\n")
        return False


def print_summary(checks):
    """Print summary of verification results."""
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    total = len(checks)
    passed = sum(1 for check in checks.values() if check)

    for name, result in checks.items():
        status = "✅ PASS" if result else "⚠️  WARN"
        print(f"{status} - {name}")

    print()
    print(f"Result: {passed}/{total} checks passed")

    if checks.get("LangSmith Enabled") and checks.get("Provider Initialized"):
        print("\n✅ LangSmith analytics is properly configured!")
        print("   Generate a report to see LangSmith-sourced analytics.")
    elif not checks.get("LangSmith Enabled"):
        print("\n⚠️  LangSmith is disabled - using internal tracker fallback")
        print("   To enable, set:")
        print("     LANGSMITH_TRACING=true")
        print("     LANGSMITH_API_KEY=your_key_here")
    else:
        print("\n⚠️  Some checks failed - review warnings above")


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("LangSmith Analytics Verification")
    print("=" * 60)
    print()

    checks = {}

    checks["LangSmith Enabled"] = check_env_vars()
    checks["LangSmith Package"] = check_langsmith_import()
    checks["Provider Initialized"] = check_provider_initialization()
    checks["LLM Client"] = check_llm_client()
    checks["Recent Analytics"] = check_recent_workspaces()

    print_summary(checks)


if __name__ == "__main__":
    main()
