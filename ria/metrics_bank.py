"""
ChromaDB-based metric bank for storing and retrieving comparison metrics.

The MetricsBank provides persistent storage for metrics with embeddings-based
similarity search to suggest relevant metrics based on research topics.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    raise ImportError(
        "ChromaDB is required for metrics bank. Install with: pip install chromadb"
    )


class MetricsBank:
    """
    Persistent metric storage with ChromaDB for similarity-based retrieval.

    Stores metrics with embeddings and metadata for intelligent suggestions
    based on research topics. Tracks usage and supports custom metrics.

    Example:
        bank = MetricsBank()
        bank.initialize_defaults()
        suggestions = bank.suggest_metrics("XPBD simulation", max_results=10)
    """

    def __init__(self, persist_directory: str = "./chroma_db/metrics"):
        """
        Initialize the metrics bank with ChromaDB.

        Args:
            persist_directory: Directory for ChromaDB persistence
        """
        self.persist_dir = Path(persist_directory)
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False)
        )

        self.collection = self.client.get_or_create_collection(
            name="metric_bank",
            metadata={"description": "Research comparison metrics"}
        )

    def add_metric(
        self,
        metric_id: str,
        name: str,
        description: str,
        category: str,
        examples: list[str] | None = None,
        source: str = "default",
        usage_count: int = 0,
    ) -> None:
        """
        Add a metric to the bank.

        Args:
            metric_id: Unique identifier for the metric
            name: Display name of the metric
            description: Detailed description
            category: Category (Algorithm, Hardware, Performance, etc.)
            examples: Example use cases or topics
            source: Metric source (default, user, generated)
            usage_count: Number of times this metric has been used
        """
        document = f"{name}. {description}. Category: {category}."
        if examples:
            document += f" Examples: {', '.join(examples)}"

        metadata = {
            "name": name,
            "description": description,
            "category": category,
            "source": source,
            "usage_count": usage_count,
            "created_at": datetime.utcnow().isoformat(),
            "examples": json.dumps(examples or []),
        }

        self.collection.add(
            documents=[document],
            metadatas=[metadata],
            ids=[metric_id]
        )

    def suggest_metrics(
        self,
        topic: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Suggest relevant metrics for a research topic.

        Uses ChromaDB similarity search to find metrics most relevant
        to the given topic based on embeddings.

        Args:
            topic: Research topic string
            max_results: Maximum number of metrics to suggest

        Returns:
            List of metric dictionaries with name, description, category, reason
        """
        # Query ChromaDB for similar metrics
        results = self.collection.query(
            query_texts=[topic],
            n_results=min(max_results, self.collection.count()),
        )

        if not results["ids"] or not results["ids"][0]:
            return []

        suggestions = []
        for i, metric_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]
            distance = results["distances"][0][i] if "distances" in results else None

            suggestions.append({
                "metric_id": metric_id,
                "name": metadata["name"],
                "description": metadata["description"],
                "category": metadata["category"],
                "source": metadata.get("source", "default"),
                "usage_count": metadata.get("usage_count", 0),
                "reason": f"Relevant to '{topic}' (similarity score: {1.0 - distance:.2f})" if distance else "Relevant",
            })

        # Sort by usage_count to prioritize frequently used metrics
        suggestions.sort(key=lambda x: x["usage_count"], reverse=True)

        return suggestions

    def increment_usage(self, metric_id: str) -> None:
        """
        Increment the usage count for a metric.

        Args:
            metric_id: ID of the metric to increment
        """
        try:
            result = self.collection.get(ids=[metric_id])
            if result["ids"]:
                metadata = result["metadatas"][0]
                current_count = metadata.get("usage_count", 0)
                metadata["usage_count"] = current_count + 1

                # Update the metric with new usage count
                self.collection.update(
                    ids=[metric_id],
                    metadatas=[metadata]
                )
        except Exception:
            # Silently fail if metric doesn't exist
            pass

    def get_metric(self, metric_id: str) -> dict[str, Any] | None:
        """
        Retrieve a specific metric by ID.

        Args:
            metric_id: ID of the metric to retrieve

        Returns:
            Metric dictionary or None if not found
        """
        result = self.collection.get(ids=[metric_id])
        if not result["ids"]:
            return None

        metadata = result["metadatas"][0]
        return {
            "metric_id": metric_id,
            "name": metadata["name"],
            "description": metadata["description"],
            "category": metadata["category"],
            "source": metadata.get("source", "default"),
            "usage_count": metadata.get("usage_count", 0),
            "examples": json.loads(metadata.get("examples", "[]")),
        }

    def initialize_defaults(self) -> None:
        """
        Initialize the bank with default metrics if empty.

        Adds a comprehensive set of default metrics covering common
        research evaluation dimensions.
        """
        if self.collection.count() > 0:
            return

        default_metrics = [
            {
                "metric_id": "ai_support",
                "name": "AI Support",
                "description": "Whether the source uses artificial intelligence, machine learning, or neural networks",
                "category": "Technology",
                "examples": ["machine learning", "neural networks", "AI"],
            },
            {
                "metric_id": "gpu_support",
                "name": "GPU Support",
                "description": "Whether the source supports GPU acceleration for parallel computing",
                "category": "Hardware",
                "examples": ["CUDA", "GPU", "parallel computing"],
            },
            {
                "metric_id": "vr_hmd",
                "name": "VR HMD Integration",
                "description": "Whether the source supports Virtual Reality Head-Mounted Displays",
                "category": "Hardware",
                "examples": ["VR", "head-mounted display", "Oculus", "HTC Vive"],
            },
            {
                "metric_id": "ar_hmd",
                "name": "AR HMD Integration",
                "description": "Whether the source supports Augmented Reality Head-Mounted Displays",
                "category": "Hardware",
                "examples": ["AR", "HoloLens", "Magic Leap", "augmented reality"],
            },
            {
                "metric_id": "haptic_robot",
                "name": "Haptic Robot Support",
                "description": "Whether the source supports haptic devices or robotic interfaces",
                "category": "Hardware",
                "examples": ["haptic", "force feedback", "robotic interface"],
            },
            {
                "metric_id": "surgical_simulation",
                "name": "Surgical Simulation Domain",
                "description": "Whether the source is applicable to surgical training or simulation",
                "category": "Domain",
                "examples": ["surgery", "surgical training", "medical simulation"],
            },
            {
                "metric_id": "medical_clinical",
                "name": "Medical / Clinical Domain",
                "description": "Whether the source has medical or clinical applications",
                "category": "Domain",
                "examples": ["medical", "clinical", "healthcare", "diagnosis"],
            },
            {
                "metric_id": "real_time",
                "name": "Real-Time Performance",
                "description": "Whether the source achieves real-time performance (typically >30 FPS)",
                "category": "Performance",
                "examples": ["real-time", "interactive", "30 FPS", "60 FPS"],
            },
            {
                "metric_id": "open_access",
                "name": "Open Access / Public Availability",
                "description": "Whether the source is publicly accessible without subscription",
                "category": "Accessibility",
                "examples": ["open access", "public", "free"],
            },
            {
                "metric_id": "code_available",
                "name": "Code or Implementation Availability",
                "description": "Whether source code or implementation is publicly available",
                "category": "Accessibility",
                "examples": ["GitHub", "source code", "implementation", "open source"],
            },
            {
                "metric_id": "benchmark_validation",
                "name": "Benchmark Validation",
                "description": "Whether the source includes benchmark tests or performance validation",
                "category": "Validation",
                "examples": ["benchmark", "performance test", "validation"],
            },
            {
                "metric_id": "user_evaluation",
                "name": "User Evaluation / Experimental Study",
                "description": "Whether the source includes user studies or experimental validation",
                "category": "Validation",
                "examples": ["user study", "experiment", "evaluation", "user testing"],
            },
            {
                "metric_id": "fem_support",
                "name": "FEM Support",
                "description": "Whether the source uses Finite Element Method",
                "category": "Algorithm",
                "examples": ["FEM", "finite element", "finite element method"],
            },
            {
                "metric_id": "pbd_support",
                "name": "PBD Support",
                "description": "Whether the source uses Position Based Dynamics",
                "category": "Algorithm",
                "examples": ["PBD", "position based dynamics"],
            },
            {
                "metric_id": "xpbd_support",
                "name": "XPBD Support",
                "description": "Whether the source uses Extended Position Based Dynamics",
                "category": "Algorithm",
                "examples": ["XPBD", "extended position based dynamics"],
            },
            {
                "metric_id": "meshless_method",
                "name": "Meshless Method Support",
                "description": "Whether the source uses meshless or mesh-free methods",
                "category": "Algorithm",
                "examples": ["meshless", "mesh-free", "SPH", "particle-based"],
            },
            {
                "metric_id": "haptic_feedback",
                "name": "Haptic Feedback",
                "description": "Whether the source provides haptic or force feedback",
                "category": "Interaction",
                "examples": ["haptic feedback", "force feedback", "tactile"],
            },
            {
                "metric_id": "training_education",
                "name": "Training / Education Use Case",
                "description": "Whether the source is designed for training or educational purposes",
                "category": "Use Case",
                "examples": ["training", "education", "learning", "teaching"],
            },
            {
                "metric_id": "patent_ip",
                "name": "Patent / IP Relevance",
                "description": "Whether the source has patent protection or intellectual property claims",
                "category": "Legal",
                "examples": ["patent", "IP", "intellectual property"],
            },
            {
                "metric_id": "commercial_product",
                "name": "Commercial Product Relevance",
                "description": "Whether the source is a commercial product or has commercial applications",
                "category": "Commercial",
                "examples": ["commercial", "product", "market"],
            },
            {
                "metric_id": "tissue_cutting",
                "name": "Tissue Cutting / Tissue Interaction Support",
                "description": "Whether the source supports tissue cutting or interaction simulation",
                "category": "Feature",
                "examples": ["tissue cutting", "tissue interaction", "deformable tissue"],
            },
        ]

        for metric in default_metrics:
            self.add_metric(**metric)
