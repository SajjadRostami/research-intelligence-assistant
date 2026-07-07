"""
Test script for new features: metrics bank and research cache.
"""

import asyncio
from ria.metrics_bank import MetricsBank
from ria.research_cache import ResearchCache, normalize_topic
from ria.models import RawSourceItem, SourceType, ConfidenceLevel


def test_metrics_bank():
    """Test metrics bank initialization and suggestions."""
    print("Testing Metrics Bank...")

    bank = MetricsBank(persist_directory="./test_chroma_db/metrics")
    bank.initialize_defaults()

    # Test suggestion
    suggestions = bank.suggest_metrics("XPBD simulation", max_results=5)

    print(f"✅ Metrics Bank initialized with {bank.collection.count()} default metrics")
    print(f"✅ Suggested {len(suggestions)} metrics for 'XPBD simulation':")
    for s in suggestions[:3]:
        print(f"   - {s['name']}: {s['description'][:50]}...")

    # Test custom metric
    bank.add_metric(
        metric_id="test_metric",
        name="Test Metric",
        description="Test description",
        category="Test",
        source="user",
    )
    print(f"✅ Added custom metric")

    # Test increment usage
    if suggestions:
        bank.increment_usage(suggestions[0]['metric_id'])
        print(f"✅ Incremented usage count")

    print()


def test_research_cache():
    """Test research cache save and lookup."""
    print("Testing Research Cache...")

    cache = ResearchCache(persist_directory="./test_chroma_db/research")

    # Test topic normalization
    normalized = normalize_topic("XPBD Soft Body Simulation")
    print(f"✅ Topic normalized: 'XPBD Soft Body Simulation' -> '{normalized}'")

    # Create test items
    test_items = [
        RawSourceItem(
            title="Extended Position Based Dynamics for Soft Bodies",
            source_type=SourceType.PAPER,
            source_url="https://example.com/paper1",
            publication_date="2023-01-15",
            author_or_assignee="John Doe, Jane Smith",
            relevance_explanation="Proposes XPBD method for soft body simulation",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1234/example.123",
            raw_adapter_source="test_adapter",
            venue="SIGGRAPH 2023",
            citation_count=42,
            is_open_access=True,
            pdf_url="https://example.com/paper1.pdf",
        ),
        RawSourceItem(
            title="Soft Body Simulation System",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US123456",
            publication_date="2022-06-10",
            author_or_assignee="Tech Corp",
            relevance_explanation="Patent for XPBD-based soft body system",
            confidence_level=ConfidenceLevel.HIGH,
            patent_number="US123456B2",
            raw_adapter_source="test_adapter",
        ),
    ]

    # Save to cache
    saved_count = cache.save_items("XPBD simulation", test_items)
    print(f"✅ Saved {saved_count} items to cache")

    # Lookup from cache
    cached_items = cache.lookup("XPBD simulation", exact_match=True)
    print(f"✅ Retrieved {len(cached_items)} items from cache")

    # Get cache status
    status = cache.get_cache_status("XPBD simulation")
    print(f"✅ Cache status:")
    print(f"   - Cached: {status['cached']}")
    print(f"   - Patents: {status['patents_count']}")
    print(f"   - Papers: {status['papers_count']}")
    print(f"   - Open Access Papers: {status['open_access_papers_count']}")

    print()


def test_comparison_matrix():
    """Test comparison matrix generation."""
    print("Testing Comparison Matrix...")

    from ria.comparison_matrix import render_matrix_markdown, MetricEvaluation, SourceMetricEvaluation

    # Create test evaluations
    test_evaluations = [
        SourceMetricEvaluation(
            source_id="paper1",
            source_title="Extended Position Based Dynamics",
            source_type="paper",
            metric_evaluations=[
                MetricEvaluation(
                    metric_name="XPBD Support",
                    status="full",
                    symbol="✅",
                    score=1.0,
                    evidence="Explicitly uses XPBD algorithm",
                    confidence="high"
                ),
                MetricEvaluation(
                    metric_name="GPU Support",
                    status="partial",
                    symbol="⚠️",
                    score=0.5,
                    evidence="Mentions GPU but not primary focus",
                    confidence="medium"
                ),
                MetricEvaluation(
                    metric_name="VR Support",
                    status="none",
                    symbol="❌",
                    score=0.0,
                    evidence="No mention of VR",
                    confidence="high"
                ),
            ],
            overall_score=0.5
        ),
        SourceMetricEvaluation(
            source_id="patent1",
            source_title="Soft Body Simulation System",
            source_type="patent",
            metric_evaluations=[
                MetricEvaluation(
                    metric_name="XPBD Support",
                    status="full",
                    symbol="✅",
                    score=1.0,
                    evidence="Patent describes XPBD implementation",
                    confidence="high"
                ),
                MetricEvaluation(
                    metric_name="GPU Support",
                    status="full",
                    symbol="✅",
                    score=1.0,
                    evidence="GPU acceleration is core feature",
                    confidence="high"
                ),
                MetricEvaluation(
                    metric_name="VR Support",
                    status="partial",
                    symbol="⚠️",
                    score=0.5,
                    evidence="VR mentioned as optional extension",
                    confidence="medium"
                ),
            ],
            overall_score=0.83
        ),
    ]

    metric_names = ["XPBD Support", "GPU Support", "VR Support"]

    markdown_matrix = render_matrix_markdown(
        evaluations=test_evaluations,
        metric_names=metric_names,
        include_evidence=False
    )

    print(f"✅ Generated comparison matrix:")
    print(markdown_matrix[:300] + "...")
    print()


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing New Features")
    print("=" * 60)
    print()

    try:
        test_metrics_bank()
        test_research_cache()
        test_comparison_matrix()

        print("=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
