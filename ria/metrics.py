"""
Metrics generation for benchmark creation.

The MetricsGenerator creates relevant benchmark metrics based on a research topic
and the top-ranked patents and papers. It uses LLM analysis to generate 5-10
metrics that are appropriate for evaluating the sources.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ria.llm import LLMClient
from ria.models import BenchmarkMetric, ScoredSourceItem
from ria.workspace import WorkspaceManager


class MetricCategory(BaseModel):
    """Category classification for a metric."""
    name: str = Field(description="Metric name")
    description: str = Field(description="Detailed description of what the metric measures")
    category: str = Field(
        description="Category: performance, accuracy, usability, hardware, efficiency, scalability, cost, safety, etc."
    )


class MetricsListResponse(BaseModel):
    """Response model for generated metrics list."""
    metrics: list[MetricCategory] = Field(
        min_length=5,
        max_length=10,
        description="List of 5-10 relevant benchmark metrics"
    )


class MetricsGenerator:
    """
    Generator for benchmark metrics using LLM analysis.

    Analyzes the research topic and top-ranked sources to generate
    5-10 relevant benchmark metrics that can be used to evaluate
    the sources against each other.

    Example:
        generator = MetricsGenerator(llm_client)
        metrics = generator.generate(
            topic="XPBD simulation",
            papers=top_papers,
            patents=top_patents
        )
    """

    def __init__(self, llm_client: LLMClient):
        """
        Initialize the metrics generator.

        Args:
            llm_client: LLM client for generating metrics
        """
        self.llm = llm_client

    def generate(
        self,
        topic: str,
        papers: list[ScoredSourceItem],
        patents: list[ScoredSourceItem],
    ) -> list[BenchmarkMetric]:
        """
        Generate benchmark metrics for the research topic.

        Uses LLM to analyze the topic and top sources to create 5-10 relevant
        metrics that capture different evaluation dimensions (performance,
        accuracy, usability, hardware requirements, etc.).

        Args:
            topic: Research topic string
            papers: Top-ranked papers
            patents: Top-ranked patents

        Returns:
            List of 5-10 BenchmarkMetric objects with name, description, and category

        Raises:
            ValueError: If LLM response is invalid or no metrics are generated
        """
        # Format sources for LLM analysis
        papers_summary = self._format_sources(papers)
        patents_summary = self._format_sources(patents)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a research analyst creating benchmark metrics for evaluating "
                    "research sources. Generate 5-10 specific, measurable metrics that would "
                    "help compare and evaluate sources on this topic.\n\n"
                    "Each metric should:\n"
                    "- Be specific and measurable\n"
                    "- Cover different evaluation dimensions (performance, accuracy, "
                    "usability, hardware, efficiency, scalability, cost, safety, etc.)\n"
                    "- Be relevant to the research topic and sources\n"
                    "- Have a clear name and detailed description\n\n"
                    "Focus on metrics that would help distinguish between different "
                    "approaches or implementations in this research area."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Research Topic: {topic}\n\n"
                    f"Top Papers:\n{papers_summary}\n\n"
                    f"Top Patents:\n{patents_summary}\n\n"
                    "Generate 5-10 benchmark metrics that would be most relevant for "
                    "evaluating and comparing these sources. Each metric should have a "
                    "clear name, detailed description, and category classification."
                ),
            },
        ]

        try:
            response = self.llm.chat_json(
                messages=messages,
                response_model=MetricsListResponse,
                temperature=0.7,
            )

            if not response.metrics:
                raise ValueError("LLM returned no metrics")

            # Convert to BenchmarkMetric objects
            benchmark_metrics = []
            for metric in response.metrics:
                benchmark_metrics.append(
                    BenchmarkMetric(
                        name=metric.name,
                        description=metric.description,
                        category=metric.category,
                    )
                )

            return benchmark_metrics

        except Exception as e:
            raise ValueError(f"Failed to generate metrics: {e}") from e

    def _format_sources(self, sources: list[ScoredSourceItem]) -> str:
        """
        Format source items into a summary for LLM analysis.

        Args:
            sources: List of scored source items

        Returns:
            Formatted text summary of sources
        """
        if not sources:
            return "(No sources available)"

        lines = []
        for i, source in enumerate(sources, 1):
            lines.append(f"{i}. {source.title}")
            if source.relevance_explanation:
                # Truncate long explanations
                explanation = source.relevance_explanation[:200]
                if len(source.relevance_explanation) > 200:
                    explanation += "..."
                lines.append(f"   Summary: {explanation}")
            lines.append(f"   Score: {source.relevance_score:.2f}")
            lines.append("")

        return "\n".join(lines)

    def save_metrics(
        self,
        workspace: Path,
        metrics: list[BenchmarkMetric],
        workspace_manager: WorkspaceManager,
    ) -> Path:
        """
        Save generated metrics to the workspace.

        Saves metrics to metrics.json using WorkspaceManager's artifact storage.

        Args:
            workspace: Workspace directory path
            metrics: List of benchmark metrics to save
            workspace_manager: WorkspaceManager instance for persistence

        Returns:
            Path to the saved metrics.json file
        """
        metrics_data = [metric.model_dump() for metric in metrics]
        return workspace_manager.save_artifact(
            workspace=workspace,
            artifact_name="metrics.json",
            data=metrics_data,
        )

    def load_metrics(
        self,
        workspace: Path,
        workspace_manager: WorkspaceManager,
    ) -> list[BenchmarkMetric]:
        """
        Load metrics from the workspace.

        Args:
            workspace: Workspace directory path
            workspace_manager: WorkspaceManager instance for loading

        Returns:
            List of BenchmarkMetric objects

        Raises:
            FileNotFoundError: If metrics.json doesn't exist
        """
        metrics_data = workspace_manager.load_artifact(
            workspace=workspace,
            artifact_name="metrics.json",
        )

        if not isinstance(metrics_data, list):
            raise ValueError("Invalid metrics.json format: expected list")

        return [BenchmarkMetric.model_validate(m) for m in metrics_data]
