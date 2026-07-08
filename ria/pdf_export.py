"""
PDF export utilities for Research Intelligence Assistant.

Generates professional PDF reports for research results and LLM usage analytics.
Uses reportlab for PDF generation. Does not expose API keys or secrets.
"""

from __future__ import annotations

import html
import io
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    Image,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import Flowable
from reportlab.graphics.shapes import Drawing, Circle, Line, String as GfxString

# Optional matplotlib for charts in LLM Usage PDF
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class IconBadge(Flowable):
    """
    Custom flowable for rendering icon badges in PDF tables.
    Renders small visual badges with check, warning, or X symbols.
    """

    def __init__(self, badge_type: str, width: float = 12, height: float = 12):
        """
        Initialize icon badge.

        Args:
            badge_type: Type of badge - 'full', 'partial', or 'none'
            width: Badge width in points
            height: Badge height in points
        """
        Flowable.__init__(self)
        self.badge_type = badge_type
        self.width = width
        self.height = height

    def draw(self):
        """Draw the badge on the canvas."""
        canvas = self.canv
        x, y = 0, 0

        if self.badge_type == 'full':
            # Green circle with check mark
            canvas.setFillColor(colors.HexColor('#2d7d46'))
            canvas.circle(x + self.width/2, y + self.height/2, self.width/2, fill=1, stroke=0)
            # White check mark
            canvas.setStrokeColor(colors.white)
            canvas.setLineWidth(1.5)
            canvas.line(x + 3, y + self.height/2, x + self.width/2.5, y + self.height/2 + 2)
            canvas.line(x + self.width/2.5, y + self.height/2 + 2, x + self.width - 3, y + 3)

        elif self.badge_type == 'partial':
            # Orange/yellow circle with exclamation mark
            canvas.setFillColor(colors.HexColor('#f39c12'))
            canvas.circle(x + self.width/2, y + self.height/2, self.width/2, fill=1, stroke=0)
            # White exclamation mark
            canvas.setStrokeColor(colors.white)
            canvas.setLineWidth(1.5)
            canvas.line(x + self.width/2, y + 4, x + self.width/2, y + self.height - 5)
            canvas.setFillColor(colors.white)
            canvas.circle(x + self.width/2, y + 2.5, 0.8, fill=1, stroke=0)

        elif self.badge_type == 'none':
            # Red circle with X mark
            canvas.setFillColor(colors.HexColor('#d9534f'))
            canvas.circle(x + self.width/2, y + self.height/2, self.width/2, fill=1, stroke=0)
            # White X mark
            canvas.setStrokeColor(colors.white)
            canvas.setLineWidth(1.5)
            canvas.line(x + 3, y + 3, x + self.width - 3, y + self.height - 3)
            canvas.line(x + 3, y + self.height - 3, x + self.width - 3, y + 3)


