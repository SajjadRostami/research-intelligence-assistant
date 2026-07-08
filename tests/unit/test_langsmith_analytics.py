"""
Unit tests for LangSmith analytics provider.

Tests LangSmith analytics retrieval, fallback behavior, and error handling.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
from ria.langsmith_analytics import LangSmithAnalyticsProvider


@pytest.fixture
def fallback_analytics():
    """Sample fallback analytics from internal tracker."""
    return {
        "topic": "AI Safety",
        "start_time": "2026-07-08T10:00:00",
        "end_time": "2026-07-08T10:05:00",
        "total_duration_seconds": 300.0,
        "total_llm_calls": 5,
        "total_prompt_tokens": 1000,
        "total_completion_tokens": 500,
        "total_tokens": 1500,
        "estimated_total_cost": 0.0150,
        "cache_status": "Fresh research",
        "cached_items_used": 0,
        "fresh_items_fetched": 10,
        "papers_found": 8,
        "patents_found": 2,
        "open_access_papers_found": 3,
        "steps": [
            {
                "step_name": "Fetch Research",
                "duration_seconds": 120.0,
                "prompt_tokens": 500,
                "completion_tokens": 250,
                "total_tokens": 750,
                "estimated_cost": 0.0075,
                "llm_calls": 3,
                "metadata": {},
            },
            {
                "step_name": "Generate Metrics",
                "duration_seconds": 180.0,
                "prompt_tokens": 500,
                "completion_tokens": 250,
                "total_tokens": 750,
                "estimated_cost": 0.0075,
                "llm_calls": 2,
                "metadata": {},
            },
        ],
    }


@pytest.fixture
def mock_langsmith_runs():
    """Sample LangSmith runs."""
    now = datetime.utcnow()

    class MockRun:
        def __init__(self, name, trace_id, prompt_tokens, completion_tokens, duration_seconds):
            self.name = name
            self.trace_id = trace_id
            self.start_time = now - timedelta(seconds=duration_seconds)
            self.end_time = now
            self.outputs = {
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                }
            }
            self.total_cost = None  # LangSmith may not provide cost

    return [
        MockRun("llm_chat", "trace-123", 600, 300, 120),
        MockRun("llm_chat_json", "trace-123", 400, 200, 80),
    ]


@pytest.mark.asyncio
async def test_langsmith_disabled(fallback_analytics):
    """Test that provider returns fallback when LangSmith is disabled."""
    with patch.dict('os.environ', {
        'LANGSMITH_TRACING': 'false',
        'LANGCHAIN_TRACING_V2': 'false'
    }, clear=False):
        provider = LangSmithAnalyticsProvider()

        result = await provider.get_analytics_for_report(
            report_id="test-123",
            fallback_analytics=fallback_analytics,
            topic="AI Safety",
        )

        assert result["source"] == "Local tracker"
        assert "LangSmith tracing not enabled" in result["analytics_source"]
        assert result["total_llm_calls"] == 5
        assert result["total_tokens"] == 1500


@pytest.mark.asyncio
async def test_langsmith_enabled_no_api_key(fallback_analytics):
    """Test that provider returns fallback when API key is missing."""
    with patch.dict('os.environ', {
        'LANGSMITH_TRACING': 'true',
        'LANGSMITH_API_KEY': '',
        'LANGCHAIN_API_KEY': '',
    }, clear=False):
        provider = LangSmithAnalyticsProvider()

        result = await provider.get_analytics_for_report(
            report_id="test-123",
            fallback_analytics=fallback_analytics,
            topic="AI Safety",
        )

        assert result["source"] == "Local tracker"
        assert "LangSmith tracing not enabled" in result["analytics_source"]


@pytest.mark.asyncio
async def test_langsmith_successful_retrieval(fallback_analytics, mock_langsmith_runs):
    """Test successful LangSmith analytics retrieval with current variables."""
    with patch.dict('os.environ', {
        'LANGSMITH_TRACING': 'true',
        'LANGSMITH_API_KEY': 'test-key',
        'LANGSMITH_PROJECT': 'test-project',
    }, clear=False):
        with patch('ria.langsmith_analytics.LANGSMITH_AVAILABLE', True):
            with patch('ria.langsmith_analytics.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.list_runs.return_value = mock_langsmith_runs
                mock_client_class.return_value = mock_client

                provider = LangSmithAnalyticsProvider()
                provider.enabled = True
                provider.client = mock_client

                result = await provider.get_analytics_for_report(
                    report_id="test-123",
                    fallback_analytics=fallback_analytics,
                    topic="AI Safety",
                )

                # Verify LangSmith was queried
                assert mock_client.list_runs.called

                # Verify analytics source
                assert result["source"] == "LangSmith"
                assert result["analytics_source"] == "LangSmith"

                # Verify aggregated token counts
                assert result["total_llm_calls"] == 2
                assert result["total_prompt_tokens"] == 1000
                assert result["total_completion_tokens"] == 500
                assert result["total_tokens"] == 1500

                # Verify trace info
                assert result["trace_id"] == "trace-123"
                assert "trace_url" in result

                # Verify steps data
                assert len(result["steps"]) == 2


@pytest.mark.asyncio
async def test_langsmith_legacy_variables(fallback_analytics, mock_langsmith_runs):
    """Test that legacy LANGCHAIN_* variables still work."""
    with patch.dict('os.environ', {
        'LANGCHAIN_TRACING_V2': 'true',  # Legacy tracing variable
        'LANGCHAIN_API_KEY': 'test-key',  # Legacy API key
        'LANGCHAIN_PROJECT': 'test-project',  # Legacy project
    }, clear=False):
        with patch('ria.langsmith_analytics.LANGSMITH_AVAILABLE', True):
            with patch('ria.langsmith_analytics.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.list_runs.return_value = mock_langsmith_runs
                mock_client_class.return_value = mock_client

                provider = LangSmithAnalyticsProvider()
                provider.enabled = True
                provider.client = mock_client

                result = await provider.get_analytics_for_report(
                    report_id="test-123",
                    fallback_analytics=fallback_analytics,
                    topic="AI Safety",
                )

                # Should work with legacy variables
                assert result["source"] == "LangSmith"
                assert result["analytics_source"] == "LangSmith"
                assert result["total_llm_calls"] == 2


@pytest.mark.asyncio
async def test_langsmith_no_traces_found(fallback_analytics):
    """Test fallback when no LangSmith traces found."""
    with patch.dict('os.environ', {
        'LANGSMITH_TRACING': 'true',
        'LANGSMITH_API_KEY': 'test-key',
    }, clear=False):
        with patch('ria.langsmith_analytics.LANGSMITH_AVAILABLE', True):
            with patch('ria.langsmith_analytics.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.list_runs.return_value = []
                mock_client_class.return_value = mock_client

                provider = LangSmithAnalyticsProvider()
                provider.enabled = True
                provider.client = mock_client

                result = await provider.get_analytics_for_report(
                    report_id="test-123",
                    fallback_analytics=fallback_analytics,
                    topic="AI Safety",
                )

                # Should fall back to local tracker
                assert result["source"] == "Local tracker"
                assert "No LangSmith traces found" in result["analytics_source"]
                assert result["total_llm_calls"] == 5


@pytest.mark.asyncio
async def test_langsmith_query_error(fallback_analytics):
    """Test fallback when LangSmith query fails."""
    with patch.dict('os.environ', {
        'LANGSMITH_TRACING': 'true',
        'LANGSMITH_API_KEY': 'test-key',
    }, clear=False):
        with patch('ria.langsmith_analytics.LANGSMITH_AVAILABLE', True):
            with patch('ria.langsmith_analytics.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.list_runs.side_effect = Exception("API error")
                mock_client_class.return_value = mock_client

                provider = LangSmithAnalyticsProvider()
                provider.enabled = True
                provider.client = mock_client

                result = await provider.get_analytics_for_report(
                    report_id="test-123",
                    fallback_analytics=fallback_analytics,
                    topic="AI Safety",
                )

                # Should fall back to local tracker
                assert result["source"] == "Local tracker"
                assert "LangSmith query failed" in result["analytics_source"]
                assert result["total_llm_calls"] == 5


@pytest.mark.asyncio
async def test_cost_estimation():
    """Test cost estimation when LangSmith doesn't provide cost."""
    provider = LangSmithAnalyticsProvider()

    # Test Claude Sonnet pricing
    with patch.dict('os.environ', {'LLM_MODEL': 'claude-sonnet'}, clear=False):
        cost = provider._estimate_cost(prompt_tokens=1000, completion_tokens=500)
        # 1000 * 0.003 / 1000 + 500 * 0.015 / 1000 = 0.003 + 0.0075 = 0.0105
        assert abs(cost - 0.0105) < 0.0001

    # Test Claude Haiku pricing
    with patch.dict('os.environ', {'LLM_MODEL': 'claude-haiku'}, clear=False):
        cost = provider._estimate_cost(prompt_tokens=1000, completion_tokens=500)
        # 1000 * 0.00025 / 1000 + 500 * 0.00125 / 1000 = 0.00025 + 0.000625 = 0.000875
        assert abs(cost - 0.000875) < 0.0001


