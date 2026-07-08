"""
Test ChromaDB integration with MetricBankAgent.

This test verifies that:
1. MetricBankAgent loads metrics from ChromaDB
2. ChromaDB metrics and adaptive data are merged correctly
3. No duplicate metrics appear
4. Adaptive usage counts accumulate correctly
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from ria.agents import MetricBankAgent
from ria.metrics_bank import MetricsBank
from ria.llm import LLMClient


def test_metric_bank_agent_loads_from_chroma():
    """Test that MetricBankAgent loads metrics from ChromaDB."""
    # Create temporary directories
    with tempfile.TemporaryDirectory() as temp_dir:
        chroma_dir = Path(temp_dir) / "chroma_test"
        adaptive_dir = Path(temp_dir) / "adaptive_test"
        adaptive_dir.mkdir(parents=True, exist_ok=True)
        adaptive_file = adaptive_dir / "metric_bank_usage.json"

        # Initialize ChromaDB with defaults
        chroma_bank = MetricsBank(persist_directory=str(chroma_dir))
        chroma_bank.initialize_defaults()

        # Get initial ChromaDB count
        chroma_count = chroma_bank.collection.count()
        assert chroma_count > 0, "ChromaDB should have default metrics"

        # Initialize agent with ChromaDB
        agent = MetricBankAgent(
            storage_path=str(adaptive_file),
            chroma_metrics_bank=chroma_bank
        )
        agent.initialize_defaults()

        # Verify agent loaded ChromaDB metrics
        assert len(agent.metrics) > 0, "Agent should have loaded metrics"
        chroma_metrics = [m for m in agent.metrics.values() if m.source == "chroma"]
        assert len(chroma_metrics) > 0, "Agent should have metrics from ChromaDB"

        print(f"ChromaDB metrics: {chroma_count}")
        print(f"Agent metrics: {len(agent.metrics)}")
        print(f"Metrics from ChromaDB: {len(chroma_metrics)}")


def test_chroma_adaptive_merge():
    """Test that ChromaDB metrics and adaptive data merge correctly."""
    with tempfile.TemporaryDirectory() as temp_dir:
        chroma_dir = Path(temp_dir) / "chroma_test"
        adaptive_dir = Path(temp_dir) / "adaptive_test"
        adaptive_dir.mkdir(parents=True, exist_ok=True)
        adaptive_file = adaptive_dir / "metric_bank_usage.json"

        # Initialize ChromaDB
        chroma_bank = MetricsBank(persist_directory=str(chroma_dir))
        chroma_bank.initialize_defaults()

        # Initialize agent
        agent = MetricBankAgent(
            storage_path=str(adaptive_file),
            chroma_metrics_bank=chroma_bank
        )
        agent.initialize_defaults()

        # Simulate user selecting a metric
        agent.record_metric_selected("AI Support", topic="test topic")

        # Save and reload
        agent._save()
        agent2 = MetricBankAgent(
            storage_path=str(adaptive_file),
            chroma_metrics_bank=chroma_bank
        )
        agent2.initialize_defaults()

        # Check that usage counts persisted
        ai_support = agent2.get_metric_by_name("AI Support")
        assert ai_support is not None
        assert ai_support["selected_count"] > 0, "Usage count should persist"


def test_no_duplicate_suggestions():
    """Test that duplicate ChromaDB and adaptive metrics don't appear."""
    with tempfile.TemporaryDirectory() as temp_dir:
        chroma_dir = Path(temp_dir) / "chroma_test"
        adaptive_dir = Path(temp_dir) / "adaptive_test"
        adaptive_dir.mkdir(parents=True, exist_ok=True)
        adaptive_file = adaptive_dir / "metric_bank_usage.json"

        # Initialize ChromaDB
        chroma_bank = MetricsBank(persist_directory=str(chroma_dir))
        chroma_bank.initialize_defaults()

        # Initialize agent
        agent = MetricBankAgent(
            storage_path=str(adaptive_file),
            chroma_metrics_bank=chroma_bank
        )
        agent.initialize_defaults()

        # Get suggestions
        suggestions = agent.get_smart_suggestions(
            topic="XPBD simulation",
            max_results=20,
            include_fresh_llm_suggestions=False
        )

        # Check for duplicates
        metric_names = [s["name"] for s in suggestions]
        normalized_names = [agent._normalize_metric_name(name) for name in metric_names]

        assert len(normalized_names) == len(set(normalized_names)), (
            f"Found duplicate metrics: {[n for n in normalized_names if normalized_names.count(n) > 1]}"
        )


def test_chroma_metrics_higher_priority_after_use():
    """Test that used ChromaDB metrics rank higher after selection."""
    with tempfile.TemporaryDirectory() as temp_dir:
        chroma_dir = Path(temp_dir) / "chroma_test"
        adaptive_dir = Path(temp_dir) / "adaptive_test"
        adaptive_dir.mkdir(parents=True, exist_ok=True)
        adaptive_file = adaptive_dir / "metric_bank_usage.json"

        # Initialize ChromaDB
        chroma_bank = MetricsBank(persist_directory=str(chroma_dir))
        chroma_bank.initialize_defaults()

        # Initialize agent
        agent = MetricBankAgent(
            storage_path=str(adaptive_file),
            chroma_metrics_bank=chroma_bank
        )
        agent.initialize_defaults()

        # Get initial suggestions
        initial_suggestions = agent.get_smart_suggestions(
            topic="GPU acceleration",
            max_results=10,
            include_fresh_llm_suggestions=False
        )

        # Select "GPU Support"
        agent.record_metric_selected("GPU Support", topic="GPU acceleration")

        # Get new suggestions
        new_suggestions = agent.get_smart_suggestions(
            topic="GPU acceleration",
            max_results=10,
            include_fresh_llm_suggestions=False
        )

        # Find positions
        initial_pos = next(
            (i for i, m in enumerate(initial_suggestions) if m["name"] == "GPU Support"),
            None
        )
        new_pos = next(
            (i for i, m in enumerate(new_suggestions) if m["name"] == "GPU Support"),
            None
        )

        assert initial_pos is not None, "GPU Support should be in initial suggestions"
        assert new_pos is not None, "GPU Support should be in new suggestions"
        assert new_pos <= initial_pos, "GPU Support should rank higher or same after selection"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
