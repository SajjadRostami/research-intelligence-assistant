"""
Comparison matrix generation for evaluating sources against metrics.

The ComparisonMatrixGenerator uses LLM to evaluate each source against each
selected metric and generates a colored matrix with coverage symbols.
"""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

from ria.llm import LLMClient
from ria.models import ScoredSourceItem


class MetricEvaluation(BaseModel):
    """Evaluation of a source against a single metric."""
    metric_name: str = Field(description="Name of the metric being evaluated")
    status: Literal["full", "partial", "none"] = Field(
        description="Coverage status: full, partial, or none"
    )
    symbol: Literal["✅", "⚠️", "❌"] = Field(
        description="Visual symbol for the coverage status"
    )
    score: float = Field(ge=0.0, le=1.0, description="Numeric score: 1.0, 0.5, or 0.0")
    evidence: str = Field(
        description="Short explanation based only on source metadata, title, abstract, or relevance analysis"
    )
    confidence: Literal["high", "medium", "low"] = Field(
        description="Confidence level in this evaluation"
    )


class SourceMetricEvaluation(BaseModel):
    """Complete evaluation of a source across all metrics."""
    source_id: str = Field(description="Unique identifier for the source")
    source_title: str = Field(description="Title of the source")
    source_type: Literal["paper", "patent"] = Field(description="Type of source")
    metric_evaluations: list[MetricEvaluation] = Field(
        description="Evaluations for each metric"
    )
    overall_score: float = Field(
        ge=0.0, le=1.0,
        description="Overall score = sum of metric scores / number of metrics"
    )


