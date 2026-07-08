"""
LangSmith analytics provider for Research Intelligence Assistant.

Retrieves usage analytics from LangSmith traces when available,
falling back to internal analytics tracker when LangSmith is unavailable.
"""

from __future__ import annotations

import os
from typing import Any, Optional
from datetime import datetime, timedelta

try:
    from langsmith import Client
    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False


class LangSmithAnalyticsProvider:
    """
    Provides analytics data from LangSmith traces with fallback to internal tracker.

    Queries LangSmith API for trace data related to a specific report generation
    and aggregates token usage, LLM calls, costs, and durations.

    Usage:
        provider = LangSmithAnalyticsProvider()
        analytics = await provider.get_analytics_for_report(
            report_id="abc123",
            fallback_analytics=tracker.get_analytics()
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        project_name: Optional[str] = None,
    ):
        """
        Initialize LangSmith analytics provider.

        Args:
            api_key: LangSmith API key (defaults to LANGSMITH_API_KEY or LANGCHAIN_API_KEY env var)
            project_name: LangSmith project name (defaults to LANGSMITH_PROJECT or LANGCHAIN_PROJECT env var)
        """
        # API key priority: LANGSMITH_API_KEY (current) -> LANGCHAIN_API_KEY (legacy)
        self.api_key = (
            api_key or
            os.getenv("LANGSMITH_API_KEY", "").strip() or
            os.getenv("LANGCHAIN_API_KEY", "").strip()
        )

        # Project name priority: LANGSMITH_PROJECT (current) -> LANGCHAIN_PROJECT (legacy)
        self.project_name = (
            project_name or
            os.getenv("LANGSMITH_PROJECT", "").strip() or
            os.getenv("LANGCHAIN_PROJECT", "").strip() or
            "research-intelligence-assistant"
        )

        # Check if LangSmith is enabled and properly configured
        # Tracing priority: LANGSMITH_TRACING (current) -> LANGCHAIN_TRACING_V2 (legacy)
        tracing_enabled = (
            os.getenv("LANGSMITH_TRACING", "false").lower() == "true" or
            os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
        )

        self.enabled = (
            LANGSMITH_AVAILABLE
            and tracing_enabled
            and bool(self.api_key)
        )

        self.client: Optional[Client] = None
        if self.enabled:
            try:
                self.client = Client(api_key=self.api_key)
            except Exception as e:
                print(f"Warning: Failed to initialize LangSmith client: {e}")
                self.enabled = False

    async def get_analytics_for_report(
        self,
        report_id: str,
        fallback_analytics: dict[str, Any],
        topic: str = "",
        max_age_minutes: int = 10,
    ) -> dict[str, Any]:
        """
        Get analytics for a report from LangSmith or fall back to internal tracker.

        Args:
            report_id: Unique identifier for the report generation
            fallback_analytics: Analytics data from internal tracker (as dict or ExecutionAnalytics.to_dict())
            topic: Research topic (used for filtering traces)
            max_age_minutes: Maximum age of traces to consider (default: 10 minutes)

        Returns:
            Analytics dictionary with 'source' field indicating data source:
            - "LangSmith" when data retrieved from LangSmith
            - "Local tracker" when falling back to internal analytics
            - "Local tracker (LangSmith unavailable: <reason>)" with specific failure reason
        """
        # If LangSmith not enabled, return fallback immediately
        if not self.enabled:
            return self._format_fallback_analytics(
                fallback_analytics,
                reason="LangSmith tracing not enabled"
            )

        try:
            # Query LangSmith for traces related to this report
            # Retry a few times since tracing may be asynchronous
            import asyncio

            langsmith_data = None
            max_retries = 3
            retry_delay = 1.0  # seconds

            for attempt in range(max_retries):
                langsmith_data = await self._query_langsmith_traces(
                    report_id=report_id,
                    topic=topic,
                    max_age_minutes=max_age_minutes,
                )

                if langsmith_data:
                    # Successfully retrieved from LangSmith
                    # Merge cache_status and data counts from fallback since LangSmith doesn't track these
                    langsmith_data["cache_status"] = fallback_analytics.get("cache_status", "N/A")
                    langsmith_data["papers_found"] = fallback_analytics.get("papers_found", 0)
                    langsmith_data["patents_found"] = fallback_analytics.get("patents_found", 0)
                    langsmith_data["open_access_papers_found"] = fallback_analytics.get("open_access_papers_found", 0)
                    langsmith_data["cached_items_used"] = fallback_analytics.get("cached_items_used", 0)
                    langsmith_data["fresh_items_fetched"] = fallback_analytics.get("fresh_items_fetched", 0)
                    return langsmith_data

                # If not found and retries remain, wait and try again
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Exponential backoff

            # No traces found after retries
            return self._format_fallback_analytics(
                fallback_analytics,
                reason="No LangSmith traces found for this report"
            )

        except Exception as e:
            # LangSmith query failed
            print(f"Warning: LangSmith analytics retrieval failed: {e}")
            return self._format_fallback_analytics(
                fallback_analytics,
                reason=f"LangSmith query failed: {str(e)}"
            )

    async def _query_langsmith_traces(
        self,
        report_id: str,
        topic: str,
        max_age_minutes: int,
    ) -> Optional[dict[str, Any]]:
        """
        Query LangSmith API for traces related to the report.

        Args:
            report_id: Report identifier to filter traces
            topic: Research topic
            max_age_minutes: Maximum age of traces

        Returns:
            Aggregated analytics dict or None if no traces found
        """
        if not self.client:
            return None

        try:
            # Calculate time window
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(minutes=max_age_minutes)

            # Query runs from LangSmith
            # Filter by project and time range
            # Note: LangSmith filter syntax varies, so we'll filter in-memory if needed
            runs = list(self.client.list_runs(
                project_name=self.project_name,
                start_time=start_time,
                end_time=end_time,
            ))

            # Filter by report_id in memory
            # Metadata is stored in run.extra['metadata'] for our traces
            filtered_runs = []
            for run in runs:
                metadata = {}
                # Try both run.metadata and run.extra['metadata']
                if hasattr(run, 'metadata') and isinstance(run.metadata, dict):
                    metadata = run.metadata
                elif hasattr(run, 'extra') and isinstance(run.extra, dict):
                    metadata = run.extra.get('metadata', {})

                if metadata.get('report_id') == report_id:
                    filtered_runs.append(run)

            if filtered_runs:
                runs = filtered_runs
            else:
                # Try filtering by topic
                topic_runs = []
                for run in runs:
                    metadata = {}
                    if hasattr(run, 'metadata') and isinstance(run.metadata, dict):
                        metadata = run.metadata
                    elif hasattr(run, 'extra') and isinstance(run.extra, dict):
                        metadata = run.extra.get('metadata', {})

                    if metadata.get('topic') == topic:
                        topic_runs.append(run)
                if topic_runs:
                    runs = topic_runs

            if not runs:
                return None

            # Aggregate metrics from all runs
            total_llm_calls = 0
            total_prompt_tokens = 0
            total_completion_tokens = 0
            total_tokens = 0
            estimated_cost = 0.0
            total_duration_seconds = 0.0
            steps_data = []

            # Track unique trace IDs
            trace_ids = set()

            for run in runs:
                # Track trace IDs
                if run.trace_id:
                    trace_ids.add(str(run.trace_id))

                # Count this as an LLM call
                total_llm_calls += 1

                # Aggregate token usage
                # Try multiple sources: run attributes, outputs.usage, or langsmith-computed fields
                prompt_tokens = 0
                completion_tokens = 0
                tokens = 0

                # 1. Check run attributes (set by LangSmith for some integrations)
                if hasattr(run, 'prompt_tokens') and run.prompt_tokens:
                    prompt_tokens = run.prompt_tokens
                if hasattr(run, 'completion_tokens') and run.completion_tokens:
                    completion_tokens = run.completion_tokens
                if hasattr(run, 'total_tokens') and run.total_tokens:
                    tokens = run.total_tokens

                # 2. Check outputs.usage (set by our RunTree)
                if run.outputs and isinstance(run.outputs, dict):
                    usage = run.outputs.get("usage", {})
                    if usage:
                        prompt_tokens = prompt_tokens or usage.get("prompt_tokens", 0)
                        completion_tokens = completion_tokens or usage.get("completion_tokens", 0)
                        tokens = tokens or usage.get("total_tokens", 0)

                # 3. Fall back to computed total
                if not tokens and (prompt_tokens or completion_tokens):
                    tokens = prompt_tokens + completion_tokens

                total_prompt_tokens += prompt_tokens
                total_completion_tokens += completion_tokens
                total_tokens += tokens

                # Aggregate cost if available
                if hasattr(run, "total_cost") and run.total_cost:
                    estimated_cost += float(run.total_cost)

                # Aggregate duration
                if run.end_time and run.start_time:
                    duration = (run.end_time - run.start_time).total_seconds()
                    total_duration_seconds += duration

                    # Estimate per-step cost
                    step_cost = self._estimate_cost(prompt_tokens, completion_tokens)

                    # Track per-step data
                    steps_data.append({
                        "step_name": run.name or "Unknown Step",
                        "duration_seconds": round(duration, 2),
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": tokens,
                        "estimated_cost": round(step_cost, 4),
                        "llm_calls": 1,
                        "metadata": {},
                    })

            # If cost not available from LangSmith, estimate it
            if estimated_cost == 0.0 and total_tokens > 0:
                estimated_cost = self._estimate_cost(
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                )

            # Get first trace URL
            trace_url = None
            if trace_ids:
                first_trace_id = next(iter(trace_ids))
                trace_url = f"https://smith.langchain.com/o/{self.project_name}/projects/p/{self.project_name}/r/{first_trace_id}"

            # Aggregate steps by normalized name
            aggregated_steps = self._aggregate_steps(steps_data)

            # Build analytics dict with LangSmith data
            analytics = {
                "source": "LangSmith",
                "analytics_source": "LangSmith",
                "trace_id": next(iter(trace_ids)) if trace_ids else None,
                "trace_url": trace_url,
                "total_llm_calls": total_llm_calls,
                "total_prompt_tokens": total_prompt_tokens,
                "total_completion_tokens": total_completion_tokens,
                "total_tokens": total_tokens,
                "estimated_total_cost": round(estimated_cost, 4),
                "total_duration_seconds": round(total_duration_seconds, 2) if total_duration_seconds > 0 else None,
                "steps": aggregated_steps,
                # Include metadata
                "langsmith_trace_id": next(iter(trace_ids)) if trace_ids else None,
                "langsmith_trace_url": trace_url,
            }

            return analytics

        except Exception as e:
            # Re-raise to let caller handle the error
            print(f"Error querying LangSmith traces: {e}")
            raise

    def _normalize_step_name(self, step_name: str) -> str:
        """
        Normalize step name to high-level readable label.

        Removes duplicate suffixes (#1, #2, etc.) and maps internal names
        to clean UI labels.

        Args:
            step_name: Raw step name from LangSmith or tracker

        Returns:
            Normalized step name for UI display
        """
        # Remove trailing numbers like #1, #2, #22, etc.
        import re
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
        # Capitalize first letter
        if step_name:
            return step_name[0].upper() + step_name[1:]
        return step_name or 'Other LLM Steps'

    def _aggregate_steps(self, steps_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Aggregate repeated step names into grouped pipeline stages.

        Groups steps by normalized name and combines their metrics.

        Args:
            steps_data: List of individual step data dicts

        Returns:
            List of aggregated step data dicts with combined metrics
        """
        if not steps_data:
            return []

        # Group steps by normalized name
        aggregated: dict[str, dict[str, Any]] = {}

        for step in steps_data:
            normalized_name = self._normalize_step_name(step['step_name'])

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
            agg['duration_seconds'] += step.get('duration_seconds', 0.0)
            agg['prompt_tokens'] += step.get('prompt_tokens', 0)
            agg['completion_tokens'] += step.get('completion_tokens', 0)
            agg['total_tokens'] += step.get('total_tokens', 0)
            agg['estimated_cost'] += step.get('estimated_cost', 0.0)
            agg['llm_calls'] += step.get('llm_calls', 1)

        # Round aggregated values
        for agg in aggregated.values():
            agg['duration_seconds'] = round(agg['duration_seconds'], 2)
            agg['estimated_cost'] = round(agg['estimated_cost'], 4)

        # Sort by duration (longest first)
        result = sorted(aggregated.values(), key=lambda x: x['duration_seconds'], reverse=True)

        return result

    def _estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """
        Estimate cost based on token usage.

        Uses same pricing logic as internal analytics tracker.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Estimated cost in USD
        """
        model = os.getenv("LLM_MODEL", "claude-haiku").lower()

        # Approximate pricing per 1K tokens (same as AnalyticsTracker)
        if "claude-haiku" in model or "haiku" in model:
            pricing = {"prompt": 0.00025, "completion": 0.00125}
        elif "claude-sonnet" in model or "sonnet" in model:
            pricing = {"prompt": 0.003, "completion": 0.015}
        elif "claude-opus" in model or "opus" in model:
            pricing = {"prompt": 0.015, "completion": 0.075}
        elif "gpt-4o-mini" in model:
            pricing = {"prompt": 0.00015, "completion": 0.0006}
        elif "gpt-4o" in model or "gpt-4-turbo" in model:
            pricing = {"prompt": 0.01, "completion": 0.03}
        elif "gpt-4" in model:
            pricing = {"prompt": 0.03, "completion": 0.06}
        elif "gpt-3.5" in model:
            pricing = {"prompt": 0.0005, "completion": 0.0015}
        else:
            pricing = {"prompt": 0.001, "completion": 0.002}

        cost = (
            (prompt_tokens / 1000) * pricing["prompt"] +
            (completion_tokens / 1000) * pricing["completion"]
        )
        return cost

    def _format_fallback_analytics(
        self,
        fallback_analytics: dict[str, Any],
        reason: str = "LangSmith unavailable",
    ) -> dict[str, Any]:
        """
        Format fallback analytics with clear source indication.

        Args:
            fallback_analytics: Internal tracker analytics
            reason: Reason for fallback

        Returns:
            Analytics dict with source field set to indicate fallback
        """
        # Copy analytics to avoid mutating original
        analytics = dict(fallback_analytics)

        # Set source fields
        analytics["source"] = "Local tracker"
        analytics["analytics_source"] = f"Local tracker ({reason})"

        return analytics
