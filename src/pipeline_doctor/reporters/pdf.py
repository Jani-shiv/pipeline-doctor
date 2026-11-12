"""PDF reporter."""

from pathlib import Path
from typing import Any

from pipeline_doctor.core.models import AnalysisReport
from pipeline_doctor.reporters.base import BaseReporter, ReporterRegistry
from pipeline_doctor.reporters.html import HTMLReporter


@ReporterRegistry.register
class PDFReporter(BaseReporter):
    """Generates PDF reports using WeasyPrint."""

    name = "pdf"
    description = "Generates professional PDF reports"

    def __init__(self, config: dict[str, Any] | None = None, output_dir: str = "./reports"):
        super().__init__(config, output_dir)
        self.page_size = self.get_config("page_size", "A4")
        self.margin = self.get_config("margin", "2cm")
        self.include_charts = self.get_config("include_charts", True)

        # Try to import weasyprint
        try:
            from weasyprint import CSS, HTML  # type: ignore[import-untyped]
            from weasyprint.text.fonts import FontConfiguration  # type: ignore[import-untyped]

            self._weasyprint_available = True
            self._HTML = HTML
            self._CSS = CSS
            self._FontConfiguration = FontConfiguration
        except ImportError:
            self._weasyprint_available = False
            self._HTML = None
            self._CSS = None
            self._FontConfiguration = None

    async def generate(self, report: AnalysisReport, output_path: Path | None = None) -> Path:
        """Generate PDF report."""
        if not self._weasyprint_available:
            raise RuntimeError(
                "WeasyPrint is required for PDF generation. Install with: pip install weasyprint"
            )

        if output_path is None:
            output_path = self.get_output_path(report, "pdf")

        # Create HTML reporter for template rendering
        html_reporter = self._create_html_reporter()
        template_data = html_reporter._prepare_template_data(report)

        # Use a PDF-optimized template
        template = html_reporter.env.from_string(self._get_pdf_template())
        html_content = str(template.render(**template_data))

        # Convert to PDF
        font_config = self._FontConfiguration()
        html_doc = self._HTML(string=html_content)
        css = self._CSS(string=self._get_pdf_css(), font_config=font_config)

        html_doc.write_pdf(
            str(output_path),
            stylesheets=[css],
            font_config=font_config,
        )

        return output_path

    def _create_html_reporter(self) -> HTMLReporter:
        """Create HTML reporter for rendering."""
        return HTMLReporter(self.config, str(self.output_dir))

    def _get_pdf_template(self) -> str:
        """Get PDF-optimized HTML template."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Pipeline Doctor Report</title>
</head>
<body>
    <div class="page">
        <header class="report-header">
            <h1>🏥 Pipeline Doctor Report</h1>
            <div class="meta">
                <span><strong>Pipeline:</strong> {{ report.pipeline_id }}</span>
                <span><strong>Run:</strong> {{ report.run_id }}</span>
                <span><strong>Platform:</strong> {{ report.platform }}</span>
                <span><strong>Generated:</strong> {{ report.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}</span>
            </div>
        </header>

        <section class="summary">
            <h2>Summary</h2>
            <table class="summary-table">
                <tr>
                    <th>Severity</th>
                    <th>Count</th>
                </tr>
                {% for severity in severity_order %}
                <tr class="{{ severity.value }}">
                    <td>{{ severity.value.title() }}</td>
                    <td>{{ findings_by_severity[severity] }}</td>
                </tr>
                {% endfor %}
                <tr class="total">
                    <td><strong>Total</strong></td>
                    <td><strong>{{ total_findings }}</strong></td>
                </tr>
            </table>
        </section>

        {% if total_findings == 0 %}
        <section class="no-findings">
            <h2>✅ No Issues Found</h2>
            <p>Your pipeline looks healthy!</p>
        </section>
        {% else %}
        {% for analyzer_name, findings in findings_by_analyzer.items() %}
        {% if findings %}
        <section class="analyzer-section">
            <h2>{{ analyzer_name.replace('_', ' ').title() }} Analyzer</h2>
            {% for finding in findings %}
            <article class="finding {{ finding.severity.value }}">
                <header class="finding-header">
                    <h3>{{ finding.title }}</h3>
                    <span class="severity-badge {{ finding.severity.value }}">{{ finding.severity.value }}</span>
                </header>
                <div class="finding-meta">
                    {% if finding.affected_job %}<span><strong>Job:</strong> {{ finding.affected_job }}</span>{% endif %}
                    {% if finding.affected_step %}<span><strong>Step:</strong> {{ finding.affected_step }}</span>{% endif %}
                    <span><strong>Category:</strong> {{ finding.category.value.replace('_', ' ').title() }}</span>
                </div>
                <div class="finding-message">{{ finding.message }}</div>
                {% if finding.suggestion %}
                <div class="finding-suggestion">
                    <strong>Suggestion:</strong> {{ finding.suggestion }}
                </div>
                {% endif %}
            </article>
            {% endfor %}
        </section>
        {% endif %}
        {% endfor %}
        {% endif %}

        <footer class="report-footer">
            <p>Generated by Pipeline Doctor</p>
        </footer>
    </div>
</body>
</html>
"""

    def _get_pdf_css(self) -> str:
        """Get CSS for PDF styling."""
        return f"""
@page {{
    size: {self.page_size};
    margin: {self.margin};
    @top-center {{
        content: "Pipeline Doctor Report";
        font-size: 10px;
        color: #666;
    }}
    @bottom-center {{
        content: "Page " counter(page) " of " counter(pages);
        font-size: 10px;
        color: #666;
    }}
}}

* {{
    box-sizing: border-box;
}}

body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 11px;
    line-height: 1.5;
    color: #1f2937;
}}

.page {{
    max-width: 100%;
}}

.report-header {{
    border-bottom: 2px solid #e5e7eb;
    padding-bottom: 1rem;
    margin-bottom: 2rem;
}}

.report-header h1 {{
    font-size: 24px;
    font-weight: 700;
    color: #111827;
    margin-bottom: 0.5rem;
}}

.meta {{
    display: flex;
    gap: 2rem;
    font-size: 12px;
    color: #6b7280;
}}

section {{
    margin-bottom: 2rem;
}}

h2 {{
    font-size: 16px;
    font-weight: 600;
    color: #111827;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
}}

.summary-table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1rem;
}}

.summary-table th,
.summary-table td {{
    padding: 0.5rem;
    text-align: left;
    border-bottom: 1px solid #e5e7eb;
}}

.summary-table th {{
    font-weight: 600;
    background: #f9fafb;
}}

.summary-table tr.critical td {{
    color: #dc2626;
}}

.summary-table tr.error td {{
    color: #ef4444;
}}

.summary-table tr.warning td {{
    color: #f59e0b;
}}

.summary-table tr.info td {{
    color: #3b82f6;
}}

.summary-table tr.total td {{
    font-weight: 600;
    border-top: 2px solid #e5e7eb;
}}

.finding {{
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 1rem;
    margin-bottom: 1rem;
    page-break-inside: avoid;
}}

.finding.critical {{
    border-left: 4px solid #dc2626;
}}

.finding.error {{
    border-left: 4px solid #ef4444;
}}

.finding.warning {{
    border-left: 4px solid #f59e0b;
}}

.finding.info {{
    border-left: 4px solid #3b82f6;
}}

.finding-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 0.5rem;
}}

.finding-header h3 {{
    font-size: 14px;
    font-weight: 600;
    margin: 0;
}}

.severity-badge {{
    font-size: 10px;
    font-weight: 600;
    padding: 0.125rem 0.5rem;
    border-radius: 3px;
    text-transform: uppercase;
}}

.severity-badge.critical {{
    background: #fef2f2;
    color: #dc2626;
}}

.severity-badge.error {{
    background: #fef2f2;
    color: #ef4444;
}}

.severity-badge.warning {{
    background: #fffbeb;
    color: #f59e0b;
}}

.severity-badge.info {{
    background: #eff6ff;
    color: #3b82f6;
}}

.finding-meta {{
    display: flex;
    gap: 1.5rem;
    font-size: 11px;
    color: #6b7280;
    margin-bottom: 0.5rem;
}}

.finding-message {{
    color: #4b5563;
    margin-bottom: 0.5rem;
}}

.finding-suggestion {{
    background: #f3f4f6;
    padding: 0.75rem;
    border-radius: 4px;
    font-size: 11px;
    border-left: 3px solid #3b82f6;
}}

.no-findings {{
    text-align: center;
    padding: 3rem;
    color: #6b7280;
}}

.report-footer {{
    border-top: 1px solid #e5e7eb;
    padding-top: 1rem;
    text-align: center;
    font-size: 10px;
    color: #9ca3af;
}}
"""
