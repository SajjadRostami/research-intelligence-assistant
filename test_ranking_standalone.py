#!/usr/bin/env python3
"""
Standalone test script for the RankingEngine with mock data.

This script demonstrates deduplication, scoring, and selection using
mock data that doesn't require a pre-existing workspace.
"""

from datetime import datetime

from ria.llm import LLMClient
from ria.models import ConfidenceLevel, RawSourceItem, SourceType
from ria.ranking import RankingEngine


def create_mock_data() -> list[RawSourceItem]:
    """Create mock raw source items for testing."""
    return [
        # Papers
        RawSourceItem(
            title="Position Based Dynamics for Soft Body Simulation",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper1",
            publication_date="2023-05-15",
            author_or_assignee="John Smith, Jane Doe",
            relevance_explanation=(
                "This paper presents a novel approach to soft body simulation using "
                "Position Based Dynamics (PBD) with extended constraints for volumetric "
                "deformation. The method achieves real-time performance while maintaining "
                "physical plausibility."
            ),
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1234/example.2023.001",
            raw_adapter_source="semantic_scholar",
        ),
        RawSourceItem(
            title="XPBD: Extended Position Based Dynamics for Fast Simulation",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper2",
            publication_date="2023-08-20",
            author_or_assignee="Alice Johnson, Bob Williams",
            relevance_explanation=(
                "We introduce XPBD, an extension of Position Based Dynamics that uses "
                "implicit constraint solving for improved stability and convergence. "
                "The method is particularly effective for cloth and soft body simulations."
            ),
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1234/example.2023.002",
            raw_adapter_source="semantic_scholar",
        ),
        # Duplicate paper (same title, different case/spacing)
        RawSourceItem(
            title="  XPBD: Extended Position   Based Dynamics for Fast Simulation  ",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper2-duplicate",
            publication_date="2023-08-20",
            author_or_assignee="Alice Johnson, Bob Williams",
            relevance_explanation="Duplicate entry",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1234/example.2023.002",
            raw_adapter_source="semantic_scholar",
        ),
        RawSourceItem(
            title="Physics-Based Animation of Deformable Objects",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper3",
            publication_date="2022-11-10",
            author_or_assignee="Carol Davis",
            relevance_explanation=(
                "A comprehensive survey of physics-based deformable object animation, "
                "covering mass-spring systems, finite element methods, and position-based "
                "approaches."
            ),
            confidence_level=ConfidenceLevel.MEDIUM,
            doi="10.1234/example.2022.003",
            raw_adapter_source="semantic_scholar",
        ),
        RawSourceItem(
            title="Machine Learning for Rigid Body Dynamics",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper4",
            publication_date="2024-01-05",
            author_or_assignee="Eve Thompson",
            relevance_explanation=(
                "This paper explores using neural networks to learn rigid body dynamics "
                "for faster simulation. Less relevant to soft body simulation."
            ),
            confidence_level=ConfidenceLevel.LOW,
            doi="10.1234/example.2024.004",
            raw_adapter_source="semantic_scholar",
        ),
        # Patents
        RawSourceItem(
            title="System and Method for Real-Time Soft Body Deformation",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US123456",
            publication_date="2023-03-12",
            author_or_assignee="Tech Corp Inc.",
            relevance_explanation=(
                "A patent describing a system for real-time soft body deformation using "
                "GPU-accelerated position-based constraints. Includes hardware and software "
                "components for interactive simulation."
            ),
            confidence_level=ConfidenceLevel.HIGH,
            patent_number="US123456A1",
            raw_adapter_source="google_patents",
        ),
        RawSourceItem(
            title="Apparatus for Simulating Elastic Materials",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US789012",
            publication_date="2022-09-30",
            author_or_assignee="Innovation Labs Ltd.",
            relevance_explanation=(
                "Patent covering methods for simulating elastic materials in computer "
                "graphics applications, with focus on game engines and VR systems."
            ),
            confidence_level=ConfidenceLevel.MEDIUM,
            patent_number="US789012B2",
            raw_adapter_source="google_patents",
        ),
        # Duplicate patent (same patent number)
        RawSourceItem(
            title="Apparatus for Simulating Elastic Materials (Continuation)",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US789012-cont",
            publication_date="2022-09-30",
            author_or_assignee="Innovation Labs Ltd.",
            relevance_explanation="Duplicate continuation patent",
            confidence_level=ConfidenceLevel.MEDIUM,
            patent_number="US789012B2",
            raw_adapter_source="google_patents",
        ),
        RawSourceItem(
            title="Virtual Reality Haptic Feedback System",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US345678",
            publication_date="2023-12-01",
            author_or_assignee="VR Systems Co.",
            relevance_explanation=(
                "Patent for a haptic feedback system in VR. Uses simple collision detection "
                "rather than advanced soft body simulation."
            ),
            confidence_level=ConfidenceLevel.LOW,
            patent_number="US345678C1",
            raw_adapter_source="google_patents",
        ),
    ]


