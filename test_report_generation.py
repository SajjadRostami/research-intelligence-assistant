#!/usr/bin/env python3
"""
Test script for report generation.

Loads the MVP workspace and generates a complete Markdown report
demonstrating the ReportRenderer functionality.
"""

import json
from pathlib import Path

from ria.models import BenchmarkMetric, RankedResults
from ria.report import ReportRenderer


def main():
    """Load workspace data and generate report."""
    # Use the existing MVP workspace
    workspace_dir = Path("test_mvp_workspace/xpbd-soft-body-simulation-algorithm")

    if not workspace_dir.exists():
        print(f"Error: Workspace directory not found at {workspace_dir}")
        return 1

    print(f"Loading workspace from: {workspace_dir}")

    # Load ranked results
    ranked_results_path = workspace_dir / "ranked_results.json"
    if not ranked_results_path.exists():
        print(f"Error: ranked_results.json not found at {ranked_results_path}")
        return 1

    with open(ranked_results_path) as f:
        ranked_results_data = json.load(f)
    ranked_results = RankedResults.model_validate(ranked_results_data)
    print(f"  ✓ Loaded {len(ranked_results.patents)} patents and {len(ranked_results.papers)} papers")

    # Load metrics
    metrics_path = workspace_dir / "metrics.json"
    if not metrics_path.exists():
        print(f"Error: metrics.json not found at {metrics_path}")
        return 1

    with open(metrics_path) as f:
        metrics_data = json.load(f)
    metrics = [BenchmarkMetric.model_validate(m) for m in metrics_data]
    print(f"  ✓ Loaded {len(metrics)} benchmark metrics")

    # Load topic from metadata
    metadata_path = workspace_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path) as f:
            metadata = json.load(f)
        topic = metadata.get("topic", "Unknown Topic")
    else:
        # Fallback: extract from directory name
        topic = workspace_dir.name.replace("-", " ").title()

    print(f"  ✓ Topic: {topic}")

    # Generate report
    print("\nGenerating report...")
    renderer = ReportRenderer()
    report_path = renderer.generate(
        topic=topic,
        ranked_results=ranked_results,
        metrics=metrics,
        workspace_dir=workspace_dir,
    )

    print(f"  ✓ Report generated successfully!")
    print(f"\nReport saved to: {report_path}")
    print(f"File size: {report_path.stat().st_size:,} bytes")

    # Show a preview
    print("\n" + "=" * 80)
    print("REPORT PREVIEW (first 30 lines):")
    print("=" * 80)

    with open(report_path) as f:
        lines = f.readlines()
        for i, line in enumerate(lines[:30], 1):
            print(f"{i:3d} | {line}", end="")

    if len(lines) > 30:
        print(f"\n... ({len(lines) - 30} more lines)")

    print("\n" + "=" * 80)
    print(f"Full report available at: {report_path.absolute()}")

    return 0


if __name__ == "__main__":
    exit(main())
