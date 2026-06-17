#!/usr/bin/env python3
"""
Test script for WorkspaceManager functionality.

Demonstrates:
1. Creating a workspace
2. Saving sample orchestrator results
3. Loading results back
4. Listing history
"""

import asyncio
from datetime import datetime
from pathlib import Path
import shutil

from ria.models import (
    OrchestratorResult,
    RawSourceItem,
    SearchQuery,
    SourceType,
    ConfidenceLevel,
)
from ria.workspace import WorkspaceManager


def create_sample_orchestrator_result() -> OrchestratorResult:
    """Create a sample orchestrator result for testing."""
    return OrchestratorResult(
        topic="XPBD Simulation and Physics",
        queries=[
            SearchQuery(
                query_string="XPBD Simulation and Physics",
                source="SerpAPIPatentAdapter",
                timestamp=datetime.utcnow(),
            ),
            SearchQuery(
                query_string="XPBD Simulation and Physics",
                source="SemanticScholarAdapter",
                timestamp=datetime.utcnow(),
            ),
        ],
        raw_items=[
            RawSourceItem(
                title="Position Based Dynamics",
                source_type=SourceType.PAPER,
                source_url="https://example.com/paper1",
                publication_date="2020-05-15",
                author_or_assignee="John Doe",
                relevance_explanation="Foundational work on position-based simulation",
                confidence_level=ConfidenceLevel.HIGH,
                doi="10.1234/example.1",
                raw_adapter_source="SemanticScholarAdapter",
            ),
            RawSourceItem(
                title="Extended Position Based Dynamics Method",
                source_type=SourceType.PATENT,
                source_url="https://patents.google.com/patent/US1234567",
                publication_date="2021-03-20",
                author_or_assignee="Tech Corp",
                relevance_explanation="Patent covering XPBD implementation",
                confidence_level=ConfidenceLevel.MEDIUM,
                patent_number="US1234567",
                raw_adapter_source="SerpAPIPatentAdapter",
            ),
            RawSourceItem(
                title="Real-time Physics Simulation using XPBD",
                source_type=SourceType.PAPER,
                source_url="https://example.com/paper2",
                publication_date="2022-08-10",
                author_or_assignee="Jane Smith",
                relevance_explanation="Practical applications of XPBD in real-time systems",
                confidence_level=ConfidenceLevel.HIGH,
                doi="10.1234/example.2",
                raw_adapter_source="SemanticScholarAdapter",
            ),
        ],
    )


