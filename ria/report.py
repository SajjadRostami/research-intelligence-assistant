"""
Report generation for research intelligence outputs.

The ReportRenderer takes ranked results, benchmark metrics, and topic information
to generate a comprehensive Markdown report with executive summary, top sources,
benchmark analysis, and references.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ria.models import BenchmarkMetric, RankedResults, ScoredSourceItem


class ReportRenderer:
    """
    Generates Markdown reports from research intelligence data.

    Takes ranked results and benchmark metrics to produce a structured
    report with executive summary, top sources, benchmark analysis, and
    complete references.

    Example:
        renderer = ReportRenderer()
        report_path = renderer.generate(
            topic="XPBD soft body simulation",
            ranked_results=ranked_results,
            metrics=metrics,
            workspace_dir=Path("./workspace")
        )
    """

    def generate(
        self,
        topic: str,
        ranked_results: RankedResults,
        metrics: list[BenchmarkMetric],
        workspace_dir: Path,
    ) -> Path:
        """
        Generate a complete Markdown report and save to workspace.

        Args:
            topic: The research topic
            ranked_results: Ranked papers and patents
            metrics: List of benchmark metrics
            workspace_dir: Directory to save the report

        Returns:
            Path to the generated report.md file
        """
        report_path = workspace_dir / "report.md"

        # Build report sections
        content = self._build_title(topic)
        content += self._build_metadata()
        content += self._build_executive_summary(topic, ranked_results, metrics)
        content += self._build_top_patents(ranked_results.patents)
        content += self._build_top_papers(ranked_results.papers)
        content += self._build_benchmark_metrics(metrics)
        content += self._build_references(ranked_results)

        # Write to file
        report_path.write_text(content, encoding="utf-8")
        return report_path

    def _build_title(self, topic: str) -> str:
        """Build the report title section."""
        return f"# Research Intelligence Report: {topic}\n\n"

    def _build_metadata(self) -> str:
        """Build the metadata section with generation date."""
        now = datetime.utcnow()
        return f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n---\n\n"

    def _build_executive_summary(
        self,
        topic: str,
        ranked_results: RankedResults,
        metrics: list[BenchmarkMetric],
    ) -> str:
        """Build the executive summary section."""
        paper_count = len(ranked_results.papers)
        patent_count = len(ranked_results.patents)
        metric_count = len(metrics)

        summary = "## Executive Summary\n\n"
        summary += f"This report presents a comprehensive analysis of **{topic}** based on "
        summary += f"{patent_count} top-ranked patents"

        if paper_count > 0:
            summary += f" and {paper_count} scientific papers"

        summary += f". The analysis evaluates sources across {metric_count} benchmark metrics "
        summary += "to identify leading implementations, methodologies, and performance characteristics.\n\n"

        # Add key findings
        if patent_count > 0:
            top_patent = ranked_results.patents[0]
            summary += f"**Key Finding:** The highest-ranked patent "
            summary += f'"{top_patent.title}" (relevance score: {top_patent.relevance_score:.2f}) '
            summary += f"demonstrates strong alignment with {topic}.\n\n"

        if paper_count > 0:
            top_paper = ranked_results.papers[0]
            summary += f"**Top Paper:** "
            summary += f'"{top_paper.title}" (relevance score: {top_paper.relevance_score:.2f}).\n\n'

        summary += "---\n\n"
        return summary

    def _build_top_patents(self, patents: list[ScoredSourceItem]) -> str:
        """Build the top patents section."""
        if not patents:
            return "## Top Patents\n\n*No patents were ranked for this topic.*\n\n---\n\n"

        section = "## Top Patents\n\n"
        section += f"The following {len(patents)} patents represent the most relevant "
        section += "prior art and implementations related to this research topic.\n\n"

        for i, patent in enumerate(patents, 1):
            section += f"### {i}. {patent.title}\n\n"
            section += f"**Patent Number:** {patent.patent_number or 'N/A'}  \n"
            section += f"**Assignee:** {patent.author_or_assignee or 'N/A'}  \n"
            section += f"**Publication Date:** {patent.publication_date or 'N/A'}  \n"
            section += f"**Relevance Score:** {patent.relevance_score:.2f}/1.00  \n"
            section += f"**Confidence:** {patent.confidence_level or 'N/A'}  \n"
            section += f"**URL:** [{patent.source_url}]({patent.source_url})\n\n"

            if patent.relevance_explanation:
                section += f"**Relevance Analysis:**\n\n{patent.relevance_explanation}\n\n"

        section += "---\n\n"
        return section

    def _build_top_papers(self, papers: list[ScoredSourceItem]) -> str:
        """Build the top papers section."""
        if not papers:
            return "## Top Papers\n\n*No scientific papers were ranked for this topic.*\n\n---\n\n"

        section = "## Top Papers\n\n"
        section += f"The following {len(papers)} scientific papers provide foundational "
        section += "research and theoretical background for this topic.\n\n"

        for i, paper in enumerate(papers, 1):
            section += f"### {i}. {paper.title}\n\n"
            section += f"**Authors:** {paper.author_or_assignee or 'N/A'}  \n"
            section += f"**Publication Date:** {paper.publication_date or 'N/A'}  \n"
            section += f"**DOI:** {paper.doi or 'N/A'}  \n"
            section += f"**Relevance Score:** {paper.relevance_score:.2f}/1.00  \n"
            section += f"**Confidence:** {paper.confidence_level or 'N/A'}  \n"
            section += f"**URL:** [{paper.source_url}]({paper.source_url})\n\n"

            if paper.relevance_explanation:
                section += f"**Relevance Analysis:**\n\n{paper.relevance_explanation}\n\n"

        section += "---\n\n"
        return section

    def _build_benchmark_metrics(self, metrics: list[BenchmarkMetric]) -> str:
        """Build the benchmark metrics section."""
        if not metrics:
            return "## Benchmark Metrics\n\n*No benchmark metrics were defined for this topic.*\n\n---\n\n"

        section = "## Benchmark Metrics\n\n"
        section += f"This analysis evaluates sources against {len(metrics)} benchmark metrics "
        section += "across multiple categories:\n\n"

        # Group metrics by category
        categorized: dict[str, list[BenchmarkMetric]] = {}
        for metric in metrics:
            category = metric.category or "Other"
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(metric)

        # Output metrics by category
        for category in sorted(categorized.keys()):
            section += f"### {category.title()} Metrics\n\n"

            for metric in categorized[category]:
                section += f"**{metric.name}**\n\n"
                if metric.description:
                    section += f"{metric.description}\n\n"

        section += "---\n\n"
        return section

    def _build_references(self, ranked_results: RankedResults) -> str:
        """Build the references section with all sources."""
        all_sources = ranked_results.patents + ranked_results.papers

        if not all_sources:
            return "## References\n\n*No sources to reference.*\n\n"

        section = "## References\n\n"

        # Separate patents and papers
        if ranked_results.patents:
            section += "### Patents\n\n"
            for i, patent in enumerate(ranked_results.patents, 1):
                section += f"{i}. {patent.title}. "
                if patent.author_or_assignee:
                    section += f"{patent.author_or_assignee}. "
                if patent.patent_number:
                    section += f"{patent.patent_number}. "
                if patent.publication_date:
                    section += f"Published {patent.publication_date}. "
                section += f"Available at: {patent.source_url}\n\n"

        if ranked_results.papers:
            section += "### Scientific Papers\n\n"
            for i, paper in enumerate(ranked_results.papers, 1):
                section += f"{i}. {paper.title}. "
                if paper.author_or_assignee:
                    section += f"{paper.author_or_assignee}. "
                if paper.publication_date:
                    section += f"({paper.publication_date}). "
                if paper.doi:
                    section += f"DOI: {paper.doi}. "
                section += f"Available at: {paper.source_url}\n\n"

        return section