class PDFExporter:
    """
    PDF export utility for generating research reports and usage analytics.

    Generates two types of PDFs:
    1. Research Report PDF - Full research report with sources and comparison matrix
    2. LLM Usage PDF - Analytics report with token usage, costs, and workflow
    """

    def __init__(self, output_dir: str = "pdf_exports"):
        """
        Initialize PDF exporter.

        Args:
            output_dir: Directory to save generated PDFs
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Setup styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

        # Register Unicode fonts if available
        self._register_unicode_fonts()

    def _register_unicode_fonts(self) -> None:
        """Register Unicode-capable fonts for non-Latin character support."""
        # Try to register DejaVu Sans or other Unicode fonts
        # These fonts are commonly available on Linux systems
        font_paths = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        ]

        try:
            if Path(font_paths[0]).exists():
                pdfmetrics.registerFont(TTFont('DejaVuSans', font_paths[0]))
            if Path(font_paths[1]).exists():
                pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', font_paths[1]))
        except Exception:
            # If font registration fails, continue with default fonts
            pass

    def _setup_custom_styles(self) -> None:
        """Setup custom paragraph styles for PDF generation."""
        # Cover page title
        self.styles.add(ParagraphStyle(
            name='CoverTitle',
            parent=self.styles['Title'],
            fontSize=28,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
        ))

        # Cover subtitle
        self.styles.add(ParagraphStyle(
            name='CoverSubtitle',
            parent=self.styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#666666'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica',
        ))

        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=30,
            alignment=TA_CENTER,
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
        ))

        # Subsection header style
        self.styles.add(ParagraphStyle(
            name='SubsectionHeader',
            parent=self.styles['Heading2'],
            fontSize=13,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold',
        ))

        # Cost label style
        self.styles.add(ParagraphStyle(
            name='CostLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#7f8c8d'),
            alignment=TA_CENTER,
            spaceAfter=6,
        ))

        # Footer style
        self.styles.add(ParagraphStyle(
            name='Footer',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#999999'),
            alignment=TA_CENTER,
        ))

        # Custom bullet style
        self.styles.add(ParagraphStyle(
            name='CustomBullet',
            parent=self.styles['Normal'],
            fontSize=11,
            leftIndent=20,
            bulletIndent=10,
        ))

    def _sanitize_text_for_paragraph(self, text: str) -> str:
        """
        Sanitize text for safe use in ReportLab Paragraph.

        Removes or escapes HTML tags that ReportLab cannot handle.
        Preserves basic formatting tags that ReportLab supports.

        Args:
            text: Raw text that may contain HTML

        Returns:
            Sanitized text safe for Paragraph
        """
        if not text:
            return ""

        # Strip unsupported HTML tags completely
        unsupported_tags = [
            'table', 'tr', 'td', 'th', 'thead', 'tbody',
            'div', 'span', 'section', 'article', 'header',
            'footer', 'nav', 'aside', 'main', 'figure',
            'style', 'script', 'iframe', 'video', 'audio',
        ]

        for tag in unsupported_tags:
            # Remove opening and closing tags
            text = re.sub(f'<{tag}[^>]*>', '', text, flags=re.IGNORECASE)
            text = re.sub(f'</{tag}>', '', text, flags=re.IGNORECASE)

        # Remove anchor tags but keep the content
        text = re.sub(r'<a\s+id=["\'][^"\']*["\'][^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<a\s+name=["\'][^"\']*["\'][^>]*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'</a>', '', text, flags=re.IGNORECASE)

        # Convert links to plain text with URL shown
        text = re.sub(
            r'<a\s+href=["\']([^"\']*)["\'][^>]*>([^<]*)</a>',
            r'\2 (\1)',
            text,
            flags=re.IGNORECASE
        )

        # Remove any remaining unclosed or malformed tags
        text = re.sub(r'<[^>]*$', '', text)  # Unclosed tag at end

        # Escape special characters for ReportLab
        # But keep basic tags that ReportLab supports: b, i, u, br
        # First, protect these tags with placeholders that won't be escaped
        text = re.sub(r'<b>', '\x00B\x00', text, flags=re.IGNORECASE)
        text = re.sub(r'</b>', '\x00/B\x00', text, flags=re.IGNORECASE)
        text = re.sub(r'<i>', '\x00I\x00', text, flags=re.IGNORECASE)
        text = re.sub(r'</i>', '\x00/I\x00', text, flags=re.IGNORECASE)
        text = re.sub(r'<u>', '\x00U\x00', text, flags=re.IGNORECASE)
        text = re.sub(r'</u>', '\x00/U\x00', text, flags=re.IGNORECASE)
        text = re.sub(r'<br\s*/?>', '\x00BR\x00', text, flags=re.IGNORECASE)

        # Escape remaining HTML
        text = html.escape(text, quote=False)

        # Restore protected tags
        text = text.replace('\x00B\x00', '<b>')
        text = text.replace('\x00/B\x00', '</b>')
        text = text.replace('\x00I\x00', '<i>')
        text = text.replace('\x00/I\x00', '</i>')
        text = text.replace('\x00U\x00', '<u>')
        text = text.replace('\x00/U\x00', '</u>')
        text = text.replace('\x00BR\x00', '<br/>')

        return text.strip()

    def _safe_add_paragraph(self, story: list, text: str, style) -> None:
        """
        Safely add a paragraph to the story with error handling.

        Args:
            story: PDF story list
            text: Text to add
            style: Paragraph style
        """
        if not text or not text.strip():
            return

        # First attempt: sanitized text
        sanitized = self._sanitize_text_for_paragraph(text)

        try:
            story.append(Paragraph(sanitized, style))
        except Exception as e:
            # Second attempt: fully escaped plain text
            try:
                plain_text = html.escape(text, quote=False)
                story.append(Paragraph(plain_text, style))
            except Exception as e2:
                # Last resort: add as plain text without Paragraph formatting
                # This should never fail
                try:
                    from reportlab.platypus import Preformatted
                    story.append(Preformatted(text[:500], style))
                except:
                    # If even this fails, skip this content
                    pass

    def generate_research_report_pdf(
        self,
        topic: str,
        report_content: str,
        stats: dict[str, Any],
        analytics: Optional[dict[str, Any]] = None,
        comparison_evaluations: Optional[list[dict]] = None,
        metric_names: Optional[list[str]] = None,
        ranked_papers: Optional[list[dict]] = None,
        ranked_patents: Optional[list[dict]] = None,
    ) -> Path:
        """
        Generate a professional business-quality PDF research report from structured data.

        CRITICAL: Does NOT use raw HTML/CSS from report_content. Generates clean
        structured content from source data only.

        Args:
            topic: Research topic
            report_content: Markdown report content (NOT USED - kept for backward compat)
            stats: Statistics dictionary
            analytics: Optional analytics data
            comparison_evaluations: Optional comparison matrix data
            metric_names: Optional list of metric names
            ranked_papers: Optional list of ranked paper objects
            ranked_patents: Optional list of ranked patent objects

        Returns:
            Path to generated PDF file
        """
        # Generate safe filename
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_'))[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"research_report_{safe_topic}_{timestamp}.pdf"
        filepath = self.output_dir / filename

        # Create PDF document with smaller margins for compact layout
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=40,
            bottomMargin=50,
        )

        story = []

        # ===== COMPACT HEADER INSTEAD OF FULL COVER PAGE =====
        self._build_research_compact_header(story, topic, stats)
        story.append(Spacer(1, 0.15 * inch))

        # ===== EXECUTIVE SUMMARY FROM STRUCTURED DATA =====
        self._build_executive_summary(
            story, topic, stats, ranked_papers, ranked_patents, comparison_evaluations
        )
        story.append(Spacer(1, 0.2 * inch))

        # ===== SOURCE COMPARISON MATRIX =====
        if comparison_evaluations and metric_names:
            self._build_comparison_matrix_section(
                story, comparison_evaluations, metric_names, ranked_papers, ranked_patents
            )
            story.append(PageBreak())

        # ===== TOP PATENTS SECTION =====
        if ranked_patents and len(ranked_patents) > 0:
            header_style = ParagraphStyle(
                name='CompactSectionHeader',
                parent=self.styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#1a5490'),
                fontName='Helvetica-Bold',
                spaceAfter=8,
            )
            story.append(Paragraph("Top Patents", header_style))

            for idx, patent in enumerate(ranked_patents[:3], 1):
                self._add_patent_details_compact(story, patent, idx)
                if idx < len(ranked_patents[:3]):
                    story.append(Spacer(1, 0.15 * inch))

            story.append(PageBreak())

        # ===== TOP PAPERS SECTION =====
        if ranked_papers and len(ranked_papers) > 0:
            header_style = ParagraphStyle(
                name='CompactSectionHeader',
                parent=self.styles['Normal'],
                fontSize=12,
                textColor=colors.HexColor('#1a5490'),
                fontName='Helvetica-Bold',
                spaceAfter=8,
            )
            story.append(Paragraph("Top Scientific Papers", header_style))

            for idx, paper in enumerate(ranked_papers[:3], 1):
                self._add_paper_details_compact(story, paper, idx)
                if idx < len(ranked_papers[:3]):
                    story.append(Spacer(1, 0.15 * inch))

            story.append(Spacer(1, 0.2 * inch))

        # ===== REFERENCES SECTION =====
        self._build_references_section(story, ranked_papers, ranked_patents)

        # Build PDF with page numbers
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

        return filepath

    def generate_usage_report_pdf(
        self,
        topic: str,
        analytics: dict[str, Any],
    ) -> Path:
        """
        Generate a professional AI execution analytics PDF with charts.
        Compact layout with minimal white space.

        Args:
            topic: Research topic
            analytics: Analytics data dictionary

        Returns:
            Path to generated PDF file
        """
        # Generate safe filename
        safe_topic = "".join(c for c in topic if c.isalnum() or c in (' ', '-', '_'))[:50]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"ai_usage_analytics_{safe_topic}_{timestamp}.pdf"
        filepath = self.output_dir / filename

        # Create PDF document with smaller margins
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=40,
            bottomMargin=50,
        )

        story = []

        # ===== PAGE 1: COMPACT HEADER + SUMMARY + WORKFLOW =====
        self._build_usage_compact_header(story, topic, analytics)
        story.append(Spacer(1, 0.15 * inch))

        self._build_usage_executive_summary(story, analytics)
        story.append(Spacer(1, 0.2 * inch))

        self._build_workflow_pipeline_table(story, analytics)
        story.append(PageBreak())

        # ===== PAGE 2+: CHARTS =====
        self._build_usage_charts(story, analytics)

        # ===== DETAILED STEP BREAKDOWN TABLE =====
        story.append(Spacer(1, 0.2 * inch))
        self._build_per_step_breakdown_table(story, analytics)

        # ===== OBSERVABILITY + DISCLAIMER =====
        story.append(Spacer(1, 0.25 * inch))
        self._build_observability_and_disclaimer(story, analytics)

        # Build PDF with page numbers
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)

        return filepath

    def _build_usage_compact_header(
        self,
        story: list,
        topic: str,
        analytics: dict[str, Any]
    ) -> None:
        """
        Build compact header for usage analytics report (no full cover page).

        Args:
            story: PDF story list
            topic: Research topic
            analytics: Analytics dictionary
        """
        # Title
        title_style = ParagraphStyle(
            name='CompactTitle',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=6,
        )
        story.append(Paragraph("AI Execution Analytics Report", title_style))

        # Topic
        topic_style = ParagraphStyle(
            name='CompactTopic',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER,
            spaceAfter=4,
        )
        story.append(Paragraph(self._escape_text(topic), topic_style))

        # Metadata row
        report_date = datetime.now().strftime('%Y-%m-%d')
        execution_date = analytics.get('start_time', 'N/A')
        if isinstance(execution_date, str) and len(execution_date) > 10:
            execution_date = execution_date[:10]

        cache_status = analytics.get('cache_status', 'N/A')

        metadata_text = (
            f"<b>Report Date:</b> {report_date} | "
            f"<b>Execution:</b> {execution_date} | "
            f"<b>Cache:</b> {cache_status}"
        )

        metadata_style = ParagraphStyle(
            name='CompactMetadata',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=4,
        )
        story.append(Paragraph(metadata_text, metadata_style))

        # Disclaimer note
        disclaimer_style = ParagraphStyle(
            name='CompactDisclaimer',
            parent=self.styles['Normal'],
            fontSize=7,
            textColor=colors.HexColor('#999999'),
            alignment=TA_CENTER,
            spaceAfter=0,
        )
        story.append(Paragraph(
            "<i>Cost estimates are approximate and for informational purposes only.</i>",
            disclaimer_style
        ))

    def _build_usage_executive_summary(
        self,
        story: list,
        analytics: dict[str, Any]
    ) -> None:
        """
        Build compact executive summary for usage analytics.

        Args:
            story: PDF story list
            analytics: Analytics dictionary
        """
        header_style = ParagraphStyle(
            name='CompactSectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a5490'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
        )
        story.append(Paragraph("Executive Usage Summary", header_style))

        # Determine analytics source
        analytics_source = analytics.get('analytics_source') or analytics.get('source', 'Local tracker')

        # Format values with "Not available" fallback
        def format_value(value, formatter=None):
            if value is None or (isinstance(value, str) and value == ''):
                return 'Not available'
            if formatter:
                return formatter(value)
            return str(value)

        # Key metrics in 2-column compact table
        summary_data = [
            ["Metric", "Value"],
            ["Analytics Source", analytics_source],
            ["Current Run Duration", format_value(analytics.get('total_duration_seconds'), lambda v: f"{v:.2f}s")],
            ["LLM Calls", format_value(analytics.get('total_llm_calls', 0))],
            ["Prompt Tokens", format_value(analytics.get('total_prompt_tokens'), lambda v: f"{v:,}")],
            ["Completion Tokens", format_value(analytics.get('total_completion_tokens'), lambda v: f"{v:,}")],
            ["Total Tokens", format_value(analytics.get('total_tokens'), lambda v: f"{v:,}")],
            ["Estimated Cost", format_value(analytics.get('estimated_total_cost'), lambda v: f"${v:.4f}")],
            ["Papers Found", format_value(analytics.get('papers_found', 0))],
            ["Patents Found", format_value(analytics.get('patents_found', 0))],
        ]

        summary_table = Table(summary_data, colWidths=[2.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('BACKGROUND', (0, 1), (0, -1), colors.HexColor('#f5f5f5')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # Header centered
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Metric labels centered
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Values centered
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('LINEBELOW', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ]))
        story.append(summary_table)

    def _build_usage_charts(
        self,
        story: list,
        analytics: dict[str, Any]
    ) -> None:
        """
        Build compact charts for usage analytics using matplotlib.
        2 charts per page in portrait layout.

        Args:
            story: PDF story list
            analytics: Analytics dictionary
        """
        header_style = ParagraphStyle(
            name='CompactSectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a5490'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
        )
        story.append(Paragraph("Performance Visualizations", header_style))

        if not MATPLOTLIB_AVAILABLE:
            story.append(Paragraph(
                "<i>Charts require matplotlib. Install with: pip install matplotlib</i>",
                self.styles['Normal']
            ))
            return

        steps = analytics.get('steps', [])
        if not steps or len(steps) == 0:
            story.append(Paragraph("<i>No step data available for visualization.</i>", self.styles['Normal']))
            return

        # Generate charts (smaller, 2 per page)
        try:
            # Chart 1: Duration by step
            duration_chart = self._create_duration_chart(steps)
            if duration_chart:
                story.append(duration_chart)
                story.append(Spacer(1, 0.15 * inch))

            # Chart 2: Tokens by step
            tokens_chart = self._create_tokens_chart(steps)
            if tokens_chart:
                story.append(tokens_chart)
                story.append(PageBreak())

            # Chart 3: Cost by step (new page)
            cost_chart = self._create_cost_chart(steps)
            if cost_chart:
                story.append(cost_chart)
                story.append(Spacer(1, 0.15 * inch))

            # Chart 4: Prompt vs Completion tokens
            token_split_chart = self._create_token_split_chart(steps)
            if token_split_chart:
                story.append(token_split_chart)

        except Exception as e:
            story.append(Paragraph(
                f"<i>Charts could not be generated: {str(e)}</i>",
                self.styles['Normal']
            ))

    def _build_workflow_pipeline_table(
        self,
        story: list,
        analytics: dict[str, Any]
    ) -> None:
        """
        Build compact workflow pipeline table with shortened step names.

        Args:
            story: PDF story list
            analytics: Analytics dictionary
        """
        header_style = ParagraphStyle(
            name='CompactSectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a5490'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
        )
        story.append(Paragraph("Workflow Pipeline", header_style))

        steps = analytics.get('steps', [])
        if not steps:
            story.append(Paragraph("<i>No workflow steps available.</i>", self.styles['Normal']))
            return

        # Map long step names to shorter versions
        step_name_mapping = {
            "Fetch and Parse Research Sources": "Fetch Sources",
            "Rank and Filter Research Sources": "Rank Sources",
            "Generate Research Metrics": "Generate Metrics",
            "Evaluate Comparison Matrix": "Evaluate Matrix",
            "Generate Research Report": "Generate Report",
        }

        # Build workflow table
        workflow_data = [["#", "Step Name", "Duration", "Calls", "Tokens", "Cost"]]

        for i, step in enumerate(steps, 1):
            step_name = step.get('step_name', 'N/A')
            # Apply name mapping if available
            short_name = step_name_mapping.get(step_name, step_name)
            # Truncate if still too long
            if len(short_name) > 20:
                short_name = short_name[:18] + ".."

            duration = step.get('duration_seconds', 0)
            llm_calls = step.get('llm_calls', 0)
            tokens = step.get('total_tokens', 0)
            cost = step.get('estimated_cost', 0)

            workflow_data.append([
                str(i),
                short_name,
                f"{duration:.1f}s" if duration else "-",
                str(llm_calls) if llm_calls > 0 else "-",
                f"{tokens:,}" if tokens > 0 else "-",
                f"${cost:.3f}" if cost > 0 else "-",
            ])

        workflow_table = Table(
            workflow_data,
            colWidths=[0.3*inch, 2.2*inch, 0.7*inch, 0.5*inch, 0.9*inch, 0.7*inch]
        )
        workflow_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # All headers centered
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Step numbers centered
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Step names left-aligned (long text)
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'), # All other values centered
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))

        story.append(workflow_table)

    def _build_per_step_breakdown_table(
        self,
        story: list,
        analytics: dict[str, Any]
    ) -> None:
        """
        Build detailed per-step breakdown as a compact table.

        Args:
            story: PDF story list
            analytics: Analytics dictionary
        """
        header_style = ParagraphStyle(
            name='CompactSectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a5490'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
        )
        story.append(Paragraph("Detailed Step Breakdown", header_style))

        steps = analytics.get('steps', [])
        if not steps:
            story.append(Paragraph("<i>No step data available.</i>", self.styles['Normal']))
            return

        # Map long step names to shorter versions
        step_name_mapping = {
            "Fetch and Parse Research Sources": "Fetch Sources",
            "Rank and Filter Research Sources": "Rank Sources",
            "Generate Research Metrics": "Generate Metrics",
            "Evaluate Comparison Matrix": "Evaluate Matrix",
            "Generate Research Report": "Generate Report",
        }

        # Build detailed table
        breakdown_data = [[
            "Step", "Duration", "Calls", "Prompt\nTokens",
            "Compl.\nTokens", "Total\nTokens", "Est. Cost"
        ]]

        for i, step in enumerate(steps, 1):
            step_name = step.get('step_name', 'N/A')
            short_name = step_name_mapping.get(step_name, step_name[:15])

            duration = step.get('duration_seconds', 0)
            llm_calls = step.get('llm_calls', 0)
            prompt_tokens = step.get('prompt_tokens', 0)
            completion_tokens = step.get('completion_tokens', 0)
            total_tokens = step.get('total_tokens', 0)
            cost = step.get('estimated_cost', 0)

            breakdown_data.append([
                short_name,
                f"{duration:.1f}s" if duration else "-",
                str(llm_calls) if llm_calls > 0 else "-",
                f"{prompt_tokens:,}" if prompt_tokens > 0 else "-",
                f"{completion_tokens:,}" if completion_tokens > 0 else "-",
                f"{total_tokens:,}" if total_tokens > 0 else "-",
                f"${cost:.3f}" if cost > 0 else "-",
            ])

        breakdown_table = Table(
            breakdown_data,
            colWidths=[1.5*inch, 0.6*inch, 0.4*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.6*inch]
        )
        breakdown_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # All headers centered
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),    # Step names left-aligned (long text)
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'), # All numeric values centered
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))

        story.append(breakdown_table)

    def _create_duration_chart(self, steps: list[dict]) -> Optional[Image]:
        """
        Create duration by step bar chart with proper label handling.

        Args:
            steps: List of step dictionaries

        Returns:
            ReportLab Image or None
        """
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            # Map long step names to shorter versions
            step_name_mapping = {
                "Fetch and Parse Research Sources": "Fetch Sources",
                "Rank and Filter Research Sources": "Rank Sources",
                "Generate Research Metrics": "Generate Metrics",
                "Evaluate Comparison Matrix": "Evaluate Matrix",
                "Generate Research Report": "Generate Report",
            }

            # Extract data with shortened names
            step_names = []
            for i, s in enumerate(steps, 1):
                name = s.get('step_name', f"Step {i}")
                short_name = step_name_mapping.get(name, name[:20])
                step_names.append(short_name)

            durations = [s.get('duration_seconds', 0) for s in steps]

            # Create figure with more space for labels
            fig, ax = plt.subplots(figsize=(6.5, 2.5))
            bars = ax.barh(step_names, durations, color='#2c3e50')
            ax.set_xlabel('Duration (seconds)', fontsize=9)
            ax.set_title('Execution Duration by Step', fontsize=10, fontweight='bold')
            ax.grid(axis='x', alpha=0.3)
            ax.tick_params(axis='y', labelsize=8)
            ax.tick_params(axis='x', labelsize=8)

            # Highlight longest step
            if durations:
                max_idx = durations.index(max(durations))
                bars[max_idx].set_color('#d9534f')

            # Adjust layout to prevent label cutoff
            plt.subplots_adjust(left=0.25)
            plt.tight_layout()

            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            # Create ReportLab Image (smaller)
            img = Image(buf, width=5*inch, height=2.2*inch)
            return img

        except Exception:
            return None

    def _create_tokens_chart(self, steps: list[dict]) -> Optional[Image]:
        """
        Create tokens by step bar chart with proper label handling.

        Args:
            steps: List of step dictionaries

        Returns:
            ReportLab Image or None
        """
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            # Map long step names to shorter versions
            step_name_mapping = {
                "Fetch and Parse Research Sources": "Fetch Sources",
                "Rank and Filter Research Sources": "Rank Sources",
                "Generate Research Metrics": "Generate Metrics",
                "Evaluate Comparison Matrix": "Evaluate Matrix",
                "Generate Research Report": "Generate Report",
            }

            # Extract data with shortened names
            step_names = []
            for i, s in enumerate(steps, 1):
                name = s.get('step_name', f"Step {i}")
                short_name = step_name_mapping.get(name, name[:20])
                step_names.append(short_name)

            tokens = [s.get('total_tokens', 0) for s in steps]

            # Create figure with more space for labels
            fig, ax = plt.subplots(figsize=(6.5, 2.5))
            bars = ax.barh(step_names, tokens, color='#2d7d46')
            ax.set_xlabel('Total Tokens', fontsize=9)
            ax.set_title('Token Usage by Step', fontsize=10, fontweight='bold')
            ax.grid(axis='x', alpha=0.3)
            ax.tick_params(axis='y', labelsize=8)
            ax.tick_params(axis='x', labelsize=8)

            # Highlight highest token step
            if tokens:
                max_idx = tokens.index(max(tokens))
                bars[max_idx].set_color('#f39c12')

            # Adjust layout to prevent label cutoff
            plt.subplots_adjust(left=0.25)
            plt.tight_layout()

            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            # Create ReportLab Image (smaller)
            img = Image(buf, width=5*inch, height=2.2*inch)
            return img

        except Exception:
            return None

    def _create_cost_chart(self, steps: list[dict]) -> Optional[Image]:
        """
        Create cost by step bar chart with proper label handling.

        Args:
            steps: List of step dictionaries

        Returns:
            ReportLab Image or None
        """
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            # Map long step names to shorter versions
            step_name_mapping = {
                "Fetch and Parse Research Sources": "Fetch Sources",
                "Rank and Filter Research Sources": "Rank Sources",
                "Generate Research Metrics": "Generate Metrics",
                "Evaluate Comparison Matrix": "Evaluate Matrix",
                "Generate Research Report": "Generate Report",
            }

            # Extract data with shortened names
            step_names = []
            for i, s in enumerate(steps, 1):
                name = s.get('step_name', f"Step {i}")
                short_name = step_name_mapping.get(name, name[:20])
                step_names.append(short_name)

            costs = [s.get('estimated_cost', 0) for s in steps]

            # Create figure with more space for labels
            fig, ax = plt.subplots(figsize=(6.5, 2.5))
            bars = ax.barh(step_names, costs, color='#8e44ad')
            ax.set_xlabel('Estimated Cost ($)', fontsize=9)
            ax.set_title('Estimated Cost by Step', fontsize=10, fontweight='bold')
            ax.grid(axis='x', alpha=0.3)
            ax.tick_params(axis='y', labelsize=8)
            ax.tick_params(axis='x', labelsize=8)

            # Highlight most expensive step
            if costs:
                max_idx = costs.index(max(costs))
                bars[max_idx].set_color('#e74c3c')

            # Adjust layout to prevent label cutoff
            plt.subplots_adjust(left=0.25)
            plt.tight_layout()

            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            # Create ReportLab Image (smaller)
            img = Image(buf, width=5*inch, height=2.2*inch)
            return img

        except Exception:
            return None

    def _create_token_split_chart(self, steps: list[dict]) -> Optional[Image]:
        """
        Create stacked bar chart showing prompt vs completion tokens.

        Args:
            steps: List of step dictionaries

        Returns:
            ReportLab Image or None
        """
        if not MATPLOTLIB_AVAILABLE:
            return None

        try:
            # Map long step names to shorter versions
            step_name_mapping = {
                "Fetch and Parse Research Sources": "Fetch Sources",
                "Rank and Filter Research Sources": "Rank Sources",
                "Generate Research Metrics": "Generate Metrics",
                "Evaluate Comparison Matrix": "Evaluate Matrix",
                "Generate Research Report": "Generate Report",
            }

            # Extract data with shortened names
            step_names = []
            for i, s in enumerate(steps, 1):
                name = s.get('step_name', f"Step {i}")
                short_name = step_name_mapping.get(name, name[:20])
                step_names.append(short_name)

            prompt_tokens = [s.get('prompt_tokens', 0) for s in steps]
            completion_tokens = [s.get('completion_tokens', 0) for s in steps]

            # Create figure
            fig, ax = plt.subplots(figsize=(6.5, 2.5))

            # Stacked horizontal bar chart
            ax.barh(step_names, prompt_tokens, label='Prompt', color='#3498db')
            ax.barh(step_names, completion_tokens, left=prompt_tokens,
                   label='Completion', color='#e67e22')

            ax.set_xlabel('Tokens', fontsize=9)
            ax.set_title('Prompt vs Completion Tokens by Step', fontsize=10, fontweight='bold')
            ax.legend(fontsize=8, loc='lower right')
            ax.grid(axis='x', alpha=0.3)
            ax.tick_params(axis='y', labelsize=8)
            ax.tick_params(axis='x', labelsize=8)

            # Adjust layout to prevent label cutoff
            plt.subplots_adjust(left=0.25)
            plt.tight_layout()

            # Save to bytes buffer
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            # Create ReportLab Image
            img = Image(buf, width=5*inch, height=2.2*inch)
            return img

        except Exception:
            return None

    def _build_observability_and_disclaimer(
        self,
        story: list,
        analytics: dict[str, Any]
    ) -> None:
        """
        Build compact observability section and disclaimer.

        Args:
            story: PDF story list
            analytics: Analytics dictionary
        """
        # Observability section (only if trace info exists and is real)
        trace_id = analytics.get('langsmith_trace_id')
        trace_url = analytics.get('langsmith_trace_url')

        # Check if trace info is real (not placeholder)
        has_real_trace = False
        if trace_id and trace_id != 'abc123' and 'abc123' not in str(trace_id):
            has_real_trace = True
        if trace_url and trace_url != 'https://smith.langchain.com/o/...' and '...' not in trace_url:
            has_real_trace = True

        if has_real_trace:
            header_style = ParagraphStyle(
                name='CompactSectionHeader',
                parent=self.styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#1a5490'),
                fontName='Helvetica-Bold',
                spaceAfter=6,
            )
            story.append(Paragraph("Observability & Tracing", header_style))

            observability_data = []
            if trace_id and trace_id != 'abc123':
                observability_data.append(["LangSmith Trace ID", trace_id])
            else:
                observability_data.append(["LangSmith Trace ID", "Not available"])

            if trace_url and '...' not in trace_url:
                display_url = trace_url if len(trace_url) < 70 else trace_url[:67] + "..."
                observability_data.append(["Trace URL", display_url])
            else:
                observability_data.append(["Trace URL", "Not available"])

            obs_table = Table(observability_data, colWidths=[1.5*inch, 4*inch])
            obs_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Labels left-aligned
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # URLs left-aligned (long text)
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
            ]))
            story.append(obs_table)
            story.append(Spacer(1, 0.2 * inch))

        # Analytics source information
        analytics_source = analytics.get('analytics_source') or analytics.get('source', 'Local tracker')
        is_langsmith = 'LangSmith' in analytics_source

        source_style = ParagraphStyle(
            name='SourceText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6,
        )

        if is_langsmith:
            story.append(Paragraph(
                f"<b>Analytics Source:</b> {analytics_source} — "
                "Usage data retrieved from LangSmith traces based on actual LLM API calls.",
                source_style
            ))
        else:
            story.append(Paragraph(
                f"<b>Analytics Source:</b> {analytics_source} — "
                "LangSmith tracing was not enabled or unavailable for this run.",
                source_style
            ))

        # Disclaimer
        disclaimer_style = ParagraphStyle(
            name='DisclaimerText',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=TA_JUSTIFY,
        )
        story.append(Paragraph(
            "<b>Usage Estimate Disclaimer:</b> The cost estimates in this report are based on "
            "approximate model pricing and token counts. <b>This is AI execution analytics, not an official invoice.</b> "
            "Actual costs may vary based on your provider's pricing, contract terms, and usage patterns. "
            "This report is provided for informational and analytical purposes only.",
            disclaimer_style
        ))

    def _add_page_number(self, canvas, doc) -> None:
        """
        Add page number and footer to each page.

        Args:
            canvas: ReportLab canvas
            doc: Document object
        """
        page_num = canvas.getPageNumber()
        footer_text = f"Page {page_num} | Generated by Research Intelligence Assistant"

        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#999999'))
        canvas.drawCentredString(
            letter[0] / 2,
            30,
            footer_text
        )
        canvas.restoreState()

    def _build_research_compact_header(
        self,
        story: list,
        topic: str,
        stats: dict[str, Any]
    ) -> None:
        """
        Build compact header for research report (no full cover page).

        Args:
            story: PDF story list
            topic: Research topic
            stats: Statistics dictionary
        """
        # Title
        title_style = ParagraphStyle(
            name='CompactResearchTitle',
            parent=self.styles['Normal'],
            fontSize=16,
            textColor=colors.HexColor('#1a1a1a'),
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
            spaceAfter=6,
        )
        story.append(Paragraph("Research Intelligence Report", title_style))

        # Subtitle
        subtitle_style = ParagraphStyle(
            name='CompactResearchSubtitle',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=4,
        )
        story.append(Paragraph("Patent and Scientific Literature Benchmark Report", subtitle_style))

        # Topic
        topic_style = ParagraphStyle(
            name='CompactTopic',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            alignment=TA_CENTER,
            spaceAfter=4,
        )
        story.append(Paragraph(self._escape_text(topic), topic_style))

        # Metadata row
        report_date = datetime.now().strftime('%Y-%m-%d')
        cache_status = stats.get('cache_status', 'Standard')
        total_sources = stats.get('total_raw_items', 0)

        metadata_text = (
            f"<b>Date:</b> {report_date} | "
            f"<b>Mode:</b> {cache_status} | "
            f"<b>Total Sources:</b> {total_sources}"
        )

        metadata_style = ParagraphStyle(
            name='CompactMetadata',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER,
            spaceAfter=0,
        )
        story.append(Paragraph(metadata_text, metadata_style))

    def _build_cover_page(self, story: list, topic: str, stats: dict[str, Any]) -> None:
        """
        Build professional cover page for research report (DEPRECATED - use compact header).

        Args:
            story: PDF story list
            topic: Research topic
            stats: Statistics dictionary
        """
        # Add vertical space to center content
        story.append(Spacer(1, 2 * inch))

        # Main title
        story.append(Paragraph(
            "Research Intelligence Report",
            self.styles['CoverTitle']
        ))
        story.append(Spacer(1, 0.3 * inch))

        # Subtitle
        story.append(Paragraph(
            "Patent and Scientific Literature Benchmark Report",
            self.styles['CoverSubtitle']
        ))
        story.append(Spacer(1, 1.5 * inch))

        # Topic section
        story.append(Paragraph(
            f"<b>Research Topic:</b>",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(
            f"{self._escape_text(topic)}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 0.4 * inch))

        # Report metadata
        report_date = datetime.now().strftime('%B %d, %Y')
        report_time = datetime.now().strftime('%I:%M %p')

        metadata = [
            ["Generated Date:", report_date],
            ["Generated Time:", report_time],
            ["Research Mode:", str(stats.get('cache_status', 'Standard'))],
            ["Total Sources:", str(stats.get('total_raw_items', 0))],
        ]

        metadata_table = Table(metadata, colWidths=[2*inch, 3*inch])
        metadata_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(metadata_table)

        # Footer on cover page
        story.append(Spacer(1, 1.5 * inch))
        story.append(Paragraph(
            "Research Intelligence Assistant",
            self.styles['Footer']
        ))

    def _build_executive_summary(
        self,
        story: list,
        topic: str,
        stats: dict[str, Any],
        ranked_papers: Optional[list[dict]],
        ranked_patents: Optional[list[dict]],
        comparison_evaluations: Optional[list[dict]],
    ) -> None:
        """
        Build executive summary from structured data (NO raw HTML/CSS).

        Args:
            story: PDF story list
            topic: Research topic
            stats: Statistics dictionary
            ranked_papers: List of ranked papers
            ranked_patents: List of ranked patents
            comparison_evaluations: Comparison matrix data
        """
        header_style = ParagraphStyle(
            name='CompactSectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a5490'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
        )
        story.append(Paragraph("Executive Summary", header_style))

        # Build single formal paragraph summary
        total_papers = stats.get('papers_found', 0)
        total_patents = stats.get('patents_found', 0)
        oa_papers = stats.get('open_access_papers_found', 0)
        metrics_count = stats.get('metrics_generated', 0)

        summary_text = (
            f"This report summarizes patents and scientific papers related to "
            f"<b>{self._escape_text(topic)}</b>. Sources are compared across selected "
            f"technical and application metrics to highlight coverage, gaps, and relevance."
        )

        summary_style = ParagraphStyle(
            name='SummaryParagraph',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        )
        story.append(Paragraph(summary_text, summary_style))

        story.append(Spacer(1, 0.08 * inch))

        # Single compact header line with key statistics
        report_date = datetime.now().strftime('%Y-%m-%d')
        cache_status = stats.get('cache_status', 'Standard')

        stats_text = (
            f"<b>Topic:</b> {self._escape_text(topic)[:50]}... | "
            f"<b>Date:</b> {report_date} | "
            f"<b>Mode:</b> {cache_status} | "
            f"<b>Papers:</b> {total_papers} | "
            f"<b>Patents:</b> {total_patents} | "
            f"<b>Open Access:</b> {oa_papers} | "
            f"<b>Metrics:</b> {metrics_count}"
        )

        stats_style = ParagraphStyle(
            name='StatsLine',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#666666'),
            spaceAfter=0,
        )
        story.append(Paragraph(stats_text, stats_style))

    def _build_comparison_matrix_section(
        self,
        story: list,
        comparison_evaluations: list[dict],
        metric_names: list[str],
        ranked_papers: list[dict],
        ranked_patents: list[dict],
    ) -> None:
        """
        Build comparison matrix section with professional layout.

        Args:
            story: PDF story list
            comparison_evaluations: List of source evaluations
            metric_names: List of metric names
            ranked_papers: List of ranked papers
            ranked_patents: List of ranked patents
        """
        header_style = ParagraphStyle(
            name='CompactSectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a5490'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
        )
        story.append(Paragraph("Source Comparison Matrix", header_style))

        desc_style = ParagraphStyle(
            name='CompactDescription',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=8,
        )
        story.append(Paragraph(
            "Matrix evaluates source coverage of key metrics. Sources ranked by overall percentage.",
            desc_style
        ))

        # Build matrix table
        matrix_table = self._build_comparison_matrix_table_structured(
            comparison_evaluations,
            metric_names,
            ranked_papers,
            ranked_patents
        )

        if matrix_table:
            story.append(matrix_table)
            story.append(Spacer(1, 0.08 * inch))

            # Add simple text legend (no table)
            legend_style = ParagraphStyle(
                name='LegendText',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=colors.HexColor('#666666'),
                spaceAfter=0,
            )
            story.append(Paragraph(
                "<b>Legend:</b> YES = Fully Matched | PART = Partially Covered | NO = Not Covered",
                legend_style
            ))

    def _build_source_index_table(
        self,
        story: list,
        ranked_papers: Optional[list[dict]],
        ranked_patents: Optional[list[dict]],
    ) -> None:
        """
        Build source index table mapping short labels to full source information.

        Args:
            story: PDF story list
            ranked_papers: List of ranked papers
            ranked_patents: List of ranked patents
        """
        header_style = ParagraphStyle(
            name='CompactSectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a5490'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
        )
        story.append(Paragraph("Source Index", header_style))

        desc_style = ParagraphStyle(
            name='CompactDescription',
            parent=self.styles['Normal'],
            fontSize=9,
            spaceAfter=8,
        )
        story.append(Paragraph(
            "Full details for sources referenced in the comparison matrix.",
            desc_style
        ))

        # Build source index data
        index_data = [["Label", "Type", "Title", "Year", "Relevance"]]

        # Add patents
        if ranked_patents:
            for idx, patent in enumerate(ranked_patents[:3], 1):
                label = f"Patent {idx}"
                title = patent.get('title', 'Unknown')[:60] + "..."
                year = str(patent.get('publication_date', 'N/A'))[:4]
                relevance = f"{patent.get('relevance_score', 0.0):.2f}"

                index_data.append([label, "Patent", title, year, relevance])

        # Add papers
        if ranked_papers:
            for idx, paper in enumerate(ranked_papers[:3], 1):
                label = f"Paper {idx}"
                title = paper.get('title', 'Unknown')[:60] + "..."
                year = str(paper.get('publication_date', 'N/A'))[:4]
                relevance = f"{paper.get('relevance_score', 0.0):.2f}"

                index_data.append([label, "Paper", title, year, relevance])

        # Create table
        index_table = Table(index_data, colWidths=[0.8*inch, 0.7*inch, 3.5*inch, 0.6*inch, 0.9*inch])
        index_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),  # All headers centered
            ('ALIGN', (0, 1), (1, -1), 'CENTER'),  # Label and Type centered
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Title left-aligned (long text)
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Year centered
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),  # Relevance centered
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))

        story.append(index_table)

    def _build_references_section(
        self,
        story: list,
        ranked_papers: Optional[list[dict]],
        ranked_patents: Optional[list[dict]],
    ) -> None:
        """
        Build formal references section.

        Args:
            story: PDF story list
            ranked_papers: List of ranked papers
            ranked_patents: List of ranked patents
        """
        header_style = ParagraphStyle(
            name='CompactSectionHeader',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1a5490'),
            fontName='Helvetica-Bold',
            spaceAfter=8,
        )
        story.append(Paragraph("References", header_style))

        ref_style = ParagraphStyle(
            name='CompactReference',
            parent=self.styles['Normal'],
            fontSize=8,
            spaceAfter=6,
        )

        # Patent references
        if ranked_patents and len(ranked_patents) > 0:
            subsection_style = ParagraphStyle(
                name='CompactSubsection',
                parent=self.styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#34495e'),
                fontName='Helvetica-Bold',
                spaceAfter=6,
            )
            story.append(Paragraph("<b>Patent References</b>", subsection_style))

            for idx, patent in enumerate(ranked_patents[:3], 1):
                ref_text = self._format_patent_reference(patent, idx)
                self._safe_add_paragraph(story, ref_text, ref_style)

            story.append(Spacer(1, 0.12 * inch))

        # Paper references
        if ranked_papers and len(ranked_papers) > 0:
            subsection_style = ParagraphStyle(
                name='CompactSubsection',
                parent=self.styles['Normal'],
                fontSize=10,
                textColor=colors.HexColor('#34495e'),
                fontName='Helvetica-Bold',
                spaceAfter=6,
            )
            story.append(Paragraph("<b>Scientific Paper References</b>", subsection_style))

            for idx, paper in enumerate(ranked_papers[:3], 1):
                ref_text = self._format_paper_reference(paper, idx)
                self._safe_add_paragraph(story, ref_text, ref_style)

        # Footer is now handled by _add_page_number callback

    def _escape_text(self, text: str) -> str:
        """
        Escape text for safe use in PDF.

        Args:
            text: Text to escape

        Returns:
            Escaped text
        """
        if not text:
            return ""
        return html.escape(str(text), quote=False)

    def _sanitize_non_latin_text(self, text: str, field_name: str = "text") -> str:
        """
        Sanitize text to handle non-Latin characters properly.
        Replaces unsupported characters to avoid black squares.

        Args:
            text: Text to sanitize
            field_name: Field name for replacement message

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Try to encode with latin-1 to detect non-Latin characters
        try:
            text.encode('latin-1')
            return text
        except UnicodeEncodeError:
            # Contains non-Latin characters
            # Check if it's mostly non-Latin (e.g., Chinese, Japanese, Korean)
            non_latin_count = sum(1 for c in text if ord(c) > 255)
            if non_latin_count > len(text) * 0.3:  # More than 30% non-Latin
                return f"[Non-Latin {field_name}]"
            else:
                # Mixed content - try to preserve Latin characters
                sanitized = ""
                for char in text:
                    if ord(char) <= 255:
                        sanitized += char
                    else:
                        sanitized += "?"
                return sanitized if sanitized.strip() else f"[Non-Latin {field_name}]"

    def _extract_section(self, content: str, section_header: str) -> str:
        """
        Extract a section from markdown content.

        Args:
            content: Full markdown content
            section_header: Section header to find (e.g., "## Executive Summary")

        Returns:
            Section content or empty string if not found
        """
        if section_header not in content:
            return ""

        start = content.find(section_header) + len(section_header)
        end = content.find("##", start)
        if end == -1:
            end = len(content)

        return content[start:end].strip()

    def _shorten_metric_name(self, metric_name: str) -> str:
        """
        Shorten long metric names for matrix headers.

        Args:
            metric_name: Full metric name

        Returns:
            Shortened metric name
        """
        # Mapping from long metric names to short labels
        metric_mapping = {
            "Tissue Cutting / Tissue Interaction Support": "Tissue\nCutting",
            "VR HMD Integration": "VR HMD",
            "Haptic Robot Support": "Haptic\nRobot",
            "Meshless Method Support": "Meshless",
            "Surgical Simulation Domain": "Surgical\nDomain",
            "GPU Support": "GPU",
            "AI-based": "AI",
            "AI Support": "AI",
            "Real-time Performance": "Real-time",
            "Collision Detection": "Collision\nDetect",
            "Deformable Body Simulation": "Deformable\nBody",
            "Soft Body Simulation": "Soft Body",
            "Physics-based": "Physics",
            "XPBD Support": "XPBD",
        }

        # Check if exact match exists
        if metric_name in metric_mapping:
            return metric_mapping[metric_name]

        # Otherwise, truncate and add line break if too long
        if len(metric_name) > 15:
            # Try to find a good breaking point
            words = metric_name.split()
            if len(words) > 1:
                mid = len(words) // 2
                return "\n".join([" ".join(words[:mid]), " ".join(words[mid:])])
            else:
                # Single long word - truncate
                return metric_name[:12] + "..."

        return metric_name

    def _build_comparison_matrix_table_structured(
        self,
        evaluations: list[dict],
        metric_names: list[str],
        ranked_papers: list[dict],
        ranked_patents: list[dict],
    ) -> Optional[Table]:
        """
        Build comparison matrix table from structured evaluation data.
        Uses text badges (YES/PART/NO) for clarity.

        Args:
            evaluations: List of source evaluation dicts
            metric_names: List of metric names
            ranked_papers: List of ranked paper dicts
            ranked_patents: List of ranked patent dicts

        Returns:
            Formatted Table object or None
        """
        if not evaluations or not metric_names:
            return None

        # Build source label mapping with clickable links
        source_labels = {}
        for idx, patent in enumerate(ranked_patents[:3], 1):
            source_id = self._get_source_id(patent)
            # Create clickable link to bookmark
            link_text = f'<a href="#patent{idx}" color="blue">Patent {idx}</a>'
            source_labels[source_id] = link_text

        for idx, paper in enumerate(ranked_papers[:3], 1):
            source_id = self._get_source_id(paper)
            # Create clickable link to bookmark
            link_text = f'<a href="#paper{idx}" color="blue">Paper {idx}</a>'
            source_labels[source_id] = link_text

        # Build table data with shortened metric names in header
        shortened_metrics = [self._shorten_metric_name(m) for m in metric_names]
        header = ["Source"] + shortened_metrics + ["Overall %"]
        table_data = [header]

        # Process evaluations (sorted by overall score)
        sorted_evals = sorted(evaluations, key=lambda e: e.get('overall_score', 0), reverse=True)

        # Define paragraph style for clickable source labels
        source_link_style = ParagraphStyle(
            name='SourceLink',
            parent=self.styles['Normal'],
            fontSize=7,
            alignment=TA_CENTER,
        )

        for evaluation in sorted_evals[:6]:  # Limit to top 6 for PDF
            source_id = evaluation.get('source_id', '')
            source_label_html = source_labels.get(source_id, 'Unknown')

            # Convert source label to Paragraph to support hyperlinks
            source_label_para = Paragraph(source_label_html, source_link_style)
            row = [source_label_para]

            # Add metric evaluations as text badges
            metric_evals = evaluation.get('metric_evaluations', [])
            metric_lookup = {m.get('metric_name'): m for m in metric_evals}

            for metric_name in metric_names:
                if metric_name in metric_lookup:
                    m_eval = metric_lookup[metric_name]
                    status = m_eval.get('status', 'none')
                    # Convert status to text badge
                    if status == 'full':
                        badge_text = "YES"
                    elif status == 'partial':
                        badge_text = "PART"
                    else:
                        badge_text = "NO"
                    row.append(badge_text)
                else:
                    row.append("NO")

            # Add overall percentage
            overall_score = evaluation.get('overall_score', 0.0)
            overall_pct = int(overall_score * 100)
            row.append(f"{overall_pct}%")

            table_data.append(row)

        # Add metric coverage row (shortened to avoid overflow)
        # Use plain text "Coverage" - TableStyle will handle bold and center alignment
        coverage_row = ["Coverage"]
        for metric_name in metric_names:
            total_score = 0.0
            count = 0
            for evaluation in sorted_evals[:6]:
                metric_evals = evaluation.get('metric_evaluations', [])
                for m_eval in metric_evals:
                    if m_eval.get('metric_name') == metric_name:
                        total_score += m_eval.get('score', 0.0)
                        count += 1
                        break

            avg_score = total_score / count if count > 0 else 0.0
            coverage_pct = int(avg_score * 100)
            coverage_row.append(f"{coverage_pct}%")

        coverage_row.append("-")
        table_data.append(coverage_row)

        # Create table with dynamic column widths
        num_cols = len(header)
        col_width = 6.5 * inch / num_cols  # Fit within page width
        col_widths = [col_width] * num_cols

        matrix_table = Table(table_data, colWidths=col_widths, repeatRows=1)

        # Apply styling with improved header and clear badge colors
        style_commands = [
            # Header row - dark navy background to stand out from heatmap
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F2937')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 7),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Data rows
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Metric coverage row - light gray background with centered bold text
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e5e7eb')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('ALIGN', (0, -1), (-1, -1), 'CENTER'),  # All Coverage row cells centered
        ]

        # Add row-based heatmap coloring for data rows (skip header and coverage row)
        for row_idx, evaluation in enumerate(sorted_evals[:6], 1):
            overall_score = evaluation.get('overall_score', 0.0)
            bg_color = self._score_to_color(overall_score)

            # Determine text color for source name and overall % based on background
            if overall_score >= 0.50:
                source_text_color = colors.white
                overall_text_color = colors.white
            else:
                source_text_color = colors.black
                overall_text_color = colors.black

            # Apply row background color
            style_commands.append(
                ('BACKGROUND', (0, row_idx), (-1, row_idx), colors.HexColor(bg_color))
            )

            # Source column text color
            style_commands.append(
                ('TEXTCOLOR', (0, row_idx), (0, row_idx), source_text_color)
            )
            style_commands.append(
                ('FONTNAME', (0, row_idx), (0, row_idx), 'Helvetica-Bold')
            )

            # Overall % column text color
            style_commands.append(
                ('TEXTCOLOR', (-1, row_idx), (-1, row_idx), overall_text_color)
            )
            style_commands.append(
                ('FONTNAME', (-1, row_idx), (-1, row_idx), 'Helvetica-Bold')
            )

        # Add individual cell styling for YES/PART/NO badges
        for row_idx in range(1, len(table_data) - 1):  # Skip header and coverage row
            for col_idx in range(1, num_cols - 1):  # Skip source and overall columns
                cell_value = table_data[row_idx][col_idx]

                if cell_value == "YES":
                    # Green badge
                    style_commands.append(
                        ('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#22c55e'))
                    )
                    style_commands.append(
                        ('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.white)
                    )
                    style_commands.append(
                        ('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'Helvetica-Bold')
                    )
                elif cell_value == "PART":
                    # Orange badge
                    style_commands.append(
                        ('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#f97316'))
                    )
                    style_commands.append(
                        ('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.white)
                    )
                    style_commands.append(
                        ('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'Helvetica-Bold')
                    )
                elif cell_value == "NO":
                    # Red badge
                    style_commands.append(
                        ('BACKGROUND', (col_idx, row_idx), (col_idx, row_idx), colors.HexColor('#ef4444'))
                    )
                    style_commands.append(
                        ('TEXTCOLOR', (col_idx, row_idx), (col_idx, row_idx), colors.white)
                    )
                    style_commands.append(
                        ('FONTNAME', (col_idx, row_idx), (col_idx, row_idx), 'Helvetica-Bold')
                    )

        matrix_table.setStyle(TableStyle(style_commands))

        return matrix_table

    def _score_to_color(self, score: float) -> str:
        """
        Convert overall score to heatmap color with improved gradation.

        Args:
            score: Score between 0.0 and 1.0

        Returns:
            Hex color string
        """
        if score >= 0.70:
            return "#2d7d46"  # dark green
        elif score >= 0.50:
            return "#70b77e"  # light green
        elif score >= 0.30:
            return "#f9e79f"  # yellow
        elif score >= 0.15:
            return "#f39c12"  # orange
        elif score >= 0.01:
            return "#ffb3b3"  # light red/pink
        else:  # 0%
            return "#e8d5d5"  # very light gray-red (distinct from low percentages)

    def _get_source_id(self, source: dict) -> str:
        """
        Get unique identifier for a source.

        Args:
            source: Source dictionary

        Returns:
            Unique identifier string
        """
        if source.get('doi'):
            return source['doi']
        if source.get('patent_number'):
            return source['patent_number']
        # Fallback to truncated title
        title = source.get('title', 'unknown')
        return title[:50].replace(" ", "_")

    def _add_patent_details_compact(self, story: list, patent: dict, index: int) -> None:
        """
        Add compact patent information to PDF story with internal bookmark.

        Args:
            story: PDF story list
            patent: Patent dictionary
            index: Patent number (1, 2, 3)
        """
        subsection_style = ParagraphStyle(
            name='CompactSubsection',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#34495e'),
            fontName='Helvetica-Bold',
            spaceAfter=6,
        )
        # Add bookmark anchor for internal linking
        story.append(Paragraph(f'<a name="patent{index}"/><b>Patent {index}</b>', subsection_style))

        # Build compact table with non-Latin text handling
        patent_data = []

        title = patent.get('title', 'Not available')
        title = self._sanitize_non_latin_text(title, 'title')
        patent_data.append(["Title", self._escape_text(title)])

        patent_num = patent.get('patent_number', 'Not available')
        patent_data.append(["Patent Number", self._escape_text(patent_num)])

        assignee = patent.get('author_or_assignee', 'Not available')
        assignee = self._sanitize_non_latin_text(assignee, 'assignee name')
        patent_data.append(["Assignee", self._escape_text(assignee)])

        pub_date = patent.get('publication_date', 'Not available')
        patent_data.append(["Date", self._escape_text(pub_date)])

        rel_score = patent.get('relevance_score', 0.0)
        patent_data.append(["Relevance", f"{rel_score:.2f}"])

        url = patent.get('source_url', 'Not available')
        if url and url != 'Not available':
            display_url = url if len(url) < 60 else url[:57] + "..."
            patent_data.append(["URL", self._escape_text(display_url)])

        patent_table = Table(patent_data, colWidths=[1.2*inch, 5*inch])
        patent_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Labels left-aligned
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Values left-aligned (long text)
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(patent_table)

        # Relevance analysis (compact)
        rel_explanation = patent.get('relevance_explanation', 'Not available')
        if rel_explanation and rel_explanation != 'Not available':
            story.append(Spacer(1, 0.06 * inch))
            analysis_style = ParagraphStyle(
                name='CompactAnalysis',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=colors.HexColor('#555555'),
                spaceAfter=0,
            )
            rel_explanation = self._sanitize_non_latin_text(rel_explanation, 'explanation')
            self._safe_add_paragraph(story, f"<b>Analysis:</b> {rel_explanation}", analysis_style)

    def _add_paper_details_compact(self, story: list, paper: dict, index: int) -> None:
        """
        Add compact paper information to PDF story with internal bookmark.

        Args:
            story: PDF story list
            paper: Paper dictionary
            index: Paper number (1, 2, 3)
        """
        subsection_style = ParagraphStyle(
            name='CompactSubsection',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#34495e'),
            fontName='Helvetica-Bold',
            spaceAfter=6,
        )
        # Add bookmark anchor for internal linking
        story.append(Paragraph(f'<a name="paper{index}"/><b>Paper {index}</b>', subsection_style))

        # Build compact table with non-Latin text handling
        paper_data = []

        title = paper.get('title', 'Not available')
        title = self._sanitize_non_latin_text(title, 'title')
        paper_data.append(["Title", self._escape_text(title)])

        authors = paper.get('author_or_assignee', 'Not available')
        authors = self._sanitize_non_latin_text(authors, 'author names')
        paper_data.append(["Authors", self._escape_text(authors)])

        venue = paper.get('venue', 'Not available')
        venue = self._sanitize_non_latin_text(venue, 'venue')
        pub_date = paper.get('publication_date', 'Not available')
        paper_data.append(["Venue", f"{self._escape_text(venue)} ({pub_date})"])

        citations = paper.get('citation_count')
        is_oa = paper.get('is_open_access', False)
        oa_text = "Open Access" if is_oa else "Subscription"
        if citations is not None:
            paper_data.append(["Citations", f"{citations} citations | {oa_text}"])
        else:
            paper_data.append(["Access", oa_text])

        doi = paper.get('doi', 'Not available')
        paper_data.append(["DOI", self._escape_text(doi)])

        rel_score = paper.get('relevance_score', 0.0)
        paper_data.append(["Relevance", f"{rel_score:.2f}"])

        pdf_url = paper.get('pdf_url')
        if pdf_url:
            display_url = pdf_url if len(pdf_url) < 60 else pdf_url[:57] + "..."
            paper_data.append(["PDF", self._escape_text(display_url)])

        paper_table = Table(paper_data, colWidths=[1.2*inch, 5*inch])
        paper_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Labels left-aligned
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # Values left-aligned (long text)
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(paper_table)

        # Relevance analysis (compact)
        rel_explanation = paper.get('relevance_explanation', 'Not available')
        if rel_explanation and rel_explanation != 'Not available':
            story.append(Spacer(1, 0.06 * inch))
            analysis_style = ParagraphStyle(
                name='CompactAnalysis',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=colors.HexColor('#555555'),
                spaceAfter=0,
            )
            rel_explanation = self._sanitize_non_latin_text(rel_explanation, 'explanation')
            self._safe_add_paragraph(story, f"<b>Analysis:</b> {rel_explanation}", analysis_style)

    def _add_patent_details(self, story: list, patent: dict, index: int) -> None:
        """
        Add detailed patent information to PDF story (DEPRECATED - use compact version).

        Args:
            story: PDF story list
            patent: Patent dictionary
            index: Patent number (1, 2, 3)
        """
        story.append(Paragraph(f"<b>Patent {index}</b>", self.styles['SubsectionHeader']))

        # Title
        title = patent.get('title', 'Not available')
        story.append(Paragraph(f"<b>Title:</b> {self._escape_text(title)}", self.styles['Normal']))

        # Patent number
        patent_num = patent.get('patent_number', 'Not available')
        story.append(Paragraph(f"<b>Patent Number:</b> {self._escape_text(patent_num)}", self.styles['Normal']))

        # Assignee
        assignee = patent.get('author_or_assignee', 'Not available')
        story.append(Paragraph(f"<b>Assignee:</b> {self._escape_text(assignee)}", self.styles['Normal']))

        # Publication date
        pub_date = patent.get('publication_date', 'Not available')
        story.append(Paragraph(f"<b>Publication Date:</b> {self._escape_text(pub_date)}", self.styles['Normal']))

        # Relevance score
        rel_score = patent.get('relevance_score', 0.0)
        story.append(Paragraph(f"<b>Relevance Score:</b> {rel_score:.2f}", self.styles['Normal']))

        # Confidence
        confidence = patent.get('confidence_level', 'Not available')
        story.append(Paragraph(f"<b>Confidence:</b> {self._escape_text(str(confidence))}", self.styles['Normal']))

        # URL
        url = patent.get('source_url', 'Not available')
        if url and url != 'Not available':
            # Truncate long URLs for display
            display_url = url if len(url) < 80 else url[:77] + "..."
            story.append(Paragraph(f"<b>URL:</b> {self._escape_text(display_url)}", self.styles['Normal']))

        # Relevance analysis
        rel_explanation = patent.get('relevance_explanation', 'Not available')
        if rel_explanation and rel_explanation != 'Not available':
            story.append(Paragraph(f"<b>Relevance Analysis:</b>", self.styles['Normal']))
            self._safe_add_paragraph(story, rel_explanation, self.styles['Normal'])

        story.append(Spacer(1, 0.1 * inch))

    def _add_paper_details(self, story: list, paper: dict, index: int) -> None:
        """
        Add detailed paper information to PDF story.

        Args:
            story: PDF story list
            paper: Paper dictionary
            index: Paper number (1, 2, 3)
        """
        story.append(Paragraph(f"<b>Paper {index}</b>", self.styles['SubsectionHeader']))

        # Title
        title = paper.get('title', 'Not available')
        story.append(Paragraph(f"<b>Title:</b> {self._escape_text(title)}", self.styles['Normal']))

        # Authors
        authors = paper.get('author_or_assignee', 'Not available')
        story.append(Paragraph(f"<b>Authors:</b> {self._escape_text(authors)}", self.styles['Normal']))

        # Year / publication date
        pub_date = paper.get('publication_date', 'Not available')
        story.append(Paragraph(f"<b>Year:</b> {self._escape_text(pub_date)}", self.styles['Normal']))

        # Venue
        venue = paper.get('venue', 'Not available')
        story.append(Paragraph(f"<b>Venue:</b> {self._escape_text(venue)}", self.styles['Normal']))

        # Citation count
        citations = paper.get('citation_count')
        if citations is not None:
            story.append(Paragraph(f"<b>Citations:</b> {citations}", self.styles['Normal']))

        # DOI
        doi = paper.get('doi', 'Not available')
        story.append(Paragraph(f"<b>DOI:</b> {self._escape_text(doi)}", self.styles['Normal']))

        # Open access status
        is_oa = paper.get('is_open_access', False)
        oa_status = "Yes" if is_oa else "No"
        story.append(Paragraph(f"<b>Open Access:</b> {oa_status}", self.styles['Normal']))

        # PDF URL
        pdf_url = paper.get('pdf_url')
        if pdf_url:
            display_url = pdf_url if len(pdf_url) < 80 else pdf_url[:77] + "..."
            story.append(Paragraph(f"<b>PDF URL:</b> {self._escape_text(display_url)}", self.styles['Normal']))

        # Relevance score
        rel_score = paper.get('relevance_score', 0.0)
        story.append(Paragraph(f"<b>Relevance Score:</b> {rel_score:.2f}", self.styles['Normal']))

        # Confidence
        confidence = paper.get('confidence_level', 'Not available')
        story.append(Paragraph(f"<b>Confidence:</b> {self._escape_text(str(confidence))}", self.styles['Normal']))

        # Relevance analysis
        rel_explanation = paper.get('relevance_explanation', 'Not available')
        if rel_explanation and rel_explanation != 'Not available':
            story.append(Paragraph(f"<b>Relevance Analysis:</b>", self.styles['Normal']))
            self._safe_add_paragraph(story, rel_explanation, self.styles['Normal'])

        story.append(Spacer(1, 0.1 * inch))

    def _format_patent_reference(self, patent: dict, index: int) -> str:
        """
        Format patent as a reference citation.

        Args:
            patent: Patent dictionary
            index: Reference number

        Returns:
            Formatted reference string
        """
        title = patent.get('title', 'Unknown')
        title = self._sanitize_non_latin_text(title, 'title')
        patent_num = patent.get('patent_number', 'N/A')
        assignee = patent.get('author_or_assignee', 'Unknown')
        assignee = self._sanitize_non_latin_text(assignee, 'assignee')
        pub_date = patent.get('publication_date', 'N/A')
        url = patent.get('source_url', '')

        ref = f"[{index}] {assignee}. {title}. Patent {patent_num} ({pub_date})."
        if url:
            ref += f" URL: {url}"

        return ref

    def _format_paper_reference(self, paper: dict, index: int) -> str:
        """
        Format paper as a reference citation.

        Args:
            paper: Paper dictionary
            index: Reference number

        Returns:
            Formatted reference string
        """
        title = paper.get('title', 'Unknown')
        title = self._sanitize_non_latin_text(title, 'title')
        authors = paper.get('author_or_assignee', 'Unknown')
        authors = self._sanitize_non_latin_text(authors, 'authors')
        year = paper.get('publication_date', 'N/A')
        venue = paper.get('venue', '')
        venue = self._sanitize_non_latin_text(venue, 'venue')
        doi = paper.get('doi', '')

        ref = f"[{index}] {authors}. {title}."
        if venue:
            ref += f" {venue}."
        ref += f" ({year})."
        if doi:
            ref += f" DOI: {doi}"

        return ref
