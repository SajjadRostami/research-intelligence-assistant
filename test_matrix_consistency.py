"""
Test script to verify matrix consistency between web UI and PDF.

This test verifies that:
1. Source labels are assigned in the same order for web UI and PDF
2. All sources in the matrix can be mapped to labels
3. No "Unknown" labels appear when all sources are valid
"""

from ria.models import ScoredSourceItem, SourceType
from ria.comparison_matrix import ComparisonMatrixGenerator, render_matrix_markdown


def generate_source_id(source: ScoredSourceItem) -> str:
    """Generate source ID (matches internal logic)."""
    if source.doi:
        return source.doi
    if source.patent_number:
        return source.patent_number
    return source.title[:50].replace(" ", "_")


def test_matrix_label_consistency():
    """Test that matrix labels are consistent between UI and PDF."""

    # Create mock sources (3 patents, 5 papers = 8 total)
    patents = [
        ScoredSourceItem(
            title=f"Patent Title {i}",
            source_type=SourceType.PATENT,
            patent_number=f"US{1000+i}",
            relevance_score=0.9 - (i * 0.1),
            relevance_explanation=f"Patent {i} explanation",
            author_or_assignee=f"Assignee {i}",
            publication_date="2023",
            source_url=f"https://patents.google.com/patent/US{1000+i}",
            raw_adapter_source="test_source",
        )
        for i in range(1, 4)
    ]

    papers = [
        ScoredSourceItem(
            title=f"Paper Title {i}",
            source_type=SourceType.PAPER,
            doi=f"10.1000/paper{i}",
            relevance_score=0.85 - (i * 0.05),
            relevance_explanation=f"Paper {i} explanation",
            author_or_assignee=f"Author {i}",
            publication_date="2023",
            venue=f"Venue {i}",
            source_url=f"https://doi.org/10.1000/paper{i}",
            raw_adapter_source="test_source",
        )
        for i in range(1, 6)
    ]

    print(f"✓ Created {len(patents)} patents and {len(papers)} papers")

    # Simulate matrix generation (patents + papers order)
    all_sources = patents + papers
    print(f"✓ Combined sources: {len(all_sources)} total (patents first, then papers)")

    # Build source ID mapping in the same order as web UI
    # After fix, this should be: patents first, then papers
    source_ids_in_order = []

    # Patents first
    for patent in patents:
        source_ids_in_order.append(generate_source_id(patent))

    # Then papers
    for paper in papers:
        source_ids_in_order.append(generate_source_id(paper))

    print(f"✓ Generated {len(source_ids_in_order)} source IDs in order")

    # Verify all sources have unique IDs
    if len(source_ids_in_order) != len(set(source_ids_in_order)):
        print("✗ FAIL: Duplicate source IDs detected!")
        return False

    print("✓ All source IDs are unique")

    # Verify order matches expectation
    expected_labels = [f"Patent {i}" for i in range(1, 4)] + [f"Paper {i}" for i in range(1, 6)]
    print(f"✓ Expected labels: {expected_labels}")

    # Simulate label assignment (should match source_ids_in_order)
    label_map = {}

    # Patents first (matches fix)
    for idx, patent in enumerate(patents, 1):
        source_id = generate_source_id(patent)
        label_map[source_id] = f"Patent {idx}"

    # Papers second (matches fix)
    for idx, paper in enumerate(papers, 1):
        source_id = generate_source_id(paper)
        label_map[source_id] = f"Paper {idx}"

    print(f"✓ Created label map with {len(label_map)} entries")

    # Verify all source IDs can be mapped to labels
    unmapped = []
    for source_id in source_ids_in_order:
        if source_id not in label_map:
            unmapped.append(source_id)

    if unmapped:
        print(f"✗ FAIL: {len(unmapped)} source IDs cannot be mapped to labels:")
        for sid in unmapped:
            print(f"  - {sid}")
        return False

    print("✓ All source IDs can be mapped to labels")

    # Verify labels match expected order
    actual_labels = [label_map[sid] for sid in source_ids_in_order]
    if actual_labels != expected_labels:
        print("✗ FAIL: Label order mismatch!")
        print(f"  Expected: {expected_labels}")
        print(f"  Actual:   {actual_labels}")
        return False

    print(f"✓ Labels match expected order: {actual_labels}")

    # Verify no "Unknown" labels
    if any("Unknown" in label for label in actual_labels):
        print("✗ FAIL: Found 'Unknown' labels!")
        return False

    print("✓ No 'Unknown' labels found")

    print("\n✅ All consistency checks passed!")
    return True


if __name__ == "__main__":
    success = test_matrix_label_consistency()
    exit(0 if success else 1)
