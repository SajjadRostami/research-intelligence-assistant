#!/usr/bin/env python3
"""
Test script for report generation with both papers and patents.

Creates a synthetic dataset to demonstrate the full report capabilities
when both papers and patents are present.
"""

import json
from pathlib import Path

from ria.models import (
    BenchmarkMetric,
    ConfidenceLevel,
    RankedResults,
    ScoredSourceItem,
    SourceType,
)
from ria.report import ReportRenderer


def create_test_data():
    """Create synthetic test data with both papers and patents."""
    # Create sample patents
    patents = [
        ScoredSourceItem(
            title="Advanced Neural Network Architecture for Image Recognition",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US1234567A1/en",
            publication_date="2023-05-15",
            author_or_assignee="Tech Innovations Inc.",
            relevance_explanation="This patent describes a novel convolutional neural network architecture with improved accuracy on ImageNet benchmarks. The multi-scale feature fusion approach is directly relevant to modern computer vision systems.",
            confidence_level=ConfidenceLevel.HIGH,
            patent_number="US1234567A1",
            raw_adapter_source="serpapi_patents",
            relevance_score=0.92,
        ),
        ScoredSourceItem(
            title="Real-time Object Detection Using Hierarchical Features",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/US9876543B2/en",
            publication_date="2022-11-20",
            author_or_assignee="Vision Systems Ltd.",
            relevance_explanation="Implements a hierarchical feature extraction pipeline for real-time object detection with <100ms latency. The spatial pyramid pooling technique is a key innovation.",
            confidence_level=ConfidenceLevel.HIGH,
            patent_number="US9876543B2",
            raw_adapter_source="serpapi_patents",
            relevance_score=0.88,
        ),
        ScoredSourceItem(
            title="Efficient Training Methods for Deep Neural Networks",
            source_type=SourceType.PATENT,
            source_url="https://patents.google.com/patent/EP3456789A1/en",
            publication_date="2023-02-10",
            author_or_assignee="AI Research Corporation",
            relevance_explanation="Patent covers novel optimization techniques that reduce training time by 40% while maintaining model accuracy. The adaptive learning rate scheduling is particularly relevant.",
            confidence_level=ConfidenceLevel.MEDIUM,
            patent_number="EP3456789A1",
            raw_adapter_source="serpapi_patents",
            relevance_score=0.85,
        ),
    ]

    # Create sample papers
    papers = [
        ScoredSourceItem(
            title="Deep Residual Learning for Image Recognition",
            source_type=SourceType.PAPER,
            source_url="https://arxiv.org/abs/1512.03385",
            publication_date="2015-12-10",
            author_or_assignee="He, K., Zhang, X., Ren, S., Sun, J.",
            relevance_explanation="Foundational paper introducing ResNet architecture with skip connections. Achieved state-of-the-art results on ImageNet and COCO datasets. The residual learning framework enables training of very deep networks (100+ layers).",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.1109/CVPR.2016.90",
            raw_adapter_source="semantic_scholar",
            relevance_score=0.95,
        ),
        ScoredSourceItem(
            title="Attention Is All You Need",
            source_type=SourceType.PAPER,
            source_url="https://arxiv.org/abs/1706.03762",
            publication_date="2017-06-12",
            author_or_assignee="Vaswani, A., Shazeer, N., Parmar, N., et al.",
            relevance_explanation="Introduced the Transformer architecture using self-attention mechanisms. While originally designed for NLP, vision transformers have become influential in computer vision. The multi-head attention mechanism is widely applicable.",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.48550/arXiv.1706.03762",
            raw_adapter_source="semantic_scholar",
            relevance_score=0.89,
        ),
        ScoredSourceItem(
            title="EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks",
            source_type=SourceType.PAPER,
            source_url="https://arxiv.org/abs/1905.11946",
            publication_date="2019-05-28",
            author_or_assignee="Tan, M., Le, Q.V.",
            relevance_explanation="Proposes a systematic method for scaling CNNs using compound scaling. Achieves better accuracy and efficiency trade-offs compared to previous architectures. The neural architecture search approach is innovative.",
            confidence_level=ConfidenceLevel.HIGH,
            doi="10.48550/arXiv.1905.11946",
            raw_adapter_source="semantic_scholar",
            relevance_score=0.87,
        ),
    ]

    # Create sample metrics
    metrics = [
        BenchmarkMetric(
            name="Top-1 Accuracy (%)",
            description="Classification accuracy on ImageNet validation set (50,000 images). Measures the percentage of test images where the model's top prediction is correct.",
            category="accuracy",
        ),
        BenchmarkMetric(
            name="Inference Latency (ms)",
            description="Average time to process a single 224x224 image on a V100 GPU. Lower values indicate faster inference suitable for real-time applications.",
            category="performance",
        ),
        BenchmarkMetric(
            name="Model Size (MB)",
            description="Total number of parameters in millions and disk storage size. Smaller models are easier to deploy on edge devices and mobile platforms.",
            category="efficiency",
        ),
        BenchmarkMetric(
            name="Training Time (GPU hours)",
            description="Total training time on ImageNet dataset using 8x V100 GPUs. Measures computational cost and carbon footprint of training.",
            category="efficiency",
        ),
        BenchmarkMetric(
            name="Robustness to Adversarial Attacks",
            description="Accuracy under FGSM and PGD adversarial perturbations with epsilon=8/255. Measures model security and reliability in adversarial settings.",
            category="robustness",
        ),
    ]

    return RankedResults(papers=papers, patents=patents), metrics


def main():
    """Generate a test report with synthetic data."""
    # Create test workspace
    workspace_dir = Path("test_report_output")
    workspace_dir.mkdir(exist_ok=True)

    print("Creating synthetic test data...")
    ranked_results, metrics = create_test_data()

    print(f"  ✓ Created {len(ranked_results.papers)} papers")
    print(f"  ✓ Created {len(ranked_results.patents)} patents")
    print(f"  ✓ Created {len(metrics)} benchmark metrics")

    # Generate report
    topic = "Deep Learning for Computer Vision"
    print(f"\nGenerating report for topic: {topic}")

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
    print("REPORT PREVIEW:")
    print("=" * 80)

    with open(report_path) as f:
        content = f.read()
        print(content[:2000])

    print("\n... (truncated)")
    print("=" * 80)
    print(f"Full report available at: {report_path.absolute()}")

    return 0


if __name__ == "__main__":
    exit(main())