def main():
    """Run the ranking engine test with mock data."""

    research_topic = "XPBD soft body simulation algorithm"

    print("=" * 80)
    print("Ranking Engine Standalone Test")
    print("=" * 80)
    print(f"Research Topic: {research_topic}")
    print()

    # Create mock data
    print("Creating mock data...")
    raw_items = create_mock_data()
    print(f"Created {len(raw_items)} raw items")
    print()

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
        print("\nExample:")
        print("  export OPENAI_API_KEY=your-api-key")
        print("  export OPENAI_BASE_URL=https://api.openai.com/v1")
        print()
        return

    # Step 1: Deduplicate
    print("Step 1: Deduplicating...")
    deduplicated = ranking_engine.deduplicate(raw_items)
    removed_count = len(raw_items) - len(deduplicated)
    print(f"  Before: {len(raw_items)} items")
    print(f"  After:  {len(deduplicated)} items")
    print(f"  Removed: {removed_count} duplicates")
    print()

    # Step 2: Score
    print("Step 2: Scoring items for relevance...")
    print("  (This may take a moment as each item is scored by the LLM)")
    scored = ranking_engine.score(deduplicated, research_topic)
    print(f"  Scored {len(scored)} items")
    print()

    # Step 3: Select top
    print("Step 3: Selecting top results...")
    top_papers, top_patents = ranking_engine.select_top(scored, top_n=3)
    print(f"  Selected {len(top_papers)} papers")
    print(f"  Selected {len(top_patents)} patents")
    print()

    # Display results
    print("=" * 80)
    print("TOP PAPERS")
    print("=" * 80)
    print()

    if not top_papers:
        print("No papers found.")
    else:
        for i, paper in enumerate(top_papers, 1):
            print(f"[{i}] Score: {paper.relevance_score:.2f}")
            print(f"    Title: {paper.title}")
            print(f"    Type: {paper.source_type.value}")
            print(f"    Date: {paper.publication_date or 'N/A'}")
            print(f"    Author: {paper.author_or_assignee or 'N/A'}")
            if paper.doi:
                print(f"    DOI: {paper.doi}")
            print(f"    Reasoning: {paper.relevance_explanation}")
            print()

    print("=" * 80)
    print("TOP PATENTS")
    print("=" * 80)
    print()

    if not top_patents:
        print("No patents found.")
    else:
        for i, patent in enumerate(top_patents, 1):
            print(f"[{i}] Score: {patent.relevance_score:.2f}")
            print(f"    Title: {patent.title}")
            print(f"    Type: {patent.source_type.value}")
            print(f"    Date: {patent.publication_date or 'N/A'}")
            print(f"    Assignee: {patent.author_or_assignee or 'N/A'}")
            if patent.patent_number:
                print(f"    Patent #: {patent.patent_number}")
            print(f"    Reasoning: {patent.relevance_explanation}")
            print()

    print("=" * 80)
    print("Test complete!")


if __name__ == "__main__":
    main()
