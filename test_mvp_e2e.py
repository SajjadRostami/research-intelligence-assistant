#!/usr/bin/env python3
"""
End-to-End MVP Test for Research Intelligence Assistant.

This test runs the complete pipeline:
1. SearchOrchestrator - searches patents and papers
2. WorkspaceManager - persists results
3. RankingEngine - deduplicates, scores, and ranks sources
4. MetricsGenerator - generates benchmark metrics

Test input: "XPBD soft body simulation algorithm"

Outputs:
- Number of patents found
- Number of papers found
- Top 3 patents (ranked by relevance)
- Top 3 papers (ranked by relevance)
- Generated benchmark metrics

All artifacts are saved to workspace for future use.
"""

import asyncio
import os
from pathlib import Path
import shutil

from ria.adapters import SemanticScholarAdapter, MockPatentAdapter, SerpAPIPatentAdapter
from ria.llm import LLMClient
from ria.metrics import MetricsGenerator
from ria.orchestrator import SearchOrchestrator
from ria.ranking import RankingEngine
from ria.workspace import WorkspaceManager


def print_separator(char="=", width=80):
    """Print a separator line."""
    print(char * width)


def print_section(title: str):
    """Print a section header."""
    print()
    print_separator("=")
    print(title)
    print_separator("=")
    print()


def print_subsection(title: str):
    """Print a subsection header."""
    print()
    print_separator("-")
    print(title)
    print_separator("-")