def test_analytics_source_field_formatting(fallback_analytics):
    """Test that analytics source field is properly formatted."""
    provider = LangSmithAnalyticsProvider()

    # Test with reason
    result = provider._format_fallback_analytics(
        fallback_analytics,
        reason="LangSmith unavailable"
    )

    assert result["source"] == "Local tracker"
    assert result["analytics_source"] == "Local tracker (LangSmith unavailable)"

    # Verify original analytics are preserved
    assert result["total_llm_calls"] == 5
    assert result["total_tokens"] == 1500


@pytest.mark.asyncio
async def test_not_available_for_missing_values(fallback_analytics):
    """Test that missing values are not hallucinated."""
    # Create fallback with None values
    incomplete_analytics = {
        **fallback_analytics,
        "total_prompt_tokens": None,
        "total_completion_tokens": None,
        "estimated_total_cost": None,
    }

    # Explicitly disable LangSmith so it uses fallback
    with patch.dict('os.environ', {
        'LANGSMITH_TRACING': 'false',
        'LANGCHAIN_TRACING_V2': 'false',
        'LANGSMITH_API_KEY': '',
        'LANGCHAIN_API_KEY': '',
    }, clear=False):
        provider = LangSmithAnalyticsProvider()

        result = await provider.get_analytics_for_report(
            report_id="test-123",
            fallback_analytics=incomplete_analytics,
            topic="AI Safety",
        )

        # Verify None values are preserved (not replaced with fake data)
        assert result["total_prompt_tokens"] is None
        assert result["total_completion_tokens"] is None
        assert result["estimated_total_cost"] is None