class ComparisonMatrixGenerator:
    """
    Generates comparison matrices by evaluating sources against metrics.

    Uses LLM to perform structured evaluation of each source against each
    selected metric, producing coverage scores with evidence.

    Example:
        generator = ComparisonMatrixGenerator(llm_client)
        evaluations = generator.evaluate_sources(
            sources=ranked_results.papers + ranked_results.patents,
            metrics=["AI Support", "GPU Support", "Real-Time Performance"]
        )
    """

    def __init__(self, llm_client: LLMClient):
        """
        Initialize the comparison matrix generator.

        Args:
            llm_client: LLM client for evaluations
        """
        self.llm = llm_client

    def evaluate_sources(
        self,
        sources: list[ScoredSourceItem],
        metric_names: list[str],
        metric_descriptions: dict[str, str] | None = None,
    ) -> list[SourceMetricEvaluation]:
        """
        Evaluate all sources against all metrics.

        Args:
            sources: List of scored source items (papers and patents)
            metric_names: List of metric names to evaluate
            metric_descriptions: Optional dictionary mapping metric names to descriptions

        Returns:
            List of SourceMetricEvaluation objects with complete evaluations
        """
        if not sources or not metric_names:
            return []

        evaluations = []
        for source in sources:
            evaluation = self._evaluate_single_source(
                source=source,
                metric_names=metric_names,
                metric_descriptions=metric_descriptions,
            )
            evaluations.append(evaluation)

        return evaluations

    def _evaluate_single_source(
        self,
        source: ScoredSourceItem,
        metric_names: list[str],
        metric_descriptions: dict[str, str] | None,
    ) -> SourceMetricEvaluation:
        """
        Evaluate a single source against all metrics.

        Args:
            source: Source item to evaluate
            metric_names: List of metric names
            metric_descriptions: Optional metric descriptions

        Returns:
            SourceMetricEvaluation with all metric evaluations
        """
        # Build source context
        source_context = self._build_source_context(source)

        # Build metrics context
        metrics_context = ""
        for metric_name in metric_names:
            metrics_context += f"- {metric_name}"
            if metric_descriptions and metric_name in metric_descriptions:
                metrics_context += f": {metric_descriptions[metric_name]}"
            metrics_context += "\n"

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a research analyst evaluating sources against specific metrics.\n\n"
                    "For each metric, determine if the source:\n"
                    "- ✅ Fully covers/matches the metric (score: 1.0, status: full)\n"
                    "- ⚠️ Partially covers/mentions the metric (score: 0.5, status: partial)\n"
                    "- ❌ Does not cover the metric (score: 0.0, status: none)\n\n"
                    "IMPORTANT RULES:\n"
                    "- Do not hallucinate. Base your evaluation ONLY on the provided metadata.\n"
                    "- If the source does not clearly mention a feature, mark it ❌.\n"
                    "- If there is indirect or implied evidence, mark it ⚠️.\n"
                    "- If there is clear and explicit evidence, mark it ✅.\n"
                    "- For XPBD, prefer the meaning 'Extended Position Based Dynamics' "
                    "(physics/simulation) unless the context clearly indicates biology.\n"
                    "- Provide short, evidence-based explanations (1-2 sentences)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"SOURCE TO EVALUATE:\n{source_context}\n\n"
                    f"METRICS TO EVALUATE:\n{metrics_context}\n\n"
                    f"Evaluate this source against each metric and provide structured output."
                ),
            },
        ]

        try:
            # Create dynamic response model with metric evaluations
            metric_evaluations_response = self.llm.chat_json(
                messages=messages,
                response_model=self._create_evaluation_response_model(metric_names),
                temperature=0.3,
            )

            metric_evals = metric_evaluations_response.metric_evaluations

            # Calculate overall score
            total_score = sum(m.score for m in metric_evals)
            overall_score = round(total_score / len(metric_names), 2) if metric_names else 0.0

            return SourceMetricEvaluation(
                source_id=self._generate_source_id(source),
                source_title=source.title,
                source_type=source.source_type.value,
                metric_evaluations=metric_evals,
                overall_score=overall_score,
            )

        except Exception as e:
            # Fallback: create default evaluations
            default_evals = []
            for metric_name in metric_names:
                default_evals.append(
                    MetricEvaluation(
                        metric_name=metric_name,
                        status="none",
                        symbol="❌",
                        score=0.0,
                        evidence=f"Evaluation failed: {str(e)}",
                        confidence="low",
                    )
                )

            return SourceMetricEvaluation(
                source_id=self._generate_source_id(source),
                source_title=source.title,
                source_type=source.source_type.value,
                metric_evaluations=default_evals,
                overall_score=0.0,
            )

    def _build_source_context(self, source: ScoredSourceItem) -> str:
        """
        Build context string for a source.

        Args:
            source: Source item

        Returns:
            Formatted context string
        """
        context_parts = [
            f"Title: {source.title}",
            f"Type: {source.source_type.value}",
        ]

        if source.author_or_assignee:
            label = "Assignee" if source.source_type.value == "patent" else "Authors"
            context_parts.append(f"{label}: {source.author_or_assignee}")

        if source.publication_date:
            context_parts.append(f"Publication Date: {source.publication_date}")

        if source.relevance_explanation:
            context_parts.append(f"Relevance Analysis: {source.relevance_explanation}")

        if source.venue:
            context_parts.append(f"Venue: {source.venue}")

        if source.doi:
            context_parts.append(f"DOI: {source.doi}")

        if source.patent_number:
            context_parts.append(f"Patent Number: {source.patent_number}")

        return "\n".join(context_parts)

    def _generate_source_id(self, source: ScoredSourceItem) -> str:
        """
        Generate a unique ID for a source.

        Args:
            source: Source item

        Returns:
            Unique identifier string
        """
        if source.doi:
            return source.doi
        if source.patent_number:
            return source.patent_number
        # Fallback: use first 50 chars of title
        return source.title[:50].replace(" ", "_")

    def _create_evaluation_response_model(self, metric_names: list[str]) -> type[BaseModel]:
        """
        Create a dynamic Pydantic model for metric evaluations.

        Args:
            metric_names: List of metric names

        Returns:
            Pydantic model class for structured output
        """
        class MetricEvaluationsResponse(BaseModel):
            metric_evaluations: list[MetricEvaluation] = Field(
                description=f"Evaluations for metrics: {', '.join(metric_names)}"
            )

        return MetricEvaluationsResponse


