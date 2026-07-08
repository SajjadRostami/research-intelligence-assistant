"""
Tests for Metric Bank Agent adaptive metric intelligence.
"""

import json
import tempfile
from pathlib import Path

import pytest

from ria.agents.metric_bank_agent import MetricBankAgent, MetricUsageData


@pytest.fixture
def temp_storage():
    """Create a temporary storage file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


def test_initialization_empty(temp_storage):
    """Test agent initialization with empty storage."""
    agent = MetricBankAgent(storage_path=temp_storage)
    assert len(agent.metrics) == 0


def test_initialize_defaults(temp_storage):
    """Test default metrics initialization."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    assert len(agent.metrics) > 0
    assert "AI Support" in agent.metrics
    assert "XPBD Support" in agent.metrics
    assert "GPU Support" in agent.metrics

    # Check default values
    ai_metric = agent.metrics["AI Support"]
    assert ai_metric.source == "default"
    assert ai_metric.selected_count == 0
    assert ai_metric.custom_added_count == 0
    assert ai_metric.is_active is True


def test_metric_normalization(temp_storage):
    """Test metric name normalization."""
    agent = MetricBankAgent(storage_path=temp_storage)

    # Test normalization
    assert agent._normalize_metric_name("AI Support") == "ai support"
    assert agent._normalize_metric_name("AI-Support") == "ai support"
    assert agent._normalize_metric_name("AI  Support") == "ai support"
    assert agent._normalize_metric_name("Artificial Intelligence") == "ai"
    assert agent._normalize_metric_name("Machine Learning") == "ml"
    assert agent._normalize_metric_name("Virtual Reality") == "vr"


def test_record_metric_selected(temp_storage):
    """Test recording metric selection."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    initial_count = agent.metrics["AI Support"].selected_count
    initial_priority = agent.metrics["AI Support"].priority_score

    # Record selection
    agent.record_metric_selected("AI Support", topic="Test Topic")

    # Verify counts increased
    assert agent.metrics["AI Support"].selected_count == initial_count + 1
    assert agent.metrics["AI Support"].priority_score > initial_priority
    assert "Test Topic" in agent.metrics["AI Support"].topics_used
    assert agent.metrics["AI Support"].last_selected_at is not None


def test_record_custom_metric_added_new(temp_storage):
    """Test adding a new custom metric."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    # Add new custom metric
    agent.record_custom_metric_added(
        metric_name="AI Capability",
        topic="XPBD Simulation",
        description="Custom AI metric",
        category="Technology",
    )

    # Verify metric was added
    assert "AI Capability" in agent.metrics
    metric = agent.metrics["AI Capability"]

    assert metric.source == "user_custom"
    assert metric.custom_added_count == 1
    assert metric.selected_count == 1  # Also counts as selection
    assert "XPBD Simulation" in metric.topics_used
    assert metric.is_active is True


def test_record_custom_metric_added_existing(temp_storage):
    """Test adding a custom metric that matches existing metric."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    initial_count = agent.metrics["AI Support"].custom_added_count

    # Add custom metric with similar name (should match existing)
    agent.record_custom_metric_added(
        metric_name="AI Support",
        topic="Test Topic",
    )

    # Verify existing metric was promoted, not duplicated
    assert agent.metrics["AI Support"].custom_added_count == initial_count + 1
    assert agent.metrics["AI Support"].selected_count >= 1
    assert "Test Topic" in agent.metrics["AI Support"].topics_used

    # Should not create duplicate
    assert "ai support" not in agent.metrics


def test_record_custom_metric_similar_name(temp_storage):
    """Test that similar custom metrics promote existing ones."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    # Add variations of AI metric
    agent.record_custom_metric_added("AI", topic="Topic 1")
    agent.record_custom_metric_added("Artificial Intelligence", topic="Topic 2")
    agent.record_custom_metric_added("AI Support", topic="Topic 3")

    # All should map to "AI Support" (default metric)
    assert agent.metrics["AI Support"].custom_added_count == 3
    assert len(agent.metrics["AI Support"].topics_used) == 3


