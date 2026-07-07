"""
Unit tests for execution analytics tracking.

Tests AnalyticsTracker to ensure it resets per request and tracks correctly.
"""

import time
import pytest
from ria.analytics import AnalyticsTracker, ExecutionAnalytics, StepMetrics


class TestAnalyticsTracker:
    """Tests for AnalyticsTracker class."""

    def test_tracker_initialization(self):
        """Test that tracker initializes with fresh state."""
        topic = "Test Research"
        tracker = AnalyticsTracker(topic=topic)

        assert tracker.analytics.topic == topic
        assert tracker.analytics.total_llm_calls == 0
        assert tracker.analytics.total_tokens == 0
        assert tracker.analytics.estimated_total_cost == 0.0
        assert len(tracker.analytics.steps) == 0
        assert tracker.current_step is None

    def test_tracker_resets_between_instances(self):
        """Test that each tracker instance is independent and doesn't accumulate."""
        # Create first tracker
        tracker1 = AnalyticsTracker(topic="Research 1")
        tracker1.start_step("Step 1")
        tracker1.add_llm_call(prompt_tokens=100, completion_tokens=50)
        tracker1.finish_step()
        tracker1.finish()

        analytics1 = tracker1.get_analytics()

        # Create second tracker (simulating a new request)
        tracker2 = AnalyticsTracker(topic="Research 2")

        # Second tracker should start fresh, not accumulate from first
        assert tracker2.analytics.total_llm_calls == 0
        assert tracker2.analytics.total_tokens == 0
        assert tracker2.analytics.estimated_total_cost == 0.0
        assert len(tracker2.analytics.steps) == 0

        # First tracker should still have its data
        assert analytics1.total_llm_calls == 1
        assert analytics1.total_tokens == 150

    def test_start_and_finish_step(self):
        """Test step tracking."""
        tracker = AnalyticsTracker(topic="Test")

        tracker.start_step("Test Step")
        assert tracker.current_step is not None
        assert tracker.current_step.step_name == "Test Step"

        time.sleep(0.01)  # Small delay to ensure duration > 0

        tracker.finish_step()
        assert tracker.current_step is None
        assert len(tracker.analytics.steps) == 1
        assert tracker.analytics.steps[0].step_name == "Test Step"
        assert tracker.analytics.steps[0].duration_seconds > 0

    def test_add_llm_call_to_current_step(self):
        """Test adding LLM call to active step."""
        tracker = AnalyticsTracker(topic="Test")

        tracker.start_step("LLM Step")
        tracker.add_llm_call(prompt_tokens=100, completion_tokens=50)
        tracker.finish_step()

        # Check overall analytics
        assert tracker.analytics.total_llm_calls == 1
        assert tracker.analytics.total_prompt_tokens == 100
        assert tracker.analytics.total_completion_tokens == 50
        assert tracker.analytics.total_tokens == 150
        assert tracker.analytics.estimated_total_cost > 0

        # Check step analytics
        step = tracker.analytics.steps[0]
        assert step.llm_calls == 1
        assert step.prompt_tokens == 100
        assert step.completion_tokens == 50
        assert step.total_tokens == 150
        assert step.estimated_cost > 0

    def test_add_multiple_llm_calls(self):
        """Test accumulation of multiple LLM calls."""
        tracker = AnalyticsTracker(topic="Test")

        tracker.start_step("Multi-call Step")
        tracker.add_llm_call(prompt_tokens=100, completion_tokens=50)
        tracker.add_llm_call(prompt_tokens=200, completion_tokens=100)
        tracker.add_llm_call(prompt_tokens=50, completion_tokens=25)
        tracker.finish_step()

        # Check totals
        assert tracker.analytics.total_llm_calls == 3
        assert tracker.analytics.total_prompt_tokens == 350
        assert tracker.analytics.total_completion_tokens == 175
        assert tracker.analytics.total_tokens == 525

    def test_add_llm_call_with_step_name(self):
        """Test adding LLM call with explicit step name."""
        tracker = AnalyticsTracker(topic="Test")

        # Add call without active step, but with step_name
        tracker.add_llm_call(
            prompt_tokens=100,
            completion_tokens=50,
            step_name="Explicit Step"
        )

        # Should create and finish a step automatically
        assert len(tracker.analytics.steps) == 1
        assert tracker.analytics.steps[0].step_name == "Explicit Step"
        assert tracker.analytics.steps[0].llm_calls == 1

    def test_set_cache_status(self):
        """Test setting cache status."""
        tracker = AnalyticsTracker(topic="Test")

        tracker.set_cache_status(
            status="Cached results",
            cached_count=15,
            fresh_count=0
        )

        assert tracker.analytics.cache_status == "Cached results"
        assert tracker.analytics.cached_items_used == 15
        assert tracker.analytics.fresh_items_fetched == 0

    def test_set_data_counts(self):
        """Test setting data collection counts."""
        tracker = AnalyticsTracker(topic="Test")

        tracker.set_data_counts(
            papers=20,
            patents=15,
            open_access_papers=8
        )

        assert tracker.analytics.papers_found == 20
        assert tracker.analytics.patents_found == 15
        assert tracker.analytics.open_access_papers_found == 8

    def test_finish_tracker(self):
        """Test finishing tracker and calculating duration."""
        tracker = AnalyticsTracker(topic="Test")

        time.sleep(0.01)  # Small delay

        tracker.finish()

        assert tracker.analytics.end_time is not None
        assert tracker.analytics.total_duration_seconds > 0

    def test_duration_only_for_current_run(self):
        """Test that duration measures only the current run, not accumulated."""
        # First run
        tracker1 = AnalyticsTracker(topic="Run 1")
        start_time_1 = tracker1.analytics.start_time
        time.sleep(0.02)
        tracker1.finish()
        duration_1 = tracker1.analytics.total_duration_seconds

        # Small gap between runs
        time.sleep(0.01)

        # Second run (new request)
        tracker2 = AnalyticsTracker(topic="Run 2")
        start_time_2 = tracker2.analytics.start_time
        time.sleep(0.02)
        tracker2.finish()
        duration_2 = tracker2.analytics.total_duration_seconds

        # Durations should be independent
        assert start_time_2 > start_time_1
        assert duration_1 > 0
        assert duration_2 > 0

        # Second duration should NOT include first duration
        # It should only measure its own run time
        assert duration_2 < duration_1 + 0.05  # Allow some margin

    def test_to_dict_serialization(self):
        """Test conversion to dictionary for JSON serialization."""
        tracker = AnalyticsTracker(topic="Test")

        tracker.start_step("Step 1")
        tracker.add_llm_call(prompt_tokens=100, completion_tokens=50)
        tracker.finish_step()

        tracker.set_cache_status("Fresh", cached_count=0, fresh_count=20)
        tracker.set_data_counts(papers=15, patents=10, open_access_papers=5)

        tracker.finish()

        data = tracker.get_analytics().to_dict()

        # Check all expected fields are present
        assert "topic" in data
        assert "start_time" in data
        assert "end_time" in data
        assert "total_duration_seconds" in data
        assert "total_llm_calls" in data
        assert "total_tokens" in data
        assert "estimated_total_cost" in data
        assert "cache_status" in data
        assert "papers_found" in data
        assert "patents_found" in data
        assert "steps" in data

        # Check values
        assert data["topic"] == "Test"
        assert data["total_llm_calls"] == 1
        assert data["cache_status"] == "Fresh"
        assert data["papers_found"] == 15
        assert data["patents_found"] == 10
        assert len(data["steps"]) == 1

    def test_get_workflow_steps(self):
        """Test getting workflow steps for visualization."""
        tracker = AnalyticsTracker(topic="Test")

        tracker.start_step("Step 1")
        tracker.add_llm_call(prompt_tokens=100, completion_tokens=50)
        tracker.finish_step()

        tracker.start_step("Step 2")
        tracker.add_llm_call(prompt_tokens=200, completion_tokens=100)
        tracker.finish_step()

        workflow_steps = tracker.get_analytics().get_workflow_steps()

        assert len(workflow_steps) == 2
        assert workflow_steps[0]["name"] == "Step 1"
        assert workflow_steps[0]["status"] == "completed"
        assert workflow_steps[0]["tokens"] == 150
        assert workflow_steps[1]["name"] == "Step 2"
        assert workflow_steps[1]["tokens"] == 300

    def test_auto_finish_previous_step(self):
        """Test that starting a new step auto-finishes the previous one."""
        tracker = AnalyticsTracker(topic="Test")

        tracker.start_step("Step 1")
        tracker.add_llm_call(prompt_tokens=100, completion_tokens=50)

        # Start a new step without finishing the previous one
        tracker.start_step("Step 2")

        # Step 1 should have been auto-finished
        assert len(tracker.analytics.steps) == 1
        assert tracker.analytics.steps[0].step_name == "Step 1"

        tracker.finish_step()

        assert len(tracker.analytics.steps) == 2
        assert tracker.analytics.steps[1].step_name == "Step 2"


