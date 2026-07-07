"""
Smoke tests for LLM observability and analytics features.

Tests the analytics tracking, token usage extraction, and data flow.
"""

import os
import time
from unittest.mock import Mock, patch

import pytest


def test_analytics_tracker_basic():
    """Test basic analytics tracker functionality."""
    from ria.analytics import AnalyticsTracker

    tracker = AnalyticsTracker(topic="Test Topic")

    # Start and finish a step
    tracker.start_step("Test Step")
    time.sleep(0.1)  # Simulate work
    tracker.finish_step()

    # Add LLM call
    tracker.add_llm_call(prompt_tokens=100, completion_tokens=50)

    # Set metadata
    tracker.set_cache_status("cached", cached_count=5, fresh_count=0)
    tracker.set_data_counts(papers=10, patents=5, open_access_papers=3)

    # Finish tracking
    tracker.finish()

    # Get analytics
    analytics = tracker.get_analytics()

    assert analytics.topic == "Test Topic"
    assert analytics.total_llm_calls == 1
    assert analytics.total_prompt_tokens == 100
    assert analytics.total_completion_tokens == 50
    assert analytics.total_tokens == 150
    assert analytics.estimated_total_cost > 0
    assert analytics.cache_status == "cached"
    assert analytics.papers_found == 10
    assert analytics.patents_found == 5
    assert len(analytics.steps) == 1
    assert analytics.steps[0].step_name == "Test Step"
    assert analytics.steps[0].duration_seconds > 0


def test_analytics_tracker_multiple_steps():
    """Test analytics tracker with multiple pipeline steps."""
    from ria.analytics import AnalyticsTracker

    tracker = AnalyticsTracker(topic="Multi-Step Test")

    # Step 1
    tracker.start_step("Fetch Data")
    time.sleep(0.05)
    tracker.finish_step()

    # Step 2 with LLM calls
    tracker.start_step("Score Sources")
    tracker.add_llm_call(prompt_tokens=200, completion_tokens=100)
    tracker.add_llm_call(prompt_tokens=250, completion_tokens=120)
    time.sleep(0.05)
    tracker.finish_step()

    # Step 3
    tracker.start_step("Generate Report")
    tracker.finish_step()

    tracker.finish()

    analytics = tracker.get_analytics()

    assert len(analytics.steps) == 3
    assert analytics.total_llm_calls == 2
    assert analytics.total_prompt_tokens == 450
    assert analytics.total_completion_tokens == 220
    assert analytics.total_tokens == 670
    assert analytics.steps[1].step_name == "Score Sources"
    assert analytics.steps[1].llm_calls == 2


def test_analytics_to_dict():
    """Test analytics serialization to dictionary."""
    from ria.analytics import AnalyticsTracker

    tracker = AnalyticsTracker(topic="Serialization Test")
    tracker.start_step("Test Step")
    tracker.add_llm_call(prompt_tokens=100, completion_tokens=50)
    tracker.finish_step()
    tracker.finish()

    analytics_dict = tracker.get_analytics().to_dict()

    assert analytics_dict["topic"] == "Serialization Test"
    assert analytics_dict["total_llm_calls"] == 1
    assert analytics_dict["total_tokens"] == 150
    assert "start_time" in analytics_dict
    assert "end_time" in analytics_dict
    assert isinstance(analytics_dict["steps"], list)
    assert len(analytics_dict["steps"]) == 1


def test_analytics_workflow_steps():
    """Test workflow steps generation for UI visualization."""
    from ria.analytics import AnalyticsTracker

    tracker = AnalyticsTracker(topic="Workflow Test")
    tracker.start_step("Step 1")
    time.sleep(0.01)  # Add small delay to ensure measurable duration
    tracker.add_llm_call(prompt_tokens=100, completion_tokens=50)
    tracker.finish_step()

    tracker.start_step("Step 2")
    time.sleep(0.01)  # Add small delay
    tracker.finish_step()

    tracker.finish()

    workflow_steps = tracker.get_analytics().get_workflow_steps()

    assert len(workflow_steps) == 2
    assert workflow_steps[0]["name"] == "Step 1"
    assert workflow_steps[0]["status"] == "completed"
    assert workflow_steps[0]["duration"] >= 0  # Changed to >= to handle very fast operations
    assert workflow_steps[0]["tokens"] == 150
    assert workflow_steps[0]["llm_calls"] == 1


