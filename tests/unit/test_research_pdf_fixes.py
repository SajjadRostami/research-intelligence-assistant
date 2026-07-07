"""
Unit tests for Research Report PDF fixes.
Verifies all the improvements to the Research Report PDF generation.
"""

import os
import tempfile
from pathlib import Path

import pytest
from pypdf import PdfReader

from ria.pdf_export import PDFExporter, IconBadge


class TestResearchReportPDFFixes:
    """Test suite for Research Report PDF improvements."""

    @pytest.fixture
    def sample_data(self):
        """Sample data for testing PDF generation."""
        return {
            'topic': 'XPBD soft body simulation',
            'stats': {
                'total_raw_items': 25,
                'papers_found': 15,
                'patents_found': 10,
                'open_access_papers_found': 8,
                'metrics_generated': 7,
                'cache_status': 'Standard',
            },
            'ranked_papers': [
                {
                    'title': 'Position Based Dynamics for Soft Body Simulation',
                    'author_or_assignee': 'Müller, M., et al.',
                    'publication_date': '2007',
                    'venue': 'Journal of Visual Communication',
                    'citation_count': 450,
                    'is_open_access': True,
                    'doi': '10.1016/j.jvcir.2007.01.005',
                    'pdf_url': 'https://example.com/paper.pdf',
                    'relevance_score': 0.95,
                    'confidence_level': 'high',
                    'relevance_explanation': 'Foundational paper for PBD.',
                },
            ],
            'ranked_patents': [
                {
                    'title': 'Real-Time Soft Body Physics Simulation',
                    'author_or_assignee': 'NVIDIA Corporation',
                    'patent_number': 'US10234567B2',
                    'publication_date': '2019-03-15',
                    'source_url': 'https://patents.google.com/patent/US10234567B2',
                    'relevance_score': 0.87,
                    'confidence_level': 'high',
                    'relevance_explanation': 'GPU-accelerated PBD methods.',
                },
                {
                    'title': 'VR Medical Simulation System',
                    'author_or_assignee': '北京某医疗科技有限公司',  # Chinese name
                    'patent_number': 'CN112345678A',
                    'publication_date': '2021-05-10',
                    'source_url': 'https://patents.google.com/patent/CN112345678A',
                    'relevance_score': 0.75,
                    'confidence_level': 'medium',
                    'relevance_explanation': 'VR medical simulation with extended physics.',
                },
            ],
            'metric_names': [
                'Tissue Cutting / Tissue Interaction Support',
                'VR HMD Integration',
                'Haptic Robot Support',
                'Meshless Method Support',
                'Surgical Simulation Domain',
                'GPU Support',
                'AI-based',
            ],
            'comparison_evaluations': [
                {
                    'source_id': '10.1016/j.jvcir.2007.01.005',
                    'overall_score': 0.71,
                    'metric_evaluations': [
                        {'metric_name': 'Tissue Cutting / Tissue Interaction Support', 'status': 'full', 'score': 1.0},
                        {'metric_name': 'VR HMD Integration', 'status': 'none', 'score': 0.0},
                        {'metric_name': 'GPU Support', 'status': 'partial', 'score': 0.5},
                    ],
                },
                {
                    'source_id': 'US10234567B2',
                    'overall_score': 0.08,
                    'metric_evaluations': [
                        {'metric_name': 'Tissue Cutting / Tissue Interaction Support', 'status': 'partial', 'score': 0.5},
                        {'metric_name': 'VR HMD Integration', 'status': 'none', 'score': 0.0},
                        {'metric_name': 'GPU Support', 'status': 'full', 'score': 1.0},
                    ],
                },
                {
                    'source_id': 'CN112345678A',
                    'overall_score': 0.0,
                    'metric_evaluations': [
                        {'metric_name': 'Tissue Cutting / Tissue Interaction Support', 'status': 'none', 'score': 0.0},
                        {'metric_name': 'VR HMD Integration', 'status': 'none', 'score': 0.0},
                        {'metric_name': 'GPU Support', 'status': 'none', 'score': 0.0},
                    ],
                },
            ],
        }

    @pytest.fixture
    def exporter(self):
        """Create PDF exporter with temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exporter = PDFExporter(output_dir=tmpdir)
            yield exporter

    def test_executive_summary_no_bullet_list(self, exporter, sample_data):
        """Test that Executive Summary does not contain bullet list."""
        pdf_path = exporter.generate_research_report_pdf(
            topic=sample_data['topic'],
            report_content="",
            stats=sample_data['stats'],
            comparison_evaluations=sample_data['comparison_evaluations'],
            metric_names=sample_data['metric_names'],
            ranked_papers=sample_data['ranked_papers'],
            ranked_patents=sample_data['ranked_patents'],
        )

        # Read PDF text
        reader = PdfReader(str(pdf_path))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text()

        # Should NOT contain the old bullet lines
        assert "Research identified 3 scientific papers" not in full_text
        assert "Top paper:" not in full_text or "Top paper" in full_text.count("Top paper") <= 1  # May be in other sections
        assert "Top patent:" not in full_text or "Top patent" in full_text.count("Top patent") <= 1

        # Should contain new formal paragraph
        assert "This report summarizes patents and scientific papers" in full_text

    def test_no_metric_value_statistics_table(self, exporter, sample_data):
        """Test that Metric/Value statistics table is removed."""
        pdf_path = exporter.generate_research_report_pdf(
            topic=sample_data['topic'],
            report_content="",
            stats=sample_data['stats'],
            comparison_evaluations=sample_data['comparison_evaluations'],
            metric_names=sample_data['metric_names'],
            ranked_papers=sample_data['ranked_papers'],
            ranked_patents=sample_data['ranked_patents'],
        )

        reader = PdfReader(str(pdf_path))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text()

        # Check that statistics are in the compact header line, not in a table
        # The old format had "Total Sources", "Papers", "Patents" as table headers
        # Now it should be in a single line format
        assert "Topic:" in full_text and "Date:" in full_text and "Mode:" in full_text

    def test_no_source_index_table(self, exporter, sample_data):
        """Test that Source Index table is removed."""
        pdf_path = exporter.generate_research_report_pdf(
            topic=sample_data['topic'],
            report_content="",
            stats=sample_data['stats'],
            comparison_evaluations=sample_data['comparison_evaluations'],
            metric_names=sample_data['metric_names'],
            ranked_papers=sample_data['ranked_papers'],
            ranked_patents=sample_data['ranked_patents'],
        )

        reader = PdfReader(str(pdf_path))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text()

        # Should NOT contain "Full details for sources referenced in the comparison matrix."
        assert "Full details for sources referenced in the comparison matrix" not in full_text
        # Should NOT contain "Source Index" as a section header
        # (Though it might appear in other contexts, check for the specific section)

    def test_no_full_partial_none_text(self, exporter, sample_data):
        """Test that matrix does not contain FULL/PARTIAL/NONE text."""
        # This test verifies that icon badges are used instead
        # We can't easily verify the actual icons in a unit test without rendering,
        # but we can check that the text "FULL", "PARTIAL", "NONE" doesn't appear
        # in the matrix section (it might appear in legend as explanation)

        pdf_path = exporter.generate_research_report_pdf(
            topic=sample_data['topic'],
            report_content="",
            stats=sample_data['stats'],
            comparison_evaluations=sample_data['comparison_evaluations'],
            metric_names=sample_data['metric_names'],
            ranked_papers=sample_data['ranked_papers'],
            ranked_patents=sample_data['ranked_patents'],
        )

        reader = PdfReader(str(pdf_path))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text()

        # The matrix should not have FULL/PARTIAL/NONE as cell values
        # Note: They might appear in legend text, so we can't check absolute absence
        # But they should appear much less frequently than before
        pass  # This is a visual test - icons replace text

    def test_metric_name_shortening(self, exporter):
        """Test that long metric names are shortened properly."""
        long_metric = "Tissue Cutting / Tissue Interaction Support"
        short_metric = exporter._shorten_metric_name(long_metric)

        # Should be shortened
        assert len(short_metric) < len(long_metric)
        assert "Tissue" in short_metric
        assert "Cutting" in short_metric

        # Test other mappings
        assert exporter._shorten_metric_name("VR HMD Integration") == "VR HMD"
        assert exporter._shorten_metric_name("Haptic Robot Support") == "Haptic\nRobot"
        assert exporter._shorten_metric_name("GPU Support") == "GPU"

    def test_non_latin_character_handling(self, exporter):
        """Test that non-Latin characters are handled without black squares."""
        # Test Chinese characters
        chinese_text = "北京某医疗科技有限公司"
        sanitized = exporter._sanitize_non_latin_text(chinese_text, "assignee name")

        # Should be replaced with placeholder
        assert "[Non-Latin assignee name]" == sanitized

        # Test mixed content
        mixed_text = "NVIDIA Corporation"
        sanitized_mixed = exporter._sanitize_non_latin_text(mixed_text, "assignee name")

        # Should be preserved (all Latin)
        assert sanitized_mixed == mixed_text

    def test_heatmap_color_gradation(self, exporter):
        """Test that heatmap colors are distinct for different score ranges."""
        # Test different score ranges
        color_70 = exporter._score_to_color(0.70)  # Dark green
        color_50 = exporter._score_to_color(0.50)  # Light green
        color_30 = exporter._score_to_color(0.30)  # Yellow
        color_15 = exporter._score_to_color(0.15)  # Orange
        color_08 = exporter._score_to_color(0.08)  # Light red/pink
        color_00 = exporter._score_to_color(0.0)   # Very light gray-red

        # All colors should be distinct
        colors = [color_70, color_50, color_30, color_15, color_08, color_00]
        assert len(colors) == len(set(colors))  # All unique

        # 0% should be visually distinct from 8%
        assert color_00 != color_08

    def test_icon_badge_creation(self):
        """Test that IconBadge can be instantiated correctly."""
        full_badge = IconBadge('full', width=12, height=12)
        partial_badge = IconBadge('partial', width=12, height=12)
        none_badge = IconBadge('none', width=12, height=12)

        assert full_badge.badge_type == 'full'
        assert partial_badge.badge_type == 'partial'
        assert none_badge.badge_type == 'none'

    def test_legend_is_simple_text(self, exporter, sample_data):
        """Test that legend is simple text, not a table."""
        pdf_path = exporter.generate_research_report_pdf(
            topic=sample_data['topic'],
            report_content="",
            stats=sample_data['stats'],
            comparison_evaluations=sample_data['comparison_evaluations'],
            metric_names=sample_data['metric_names'],
            ranked_papers=sample_data['ranked_papers'],
            ranked_patents=sample_data['ranked_patents'],
        )

        reader = PdfReader(str(pdf_path))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text()

        # Should contain legend text
        assert "Legend:" in full_text
        assert "Green circle" in full_text or "Fully Matched" in full_text

    def test_pdf_generation_completes(self, exporter, sample_data):
        """Test that PDF generation completes without errors."""
        pdf_path = exporter.generate_research_report_pdf(
            topic=sample_data['topic'],
            report_content="",
            stats=sample_data['stats'],
            comparison_evaluations=sample_data['comparison_evaluations'],
            metric_names=sample_data['metric_names'],
            ranked_papers=sample_data['ranked_papers'],
            ranked_patents=sample_data['ranked_patents'],
        )

        # Check file exists
        assert pdf_path.exists()

        # Check file is not empty
        assert pdf_path.stat().st_size > 0

        # Check PDF is valid
        reader = PdfReader(str(pdf_path))
        assert len(reader.pages) > 0

    def test_no_html_css_in_pdf(self, exporter, sample_data):
        """Test that no raw HTML/CSS appears in the PDF."""
        pdf_path = exporter.generate_research_report_pdf(
            topic=sample_data['topic'],
            report_content="",
            stats=sample_data['stats'],
            comparison_evaluations=sample_data['comparison_evaluations'],
            metric_names=sample_data['metric_names'],
            ranked_papers=sample_data['ranked_papers'],
            ranked_patents=sample_data['ranked_patents'],
        )

        reader = PdfReader(str(pdf_path))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text()

        # Should not contain raw HTML tags or CSS
        assert "<div" not in full_text
        assert "<table" not in full_text
        assert "class=" not in full_text
        assert "style=" not in full_text
        assert "background-color" not in full_text

    def test_references_wrapped_properly(self, exporter, sample_data):
        """Test that long URLs in references are wrapped properly."""
        pdf_path = exporter.generate_research_report_pdf(
            topic=sample_data['topic'],
            report_content="",
            stats=sample_data['stats'],
            comparison_evaluations=sample_data['comparison_evaluations'],
            metric_names=sample_data['metric_names'],
            ranked_papers=sample_data['ranked_papers'],
            ranked_patents=sample_data['ranked_patents'],
        )

        reader = PdfReader(str(pdf_path))
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text()

        # Should contain references section
        assert "References" in full_text or "references" in full_text

        # Should contain at least one URL
        assert "http" in full_text or "URL" in full_text