def test_record_metric_ignored(temp_storage):
    """Test recording ignored metrics."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    metric_name = "Meshless Method Support"
    initial_priority = agent.metrics[metric_name].priority_score

    # Record ignore
    agent.record_metric_ignored(metric_name, topic="Test Topic")

    # Verify rejection count increased and priority decreased
    assert agent.metrics[metric_name].rejected_count == 1
    assert agent.metrics[metric_name].priority_score < initial_priority
    assert agent.metrics[metric_name].is_active is True  # Still active after 1 ignore


def test_metric_deactivation_after_many_ignores(temp_storage):
    """Test metric deactivation after repeated ignores."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    metric_name = "Meshless Method Support"

    # Ignore many times
    for i in range(agent.IGNORE_THRESHOLD + 1):
        agent.record_metric_ignored(metric_name, topic=f"Topic {i}")

    # Verify metric was deactivated
    assert agent.metrics[metric_name].is_active is False
    assert agent.metrics[metric_name].rejected_count >= agent.IGNORE_THRESHOLD


def test_get_smart_suggestions(temp_storage):
    """Test smart suggestions with learned behavior."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    # Record some usage
    agent.record_metric_selected("AI Support", topic="Machine Learning")
    agent.record_metric_selected("AI Support", topic="Machine Learning")
    agent.record_custom_metric_added("AI Capability", topic="Machine Learning")

    # Get suggestions
    suggestions = agent.get_smart_suggestions(
        topic="Machine Learning",
        max_results=10,
        include_fresh_llm_suggestions=False,  # Disable LLM for this test
    )

    assert len(suggestions) > 0
    assert len(suggestions) <= 10

    # AI Support should rank high due to usage
    ai_suggestions = [s for s in suggestions if "AI" in s["metric_name"]]
    assert len(ai_suggestions) > 0

    # Check suggestion structure
    first = suggestions[0]
    assert "metric_name" in first
    assert "description" in first
    assert "category" in first
    assert "final_score" in first
    assert "reason" in first


def test_smart_suggestions_ignore_inactive(temp_storage):
    """Test that inactive metrics are not suggested."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    metric_name = "Meshless Method Support"

    # Deactivate metric
    for i in range(agent.IGNORE_THRESHOLD + 1):
        agent.record_metric_ignored(metric_name, topic=f"Topic {i}")

    # Get suggestions
    suggestions = agent.get_smart_suggestions(
        topic="Test Topic",
        max_results=20,
        include_fresh_llm_suggestions=False,
    )

    # Inactive metric should not appear
    suggested_names = [s["metric_name"] for s in suggestions]
    assert metric_name not in suggested_names


def test_batch_feedback(temp_storage):
    """Test batch feedback recording."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    selected = ["AI Support", "GPU Support"]
    custom = ["AI Capability", "Custom Metric"]
    suggested = ["AI Support", "GPU Support", "VR HMD Integration", "XPBD Support"]

    # Record batch feedback
    agent.record_batch_feedback(
        selected_metrics=selected,
        custom_metrics=custom,
        suggested_metrics=suggested,
        topic="Test Topic",
    )

    # Verify selected metrics
    assert agent.metrics["AI Support"].selected_count >= 1
    assert agent.metrics["GPU Support"].selected_count >= 1

    # Verify custom metrics
    assert "AI Capability" in agent.metrics or agent.metrics["AI Support"].custom_added_count >= 1
    assert "Custom Metric" in agent.metrics

    # Verify ignored metrics
    assert agent.metrics["VR HMD Integration"].rejected_count >= 1
    assert agent.metrics["XPBD Support"].rejected_count >= 1


def test_metric_score_calculation(temp_storage):
    """Test metric scoring formula."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    metric = agent.metrics["AI Support"]
    topic = "Test Topic"

    # Initial score (just priority)
    score_initial = agent._calculate_metric_score(metric, topic)

    # Add selections
    agent.record_metric_selected("AI Support", topic)
    agent.record_metric_selected("AI Support", topic)

    score_after_selections = agent._calculate_metric_score(metric, topic)
    assert score_after_selections > score_initial

    # Add custom additions (strong signal)
    agent.record_custom_metric_added("AI Support", topic)

    score_after_custom = agent._calculate_metric_score(metric, topic)
    assert score_after_custom > score_after_selections

    # Add ignores (penalty)
    agent.record_metric_ignored("AI Support", topic)
    agent.record_metric_ignored("AI Support", topic)

    score_after_ignores = agent._calculate_metric_score(metric, topic)
    assert score_after_ignores < score_after_custom