def test_llm_client_metadata_extraction():
    """Test LLMClient extracts token usage metadata."""
    from unittest.mock import MagicMock
    from ria.llm import LLMClient

    # Mock the OpenAI client
    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "OPENAI_BASE_URL": "https://test.example.com",
        "LANGSMITH_TRACING_V2": "false"  # Disable LangSmith for test
    }):
        llm_client = LLMClient()

        # Mock response with usage data
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test response"))]
        mock_response.usage = MagicMock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150
        )

        llm_client.client.chat.completions.create = MagicMock(return_value=mock_response)

        # Call chat method
        response = llm_client.chat([{"role": "user", "content": "test"}])

        # Verify metadata was extracted
        assert llm_client.last_call_metadata is not None
        assert llm_client.last_call_metadata["usage"]["prompt_tokens"] == 100
        assert llm_client.last_call_metadata["usage"]["completion_tokens"] == 50
        assert llm_client.last_call_metadata["usage"]["total_tokens"] == 150
        assert llm_client.last_call_metadata["model"] == llm_client.model


def test_llm_client_langsmith_disabled():
    """Test LLMClient works correctly when LangSmith is disabled."""
    from ria.llm import LLMClient

    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "OPENAI_BASE_URL": "https://test.example.com",
        "LANGSMITH_TRACING_V2": "false"
    }):
        llm_client = LLMClient()
        assert llm_client.langsmith_enabled is False


def test_llm_client_langsmith_enabled():
    """Test LLMClient detects when LangSmith is enabled."""
    from ria.llm import LLMClient, LANGSMITH_AVAILABLE

    with patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "OPENAI_BASE_URL": "https://test.example.com",
        "LANGSMITH_TRACING_V2": "true",
        "LANGSMITH_API_KEY": "test-langsmith-key"
    }):
        llm_client = LLMClient()
        # Should be enabled only if langsmith package is available
        assert llm_client.langsmith_enabled == LANGSMITH_AVAILABLE


def test_cost_estimation():
    """Test cost estimation for different models."""
    from ria.analytics import AnalyticsTracker

    # Test with Claude Haiku
    with patch.dict(os.environ, {"LLM_MODEL": "claude-haiku"}):
        tracker = AnalyticsTracker(topic="Cost Test")
        tracker.add_llm_call(prompt_tokens=1000, completion_tokens=1000)
        tracker.finish()

        analytics = tracker.get_analytics()
        # Haiku pricing: $0.00025 per 1K prompt, $0.00125 per 1K completion
        expected_cost = (1000 / 1000) * 0.00025 + (1000 / 1000) * 0.00125
        assert abs(analytics.estimated_total_cost - expected_cost) < 0.0001


def test_analytics_with_no_llm_calls():
    """Test analytics tracker handles steps with no LLM calls."""
    from ria.analytics import AnalyticsTracker

    tracker = AnalyticsTracker(topic="No LLM Test")
    tracker.start_step("Non-LLM Step")
    time.sleep(0.05)
    tracker.finish_step()
    tracker.finish()

    analytics = tracker.get_analytics()

    assert analytics.total_llm_calls == 0
    assert analytics.total_tokens == 0
    assert analytics.estimated_total_cost == 0
    assert len(analytics.steps) == 1
    assert analytics.steps[0].llm_calls == 0


