"""
Metric Bank Agent for adaptive metric intelligence.

The Metric Bank Agent learns from user behavior to improve metric suggestions over time.
It tracks which metrics users select, which they add as custom metrics, and which they ignore,
then adapts future suggestions accordingly.

Key responsibilities:
- Track metric usage patterns (selected, custom-added, ignored)
- Promote frequently used metrics
- Deprioritize repeatedly ignored metrics
- Suggest new topic-relevant metrics using LLM
- Merge static/default metrics with learned/adaptive metrics
- Handle duplicate/similar metrics intelligently
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from ria.llm import LLMClient

logger = logging.getLogger(__name__)


class TopicUsageStats(BaseModel):
    """Per-topic usage statistics."""

    selected_count: int = 0
    ignored_count: int = 0
    last_used_at: Optional[str] = None


class MetricUsageData(BaseModel):
    """Usage tracking data for a single metric."""

    metric_name: str
    normalized_name: str
    description: str
    category: str
    source: Literal["default", "chroma", "llm_suggested", "user_custom", "learned"]

    # Topic tracking (for backward compatibility and simple topic list)
    topics_used: list[str] = Field(default_factory=list)

    # Per-topic usage statistics (new, topic-aware learning)
    topic_stats: dict[str, TopicUsageStats] = Field(default_factory=dict)

    # Usage counts (global, for backward compatibility)
    selected_count: int = 0
    rejected_count: int = 0
    custom_added_count: int = 0

    # Timestamps
    last_selected_at: Optional[str] = None
    last_suggested_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    # Scoring
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    priority_score: float = Field(default=0.5, ge=0.0, le=1.0)

    # State
    is_active: bool = True


class MetricSuggestionRequest(BaseModel):
    """Request for generating new metric suggestions via LLM."""

    topic: str
    existing_metrics: list[str]
    max_suggestions: int = Field(default=5, ge=1, le=10)


class LLMMetricSuggestion(BaseModel):
    """LLM-generated metric suggestion."""

    name: str
    description: str
    category: str


class LLMMetricSuggestionsResponse(BaseModel):
    """Response model for LLM metric suggestions."""

    suggestions: list[LLMMetricSuggestion] = Field(
        description="List of new metric suggestions relevant to the topic"
    )


class MetricBankAgent:
    """
    Adaptive Metric Bank Agent for intelligent metric suggestions.

    This agent learns from user behavior to improve metric suggestions over time.
    It tracks selections, custom additions, and rejections, then adapts future
    suggestions to match user preferences and patterns.

    Example:
        agent = MetricBankAgent()
        agent.initialize_defaults()

        # Get smart suggestions
        suggestions = agent.get_smart_suggestions(
            topic="XPBD soft body simulation",
            max_results=10
        )

        # Record user feedback
        agent.record_metric_selected("AI Support", topic="XPBD soft body simulation")
        agent.record_custom_metric_added("AI Capability", topic="XPBD soft body simulation")
        agent.record_metric_ignored("Meshless Method Support", topic="XPBD soft body simulation")
    """

    # Normalization constants
    IGNORE_THRESHOLD = 10  # Deactivate after 10 ignores
    RECENCY_WEIGHT_DAYS = 30  # Weight recent usage more heavily

    def __init__(
        self,
        storage_path: str = "./data/metric_bank_usage.json",
        llm_client: Optional[LLMClient] = None,
        chroma_metrics_bank: Optional[Any] = None,
    ):
        """
        Initialize the Metric Bank Agent.

        Args:
            storage_path: Path to the JSON file for persisting metric usage data
            llm_client: Optional LLM client for generating new metric suggestions
            chroma_metrics_bank: Optional ChromaDB MetricsBank instance to load initial metrics from
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        self.llm = llm_client
        self.metrics: dict[str, MetricUsageData] = {}
        self.chroma_metrics_bank = chroma_metrics_bank

        # Load existing data
        self._load()

        logger.info(f"MetricBankAgent initialized with {len(self.metrics)} metrics")

    def initialize_defaults(self) -> None:
        """
        Initialize with default metrics.

        Priority order:
        1. Load metrics from ChromaDB (if available)
        2. Merge with adaptive usage data from JSON storage
        3. Fall back to hardcoded defaults if ChromaDB is empty

        This ensures we use existing ChromaDB metrics as the foundation,
        then layer adaptive learning on top.
        """
        # First, try to load from ChromaDB
        chroma_loaded = self._load_from_chroma()

        if chroma_loaded > 0:
            logger.info(f"Loaded {chroma_loaded} metrics from ChromaDB")
            # ChromaDB metrics loaded, adaptive data already merged from _load()
            return

        # Fall back to hardcoded defaults only if ChromaDB is empty
        if self.metrics:
            logger.info("Metrics already exist, skipping default initialization")
            return

        default_metrics = [
            {
                "metric_name": "AI Support",
                "description": "Whether the source uses artificial intelligence, machine learning, or neural networks",
                "category": "Technology",
            },
            {
                "metric_name": "GPU Support",
                "description": "Whether the source supports GPU acceleration for parallel computing",
                "category": "Hardware",
            },
            {
                "metric_name": "VR HMD Integration",
                "description": "Whether the source supports Virtual Reality Head-Mounted Displays",
                "category": "Hardware",
            },
            {
                "metric_name": "AR HMD Integration",
                "description": "Whether the source supports Augmented Reality Head-Mounted Displays",
                "category": "Hardware",
            },
            {
                "metric_name": "Haptic Robot Support",
                "description": "Whether the source supports haptic devices or robotic interfaces",
                "category": "Hardware",
            },
            {
                "metric_name": "Surgical Simulation Domain",
                "description": "Whether the source is applicable to surgical training or simulation",
                "category": "Domain",
            },
            {
                "metric_name": "Medical / Clinical Domain",
                "description": "Whether the source has medical or clinical applications",
                "category": "Domain",
            },
            {
                "metric_name": "Real-Time Performance",
                "description": "Whether the source achieves real-time performance (typically >30 FPS)",
                "category": "Performance",
            },
            {
                "metric_name": "Open Access / Public Availability",
                "description": "Whether the source is publicly accessible without subscription",
                "category": "Accessibility",
            },
            {
                "metric_name": "Code or Implementation Availability",
                "description": "Whether source code or implementation is publicly available",
                "category": "Accessibility",
            },
            {
                "metric_name": "Benchmark Validation",
                "description": "Whether the source includes benchmark tests or performance validation",
                "category": "Validation",
            },
            {
                "metric_name": "User Evaluation / Experimental Study",
                "description": "Whether the source includes user studies or experimental validation",
                "category": "Validation",
            },
            {
                "metric_name": "FEM Support",
                "description": "Whether the source uses Finite Element Method",
                "category": "Algorithm",
            },
            {
                "metric_name": "PBD Support",
                "description": "Whether the source uses Position Based Dynamics",
                "category": "Algorithm",
            },
            {
                "metric_name": "XPBD Support",
                "description": "Whether the source uses Extended Position Based Dynamics",
                "category": "Algorithm",
            },
            {
                "metric_name": "Meshless Method Support",
                "description": "Whether the source uses meshless or mesh-free methods",
                "category": "Algorithm",
            },
            {
                "metric_name": "Haptic Feedback",
                "description": "Whether the source provides haptic or force feedback",
                "category": "Interaction",
            },
            {
                "metric_name": "Training / Education Use Case",
                "description": "Whether the source is designed for training or educational purposes",
                "category": "Use Case",
            },
            {
                "metric_name": "Patent / IP Relevance",
                "description": "Whether the source has patent protection or intellectual property claims",
                "category": "Legal",
            },
            {
                "metric_name": "Commercial Product Relevance",
                "description": "Whether the source is a commercial product or has commercial applications",
                "category": "Commercial",
            },
            {
                "metric_name": "Tissue Cutting / Tissue Interaction Support",
                "description": "Whether the source supports tissue cutting or interaction simulation",
                "category": "Feature",
            },
        ]

        for metric_data in default_metrics:
            self._add_or_update_metric(
                metric_name=metric_data["metric_name"],
                description=metric_data["description"],
                category=metric_data["category"],
                source="default",
            )

        self._save()
        logger.info(f"Initialized {len(default_metrics)} default metrics")

    def get_smart_suggestions(
        self,
        topic: str,
        max_results: int = 10,
        include_fresh_llm_suggestions: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get smart metric suggestions based on topic and learned user behavior.

        Strategy:
        1. Query ChromaDB for topic-relevant metrics (semantic similarity)
        2. Score all metrics with topic relevance as primary factor
        3. Add fresh LLM suggestions if enabled
        4. Return top-scored, topic-relevant metrics

        Args:
            topic: Research topic for context
            max_results: Maximum number of suggestions to return
            include_fresh_llm_suggestions: Whether to include new LLM-generated metrics

        Returns:
            List of metric suggestion dictionaries, sorted by relevance
        """
        logger.info(f"Getting smart suggestions for topic: '{topic}'")

        # Step 1: Get topic-relevant metrics from ChromaDB
        chroma_candidates = self._get_chroma_topic_candidates(topic, max_results=max_results * 3)

        logger.info(f"ChromaDB query topic: '{topic}'")
        logger.info(f"Retrieved {len(chroma_candidates)} ChromaDB candidates")
        if chroma_candidates:
            logger.info(f"Top 3 ChromaDB candidates:")
            for i, c in enumerate(chroma_candidates[:3]):
                logger.info(f"  {i+1}. {c['name']}: topic_rel={c.get('topic_relevance_score', 0):.3f}")

        # Step 2: Build topic relevance map from ChromaDB results
        topic_relevance_map = {}
        for candidate in chroma_candidates:
            metric_name = candidate["name"]
            topic_relevance_map[metric_name] = candidate.get("topic_relevance_score", 0.5)

        # Step 3: Score all active metrics
        scored_metrics = []
        for metric in self.metrics.values():
            if not metric.is_active:
                continue

            # Get topic relevance score
            topic_relevance_score = topic_relevance_map.get(metric.metric_name, 0.0)

            # Calculate final score with topic relevance as primary factor
            final_score = self._calculate_metric_score_with_topic(
                metric, topic, topic_relevance_score
            )

            # Log detailed scoring for top candidates (only first 15 to avoid spam)
            if len(scored_metrics) < 15:
                logger.debug(
                    f"Scored: {metric.metric_name}: "
                    f"topic_rel={topic_relevance_score:.3f}, "
                    f"final={final_score:.3f}, "
                    f"selected_count={metric.selected_count}"
                )

            scored_metrics.append({
                "name": metric.metric_name,
                "description": metric.description,
                "category": metric.category,
                "source": metric.source,
                "score": final_score,  # UI backward compatibility
                "topic_relevance_score": topic_relevance_score,
                "final_score": final_score,
                "selected_count": metric.selected_count,
                "custom_added_count": metric.custom_added_count,
                "priority_score": metric.priority_score,
                "reason": self._generate_suggestion_reason(metric, topic),
            })

        # Sort by final score (topic relevance is primary)
        scored_metrics.sort(key=lambda x: x["final_score"], reverse=True)

        # Log top suggestions for debugging
        logger.info(f"Top 10 scored metrics for topic '{topic}':")
        for i, m in enumerate(scored_metrics[:10]):
            logger.info(
                f"  {i+1}. {m['name']}: final={m['final_score']:.3f}, "
                f"topic_rel={m['topic_relevance_score']:.3f}, "
                f"selected={m['selected_count']}, source={m['source']}"
            )

        # Take top results
        top_suggestions = scored_metrics[:max_results]

        # Step 4: Add fresh LLM suggestions if needed
        should_generate_llm = include_fresh_llm_suggestions

        # AUTOMATIC FALLBACK: If ChromaDB has poor coverage for this topic, generate LLM suggestions
        if not should_generate_llm:
            # Check if we have enough high-relevance metrics
            high_relevance_count = sum(1 for m in top_suggestions if m.get('topic_relevance_score', 0) >= 0.5)
            if high_relevance_count < max(3, max_results // 2):
                logger.info(
                    f"Only {high_relevance_count} high-relevance metrics found for '{topic}'. "
                    f"Generating fresh LLM suggestions as fallback."
                )
                should_generate_llm = True

        if should_generate_llm and self.llm:
            try:
                existing_names = [m["name"] for m in top_suggestions]
                llm_suggestions = self._generate_llm_suggestions(
                    topic=topic,
                    existing_metrics=existing_names,
                    max_suggestions=min(5, max_results // 2),  # Increased from 3
                )

                # Merge LLM suggestions with HIGH topic relevance score
                for llm_metric in llm_suggestions:
                    normalized = self._normalize_metric_name(llm_metric["name"])
                    if not any(
                        self._normalize_metric_name(m["name"]) == normalized
                        for m in top_suggestions
                    ):
                        # LLM suggestions for a NEW topic are HIGHLY relevant by definition
                        llm_metric["topic_relevance_score"] = 0.95  # Very high (was 0.9)
                        llm_metric["final_score"] = 0.95 * 0.70  # Use new topic weight formula
                        top_suggestions.append(llm_metric)

                logger.info(f"Added {len(llm_suggestions)} fresh LLM suggestions")

                # Re-sort after adding LLM suggestions
                top_suggestions.sort(key=lambda x: x.get("final_score", 0), reverse=True)

            except Exception as e:
                logger.warning(f"Failed to generate LLM suggestions: {e}")

        # Update last_suggested_at for returned metrics
        now = datetime.utcnow().isoformat()
        for suggestion in top_suggestions[:max_results]:
            metric_name = suggestion["name"]
            if metric_name in self.metrics:
                self.metrics[metric_name].last_suggested_at = now

        self._save()

        return top_suggestions[:max_results]

    def record_metric_selected(self, metric_name: str, topic: str) -> None:
        """
        Record that a user selected a suggested metric.

        Args:
            metric_name: Name of the selected metric
            topic: Research topic context
        """
        normalized = self._normalize_metric_name(metric_name)

        # Find or create metric
        existing = self._find_metric_by_normalized_name(normalized)
        if existing:
            metric = self.metrics[existing]
            metric.selected_count += 1
            now = datetime.utcnow().isoformat()
            metric.last_selected_at = now

            # Add topic if not already tracked
            if topic not in metric.topics_used:
                metric.topics_used.append(topic)

            # Update per-topic statistics
            normalized_topic = self._normalize_topic(topic)
            if normalized_topic not in metric.topic_stats:
                metric.topic_stats[normalized_topic] = TopicUsageStats()
            metric.topic_stats[normalized_topic].selected_count += 1
            metric.topic_stats[normalized_topic].last_used_at = now

            # Increase priority and confidence
            metric.priority_score = min(1.0, metric.priority_score + 0.1)
            metric.confidence_score = min(1.0, metric.confidence_score + 0.05)

            logger.info(
                f"Recorded selection: {metric_name} (global: {metric.selected_count}, "
                f"topic '{normalized_topic}': {metric.topic_stats[normalized_topic].selected_count})"
            )
        else:
            # Metric not found, log warning
            logger.warning(f"Metric not found for selection: {metric_name}")

        self._save()

    def record_custom_metric_added(
        self,
        metric_name: str,
        topic: str,
        description: str = "",
        category: str = "Custom",
    ) -> None:
        """
        Record that a user added a custom metric.

        This is a strong signal - promote similar metrics or create a new learned metric.

        Args:
            metric_name: Name of the custom metric
            topic: Research topic context
            description: Optional description
            category: Optional category (default: Custom)
        """
        normalized = self._normalize_metric_name(metric_name)

        # Check if similar metric exists
        existing = self._find_metric_by_normalized_name(normalized)

        if existing:
            # Similar metric exists - promote it heavily
            metric = self.metrics[existing]
            metric.custom_added_count += 1
            metric.selected_count += 1  # Also count as a selection
            now = datetime.utcnow().isoformat()
            metric.last_selected_at = now

            # Add topic
            if topic not in metric.topics_used:
                metric.topics_used.append(topic)

            # Update per-topic statistics
            normalized_topic = self._normalize_topic(topic)
            if normalized_topic not in metric.topic_stats:
                metric.topic_stats[normalized_topic] = TopicUsageStats()
            metric.topic_stats[normalized_topic].selected_count += 1
            metric.topic_stats[normalized_topic].last_used_at = now

            # Significantly boost priority and confidence
            metric.priority_score = min(1.0, metric.priority_score + 0.2)
            metric.confidence_score = min(1.0, metric.confidence_score + 0.15)

            # If it was user_custom or learned, keep that source
            # If it was default, upgrade to learned
            if metric.source == "default":
                metric.source = "learned"

            logger.info(f"Promoted existing metric: {existing} (custom_added: {metric.custom_added_count})")
        else:
            # Create new learned metric
            self._add_or_update_metric(
                metric_name=metric_name,
                description=description or f"User-defined metric: {metric_name}",
                category=category,
                source="user_custom",
                custom_added_count=1,
                selected_count=1,
                topic=topic,
            )

            logger.info(f"Created new learned metric: {metric_name}")

        self._save()

    def record_metric_ignored(self, metric_name: str, topic: str) -> None:
        """
        Record that a user was shown a metric but did not select it.

        After repeated ignores FOR THE SAME TOPIC, the metric is deprioritized.
        Global ignores are tracked lightly.

        Args:
            metric_name: Name of the ignored metric
            topic: Research topic context
        """
        normalized = self._normalize_metric_name(metric_name)

        existing = self._find_metric_by_normalized_name(normalized)
        if existing:
            metric = self.metrics[existing]
            metric.rejected_count += 1

            # Update per-topic statistics
            normalized_topic = self._normalize_topic(topic)
            if normalized_topic not in metric.topic_stats:
                metric.topic_stats[normalized_topic] = TopicUsageStats()
            metric.topic_stats[normalized_topic].ignored_count += 1

            # Light global penalty (reduced from -0.05 to -0.02)
            metric.priority_score = max(0.0, metric.priority_score - 0.02)

            # Deactivate only if ignored globally too many times
            if metric.rejected_count >= self.IGNORE_THRESHOLD:
                metric.is_active = False
                logger.info(
                    f"Deactivated metric: {metric_name} (globally rejected {metric.rejected_count} times)"
                )
            else:
                logger.debug(
                    f"Recorded ignore: {metric_name} (global: {metric.rejected_count}, "
                    f"topic '{normalized_topic}': {metric.topic_stats[normalized_topic].ignored_count})"
                )

        self._save()

    def record_batch_feedback(
        self,
        selected_metrics: list[str],
        custom_metrics: list[str],
        suggested_metrics: list[str],
        topic: str,
    ) -> None:
        """
        Record batch feedback from a single research session.

        Args:
            selected_metrics: Metrics that were selected from suggestions
            custom_metrics: Metrics that were manually added
            suggested_metrics: All metrics that were suggested
            topic: Research topic context
        """
        logger.info(f"Recording batch feedback for topic: {topic}")

        # Record selections
        for metric in selected_metrics:
            self.record_metric_selected(metric, topic)

        # Record custom additions
        for metric in custom_metrics:
            self.record_custom_metric_added(metric, topic)

        # Record ignores (suggested but not selected)
        # BUT: Don't heavily penalize if user added a similar custom metric
        ignored = [m for m in suggested_metrics if m not in selected_metrics]

        for metric in ignored:
            # Check if any custom metric is similar to this ignored metric
            normalized_ignored = self._normalize_metric_name(metric)

            # If user added a similar custom metric, don't heavily penalize the suggested one
            has_similar_custom = False
            for custom_metric in custom_metrics:
                normalized_custom = self._normalize_metric_name(custom_metric)

                # Check if they share significant overlap
                ignored_words = set(normalized_ignored.split())
                custom_words = set(normalized_custom.split())

                if ignored_words and custom_words:
                    overlap = len(ignored_words & custom_words)
                    min_words = min(len(ignored_words), len(custom_words))

                    # If 50%+ word overlap, consider them similar
                    if overlap >= min_words * 0.5:
                        has_similar_custom = True
                        break

            if not has_similar_custom:
                # Normal ignore penalty
                self.record_metric_ignored(metric, topic)
            else:
                # Light penalty - user showed interest but wanted different wording
                # Just increment rejected_count by 1, but don't decrease priority as much
                normalized = self._normalize_metric_name(metric)
                existing = self._find_metric_by_normalized_name(normalized)
                if existing:
                    metric_obj = self.metrics[existing]
                    metric_obj.rejected_count += 1
                    # Decrease priority less aggressively (only -0.01 instead of -0.05)
                    metric_obj.priority_score = max(0.0, metric_obj.priority_score - 0.01)
                    logger.debug(f"Light penalty for {metric} (user added similar custom metric)")

        self._save()

        logger.info(
            f"Batch feedback: {len(selected_metrics)} selected, "
            f"{len(custom_metrics)} custom, {len(ignored)} ignored"
        )

    def get_metric_by_name(self, metric_name: str) -> Optional[dict[str, Any]]:
        """
        Get a metric by its name.

        Args:
            metric_name: Name of the metric

        Returns:
            Metric dictionary or None if not found
        """
        normalized = self._normalize_metric_name(metric_name)
        existing = self._find_metric_by_normalized_name(normalized)

        if existing:
            metric = self.metrics[existing]
            return {
                "name": metric.metric_name,  # UI expects "name" field
                "description": metric.description,
                "category": metric.category,
                "source": metric.source,
                "score": self._calculate_metric_score(metric, ""),  # Add score for consistency
                "selected_count": metric.selected_count,
                "custom_added_count": metric.custom_added_count,
                "priority_score": metric.priority_score,
                "is_active": metric.is_active,
            }

        return None

    def reactivate_metric(self, metric_name: str) -> bool:
        """
        Reactivate a previously deactivated metric.

        Args:
            metric_name: Name of the metric to reactivate

        Returns:
            True if reactivated, False if not found
        """
        normalized = self._normalize_metric_name(metric_name)
        existing = self._find_metric_by_normalized_name(normalized)

        if existing:
            metric = self.metrics[existing]
            metric.is_active = True
            metric.rejected_count = 0  # Reset reject count
            metric.priority_score = 0.5  # Reset to neutral

            self._save()
            logger.info(f"Reactivated metric: {metric_name}")
            return True

        return False

    def _calculate_metric_score_with_topic(
        self, metric: MetricUsageData, topic: str, topic_relevance_score: float
    ) -> float:
        """
        Calculate final score for a metric with topic relevance as primary factor.

        Formula:
            final_score = 0.55 * topic_relevance_score
                        + 0.25 * adaptive_usage_score
                        + 0.15 * recent_topic_usage_score
                        + 0.05 * freshness_score
                        - topic_specific_penalty
                        - light_global_penalty

        Args:
            metric: Metric usage data
            topic: Current research topic
            topic_relevance_score: Semantic relevance score from ChromaDB (0.0-1.0)

        Returns:
            Final score (0.0-1.0, higher is better)
        """
        import math

        normalized_topic = self._normalize_topic(topic)

        # Initialize penalty
        penalty = 0.0

        # 1. Topic relevance score (70% weight - INCREASED from 55%) - PRIMARY FACTOR
        topic_component = 0.70 * topic_relevance_score

        # Penalty for very low topic relevance (only if metric has no topic-specific history)
        # This prevents globally popular but completely unrelated metrics from ranking high
        if topic_relevance_score < 0.15:  # Very low relevance threshold (reduced from 0.25)
            if normalized_topic not in metric.topic_stats or \
               metric.topic_stats[normalized_topic].selected_count == 0:
                # Apply moderate penalty for very low relevance without topic history
                penalty += 0.20  # Reduced from 0.3

        # 2. Adaptive usage score (15% weight - REDUCED from 25%) - topic-aware learning
        # PRIMARY: Use topic-specific stats
        adaptive_score = 0.0

        if normalized_topic in metric.topic_stats:
            # Strong boost for same/similar topic
            topic_stat = metric.topic_stats[normalized_topic]
            if topic_stat.selected_count > 0:
                adaptive_score = min(1.0, math.log10(topic_stat.selected_count + 1) * 0.5)
        else:
            # FALLBACK: Only use global usage if topics are VERY similar
            if metric.selected_count > 0:
                similar_topic_boost = self._get_similar_topic_boost(metric, topic)
                # Require 60%+ word overlap for cross-topic boost (was: any > 0)
                if similar_topic_boost >= 0.6:
                    # Smaller boost for cross-topic usage (0.15 factor instead of 0.2)
                    adaptive_score = min(0.3, math.log10(metric.selected_count + 1) * 0.15)

        adaptive_component = 0.15 * adaptive_score

        # 3. Recent topic usage score (10% weight - REDUCED from 15%)
        recent_topic_score = 0.0
        if normalized_topic in metric.topic_stats:
            topic_stat = metric.topic_stats[normalized_topic]
            if topic_stat.last_used_at:
                try:
                    last_used = datetime.fromisoformat(topic_stat.last_used_at)
                    days_since = (datetime.utcnow() - last_used).days

                    if days_since < self.RECENCY_WEIGHT_DAYS:
                        recent_topic_score = 1.0 - (days_since / self.RECENCY_WEIGHT_DAYS)
                except Exception:
                    pass

        recent_component = 0.10 * recent_topic_score

        # 4. Freshness score (5% weight) - slight boost for recently suggested
        freshness_score = 0.0
        if metric.last_suggested_at:
            try:
                last_suggested = datetime.fromisoformat(metric.last_suggested_at)
                days_since = (datetime.utcnow() - last_suggested).days

                if days_since < 7:  # Within last week
                    freshness_score = 1.0 - (days_since / 7.0)
            except Exception:
                pass

        freshness_component = 0.05 * freshness_score

        # 5. Topic-specific penalties (already initialized above)
        # Heavy penalty for metrics ignored for THIS topic
        if normalized_topic in metric.topic_stats:
            topic_stat = metric.topic_stats[normalized_topic]
            if topic_stat.ignored_count > 0:
                # Strong topic-specific penalty
                penalty += min(0.3, topic_stat.ignored_count * 0.05)

        # Light penalty for global ignores
        if metric.rejected_count > 0:
            penalty += min(0.1, math.log10(metric.rejected_count + 1) * 0.03)

        final_score = (
            topic_component + adaptive_component + recent_component + freshness_component - penalty
        )

        return max(0.0, min(1.0, final_score))

    def _calculate_metric_score(self, metric: MetricUsageData, topic: str) -> float:
        """
        Legacy scoring method for backward compatibility.
        Uses the new topic-aware scoring with default topic relevance.
        """
        return self._calculate_metric_score_with_topic(metric, topic, topic_relevance_score=0.3)

    def _generate_suggestion_reason(self, metric: MetricUsageData, topic: str) -> str:
        """Generate a human-readable reason for suggesting a metric."""
        reasons = []

        if metric.custom_added_count > 0:
            reasons.append(f"Added {metric.custom_added_count}× as custom metric")

        if metric.selected_count > 5:
            reasons.append(f"Selected {metric.selected_count}× in past sessions")
        elif metric.selected_count > 0:
            reasons.append(f"Used {metric.selected_count}× before")

        if topic in metric.topics_used:
            reasons.append(f"Relevant to '{topic}'")

        if metric.source == "learned":
            reasons.append("Learned from your usage")

        if not reasons:
            reasons.append("Default metric")

        return " • ".join(reasons)

    def _generate_llm_suggestions(
        self,
        topic: str,
        existing_metrics: list[str],
        max_suggestions: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Generate fresh metric suggestions using LLM.

        Args:
            topic: Research topic
            existing_metrics: Metrics already being suggested
            max_suggestions: Maximum number of new suggestions

        Returns:
            List of new metric suggestion dictionaries
        """
        if not self.llm:
            return []

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a research metrics expert. Generate NEW, relevant comparison metrics "
                    "for evaluating research sources on a given topic.\n\n"
                    "Requirements:\n"
                    "- Suggest metrics that are NOT already in the existing metrics list\n"
                    "- Each metric should be specific, measurable, and relevant to the topic\n"
                    "- Cover different dimensions: technology, performance, validation, accessibility, etc.\n"
                    "- Avoid redundancy with existing metrics"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research Topic: {topic}\n\n"
                    f"Existing Metrics (do NOT duplicate these):\n"
                    f"{', '.join(existing_metrics)}\n\n"
                    f"Generate {max_suggestions} NEW metrics that would be valuable for this research topic."
                ),
            },
        ]

        try:
            response = self.llm.chat_json(
                messages=messages,
                response_model=LLMMetricSuggestionsResponse,
                temperature=0.7,
                step_name="Generate Fresh Metrics",
            )

            suggestions = []
            for llm_metric in response.suggestions:
                # Add as llm_suggested metric
                suggestions.append({
                    "name": llm_metric.name,  # UI expects "name"
                    "description": llm_metric.description,
                    "category": llm_metric.category,
                    "source": "llm_suggested",
                    "score": 0.5,  # Add score field for UI
                    "selected_count": 0,
                    "custom_added_count": 0,
                    "priority_score": 0.5,
                    "final_score": 0.5,
                    "reason": "Fresh AI-generated suggestion",
                })

                # Also add to internal storage
                self._add_or_update_metric(
                    metric_name=llm_metric.name,
                    description=llm_metric.description,
                    category=llm_metric.category,
                    source="llm_suggested",
                )

            logger.info(f"Generated {len(suggestions)} LLM suggestions")
            return suggestions

        except Exception as e:
            logger.error(f"Failed to generate LLM suggestions: {e}")
            return []

    def _normalize_topic(self, topic: str) -> str:
        """
        Normalize a topic string for comparison and storage.

        Args:
            topic: Original topic string

        Returns:
            Normalized topic (lowercase, cleaned)
        """
        import re

        normalized = topic.lower().strip()
        normalized = re.sub(r'[^\w\s-]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def _get_similar_topic_boost(self, metric: MetricUsageData, current_topic: str) -> float:
        """
        Calculate boost based on similarity between current topic and past topics.

        Args:
            metric: Metric to check
            current_topic: Current research topic

        Returns:
            Boost factor (0.0-1.0)
        """
        if not metric.topics_used:
            return 0.0

        current_words = set(self._normalize_topic(current_topic).split())
        if not current_words:
            return 0.0

        max_similarity = 0.0
        for past_topic in metric.topics_used:
            past_words = set(self._normalize_topic(past_topic).split())
            if not past_words:
                continue

            # Jaccard similarity
            intersection = len(current_words & past_words)
            union = len(current_words | past_words)

            if union > 0:
                similarity = intersection / union
                max_similarity = max(max_similarity, similarity)

        return max_similarity

    def _get_chroma_topic_candidates(
        self, topic: str, max_results: int = 30
    ) -> list[dict[str, Any]]:
        """
        Query ChromaDB for topic-relevant metrics.

        Args:
            topic: Research topic
            max_results: Maximum number of candidates to retrieve

        Returns:
            List of candidate metrics with topic_relevance_score
        """
        if not self.chroma_metrics_bank:
            logger.debug("No ChromaDB metrics bank available")
            return []

        try:
            from ria.metrics_bank import MetricsBank

            if not isinstance(self.chroma_metrics_bank, MetricsBank):
                logger.warning("Invalid ChromaDB metrics bank instance")
                return []

            # Query ChromaDB with the topic
            chroma_results = self.chroma_metrics_bank.collection.query(
                query_texts=[topic], n_results=min(max_results, self.chroma_metrics_bank.collection.count())
            )

            if not chroma_results["ids"] or not chroma_results["ids"][0]:
                logger.warning("No ChromaDB results for topic")
                return []

            candidates = []
            for i, metric_id in enumerate(chroma_results["ids"][0]):
                metadata = chroma_results["metadatas"][0][i]
                distance = chroma_results["distances"][0][i] if "distances" in chroma_results else 1.0

                # Convert distance to similarity score (ChromaDB uses cosine distance)
                # Distance typically ranges from 0.0 (identical) to 2.0 (opposite)
                # Convert to 0.0-1.0 similarity score
                similarity = max(0.0, 1.0 - (distance / 2.0))

                candidates.append({
                    "metric_id": metric_id,
                    "name": metadata["name"],
                    "description": metadata["description"],
                    "category": metadata.get("category", "General"),
                    "source": "chroma",
                    "topic_relevance_score": similarity,
                })

            logger.info(
                f"ChromaDB returned {len(candidates)} candidates, "
                f"top score: {candidates[0]['topic_relevance_score']:.3f}"
            )

            return candidates

        except Exception as e:
            logger.error(f"Failed to query ChromaDB for topic candidates: {e}")
            import traceback

            traceback.print_exc()
            return []

    def _normalize_metric_name(self, name: str) -> str:
        """
        Normalize a metric name for comparison.

        Args:
            name: Original metric name

        Returns:
            Normalized name (lowercase, no punctuation, standardized spaces)
        """
        import re

        # Lowercase
        normalized = name.lower()

        # Common synonym mappings (apply before removing punctuation)
        synonym_map = {
            "artificial intelligence": "ai",
            "machine learning": "ml",
            "deep learning": "dl",
            "virtual reality": "vr",
            "augmented reality": "ar",
            "head mounted display": "hmd",
            "head-mounted display": "hmd",
        }

        for full, short in synonym_map.items():
            normalized = normalized.replace(full, short)

        # Replace punctuation with spaces (preserves word boundaries)
        normalized = re.sub(r'[^\w\s]', ' ', normalized)

        # Remove extra spaces
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized

    def _find_metric_by_normalized_name(self, normalized: str) -> Optional[str]:
        """
        Find a metric by its normalized name with fuzzy matching.

        Checks for exact match first, then checks for very similar metrics
        where all words from one are contained in the other.

        Args:
            normalized: Normalized metric name

        Returns:
            Original metric name (key) or None if not found
        """
        # First: exact match
        for key, metric in self.metrics.items():
            if metric.normalized_name == normalized:
                return key

        # Second: Check if one is a subset of the other (handles "AI" <-> "AI Support")
        # Only match if ALL words from shorter name appear in longer name
        normalized_words = set(normalized.split())

        for key, metric in self.metrics.items():
            existing_words = set(metric.normalized_name.split())

            # Check if all words from one are in the other
            if normalized_words and existing_words:
                # If normalized is subset of existing, or vice versa
                if normalized_words.issubset(existing_words) or existing_words.issubset(normalized_words):
                    return key

        return None

    def _add_or_update_metric(
        self,
        metric_name: str,
        description: str,
        category: str,
        source: Literal["default", "chroma", "llm_suggested", "user_custom", "learned"],
        selected_count: int = 0,
        custom_added_count: int = 0,
        topic: Optional[str] = None,
    ) -> None:
        """
        Add a new metric or update an existing one.

        Args:
            metric_name: Metric name
            description: Metric description
            category: Metric category
            source: Source type
            selected_count: Initial selected count
            custom_added_count: Initial custom added count
            topic: Optional topic to add to topics_used
        """
        normalized = self._normalize_metric_name(metric_name)

        # Check if already exists
        existing = self._find_metric_by_normalized_name(normalized)

        if existing:
            # Update existing
            metric = self.metrics[existing]
            metric.description = description  # Update description
            metric.category = category
            metric.selected_count += selected_count
            metric.custom_added_count += custom_added_count

            if topic and topic not in metric.topics_used:
                metric.topics_used.append(topic)
        else:
            # Create new
            now = datetime.utcnow().isoformat()

            topics_used = []
            if topic:
                topics_used.append(topic)

            last_selected_at = now if selected_count > 0 or custom_added_count > 0 else None

            metric = MetricUsageData(
                metric_name=metric_name,
                normalized_name=normalized,
                description=description,
                category=category,
                source=source,
                topics_used=topics_used,
                selected_count=selected_count,
                custom_added_count=custom_added_count,
                last_selected_at=last_selected_at,
                created_at=now,
            )

            self.metrics[metric_name] = metric

    def _load_from_chroma(self) -> int:
        """
        Load metrics from ChromaDB MetricsBank.

        Converts ChromaDB metrics into MetricUsageData records and merges
        with existing adaptive data from JSON storage.

        Returns:
            Number of metrics loaded from ChromaDB
        """
        if not self.chroma_metrics_bank:
            logger.debug("No ChromaDB metrics bank provided")
            return 0

        try:
            # Get all metrics from ChromaDB
            # We'll query with a generic term to get all metrics
            from ria.metrics_bank import MetricsBank

            if not isinstance(self.chroma_metrics_bank, MetricsBank):
                logger.warning("Invalid ChromaDB metrics bank instance")
                return 0

            # Get collection count
            collection = self.chroma_metrics_bank.collection
            total_count = collection.count()

            if total_count == 0:
                logger.info("ChromaDB metrics bank is empty")
                return 0

            # Get all metrics (ChromaDB query with empty string or generic term)
            # We'll use a broad query to get all metrics
            all_chroma_metrics = self.chroma_metrics_bank.suggest_metrics(
                topic="research technology hardware performance validation",
                max_results=total_count,
            )

            logger.info(f"Found {len(all_chroma_metrics)} metrics in ChromaDB")

            loaded_count = 0
            for chroma_metric in all_chroma_metrics:
                metric_name = chroma_metric["name"]
                normalized = self._normalize_metric_name(metric_name)

                # Check if we already have adaptive data for this metric
                existing = self._find_metric_by_normalized_name(normalized)

                if existing:
                    # Merge: keep adaptive data, update description if ChromaDB is better
                    existing_metric = self.metrics[existing]
                    # Prefer ChromaDB description if it's more detailed
                    if len(chroma_metric["description"]) > len(existing_metric.description):
                        existing_metric.description = chroma_metric["description"]
                    # Keep category from ChromaDB
                    existing_metric.category = chroma_metric.get("category", existing_metric.category)
                    logger.debug(f"Merged ChromaDB metric with existing: {metric_name}")
                else:
                    # Create new metric from ChromaDB data
                    self._add_or_update_metric(
                        metric_name=metric_name,
                        description=chroma_metric["description"],
                        category=chroma_metric.get("category", "General"),
                        source="chroma",  # Mark as coming from ChromaDB
                        selected_count=chroma_metric.get("usage_count", 0),
                        custom_added_count=0,
                        topic=None,
                    )
                    loaded_count += 1
                    logger.debug(f"Added ChromaDB metric: {metric_name}")

            logger.info(f"Loaded {loaded_count} new metrics from ChromaDB, merged {len(all_chroma_metrics) - loaded_count} existing")
            return loaded_count

        except Exception as e:
            logger.error(f"Failed to load metrics from ChromaDB: {e}")
            import traceback
            traceback.print_exc()
            return 0

    def _load(self) -> None:
        """Load metric usage data from storage."""
        if not self.storage_path.exists():
            logger.info("No existing metric usage data found")
            return

        try:
            # Check if file is empty or invalid
            file_size = self.storage_path.stat().st_size
            if file_size == 0:
                logger.info("Metric usage data file is empty, initializing fresh")
                self.metrics = {}
                return

            with open(self.storage_path, "r", encoding="utf-8") as f:
                content = f.read().strip()

                # Handle empty content
                if not content:
                    logger.info("Metric usage data file is empty, initializing fresh")
                    self.metrics = {}
                    return

                # Parse JSON
                data = json.loads(content)

                # Validate it's a dict
                if not isinstance(data, dict):
                    logger.warning("Metric usage data is not a dictionary, initializing fresh")
                    self.metrics = {}
                    return

            # Load metrics with backward compatibility
            self.metrics = {}
            for key, value in data.items():
                # Ensure topic_stats exists (backward compatibility)
                if "topic_stats" not in value:
                    value["topic_stats"] = {}

                try:
                    self.metrics[key] = MetricUsageData.model_validate(value)
                except Exception as e:
                    logger.warning(f"Failed to load metric {key}: {e}. Skipping.")
                    continue

            logger.info(f"Loaded {len(self.metrics)} metrics from adaptive storage")
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in metric usage data: {e}. Initializing fresh.")
            self.metrics = {}
        except Exception as e:
            logger.error(f"Failed to load metric usage data: {e}. Initializing fresh.")
            self.metrics = {}

    def _save(self) -> None:
        """Save metric usage data to storage."""
        try:
            data = {
                key: value.model_dump()
                for key, value in self.metrics.items()
            }

            with open(self.storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.debug(f"Saved {len(self.metrics)} metrics to storage")
        except Exception as e:
            logger.error(f"Failed to save metric usage data: {e}")