def render_matrix_markdown(
    evaluations: list[SourceMetricEvaluation],
    metric_names: list[str],
    include_evidence: bool = False,
    papers: list[ScoredSourceItem] | None = None,
    patents: list[ScoredSourceItem] | None = None,
) -> str:
    """
    Render comparison matrix as HTML table with color coding and linked labels.

    Args:
        evaluations: List of source evaluations
        metric_names: List of metric names (column headers)
        include_evidence: Whether to include evidence section
        papers: List of paper sources for generating links
        patents: List of patent sources for generating links

    Returns:
        HTML-formatted comparison matrix
    """
    if not evaluations or not metric_names:
        return "_No comparison matrix data available._\n\n"

    # Sort evaluations by overall score (descending)
    sorted_evals = sorted(evaluations, key=lambda e: e.overall_score, reverse=True)

    # Create source ID to label mapping
    source_label_map = {}
    paper_counter = 1
    patent_counter = 1

    if papers:
        for paper in papers:
            source_id = _generate_source_id_for_item(paper)
            source_label_map[source_id] = (f"Paper {paper_counter}", f"paper-{paper_counter}", paper.title)
            paper_counter += 1

    if patents:
        for patent in patents:
            source_id = _generate_source_id_for_item(patent)
            source_label_map[source_id] = (f"Patent {patent_counter}", f"patent-{patent_counter}", patent.title)
            patent_counter += 1

    def score_to_color_and_text(score: float) -> tuple[str, str]:
        """
        Convert overall score to row background color and text color.
        Returns (background_color, text_color).
        """
        if score >= 0.70:
            return ("#2d7d46", "white")  # dark green, white text
        elif score >= 0.50:
            return ("#70b77e", "white")  # light green, white text
        elif score >= 0.30:
            return ("#ffe4b5", "#333")  # light yellow/orange, dark text
        elif score >= 0.15:
            return ("#ffb347", "#333")  # light orange, dark text
        else:
            return ("#ffcccb", "#333")  # light red/pink, dark text

    def score_to_color(score: float) -> str:
        """Convert score to background color (for metric coverage row)."""
        if score >= 0.70:
            return "#2d7d46"  # dark green
        elif score >= 0.50:
            return "#70b77e"  # light green
        elif score >= 0.30:
            return "#ffe4b5"  # light yellow/orange
        elif score >= 0.15:
            return "#ffb347"  # light orange
        else:
            return "#ffcccb"  # light red/pink

    # Build HTML with embedded CSS for status badges
    lines = ['<div style="text-align: center; margin: 20px 0;">']
    lines.append('<style>')
    lines.append('.status-badge { display: inline-block; background: white; border: 1px solid #ccc; '
                 'border-radius: 4px; padding: 2px 6px; font-size: 16px; font-weight: bold; }')
    lines.append('.comparison-matrix a { text-decoration: none; font-weight: bold; }')
    lines.append('.comparison-matrix a:hover { text-decoration: underline; }')
    lines.append('.comparison-matrix th { background: #2d7d46 !important; color: white !important; }')
    lines.append('</style>')
    lines.append('<h3>Source Comparison Matrix</h3>')
    lines.append('<table class="comparison-matrix" style="border-collapse: collapse; margin: 20px auto; max-width: 90%;">')

    # Header row
    lines.append('<thead><tr>')
    lines.append('<th style="border: 1px solid #ddd; padding: 10px; text-align: center;">Source</th>')
    for metric_name in metric_names:
        lines.append(f'<th style="border: 1px solid #ddd; padding: 10px; text-align: center;">{metric_name}</th>')
    lines.append('<th style="border: 1px solid #ddd; padding: 10px; text-align: center;">Overall %</th>')
    lines.append('</tr></thead>')

    # Body rows
    lines.append('<tbody>')
    for eval in sorted_evals:
        metric_lookup = {m.metric_name: m for m in eval.metric_evaluations}

        # Get row background and text color based on overall score
        row_bg_color, row_text_color = score_to_color_and_text(eval.overall_score)

        lines.append('<tr>')

        # Source name cell with linked label
        source_label_info = source_label_map.get(eval.source_id)
        if source_label_info:
            label, anchor, full_title = source_label_info
            # Use white text on dark backgrounds, blue on light backgrounds
            link_color = "white" if row_text_color == "white" else "#3498db"
            lines.append(
                f'<td style="border: 1px solid #ddd; padding: 10px; text-align: center; '
                f'background-color: {row_bg_color}; color: {row_text_color};">'
                f'<a href="#{anchor}" title="{full_title}" style="color: {link_color};"><strong>{label}</strong></a></td>'
            )
        else:
            # Fallback if label not found
            source_name = eval.source_title[:30]
            if len(eval.source_title) > 30:
                source_name += "..."
            lines.append(
                f'<td style="border: 1px solid #ddd; padding: 10px; text-align: center; '
                f'background-color: {row_bg_color}; color: {row_text_color};"><strong>{source_name}</strong></td>'
            )

        # Metric cells - inherit row background, show badge with symbol
        for metric_name in metric_names:
            if metric_name in metric_lookup:
                m = metric_lookup[metric_name]
                lines.append(
                    f'<td style="border: 1px solid #ddd; padding: 10px; text-align: center; '
                    f'background-color: {row_bg_color}; color: {row_text_color};" title="{m.evidence}">'
                    f'<span class="status-badge">{m.symbol}</span></td>'
                )
            else:
                lines.append(
                    f'<td style="border: 1px solid #ddd; padding: 10px; text-align: center; '
                    f'background-color: {row_bg_color}; color: {row_text_color};">'
                    f'<span class="status-badge">❌</span></td>'
                )

        # Overall percentage cell - inherit row background
        overall_pct = int(eval.overall_score * 100)
        lines.append(
            f'<td style="border: 1px solid #ddd; padding: 10px; text-align: center; '
            f'background-color: {row_bg_color}; color: {row_text_color};"><strong>{overall_pct}%</strong></td>'
        )

        lines.append('</tr>')

    # Metric coverage row (last row, column-based coloring is OK here)
    lines.append('<tr>')
    lines.append('<td style="border: 1px solid #ddd; padding: 10px; text-align: center; background: #f8f9fa;"><strong>Metric Coverage</strong></td>')

    for metric_name in metric_names:
        total_score = sum(
            next((m.score for m in e.metric_evaluations if m.metric_name == metric_name), 0.0)
            for e in sorted_evals
        )
        avg_score = total_score / len(sorted_evals) if sorted_evals else 0.0
        coverage_pct = int(avg_score * 100)
        color = score_to_color(avg_score)
        text_color = "white" if avg_score >= 0.50 else "#333"

        lines.append(
            f'<td style="border: 1px solid #ddd; padding: 10px; text-align: center; '
            f'background-color: {color}; color: {text_color};"><strong>{coverage_pct}%</strong></td>'
        )

    lines.append('<td style="border: 1px solid #ddd; padding: 10px; text-align: center; background: #f8f9fa;">-</td>')
    lines.append('</tr>')

    lines.append('</tbody>')
    lines.append('</table>')

    # Legend
    lines.append('<div style="margin-top: 15px; text-align: center;">')
    lines.append('<p><strong>Legend:</strong></p>')
    lines.append('<ul style="list-style: none; padding: 0; margin: 0 auto; max-width: 500px; text-align: left;">')
    lines.append('<li>✅ Fully Matched</li>')
    lines.append('<li>⚠️ Partially Covered</li>')
    lines.append('<li>❌ Not Covered</li>')
    lines.append('</ul>')
    lines.append('</div>')
    lines.append('</div>')

    # Add evidence section if requested
    if include_evidence:
        lines.append("\n### Evidence Details\n")
        for eval in sorted_evals:
            lines.append(f"#### {eval.source_title}\n")
            for metric_eval in eval.metric_evaluations:
                lines.append(f"**{metric_eval.metric_name}** ({metric_eval.symbol}):")
                lines.append(f"{metric_eval.evidence}\n")

    return "\n".join(lines)


