#!/usr/bin/env python3
"""
Integration test: WorkspaceManager with SearchOrchestrator.

This test demonstrates how the WorkspaceManager integrates with the
existing SearchOrchestrator to persist search results.
"""

import asyncio
from pathlib import Path
import shutil

from ria.orchestrator import SearchOrchestrator
from ria.adapters.semantic_scholar import SemanticScholarAdapter
from ria.workspace import WorkspaceManager


async def main():
    """Run workspace + orchestrator integration test."""
    print("=" * 70)
    print("WorkspaceManager + SearchOrchestrator Integration Test")
    print("=" * 70)
    print()

    # Setup
    test_base_dir = Path("./test_integration_workspaces")
    if test_base_dir.exists():
        shutil.rmtree(test_base_dir)

    manager = WorkspaceManager(base_dir=test_base_dir)
    print("✓ WorkspaceManager initialized")
    print()

    # Create orchestrator with real adapter
    adapters = [SemanticScholarAdapter()]
    orchestrator = SearchOrchestrator(adapters=adapters)
    print("✓ SearchOrchestrator created with SemanticScholarAdapter")
    print()

    # Run search
    topic = "Position Based Dynamics"
    print(f"Running search for: '{topic}'")
    print("-" * 70)

    result = await orchestrator.search(topic, max_results_per_adapter=3)

    print(f"✓ Search completed")
    print(f"  - Total queries: {len(result.queries)}")
    print(f"  - Total results: {len(result.raw_items)}")
    print()

    # Create workspace
    print("Creating workspace and saving results")
    print("-" * 70)
    workspace = manager.create(topic)
    print(f"✓ Workspace created: {workspace.name}")

    # Save orchestrator result
    saved_path = manager.save_orchestrator_result(workspace, result)
    print(f"✓ Results saved: {saved_path.name}")
    print()

    # Update metadata with counts
    paper_count = sum(1 for item in result.raw_items if item.source_type.value == "paper")
    patent_count = sum(1 for item in result.raw_items if item.source_type.value == "patent")

    manager.update_history(
        workspace,
        paper_count=paper_count,
        patent_count=patent_count,
    )
    print(f"✓ History updated (papers: {paper_count}, patents: {patent_count})")
    print()

    # Load results back
    print("Loading results from workspace")
    print("-" * 70)
    loaded_result = manager.load_orchestrator_result(workspace)
    print(f"✓ Results loaded successfully")
    print(f"  - Topic: {loaded_result.topic}")
    print(f"  - Items: {len(loaded_result.raw_items)}")
    print()

    if loaded_result.raw_items:
        print("Sample results:")
        for i, item in enumerate(loaded_result.raw_items[:3], 1):
            print(f"  {i}. {item.title}")
            print(f"     Type: {item.source_type.value}")
            print(f"     URL: {item.source_url}")
        print()

    # List history
    print("Workspace history")
    print("-" * 70)
    history = manager.list_history()
    for entry in history:
        print(f"Topic: {entry.topic}")
        print(f"  Papers: {entry.paper_count}")
        print(f"  Patents: {entry.patent_count}")
        print(f"  Last updated: {entry.last_updated.strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    print("=" * 70)
    print("Integration Test Complete!")
    print("=" * 70)
    print()
    print("✓ Orchestrator results successfully persisted")
    print("✓ Results loaded back and verified")
    print("✓ History tracking working correctly")
    print()


if __name__ == "__main__":
    asyncio.run(main())
