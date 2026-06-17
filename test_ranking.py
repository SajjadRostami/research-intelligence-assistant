#!/usr/bin/env python3
"""
Test script for the RankingEngine.

This script demonstrates deduplication, scoring, and selection by:
1. Loading raw results from a workspace
2. Deduplicating the results
3. Scoring them against a research topic
4. Selecting and displaying the top results
"""

import sys
from pathlib import Path

from ria.llm import LLMClient
from ria.ranking import RankingEngine
from ria.workspace import WorkspaceManager


def main():
    """Run the ranking engine test."""

    # Configuration
    research_topic = "XPBD soft body simulation algorithm"
    workspace_name = "xpbd-soft-body-simulation-algorithm"  # Adjust based on actual workspace

    print(f"=" * 80)
    print(f"Ranking Engine Test")
    print(f"=" * 80)
    print(f"Research Topic: {research_topic}")
    print()

    # Initialize workspace manager
    workspace_manager = WorkspaceManager(base_dir="./workspaces")

    # Check if workspace exists
    workspace_path = workspace_manager.base_dir / workspace_name
    if not workspace_path.exists():
        print(f"Error: Workspace not found at {workspace_path}")
        print(f"\nAvailable workspaces:")
        for entry in workspace_manager.list_history():
            print(f"  - {entry.topic} ({entry.workspace_dir})")
        sys.exit(1)

    print(f"Loading results from: {workspace_path}")

    # Load orchestrator results
    try:
        orchestrator_result = workspace_manager.load_orchestrator_result(workspace_path)
        print(f"Loaded {len(orchestrator_result.raw_items)} raw items")
        print()
    except FileNotFoundError:
        print(f"Error: orchestrator_result.json not found in workspace")
        sys.exit(1)

    # Initialize LLM client and ranking engine
    print("Initializing LLM client and ranking engine...")
    try:
        llm_client = LLMClient()
        ranking_engine = RankingEngine(llm_client)
        print(f"Using model: {llm_client.model}")
        print()
    except ValueError as e:
        print(f"Error initializing LLM client: {e}")
        print("\nMake sure OPENAI_API_KEY and OPENAI_BASE_URL are set in your environment.")
        sys.exit(1)

    # Step 1: Deduplicate
    print(f"Step 1: Deduplicating...")
    deduplicated = ranking_engine.deduplicate(orchestrator_result.raw_items)
    removed_count = len(orchestrator_result.raw_items) - len(deduplicated)
    print(f"  Before: {len(orchestrator_result.raw_items)} items")
    print(f"  After:  {len(deduplicated)} items")
    print(f"  Removed: {removed_count} duplicates")
    print()

    # Step 2: Score
    print(f"Step 2: Scoring items for relevance...")
    scored = ranking_engine.score(deduplicated, research_topic)
    print(f"  Scored {len(scored)} items")
    print()

    # Step 3: Select top
    print(f"Step 3: Selecting top results...")
    top_papers, top_patents = ranking_engine.select_top(scored, top_n=3)
    print(f"  Selected {len(top_papers)} papers")
    print(f"  Selected {len(top_patents)} patents")
    print()

    # Display results
    print(f"=" * 80)
    print(f"TOP PAPERS")
    print(f"=" * 80)
    print()

    if not top_papers:
        print("No papers found.")

    for i, paper in enumerate(top_papers, 1):
        print(f"[{i}] Score: {paper.relevance_score:.2f}")
        print(f"    Title: {paper.title}")
        print(f"    Type: {paper.source_type.value}")
        if paper.publication_date:
            print(f"    Date: {paper.publication_date}")
        if paper.author_or_assignee:
            print(f"    Author: {paper.author_or_assignee}")
        if paper.doi:
            print(f"    DOI: {paper.doi}")
        print(f"    URL: {paper.source_url}")
        print(f"    Reasoning: {paper.relevance_explanation}")
        print()

    print(f"=" * 80)
    print(f"TOP PATENTS")
    print(f"=" * 80)
    print()

    if not top_patents:
        print("No patents found.")

    for i, patent in enumerate(top_patents, 1):
        print(f"[{i}] Score: {patent.relevance_score:.2f}")
        print(f"    Title: {patent.title}")
        print(f"    Type: {patent.source_type.value}")
        if patent.publication_date:
            print(f"    Date: {patent.publication_date}")
        if patent.author_or_assignee:
            print(f"    Assignee: {patent.author_or_assignee}")
        if patent.patent_number:
            print(f"    Patent #: {patent.patent_number}")
        print(f"    URL: {patent.source_url}")
        print(f"    Reasoning: {patent.relevance_explanation}")
        print()

    # Save ranked results
    print(f"=" * 80)
    print(f"Saving ranked results to workspace...")

    ranked_data = {
        "papers": [paper.model_dump(mode='json') for paper in top_papers],
        "patents": [patent.model_dump(mode='json') for patent in top_patents],
    }

    output_path = workspace_manager.save_artifact(
        workspace_path,
        "ranked_results.json",
        ranked_data,
    )
    print(f"Saved to: {output_path}")
    print()

    print(f"Test complete!")


if __name__ == "__main__":
    main()
