"""
Test to reproduce the metric name bug.

This test verifies that:
1. /suggest-metrics returns metrics with "name" field
2. The UI-compatible response shape is correct
3. No metric has undefined/missing name
"""

import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_suggest_metrics_returns_name_field():
    """Test that /suggest-metrics returns metrics with 'name' field."""
    response = client.post(
        "/suggest-metrics",
        json={"topic": "XPBD soft body simulation", "max_metrics": 5}
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "suggested_metrics" in data
    assert len(data["suggested_metrics"]) > 0

    # Check each metric has the required fields
    for metric in data["suggested_metrics"]:
        assert "name" in metric, f"Metric missing 'name' field: {metric}"
        assert metric["name"] is not None, f"Metric has None name: {metric}"
        assert metric["name"] != "", f"Metric has empty name: {metric}"
        assert "description" in metric
        assert "category" in metric
        assert "source" in metric

        # Optional but recommended fields
        if "score" in metric:
            assert isinstance(metric["score"], (int, float))


def test_suggest_metrics_ui_compatible_shape():
    """Test that the response shape matches UI expectations."""
    response = client.post(
        "/suggest-metrics",
        json={"topic": "XPBD soft body simulation", "max_metrics": 10}
    )

    data = response.json()
    metrics = data["suggested_metrics"]

    expected_fields = {"name", "description", "category", "source"}

    for metric in metrics:
        actual_fields = set(metric.keys())
        assert expected_fields.issubset(actual_fields), (
            f"Metric missing required fields. "
            f"Expected: {expected_fields}, Got: {actual_fields}"
        )


def test_no_metric_name_field_in_response():
    """Verify that we don't return 'metric_name' instead of 'name'."""
    response = client.post(
        "/suggest-metrics",
        json={"topic": "AI research", "max_metrics": 5}
    )

    data = response.json()
    metrics = data["suggested_metrics"]

    for metric in metrics:
        # Should use 'name', not 'metric_name'
        assert "name" in metric, "Response should use 'name' field"
        # Ensure we're not accidentally including both
        if "metric_name" in metric:
            # If both exist, they should match
            assert metric["name"] == metric["metric_name"], (
                "If both 'name' and 'metric_name' exist, they should match"
            )


def test_metric_bank_agent_direct():
    """Test MetricBankAgent directly to see what it returns."""
    from ria.agents import MetricBankAgent
    from ria.llm import LLMClient

    llm_client = LLMClient()
    agent = MetricBankAgent(llm_client=llm_client)
    agent.initialize_defaults()

    suggestions = agent.get_smart_suggestions(
        topic="XPBD soft body simulation",
        max_results=5,
        include_fresh_llm_suggestions=False,
    )

    assert len(suggestions) > 0

    for suggestion in suggestions:
        print(f"Agent returned: {suggestion.keys()}")
        # The agent currently returns 'metric_name', not 'name'
        # This is the root cause of the bug
        assert "metric_name" in suggestion or "name" in suggestion, (
            f"Metric missing both 'metric_name' and 'name': {suggestion}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