@pytest.mark.asyncio
async def test_langsmith_missing_usage_returns_none(fallback_analytics):
    """Test that LangSmith runs without usage data return 0 for tokens (from aggregation)."""
    # Create mocks for runs without usage data
    now = datetime.utcnow()

    class MockRunNoUsage:
        def __init__(self, name):
            self.name = name
            self.trace_id = "trace-456"
            self.start_time = now - timedelta(seconds=100)
            self.end_time = now
            self.outputs = {}  # No usage data
            self.total_cost = None
            # No token attributes
            self.prompt_tokens = None
            self.completion_tokens = None
            self.total_tokens = None

    mock_runs = [MockRunNoUsage("llm_call_1"), MockRunNoUsage("llm_call_2")]

    with patch.dict('os.environ', {
        'LANGSMITH_TRACING': 'true',
        'LANGSMITH_API_KEY': 'test-key',
    }, clear=False):
        with patch('ria.langsmith_analytics.LANGSMITH_AVAILABLE', True):
            with patch('ria.langsmith_analytics.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.list_runs.return_value = mock_runs
                mock_client_class.return_value = mock_client

                provider = LangSmithAnalyticsProvider()
                provider.enabled = True
                provider.client = mock_client

                result = await provider.get_analytics_for_report(
                    report_id="test-456",
                    fallback_analytics=fallback_analytics,
                    topic="AI Safety",
                )

                # Verify source is LangSmith
                assert result["source"] == "LangSmith"

                # Verify that missing usage data results in 0 tokens (aggregated from multiple runs with no data)
                # Since we're summing across runs with no data, we get 0, not None
                assert result["total_llm_calls"] == 2
                assert result["total_prompt_tokens"] == 0
                assert result["total_completion_tokens"] == 0
                assert result["total_tokens"] == 0

                # Cost estimation should return 0 for 0 tokens
                assert result["estimated_total_cost"] == 0.0


@pytest.mark.asyncio
async def test_langsmith_with_usage_returns_values(fallback_analytics):
    """Test that LangSmith runs with usage data return actual token counts."""
    now = datetime.utcnow()

    class MockRunWithUsage:
        def __init__(self, name, prompt_tokens, completion_tokens):
            self.name = name
            self.trace_id = "trace-789"
            self.start_time = now - timedelta(seconds=100)
            self.end_time = now
            self.outputs = {
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens,
                }
            }
            self.total_cost = None
            self.prompt_tokens = None
            self.completion_tokens = None
            self.total_tokens = None

    mock_runs = [
        MockRunWithUsage("llm_call_1", 100, 50),
        MockRunWithUsage("llm_call_2", 200, 100),
    ]

    with patch.dict('os.environ', {
        'LANGSMITH_TRACING': 'true',
        'LANGSMITH_API_KEY': 'test-key',
    }, clear=False):
        with patch('ria.langsmith_analytics.LANGSMITH_AVAILABLE', True):
            with patch('ria.langsmith_analytics.Client') as mock_client_class:
                mock_client = Mock()
                mock_client.list_runs.return_value = mock_runs
                mock_client_class.return_value = mock_client

                provider = LangSmithAnalyticsProvider()
                provider.enabled = True
                provider.client = mock_client

                result = await provider.get_analytics_for_report(
                    report_id="test-789",
                    fallback_analytics=fallback_analytics,
                    topic="AI Safety",
                )

                # Verify source is LangSmith
                assert result["source"] == "LangSmith"

                # Verify actual usage data is returned
                assert result["total_llm_calls"] == 2
                assert result["total_prompt_tokens"] == 300
                assert result["total_completion_tokens"] == 150
                assert result["total_tokens"] == 450

                # Cost should be estimated (non-zero)
                assert result["estimated_total_cost"] > 0