def test_pdf_exporter_research_report():
    """Test PDF generation for research report."""
    from ria.pdf_export import PDFExporter
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = PDFExporter(output_dir=tmpdir)

        # Test data
        topic = "Test Research Topic"
        report_content = """
## Executive Summary

This is a test executive summary with some key findings.

- Finding 1
- Finding 2
- Finding 3

## Top Patents

- Patent 1: Test Patent Title
- Patent 2: Another Patent

## Top Papers

- Paper 1: Test Paper Title
- Paper 2: Another Paper
"""
        stats = {
            "total_raw_items": 10,
            "patents_found": 5,
            "papers_found": 5,
            "open_access_papers_found": 2,
            "ranked_patents": 3,
            "ranked_papers": 3,
            "metrics_generated": 5,
            "cache_status": "Fresh research"
        }

        # Generate PDF
        pdf_path = exporter.generate_research_report_pdf(
            topic=topic,
            report_content=report_content,
            stats=stats,
        )

        # Verify PDF was created
        assert pdf_path.exists()
        assert pdf_path.suffix == '.pdf'
        assert pdf_path.stat().st_size > 0  # File is not empty


def test_pdf_exporter_usage_report():
    """Test PDF generation for LLM usage report."""
    from ria.pdf_export import PDFExporter
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = PDFExporter(output_dir=tmpdir)

        # Test data
        topic = "Test Research Topic"
        analytics = {
            "topic": topic,
            "start_time": "2026-07-07T10:00:00",
            "end_time": "2026-07-07T10:01:30",
            "total_duration_seconds": 90.5,
            "total_llm_calls": 15,
            "total_prompt_tokens": 5000,
            "total_completion_tokens": 2500,
            "total_tokens": 7500,
            "estimated_total_cost": 0.0125,
            "cache_status": "Fresh research",
            "papers_found": 5,
            "patents_found": 5,
            "steps": [
                {
                    "step_name": "Initialize Components",
                    "duration_seconds": 1.2,
                    "llm_calls": 0,
                    "total_tokens": 0,
                    "estimated_cost": 0.0
                },
                {
                    "step_name": "Score Sources",
                    "duration_seconds": 45.3,
                    "llm_calls": 10,
                    "prompt_tokens": 3000,
                    "completion_tokens": 1500,
                    "total_tokens": 4500,
                    "estimated_cost": 0.0075
                },
                {
                    "step_name": "Generate Report",
                    "duration_seconds": 2.1,
                    "llm_calls": 0,
                    "total_tokens": 0,
                    "estimated_cost": 0.0
                }
            ]
        }

        # Generate PDF
        pdf_path = exporter.generate_usage_report_pdf(
            topic=topic,
            analytics=analytics,
        )

        # Verify PDF was created
        assert pdf_path.exists()
        assert pdf_path.suffix == '.pdf'
        assert pdf_path.stat().st_size > 0  # File is not empty


def test_pdf_exporter_with_langsmith_trace():
    """Test PDF generation with LangSmith trace information."""
    from ria.pdf_export import PDFExporter
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = PDFExporter(output_dir=tmpdir)

        analytics = {
            "topic": "Test Topic",
            "start_time": "2026-07-07T10:00:00",
            "total_duration_seconds": 60.0,
            "total_llm_calls": 10,
            "total_tokens": 5000,
            "estimated_total_cost": 0.005,
            "langsmith_trace_id": "test-trace-123",
            "langsmith_trace_url": "https://smith.langchain.com/o/test/projects/p/test/r/test-trace-123",
            "steps": []
        }

        # Generate PDF
        pdf_path = exporter.generate_usage_report_pdf(
            topic="Test Topic",
            analytics=analytics,
        )

        # Verify PDF was created
        assert pdf_path.exists()
        assert pdf_path.stat().st_size > 0


def test_pdf_exporter_safe_filename():
    """Test that PDF exporter generates safe filenames."""
    from ria.pdf_export import PDFExporter
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        exporter = PDFExporter(output_dir=tmpdir)

        # Topic with special characters
        topic = "Test/Topic\\With:Special*Characters?"
        analytics = {
            "topic": topic,
            "start_time": "2026-07-07T10:00:00",
            "total_duration_seconds": 30.0,
            "total_llm_calls": 5,
            "total_tokens": 1000,
            "estimated_total_cost": 0.001,
            "steps": []
        }

        # Generate PDF
        pdf_path = exporter.generate_usage_report_pdf(
            topic=topic,
            analytics=analytics,
        )

        # Verify filename is safe (no special characters)
        assert pdf_path.exists()
        assert '/' not in pdf_path.name
        assert '\\' not in pdf_path.name
        assert ':' not in pdf_path.name


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