def main():
    """Run workspace manager demonstration."""
    print("=" * 70)
    print("WorkspaceManager Test Script")
    print("=" * 70)
    print()

    # Use a test directory to avoid polluting the main workspaces
    test_base_dir = Path("./test_workspaces")

    # Clean up any existing test workspaces
    if test_base_dir.exists():
        print(f"Cleaning up existing test directory: {test_base_dir}")
        shutil.rmtree(test_base_dir)
        print()

    # Initialize workspace manager
    print("1. Initializing WorkspaceManager")
    print("-" * 70)
    manager = WorkspaceManager(base_dir=test_base_dir)
    print(f"   Base directory: {manager.base_dir}")
    print(f"   Directory exists: {manager.base_dir.exists()}")
    print()

    # Create workspace
    print("2. Creating workspace for topic")
    print("-" * 70)
    topic = "XPBD Simulation and Physics"
    print(f"   Topic: {topic}")
    workspace = manager.create(topic)
    print(f"   Workspace path: {workspace}")
    print(f"   Workspace exists: {workspace.exists()}")
    print()

    # List files in workspace
    print("   Files in workspace:")
    for file in workspace.iterdir():
        print(f"     - {file.name}")
    print()

    # Create sample data
    print("3. Saving orchestrator result")
    print("-" * 70)
    result = create_sample_orchestrator_result()
    print(f"   Topic: {result.topic}")
    print(f"   Number of queries: {len(result.queries)}")
    print(f"   Number of raw items: {len(result.raw_items)}")

    saved_path = manager.save_orchestrator_result(workspace, result)
    print(f"   Saved to: {saved_path.name}")
    print()

    # Save additional artifacts
    print("4. Saving additional artifacts")
    print("-" * 70)
    sample_metadata = {
        "stage": "orchestration_complete",
        "total_papers": 2,
        "total_patents": 1,
        "status": "ready_for_ranking",
    }
    artifact_path = manager.save_artifact(
        workspace,
        "pipeline_metadata",
        sample_metadata,
    )
    print(f"   Saved artifact: {artifact_path.name}")
    print(f"   Data: {sample_metadata}")
    print()

    # Load results back
    print("5. Loading results back from workspace")
    print("-" * 70)
    loaded_result = manager.load_orchestrator_result(workspace)
    print(f"   Topic: {loaded_result.topic}")
    print(f"   Number of queries: {len(loaded_result.queries)}")
    print(f"   Number of raw items: {len(loaded_result.raw_items)}")
    print()

    print("   Raw items loaded:")
    for i, item in enumerate(loaded_result.raw_items, 1):
        print(f"     {i}. {item.title}")
        print(f"        Type: {item.source_type.value}")
        print(f"        Source: {item.raw_adapter_source}")
        print()

    # Load artifact back
    print("6. Loading artifact back")
    print("-" * 70)
    loaded_artifact = manager.load_artifact(workspace, "pipeline_metadata")
    print(f"   Loaded data: {loaded_artifact}")
    print()

    # Update history
    print("7. Updating workspace history")
    print("-" * 70)
    manager.update_history(
        workspace,
        report_version=1,
        paper_count=2,
        patent_count=1,
        report_file_path="report_v1.md",
    )
    print("   Updated metadata with:")
    print("     - report_version: 1")
    print("     - paper_count: 2")
    print("     - patent_count: 1")
    print("     - report_file_path: report_v1.md")
    print()

    # Create a second workspace to test history listing
    print("8. Creating second workspace for history demo")
    print("-" * 70)
    topic2 = "Machine Learning for Robotics"
    workspace2 = manager.create(topic2)
    print(f"   Created workspace: {workspace2}")

    # Save minimal result to second workspace
    result2 = OrchestratorResult(
        topic=topic2,
        queries=[],
        raw_items=[],
    )
    manager.save_orchestrator_result(workspace2, result2)
    manager.update_history(
        workspace2,
        report_version=2,
        paper_count=3,
        patent_count=2,
    )
    print("   Saved result and updated history")
    print()

    # List history
    print("9. Listing all workspace history")
    print("-" * 70)
    history = manager.list_history()
    print(f"   Found {len(history)} workspace(s):\n")

    for i, entry in enumerate(history, 1):
        print(f"   {i}. {entry.topic}")
        print(f"      Workspace: {Path(entry.workspace_dir).name}")
        print(f"      Created: {entry.creation_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      Updated: {entry.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"      Version: {entry.report_version}")
        print(f"      Papers: {entry.paper_count}, Patents: {entry.patent_count}")
        if entry.report_file_path:
            print(f"      Report: {entry.report_file_path}")
        print()

    # Verify workspace lookup
    print("10. Testing workspace lookup")
    print("-" * 70)
    found_workspace = manager.get_workspace_by_topic(topic)
    print(f"   Looking up topic: {topic}")
    print(f"   Found workspace: {found_workspace}")
    print(f"   Matches original: {found_workspace == workspace}")
    print()

    exists = manager.workspace_exists(topic)
    print(f"   Workspace exists for '{topic}': {exists}")

    exists_fake = manager.workspace_exists("Nonexistent Topic")
    print(f"   Workspace exists for 'Nonexistent Topic': {exists_fake}")
    print()

    # Summary
    print("=" * 70)
    print("Test Complete!")
    print("=" * 70)
    print("\nAll workspace operations completed successfully:")
    print("  ✓ Created workspaces")
    print("  ✓ Saved orchestrator results")
    print("  ✓ Saved custom artifacts")
    print("  ✓ Loaded results back")
    print("  ✓ Updated history metadata")
    print("  ✓ Listed workspace history")
    print("  ✓ Looked up workspaces by topic")
    print()
    print(f"Test workspaces saved in: {test_base_dir.absolute()}")
    print()


if __name__ == "__main__":
    main()
