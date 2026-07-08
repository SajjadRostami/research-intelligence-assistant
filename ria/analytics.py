"""
Execution analytics and metrics tracking for the Research Intelligence Assistant.

Tracks execution time, LLM token usage, costs, and pipeline steps for observability
and reporting. Supports optional LangSmith integration.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class StepMetrics:
    """Metrics for a single pipeline step."""
    step_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_seconds: Optional[float] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost: float = 0.0
    llm_calls: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self) -> None:
        """Mark step as finished and calculate duration."""
        self.end_time = time.time()
        self.duration_seconds = self.end_time - self.start_time


@dataclass
class ExecutionAnalytics:
    """Complete execution analytics for a research pipeline run."""
    topic: str
    start_time: float
    end_time: Optional[float] = None
    total_duration_seconds: Optional[float] = None

    # Overall metrics
    total_llm_calls: int = 0
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_tokens: int = 0
    estimated_total_cost: float = 0.0

    # Cache and data metrics
    cache_status: str = "unknown"
    cached_items_used: int = 0
    fresh_items_fetched: int = 0
    papers_found: int = 0
    patents_found: int = 0
    open_access_papers_found: int = 0

    # Step breakdown
    steps: list[StepMetrics] = field(default_factory=list)

    # LangSmith integration
    langsmith_trace_id: Optional[str] = None
    langsmith_trace_url: Optional[str] = None

    def finish(self) -> None:
        """Mark execution as finished and calculate total duration."""
        self.end_time = time.time()
        self.total_duration_seconds = self.end_time - self.start_time

    def _normalize_step_name(self, step_name: str) -> str:
        """
        Normalize step name to high-level readable label.

        Removes duplicate suffixes (#1, #2, etc.) and maps internal names
        to clean UI labels.
        """
        import re
        # Remove trailing numbers like #1, #2, #22, etc.
        step_name = re.sub(r'\s*#\d+$', '', step_name)

        # Map common internal names to readable labels
        name_mappings = {
            'llm_chat_json': 'Other LLM Steps',
            'llm_chat': 'Other LLM Steps',
            'Comparison Matrix Generation': 'Comparison Matrix',
            'comparison_matrix_generation': 'Comparison Matrix',
            'matrix_validation': 'Matrix Validation',
            'result_ranking': 'Result Ranking',
            'metric_suggestion': 'Metric Suggestion',
            'executive_summary': 'Executive Summary',
            'report_generation': 'Report Generation',
        }

        # Check exact match first (case-insensitive)
        step_lower = step_name.lower()
        for key, value in name_mappings.items():
            if step_lower == key.lower():
                return value

        # Check if any mapping key is contained in the step name
        for key, value in name_mappings.items():
            if key.lower() in step_lower:
                return value

        # Return cleaned name if no mapping found
        if step_name:
            return step_name[0].upper() + step_name[1:]
        return step_name or 'Other LLM Steps'

    def _aggregate_steps(self) -> list[dict[str, Any]]:
        """
        Aggregate repeated step names into grouped pipeline stages.

        Groups steps by normalized name and combines their metrics.
        """
        if not self.steps:
            return []

        # Group steps by normalized name
        aggregated: dict[str, dict[str, Any]] = {}

        for step in self.steps:
            normalized_name = self._normalize_step_name(step.step_name)

            if normalized_name not in aggregated:
                # Initialize aggregate for this step
                aggregated[normalized_name] = {
                    'step_name': normalized_name,
                    'duration_seconds': 0.0,
                    'prompt_tokens': 0,
                    'completion_tokens': 0,
                    'total_tokens': 0,
                    'estimated_cost': 0.0,
                    'llm_calls': 0,
                    'metadata': {},
                }

            # Accumulate metrics
            agg = aggregated[normalized_name]
            agg['duration_seconds'] += step.duration_seconds or 0.0
            agg['prompt_tokens'] += step.prompt_tokens
            agg['completion_tokens'] += step.completion_tokens
            agg['total_tokens'] += step.total_tokens
            agg['estimated_cost'] += step.estimated_cost
            agg['llm_calls'] += step.llm_calls

        # Round aggregated values
        for agg in aggregated.values():
            agg['duration_seconds'] = round(agg['duration_seconds'], 2)
            agg['estimated_cost'] = round(agg['estimated_cost'], 4)

        # Sort by duration (longest first)
        result = sorted(aggregated.values(), key=lambda x: x['duration_seconds'], reverse=True)

        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "topic": self.topic,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "total_duration_seconds": round(self.total_duration_seconds, 2) if self.total_duration_seconds else None,
            "total_llm_calls": self.total_llm_calls,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_total_cost": round(self.estimated_total_cost, 4),
            "cache_status": self.cache_status,
            "cached_items_used": self.cached_items_used,
            "fresh_items_fetched": self.fresh_items_fetched,
            "papers_found": self.papers_found,
            "patents_found": self.patents_found,
            "open_access_papers_found": self.open_access_papers_found,
            "steps": self._aggregate_steps(),
            "langsmith_trace_id": self.langsmith_trace_id,
            "langsmith_trace_url": self.langsmith_trace_url,
        }

    def get_workflow_steps(self) -> list[dict[str, Any]]:
        """Get workflow steps for visualization."""
        return [
            {
                "name": step.step_name,
                "status": "completed" if step.end_time else "in_progress",
                "duration": round(step.duration_seconds, 2) if step.duration_seconds else None,
                "tokens": step.total_tokens,
                "cost": round(step.estimated_cost, 4),
                "llm_calls": step.llm_calls,
            }
            for step in self.steps
        ]


class AnalyticsTracker:
    """
    Tracks execution analytics for a single pipeline run.

    IMPORTANT: Each tracker instance is for ONE request/generation only.
    A new tracker is created at the start of each /generate request,
    so analytics never accumulate across multiple reports.

    Usage:
        tracker = AnalyticsTracker(topic="AI Safety")
        tracker.start_step("Fetch Papers")
        # ... do work ...
        tracker.add_llm_call(prompt_tokens=100, completion_tokens=50)
        tracker.finish_step()
        tracker.finish()
        analytics = tracker.get_analytics()
    """

    def __init__(self, topic: str):
        """
        Initialize tracker for a new pipeline run.

        Creates a fresh analytics object with start_time = now.
        Does not reuse or accumulate from previous runs.
        """
        self.analytics = ExecutionAnalytics(
            topic=topic,
            start_time=time.time(),
        )
        self.current_step: Optional[StepMetrics] = None

        # Token pricing (approximate, in USD per 1K tokens)
        # These are rough estimates; adjust based on actual model pricing
        self.pricing = self._get_pricing()

    def _get_pricing(self) -> dict[str, dict[str, float]]:
        """Get token pricing based on model."""
        model = os.getenv("LLM_MODEL", "claude-haiku").lower()

        # Approximate pricing per 1K tokens
        if "claude-haiku" in model or "haiku" in model:
            return {"prompt": 0.00025, "completion": 0.00125}
        elif "claude-sonnet" in model or "sonnet" in model:
            return {"prompt": 0.003, "completion": 0.015}
        elif "claude-opus" in model or "opus" in model:
            return {"prompt": 0.015, "completion": 0.075}
        elif "gpt-4o-mini" in model:
            return {"prompt": 0.00015, "completion": 0.0006}
        elif "gpt-4o" in model or "gpt-4-turbo" in model:
            return {"prompt": 0.01, "completion": 0.03}
        elif "gpt-4" in model:
            return {"prompt": 0.03, "completion": 0.06}
        elif "gpt-3.5" in model:
            return {"prompt": 0.0005, "completion": 0.0015}
        else:
            # Default conservative pricing
            return {"prompt": 0.001, "completion": 0.002}

    def start_step(self, step_name: str, metadata: Optional[dict[str, Any]] = None) -> None:
        """Start tracking a new pipeline step."""
        if self.current_step:
            # Auto-finish previous step if not finished
            self.finish_step()

        self.current_step = StepMetrics(
            step_name=step_name,
            start_time=time.time(),
            metadata=metadata or {},
        )

    def finish_step(self) -> None:
        """Finish the current step and add to analytics."""
        if self.current_step:
            self.current_step.finish()
            self.analytics.steps.append(self.current_step)
            self.current_step = None

    def add_llm_call(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        step_name: Optional[str] = None,
    ) -> None:
        """
        Record an LLM call with token usage.

        Args:
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            step_name: Optional step name if not in an active step
        """
        total_tokens = prompt_tokens + completion_tokens
        cost = (
            (prompt_tokens / 1000) * self.pricing["prompt"] +
            (completion_tokens / 1000) * self.pricing["completion"]
        )

        # Update overall analytics
        self.analytics.total_llm_calls += 1
        self.analytics.total_prompt_tokens += prompt_tokens
        self.analytics.total_completion_tokens += completion_tokens
        self.analytics.total_tokens += total_tokens
        self.analytics.estimated_total_cost += cost

        # Update current step if active
        if self.current_step:
            self.current_step.llm_calls += 1
            self.current_step.prompt_tokens += prompt_tokens
            self.current_step.completion_tokens += completion_tokens
            self.current_step.total_tokens += total_tokens
            self.current_step.estimated_cost += cost
        elif step_name:
            # Create a step on-the-fly if step_name provided
            self.start_step(step_name)
            self.current_step.llm_calls += 1
            self.current_step.prompt_tokens += prompt_tokens
            self.current_step.completion_tokens += completion_tokens
            self.current_step.total_tokens += total_tokens
            self.current_step.estimated_cost += cost
            self.finish_step()

    def set_cache_status(self, status: str, cached_count: int = 0, fresh_count: int = 0) -> None:
        """Record cache usage status."""
        self.analytics.cache_status = status
        self.analytics.cached_items_used = cached_count
        self.analytics.fresh_items_fetched = fresh_count

    def set_data_counts(
        self,
        papers: int = 0,
        patents: int = 0,
        open_access_papers: int = 0,
    ) -> None:
        """Record data collection counts."""
        self.analytics.papers_found = papers
        self.analytics.patents_found = patents
        self.analytics.open_access_papers_found = open_access_papers

    def set_langsmith_trace(self, trace_id: str, trace_url: Optional[str] = None) -> None:
        """Record LangSmith trace information."""
        self.analytics.langsmith_trace_id = trace_id
        self.analytics.langsmith_trace_url = trace_url

    def finish(self) -> None:
        """Finish tracking execution."""
        if self.current_step:
            self.finish_step()
        self.analytics.finish()

    def get_analytics(self) -> ExecutionAnalytics:
        """Get the complete analytics data."""
        return self.analytics