def _generate_source_id_for_item(source: ScoredSourceItem) -> str:
    """
    Generate a unique ID for a source item (used for mapping).

    Args:
        source: Source item

    Returns:
        Unique identifier string
    """
    if source.doi:
        return source.doi
    if source.patent_number:
        return source.patent_number
    # Fallback: use first 50 chars of title
    return source.title[:50].replace(" ", "_")


def render_matrix_html(
    evaluations: list[SourceMetricEvaluation],
    metric_names: list[str],
) -> str:
    """
    Render comparison matrix as HTML table with row-based heatmap coloring.

    Args:
        evaluations: List of source evaluations
        metric_names: List of metric names (column headers)

    Returns:
        HTML-formatted comparison matrix
    """
    if not evaluations or not metric_names:
        return "<p><em>No comparison matrix data available.</em></p>"

    # Sort evaluations by overall score (descending)
    sorted_evals = sorted(evaluations, key=lambda e: e.overall_score, reverse=True)

    def score_to_color_and_text(score: float) -> tuple[str, str]:
        """Convert overall score to row background and text color."""
        if score >= 0.70:
            return ("#2d7d46", "white")  # dark green, white text
        elif score >= 0.50:
            return ("#70b77e", "white")  # light green, white text
        elif score >= 0.30:
            return ("#ffe4b5", "#333")  # light yellow/orange, dark text
        elif score >= 0.15:
            return ("#ffb347", "#333")  # light orange, dark text
        else:
            return ("#ffcccb", "#333")  # light red/pink, dark text

    def score_to_color(score: float) -> str:
        """Convert score to background color (for metric coverage row)."""
        if score >= 0.70:
            return "#2d7d46"
        elif score >= 0.50:
            return "#70b77e"
        elif score >= 0.30:
            return "#ffe4b5"
        elif score >= 0.15:
            return "#ffb347"
        else:
            return "#ffcccb"

    # Build HTML
    html = ['<style>']
    html.append('.status-badge { display: inline-block; background: white; border: 1px solid #ccc; '
                'border-radius: 4px; padding: 2px 6px; font-size: 16px; font-weight: bold; }')
    html.append('.comparison-matrix th { background: #2d7d46 !important; color: white !important; }')
    html.append('</style>')
    html.append('<table class="comparison-matrix" style="width: 100%; border-collapse: collapse;">')

    # Header row
    html.append("<thead><tr>")
    html.append('<th style="border: 1px solid #ddd; padding: 8px; text-align: center;">Source</th>')
    for metric_name in metric_names:
        html.append(f'<th style="border: 1px solid #ddd; padding: 8px; text-align: center;">{metric_name}</th>')
    html.append('<th style="border: 1px solid #ddd; padding: 8px; text-align: center;">Overall %</th>')
    html.append("</tr></thead>")

    # Body rows
    html.append("<tbody>")
    for eval in sorted_evals:
        metric_lookup = {m.metric_name: m for m in eval.metric_evaluations}

        # Get row colors based on overall score
        row_bg_color, row_text_color = score_to_color_and_text(eval.overall_score)

        html.append("<tr>")

        # Source name cell
        html.append(
            f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center; '
            f'background-color: {row_bg_color}; color: {row_text_color};"><strong>{eval.source_title}</strong></td>'
        )

        # Metric cells - inherit row background, show badge
        for metric_name in metric_names:
            if metric_name in metric_lookup:
                m = metric_lookup[metric_name]
                html.append(
                    f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center; '
                    f'background-color: {row_bg_color}; color: {row_text_color};" title="{m.evidence}">'
                    f'<span class="status-badge">{m.symbol}</span></td>'
                )
            else:
                html.append(
                    f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center; '
                    f'background-color: {row_bg_color}; color: {row_text_color};">'
                    f'<span class="status-badge">❌</span></td>'
                )

        # Overall percentage cell - inherit row background
        overall_pct = int(eval.overall_score * 100)
        html.append(
            f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center; '
            f'background-color: {row_bg_color}; color: {row_text_color};"><strong>{overall_pct}%</strong></td>'
        )

        html.append("</tr>")

    # Metric coverage row (column-based coloring)
    html.append('<tr>')
    html.append('<td style="border: 1px solid #ddd; padding: 8px; text-align: center; background: #f8f9fa;"><strong>Metric Coverage</strong></td>')

    for metric_name in metric_names:
        total_score = sum(
            next((m.score for m in e.metric_evaluations if m.metric_name == metric_name), 0.0)
            for e in sorted_evals
        )
        avg_score = total_score / len(sorted_evals) if sorted_evals else 0.0
        coverage_pct = int(avg_score * 100)
        color = score_to_color(avg_score)
        text_color = "white" if avg_score >= 0.50 else "#333"

        html.append(
            f'<td style="border: 1px solid #ddd; padding: 8px; text-align: center; '
            f'background-color: {color}; color: {text_color};"><strong>{coverage_pct}%</strong></td>'
        )

    html.append('<td style="border: 1px solid #ddd; padding: 8px; text-align: center; background: #f8f9fa;">-</td>')
    html.append("</tr>")

    html.append("</tbody>")
    html.append("</table>")

    # Legend
    html.append('<div style="margin-top: 10px; text-align: center;">')
    html.append('<p><strong>Legend:</strong></p>')
    html.append('<ul style="list-style: none; padding: 0; margin: 0 auto; max-width: 500px; text-align: left;">')
    html.append('<li>✅ Fully Matched</li>')
    html.append('<li>⚠️ Partially Covered</li>')
    html.append('<li>❌ Not Covered</li>')
    html.append('</ul>')
    html.append('</div>')

    return "\n".join(html)
