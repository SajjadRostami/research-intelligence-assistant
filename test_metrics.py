#!/usr/bin/env python3
"""
Test script for MetricsGenerator.

This script demonstrates:
1. Creating sample ranked results (or loading existing ones)
2. Generating benchmark metrics
3. Saving metrics to workspace
4. Printing all generated metrics

Usage:
    python test_metrics.py
"""

from pathlib import Path

from ria.llm import LLMClient
from ria.metrics import MetricsGenerator
from ria.models import ConfidenceLevel, RankedResults, ScoredSourceItem, SourceType
from ria.workspace import WorkspaceManager


def create_sample_ranked_results() -> tuple[str, RankedResults]:
    """
    Create sample ranked results for testing.

    Returns:
        Tuple of (topic, RankedResults)
    """
    topic = "Extended Position Based Dynamics (XPBD) for physics simulation"

    # Sample papers
    papers = [
        ScoredSourceItem(
            title="XPBD: Position-Based Simulation of Compliant Constrained Dynamics",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper1",
            publication_date="2020-07-15",
            author_or_assignee="Macklin, Miles; Müller, Matthias; Chentanez, Nuttapong",
            relevance_explanation="Introduces XPBD method for constraint-based physics simulation with improved stability and compliance",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1145/3384538",
            patent_number=None,
            raw_adapter_source="semantic_scholar",
            relevance_score=0.95,
        ),
        ScoredSourceItem(
            title="Position Based Dynamics: A Survey",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper2",
            publication_date="2021-03-20",
            author_or_assignee="Bender, Jan; Müller, Matthias; Macklin, Miles",
            relevance_explanation="Comprehensive survey of PBD methods including XPBD variants and applications",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1111/cgf.14344",
            patent_number=None,
            raw_adapter_source="semantic_scholar",
            relevance_score=0.89,
        ),
        ScoredSourceItem(
            title="Real-time Cloth Simulation with XPBD",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper3",
            publication_date="2019-11-08",
            author_or_assignee="Kim, Theodore; Desbrun, Mathieu",
            relevance_explanation="Application of XPBD to real-time cloth simulation with GPU acceleration",
            confidence_level=ConfidenceLevel.MEDIUM,
            doi="10.1145/3355089.3356503",
            patent_number=None,
            raw_adapter_source="semantic_scholar",
            relevance_score=0.82,
        ),
    ]

    # Sample patents
    patents = [
        ScoredSourceItem(
            title="Physics-Based Animation System Using Extended Position Based Dynamics",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US10896534B2",
            publication_date="2021-01-19",
            author_or_assignee="NVIDIA Corporation",
            relevance_explanation="Patent covering implementation of XPBD in real-time graphics engines",
            confidence_level=ConfidenceLevel.HIGH,
            doi=None,
            patent_number="US10896534B2",
            raw_adapter_source="google_patents",
            relevance_score=0.91,
        ),
        ScoredSourceItem(
            title="Method for Soft Body Simulation Using Position-Based Constraints",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US11047695B2",
            publication_date="2021-06-29",
            author_or_assignee="Unity Technologies",
            relevance_explanation="Patent for soft body physics using position-based dynamics with compliance",
            confidence_level=ConfidenceLevel.MEDIUM,
            doi=None,
            patent_number="US11047695B2",
            raw_adapter_source="google_patents",
            relevance_score=0.86,
        ),
        ScoredSourceItem(
            title="GPU-Accelerated Constraint Solver for Real-Time Simulation",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US10755484B2",
            publication_date="2020-08-25",
            author_or_assignee="Epic Games, Inc.",
            relevance_explanation="GPU implementation of position-based constraint solving for game physics",
            confidence_level=ConfidenceLevel.MEDIUM,
            doi=None,
            patent_number="US10755484B2",
            raw_adapter_source="google_patents",
            relevance_score=0.79,
        ),
    ]

    ranked_results = RankedResults(papers=papers, patents=patents)
    return topic, ranked_results


def main():
    """Run the metrics generation test."""
    print("=" * 80)
    print("MetricsGenerator Test Script")
    print("=" * 80)
    print()

    # Initialize components
    print("1. Initializing components...")
    llm_client = LLMClient()
    workspace_manager = WorkspaceManager(base_dir="./workspaces")
    metrics_generator = MetricsGenerator(llm_client=llm_client)
    print("   ✓ LLM client initialized")
    print("   ✓ Workspace manager initialized")
    print("   ✓ Metrics generator initialized")
    print()

    # Create or load ranked results
    print("2. Loading ranked results...")
    topic, ranked_results = create_sample_ranked_results()
    print(f"   ✓ Topic: {topic}")
    print(f"   ✓ Papers: {len(ranked_results.papers)}")
    print(f"   ✓ Patents: {len(ranked_results.patents)}")
    print()

    # Create workspace
    print("3. Creating workspace...")
    workspace = workspace_manager.create(topic)
    print(f"   ✓ Workspace created at: {workspace}")
    print()

    # Save ranked results to workspace (for reference)
    print("4. Saving ranked results to workspace...")
    ranked_data = ranked_results.model_dump()
    workspace_manager.save_artifact(
        workspace=workspace,
        artifact_name="ranked_results.json",
        data=ranked_data,
    )
    print("   ✓ Ranked results saved")
    print()

    # Generate metrics
    print("5. Generating benchmark metrics...")
    print("   (This may take 10-30 seconds depending on LLM response time)")
    try:
        metrics = metrics_generator.generate(
            topic=topic,
            papers=ranked_results.papers,
            patents=ranked_results.patents,
        )
        print(f"   ✓ Generated {len(metrics)} metrics")
    except Exception as e:
        print(f"   ✗ Error generating metrics: {e}")
        return
    print()

    # Save metrics
    print("6. Saving metrics to workspace...")
    metrics_path = metrics_generator.save_metrics(
        workspace=workspace,
        metrics=metrics,
        workspace_manager=workspace_manager,
    )
    print(f"   ✓ Metrics saved to: {metrics_path}")
    print()

    # Print all metrics
    print("7. Generated Metrics:")
    print("=" * 80)
    for i, metric in enumerate(metrics, 1):
        print(f"\nMetric {i}: {metric.name}")
        print("-" * 80)
        if metric.description:
            print(f"Description: {metric.description}")
        else:
            print("Description: (none)")

        if metric.category:
            print(f"Category: {metric.category}")
        else:
            print("Category: (none)")

    print()
    print("=" * 80)
    print("Test completed successfully!")
    print()
    print("Next steps:")
    print("  - Metrics are saved in workspace/metrics.json")
    print("  - Use these metrics for benchmark scoring in the next phase")
    print("  - Implement report generation to visualize results")
    print("=" * 80)


if __name__ == "__main__":
    main()