def test_get_metric_by_name(temp_storage):
    """Test retrieving a metric by name."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    metric = agent.get_metric_by_name("AI Support")

    assert metric is not None
    assert metric["metric_name"] == "AI Support"
    assert metric["source"] == "default"
    assert "description" in metric
    assert "category" in metric


def test_get_metric_by_name_not_found(temp_storage):
    """Test retrieving a non-existent metric."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    metric = agent.get_metric_by_name("Nonexistent Metric")
    assert metric is None


def test_reactivate_metric(temp_storage):
    """Test reactivating a deactivated metric."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    metric_name = "Meshless Method Support"

    # Deactivate
    for i in range(agent.IGNORE_THRESHOLD + 1):
        agent.record_metric_ignored(metric_name, topic=f"Topic {i}")

    assert agent.metrics[metric_name].is_active is False

    # Reactivate
    success = agent.reactivate_metric(metric_name)

    assert success is True
    assert agent.metrics[metric_name].is_active is True
    assert agent.metrics[metric_name].rejected_count == 0
    assert agent.metrics[metric_name].priority_score == 0.5


def test_persistence(temp_storage):
    """Test that data persists across sessions."""
    # Session 1: Create and modify data
    agent1 = MetricBankAgent(storage_path=temp_storage)
    agent1.initialize_defaults()
    agent1.record_metric_selected("AI Support", topic="Test")
    agent1.record_custom_metric_added("Custom Metric", topic="Test")

    selected_count = agent1.metrics["AI Support"].selected_count

    # Session 2: Load data
    agent2 = MetricBankAgent(storage_path=temp_storage)

    # Verify data persisted
    assert len(agent2.metrics) > 0
    assert "AI Support" in agent2.metrics
    assert agent2.metrics["AI Support"].selected_count == selected_count
    assert "Custom Metric" in agent2.metrics


def test_no_duplicate_metrics(temp_storage):
    """Test that duplicate/similar metrics are not created."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    # Add multiple variations
    agent.record_custom_metric_added("AI", topic="Topic 1")
    agent.record_custom_metric_added("AI Support", topic="Topic 2")
    agent.record_custom_metric_added("Artificial Intelligence", topic="Topic 3")
    agent.record_custom_metric_added("ai support", topic="Topic 4")

    # Should not create duplicates
    # All should map to "AI Support" (the default metric)
    # Check for metrics where "ai" is the main term (not just a substring in other words)
    ai_metrics = [
        key for key, metric in agent.metrics.items()
        if agent._normalize_metric_name(key) in ["ai", "ai support", "artificial intelligence"]
    ]

    # Should only have 1 metric (AI Support, since all variations map to it)
    assert len(ai_metrics) == 1
    assert "AI Support" in ai_metrics

    # Verify the metric has accumulated counts
    assert agent.metrics["AI Support"].custom_added_count == 4


def test_suggestion_reason_generation(temp_storage):
    """Test that suggestion reasons are meaningful."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    # Record some activity
    agent.record_metric_selected("AI Support", topic="Test")
    agent.record_custom_metric_added("AI Support", topic="Test")

    suggestions = agent.get_smart_suggestions(
        topic="Test",
        max_results=5,
        include_fresh_llm_suggestions=False,
    )

    # Find AI Support in suggestions
    ai_suggestion = next((s for s in suggestions if s["metric_name"] == "AI Support"), None)

    assert ai_suggestion is not None
    assert "reason" in ai_suggestion
    assert len(ai_suggestion["reason"]) > 0


def test_topic_relevance_boost(temp_storage):
    """Test that metrics used for a topic get relevance boost."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    # Record usage for specific topic
    agent.record_metric_selected("AI Support", topic="Machine Learning Research")
    agent.record_metric_selected("GPU Support", topic="Other Topic")

    # Get suggestions for the specific topic
    suggestions = agent.get_smart_suggestions(
        topic="Machine Learning Research",
        max_results=10,
        include_fresh_llm_suggestions=False,
    )

    # AI Support should rank higher than GPU Support due to topic relevance
    ai_index = next((i for i, s in enumerate(suggestions) if s["metric_name"] == "AI Support"), None)
    gpu_index = next((i for i, s in enumerate(suggestions) if s["metric_name"] == "GPU Support"), None)

    if ai_index is not None and gpu_index is not None:
        assert ai_index < gpu_index, "AI Support should rank higher due to topic relevance"


