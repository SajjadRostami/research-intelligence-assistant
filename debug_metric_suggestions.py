#!/usr/bin/env python3
"""
Debug script to manually test metric suggestions for different topics.

Usage:
    python debug_metric_suggestions.py
"""

from ria.agents import MetricBankAgent
from ria.llm import LLMClient
from ria.metrics_bank import MetricsBank


def test_topic(agent, topic_name):
    """Test suggestions for a single topic."""
    print(f"\n{'='*80}")
    print(f"TOPIC: {topic_name}")
    print('='*80)

    suggestions = agent.get_smart_suggestions(
        topic=topic_name,
        max_results=10,
        include_fresh_llm_suggestions=True,
    )

    print(f"\nTop 10 suggestions:")
    for i, m in enumerate(suggestions):
        print(
            f"{i+1:2d}. {m['name']:40s} | "
            f"final={m['final_score']:.3f} | "
            f"topic_rel={m.get('topic_relevance_score', 0):.3f} | "
            f"selected={m['selected_count']:2d} | "
            f"source={m['source']:12s}"
        )

    return suggestions


def main():
    print("Initializing Metric Bank Agent...")

    # Initialize components
    llm_client = LLMClient()
    chroma_bank = MetricsBank()
    chroma_bank.initialize_defaults()

    agent = MetricBankAgent(
        llm_client=llm_client,
        chroma_metrics_bank=chroma_bank
    )
    agent.initialize_defaults()

    print(f"Loaded {len(agent.metrics)} metrics from storage")

    # Test multiple topics
    topics = [
        "Eye modeling",
        "XPBD soft body simulation",
        "LLM medical summarization",
    ]

    results = {}
    for topic in topics:
        results[topic] = test_topic(agent, topic)

    # Compare overlaps
    print(f"\n{'='*80}")
    print("OVERLAP ANALYSIS")
    print('='*80)

    for i, topic1 in enumerate(topics):
        for topic2 in topics[i+1:]:
            top5_1 = set(m['name'] for m in results[topic1][:5])
            top5_2 = set(m['name'] for m in results[topic2][:5])
            overlap = top5_1 & top5_2
            overlap_ratio = len(overlap) / 5.0

            print(f"\n'{topic1}' vs '{topic2}':")
            print(f"  Overlap: {len(overlap)}/5 = {overlap_ratio:.1%}")
            if overlap:
                print(f"  Shared: {', '.join(overlap)}")


if __name__ == "__main__":
    main()