async def main():
    """Run end-to-end MVP test."""
    print_section("Research Intelligence Assistant - End-to-End MVP Test")

    # Configuration
    TEST_TOPIC = "XPBD soft body simulation algorithm"
    TEST_BASE_DIR = Path("./test_mvp_workspace")
    MAX_RESULTS_PER_ADAPTER = 10

    print(f"Test Configuration:")
    print(f"  Topic: {TEST_TOPIC}")
    print(f"  Workspace: {TEST_BASE_DIR}")
    print(f"  Max results per adapter: {MAX_RESULTS_PER_ADAPTER}")
    print()

    # Clean up previous test workspace
    if TEST_BASE_DIR.exists():
        print(f"Cleaning up previous test workspace: {TEST_BASE_DIR}")
        shutil.rmtree(TEST_BASE_DIR)
        print("✓ Cleanup complete")
        print()

    # =========================================================================
    # STEP 1: Initialize Components
    # =========================================================================
    print_section("Step 1: Initialize Components")

    # Initialize LLM client
    print("Initializing LLM client...")
    llm_client = LLMClient()
    print(f"✓ LLM client initialized")
    print(f"  Model: {os.getenv('LLM_MODEL', 'claude-haiku')}")
    print(f"  Base URL: {os.getenv('OPENAI_BASE_URL', 'default')}")
    print()

    # Initialize adapters
    print("Initializing search adapters...")

    # Choose patent adapter based on SERPAPI_API_KEY availability
    serpapi_key = os.getenv("SERPAPI_API_KEY")
    if serpapi_key:
        patent_adapter = SerpAPIPatentAdapter()
        patent_adapter_name = "SerpAPIPatentAdapter (real patents)"
    else:
        patent_adapter = MockPatentAdapter()
        patent_adapter_name = "MockPatentAdapter (synthetic patents)"

    adapters = [
        SemanticScholarAdapter(),  # For papers
        patent_adapter,             # For patents
    ]

    print(f"✓ {len(adapters)} adapters initialized:")
    print(f"  - SemanticScholarAdapter (academic papers)")
    print(f"  - {patent_adapter_name}")
    if not serpapi_key:
        print(f"    Note: Set SERPAPI_API_KEY for real patent data")
    print()

    # Initialize orchestrator
    print("Initializing SearchOrchestrator...")
    orchestrator = SearchOrchestrator(adapters=adapters)
    print("✓ SearchOrchestrator initialized")
    print()

    # Initialize workspace manager
    print("Initializing WorkspaceManager...")
    workspace_manager = WorkspaceManager(base_dir=TEST_BASE_DIR)
    print(f"✓ WorkspaceManager initialized")
    print(f"  Base directory: {workspace_manager.base_dir}")
    print()

    # Initialize ranking engine
    print("Initializing RankingEngine...")
    ranking_engine = RankingEngine(llm_client=llm_client)
    print("✓ RankingEngine initialized")
    print()

    # Initialize metrics generator
    print("Initializing MetricsGenerator...")
    metrics_generator = MetricsGenerator(llm_client=llm_client)
    print("✓ MetricsGenerator initialized")
    print()

    # =========================================================================
    # STEP 2: Run Search Orchestrator
    # =========================================================================
    print_section("Step 2: Run Search Orchestrator")

    print(f"Searching for: '{TEST_TOPIC}'")
    print("Running concurrent searches across all adapters...")
    print()

    orchestrator_result = await orchestrator.search(
        topic=TEST_TOPIC,
        max_results_per_adapter=MAX_RESULTS_PER_ADAPTER,
    )

    print(f"✓ Search completed!")
    print(f"  Total queries: {len(orchestrator_result.queries)}")
    print(f"  Total raw items: {len(orchestrator_result.raw_items)}")
    print()

    # Count by source type
    papers_raw = [item for item in orchestrator_result.raw_items
                  if item.source_type.value == "paper"]
    patents_raw = [item for item in orchestrator_result.raw_items
                   if item.source_type.value == "patent"]

    print("Raw Results by Type:")
    print(f"  Papers: {len(papers_raw)}")
    print(f"  Patents: {len(patents_raw)}")
    print()

    # =========================================================================
    # STEP 3: Create Workspace and Save Results
    # =========================================================================
    print_section("Step 3: Create Workspace and Save Results")

    print(f"Creating workspace for topic: '{TEST_TOPIC}'")
    workspace = workspace_manager.create(TEST_TOPIC)
    print(f"✓ Workspace created: {workspace}")
    print()

    print("Saving orchestrator results...")
    orchestrator_path = workspace_manager.save_orchestrator_result(
        workspace=workspace,
        result=orchestrator_result,
    )
    print(f"✓ Results saved: {orchestrator_path}")
    print()

    # Update metadata with raw counts
    workspace_manager.update_history(
        workspace,
        paper_count=len(papers_raw),
        patent_count=len(patents_raw),
    )
    print("✓ Workspace metadata updated")
    print()

    # =========================================================================
    # STEP 4: Run Ranking Engine
    # =========================================================================
    print_section("Step 4: Run Ranking Engine")

    print_subsection("4.1: Deduplication")
    print(f"Deduplicating {len(orchestrator_result.raw_items)} raw items...")
    deduplicated = ranking_engine.deduplicate(orchestrator_result.raw_items)
    print(f"✓ Deduplication complete")
    print(f"  Before: {len(orchestrator_result.raw_items)} items")
    print(f"  After: {len(deduplicated)} items")
    print(f"  Duplicates removed: {len(orchestrator_result.raw_items) - len(deduplicated)}")
    print()

    print_subsection("4.2: Relevance Scoring")
    print("Scoring sources for relevance using LLM...")
    print("(This may take a moment...)")
    print()

    scored_items = ranking_engine.score(
        items=deduplicated,
        research_topic=TEST_TOPIC,
    )

    print(f"✓ Scoring complete")
    print(f"  Scored items: {len(scored_items)}")
    print()

    print_subsection("4.3: Top Selection")
    print("Selecting top 3 papers and top 3 patents...")
    top_papers, top_patents = ranking_engine.select_top(
        scored_items=scored_items,
        top_n=3,
    )

    print(f"✓ Top sources selected")
    print(f"  Top papers: {len(top_papers)}")
    print(f"  Top patents: {len(top_patents)}")
    print()

    # Save ranked results
    print("Saving ranked results to workspace...")
    ranked_results_data = {
        "papers": [item.model_dump() for item in top_papers],
        "patents": [item.model_dump() for item in top_patents],
    }
    ranked_path = workspace_manager.save_artifact(
        workspace=workspace,
        artifact_name="ranked_results.json",
        data=ranked_results_data,
    )
    print(f"✓ Ranked results saved: {ranked_path}")
    print()

    # =========================================================================
    # STEP 5: Generate Benchmark Metrics
    # =========================================================================
    print_section("Step 5: Generate Benchmark Metrics")

    print("Generating benchmark metrics using LLM...")
    print("(Analyzing top sources to determine relevant metrics...)")
    print()

    metrics = metrics_generator.generate(
        topic=TEST_TOPIC,
        papers=top_papers,
        patents=top_patents,
    )

    print(f"✓ Metrics generation complete")
    print(f"  Generated {len(metrics)} benchmark metrics")
    print()

    # Save metrics
    print("Saving metrics to workspace...")
    metrics_path = metrics_generator.save_metrics(
        workspace=workspace,
        metrics=metrics,
        workspace_manager=workspace_manager,
    )
    print(f"✓ Metrics saved: {metrics_path}")
    print()

    # =========================================================================
    # STEP 6: Display Results
    # =========================================================================
    print_section("Step 6: Final Results")

    print_subsection("Summary Statistics")
    print(f"Research Topic: {TEST_TOPIC}")
    print(f"Workspace: {workspace}")
    print()
    print(f"Number of patents found: {len(patents_raw)}")
    print(f"Number of papers found: {len(papers_raw)}")
    print(f"Total raw sources: {len(orchestrator_result.raw_items)}")
    print(f"After deduplication: {len(deduplicated)}")
    print()

    print_subsection("Top 3 Patents (Ranked by Relevance)")
    if top_patents:
        for i, patent in enumerate(top_patents, 1):
            print(f"\n{i}. {patent.title}")
            print(f"   Score: {patent.relevance_score:.3f}")
            print(f"   Patent Number: {patent.patent_number or 'N/A'}")
            print(f"   Assignee: {patent.author_or_assignee or 'N/A'}")
            print(f"   Date: {patent.publication_date or 'N/A'}")
            print(f"   URL: {patent.source_url}")
            if patent.relevance_explanation:
                explanation = patent.relevance_explanation[:150]
                if len(patent.relevance_explanation) > 150:
                    explanation += "..."
                print(f"   Reasoning: {explanation}")
    else:
        print("  No patents found.")
    print()

    print_subsection("Top 3 Papers (Ranked by Relevance)")
    if top_papers:
        for i, paper in enumerate(top_papers, 1):
            print(f"\n{i}. {paper.title}")
            print(f"   Score: {paper.relevance_score:.3f}")
            print(f"   Author(s): {paper.author_or_assignee or 'N/A'}")
            print(f"   Date: {paper.publication_date or 'N/A'}")
            print(f"   DOI: {paper.doi or 'N/A'}")
            print(f"   URL: {paper.source_url}")
            if paper.relevance_explanation:
                explanation = paper.relevance_explanation[:150]
                if len(paper.relevance_explanation) > 150:
                    explanation += "..."
                print(f"   Reasoning: {explanation}")
    else:
        print("  No papers found.")
    print()

    print_subsection("Generated Benchmark Metrics")
    print(f"\nTotal metrics: {len(metrics)}\n")

    for i, metric in enumerate(metrics, 1):
        print(f"{i}. {metric.name}")
        print(f"   Category: {metric.category or 'N/A'}")
        print(f"   Description: {metric.description or 'N/A'}")
        print()

    # =========================================================================
    # STEP 7: Workspace Artifacts Summary
    # =========================================================================
    print_section("Step 7: Saved Artifacts")

    print("All artifacts have been saved to the workspace:")
    print(f"  Workspace directory: {workspace}")
    print()
    print("Files created:")

    for file in sorted(workspace.iterdir()):
        if file.is_file():
            size = file.stat().st_size
            print(f"  - {file.name} ({size:,} bytes)")

    print()
    print("You can reload these artifacts using WorkspaceManager methods:")
    print("  - workspace_manager.load_orchestrator_result(workspace)")
    print("  - workspace_manager.load_artifact(workspace, 'ranked_results.json')")
    print("  - metrics_generator.load_metrics(workspace, workspace_manager)")
    print()

    # =========================================================================
    # Test Complete
    # =========================================================================
    print_section("End-to-End MVP Test Complete! ✓")

    print("All pipeline stages completed successfully:")
    print("  ✓ Search orchestration")
    print("  ✓ Workspace persistence")
    print("  ✓ Ranking and scoring")
    print("  ✓ Metrics generation")
    print("  ✓ Artifact storage")
    print()
    print(f"Review the workspace at: {workspace}")
    print()


if __name__ == "__main__":
    asyncio.run(main())