def test_suggested_but_unselected_recorded_as_ignored(temp_storage):
    """Test that suggested but unselected metrics are recorded as ignored."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    suggested = ["AI Support", "GPU Support", "XPBD Support", "VR HMD Integration"]
    selected = ["AI Support", "GPU Support"]
    custom = []

    agent.record_batch_feedback(
        selected_metrics=selected,
        custom_metrics=custom,
        suggested_metrics=suggested,
        topic="Test Topic"
    )

    # XPBD Support and VR HMD should be marked as ignored
    assert agent.metrics["XPBD Support"].rejected_count >= 1
    assert agent.metrics["VR HMD Integration"].rejected_count >= 1

    # AI Support and GPU Support should NOT be marked as ignored
    assert agent.metrics["AI Support"].rejected_count == 0
    assert agent.metrics["GPU Support"].rejected_count == 0


def test_selected_metrics_not_recorded_as_ignored(temp_storage):
    """Test that selected metrics are NOT recorded as ignored."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    suggested = ["AI Support", "GPU Support"]
    selected = ["AI Support", "GPU Support"]
    custom = []

    agent.record_batch_feedback(
        selected_metrics=selected,
        custom_metrics=custom,
        suggested_metrics=suggested,
        topic="Test Topic"
    )

    # Neither should be marked as ignored
    assert agent.metrics["AI Support"].rejected_count == 0
    assert agent.metrics["GPU Support"].rejected_count == 0

    # Both should be marked as selected
    assert agent.metrics["AI Support"].selected_count >= 1
    assert agent.metrics["GPU Support"].selected_count >= 1


def test_similar_custom_metric_avoids_unfair_penalty(temp_storage):
    """Test that adding a similar custom metric doesn't heavily penalize the suggested one."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    suggested = ["AI Support", "GPU Support"]
    selected = []
    custom = ["AI Capability"]  # Similar to "AI Support"

    agent.record_batch_feedback(
        selected_metrics=selected,
        custom_metrics=custom,
        suggested_metrics=suggested,
        topic="Test Topic"
    )

    # AI Support should get light penalty (not full ignore penalty)
    # Since user added "AI Capability", they showed interest in AI
    ai_metric = agent.metrics["AI Support"]

    # Should have some penalty but not harsh
    assert ai_metric.rejected_count >= 1
    # Priority should decrease only slightly (from 0.5)
    assert ai_metric.priority_score >= 0.45  # Light penalty: -0.01 instead of -0.05

    # GPU Support should get normal penalty (no similar custom)
    gpu_metric = agent.metrics["GPU Support"]
    assert gpu_metric.priority_score < 0.48  # Normal penalty: -0.05


def test_repeated_ignored_metrics_deactivate(temp_storage):
    """Test that repeatedly ignored metrics become inactive."""
    agent = MetricBankAgent(storage_path=temp_storage)
    agent.initialize_defaults()

    metric_name = "VR HMD Integration"

    # Ignore 11 times
    for i in range(11):
        agent.record_batch_feedback(
            selected_metrics=[],
            custom_metrics=[],
            suggested_metrics=[metric_name],
            topic=f"Topic {i}"
        )

    # After IGNORE_THRESHOLD (10), should be deactivated
    assert agent.metrics[metric_name].is_active is False
    assert agent.metrics[metric_name].rejected_count >= agent.IGNORE_THRESHOLD

    # Should not appear in suggestions
    suggestions = agent.get_smart_suggestions(
        topic="Test Topic",
        max_results=20,
        include_fresh_llm_suggestions=False
    )

    suggested_names = [s["metric_name"] for s in suggestions]
    assert metric_name not in suggested_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
