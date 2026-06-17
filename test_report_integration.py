#!/usr/bin/env python3
"""
Integration test for report generation with WorkspaceManager.

Demonstrates the complete workflow: load workspace, generate report,
and verify all components work together.
"""

from pathlib import Path

from ria.models import BenchmarkMetric, RankedResults
from ria.report import ReportRenderer
from ria.workspace import WorkspaceManager


def main():
    """Test report generation with workspace manager integration."""
    # Initialize workspace manager
    workspace_manager = WorkspaceManager(base_dir="test_mvp_workspace")
    print("WorkspaceManager initialized")

    # Topic from the existing workspace
    topic = "XPBD soft body simulation algorithm"
    workspace_dir = workspace_manager.base_dir / workspace_manager._make_slug(topic)

    if not workspace_dir.exists():
        print(f"Error: Workspace not found at {workspace_dir}")
        return 1

    print(f"Using workspace: {workspace_dir}")

    # Load ranked results using workspace manager
    print("\nLoading workspace artifacts...")
    ranked_results_data = workspace_manager.load_artifact(workspace_dir, "ranked_results.json")
    ranked_results = RankedResults.model_validate(ranked_results_data)
    print(f"  ✓ Loaded ranked results: {len(ranked_results.patents)} patents, {len(ranked_results.papers)} papers")

    # Load metrics
    metrics_data = workspace_manager.load_artifact(workspace_dir, "metrics.json")
    metrics = [BenchmarkMetric.model_validate(m) for m in metrics_data]
    print(f"  ✓ Loaded {len(metrics)} metrics")

    # Generate report
    print("\nGenerating report...")
    renderer = ReportRenderer()
    report_path = renderer.generate(
        topic=topic,
        ranked_results=ranked_results,
        metrics=metrics,
        workspace_dir=workspace_dir,
    )

    print(f"  ✓ Report generated at: {report_path}")
    print(f"  ✓ File size: {report_path.stat().st_size:,} bytes")

    # Verify report structure
    print("\nVerifying report structure...")
    content = report_path.read_text()

    required_sections = [
        "# Research Intelligence Report:",
        "## Executive Summary",
        "## Top Patents",
        "## Top Papers",
        "## Benchmark Metrics",
        "## References",
    ]

    for section in required_sections:
        if section in content:
            print(f"  ✓ Found section: {section}")
        else:
            print(f"  ✗ Missing section: {section}")
            return 1

    # Check for patents in content
    if len(ranked_results.patents) > 0:
        first_patent_title = ranked_results.patents[0].title
        if first_patent_title in content:
            print(f"  ✓ Found patent: {first_patent_title[:50]}...")
        else:
            print(f"  ✗ Missing patent: {first_patent_title}")
            return 1

    # Check for metrics in content
    if len(metrics) > 0:
        first_metric_name = metrics[0].name
        if first_metric_name in content:
            print(f"  ✓ Found metric: {first_metric_name}")
        else:
            print(f"  ✗ Missing metric: {first_metric_name}")
            return 1

    print("\n" + "=" * 80)
    print("✓ All integration tests passed!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    exit(main())