class TestStepMetrics:
    """Tests for StepMetrics dataclass."""

    def test_step_metrics_initialization(self):
        """Test step metrics initialization."""
        step = StepMetrics(
            step_name="Test Step",
            start_time=time.time()
        )

        assert step.step_name == "Test Step"
        assert step.end_time is None
        assert step.duration_seconds is None
        assert step.prompt_tokens == 0
        assert step.completion_tokens == 0
        assert step.total_tokens == 0
        assert step.estimated_cost == 0.0
        assert step.llm_calls == 0

    def test_step_finish_calculates_duration(self):
        """Test that finish() calculates duration correctly."""
        start = time.time()
        step = StepMetrics(step_name="Test", start_time=start)

        time.sleep(0.01)  # Small delay

        step.finish()

        assert step.end_time is not None
        assert step.end_time > start
        assert step.duration_seconds > 0
        assert step.duration_seconds == step.end_time - step.start_time


class TestExecutionAnalytics:
    """Tests for ExecutionAnalytics dataclass."""

    def test_execution_analytics_initialization(self):
        """Test execution analytics initialization."""
        analytics = ExecutionAnalytics(
            topic="Test Topic",
            start_time=time.time()
        )

        assert analytics.topic == "Test Topic"
        assert analytics.end_time is None
        assert analytics.total_duration_seconds is None
        assert analytics.total_llm_calls == 0
        assert analytics.cache_status == "unknown"
        assert len(analytics.steps) == 0

    def test_execution_analytics_finish(self):
        """Test finish() calculates total duration."""
        start = time.time()
        analytics = ExecutionAnalytics(topic="Test", start_time=start)

        time.sleep(0.01)

        analytics.finish()

        assert analytics.end_time is not None
        assert analytics.total_duration_seconds > 0
        assert analytics.total_duration_seconds == analytics.end_time - start
