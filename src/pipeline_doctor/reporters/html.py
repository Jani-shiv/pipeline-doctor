"""HTML reporter."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from pipeline_doctor.core.models import AnalysisReport, FindingCategory, FindingSeverity
from pipeline_doctor.reporters.base import BaseReporter, ReporterRegistry


@ReporterRegistry.register
class HTMLReporter(BaseReporter):
    """Generates HTML reports."""

    name = "html"
    description = "Generates interactive HTML reports with charts"

    def __init__(self, config: dict[str, Any] = None, output_dir: str = "./reports"):
        super().__init__(config, output_dir)
        self.template_name = self.get_config("template", "default")
        self.include_charts = self.get_config("include_charts", True)
        self.include_raw_data = self.get_config("include_raw_data", False)
        self.theme = self.get_config("theme", "light")

        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        # Add custom filters
        self.env.filters["severity_color"] = self._severity_color
        self.env.filters["severity_icon"] = self._severity_icon

    def _severity_color(self, severity: FindingSeverity) -> str:
        colors = {
            FindingSeverity.CRITICAL: "#dc2626",
            FindingSeverity.ERROR: "#ef4444",
            FindingSeverity.WARNING: "#f59e0b",
            FindingSeverity.INFO: "#3b82f6",
        }
        return colors.get(severity, "#6b7280")

    def _severity_icon(self, severity: FindingSeverity) -> str:
        icons = {
            FindingSeverity.CRITICAL: "🔴",
            FindingSeverity.ERROR: "🟠",
            FindingSeverity.WARNING: "🟡",
            FindingSeverity.INFO: "🔵",
        }
        return icons.get(severity, "⚪")

    async def generate(self, report: AnalysisReport, output_path: Path | None = None) -> Path:
        """Generate HTML report."""
        if output_path is None:
            output_path = self.get_output_path(report, "html")

        # Prepare template data
        template_data = self._prepare_template_data(report)

        # Render template
        try:
            template = self.env.get_template(f"{self.template_name}.html")
        except Exception:
            # Fallback to inline template
            template = self.env.from_string(self._get_default_template())

        html_content = template.render(**template_data)

        # Write output
        output_path.write_text(html_content, encoding="utf-8")
        return output_path

    def _prepare_template_data(self, report: AnalysisReport) -> dict[str, Any]:
        """Prepare data for template rendering."""
        findings_by_severity = report.findings_by_severity
        findings_by_category = report.findings_by_category

        # Group findings by analyzer
        findings_by_analyzer = {}
        for analyzer_result in report.analyzer_results:
            findings_by_analyzer[analyzer_result.analyzer_name] = analyzer_result.findings

        return {
            "report": report,
            "findings_by_severity": findings_by_severity,
            "findings_by_category": findings_by_category,
            "findings_by_analyzer": findings_by_analyzer,
            "total_findings": report.total_findings,
            "has_critical": report.has_critical_findings,
            "include_charts": self.include_charts,
            "include_raw_data": self.include_raw_data,
            "theme": self.theme,
            "severity_order": [FindingSeverity.CRITICAL, FindingSeverity.ERROR, FindingSeverity.WARNING, FindingSeverity.INFO],
            "category_order": list(FindingCategory),
        }

    def _get_default_template(self) -> str:
        """Get default HTML template."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline Doctor Report - {{ report.id }}</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1f2937; background: #f9fafb; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        .header { background: white; border-radius: 8px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .header h1 { font-size: 2rem; font-weight: 700; color: #111827; }
        .header .meta { display: flex; gap: 2rem; margin-top: 1rem; color: #6b7280; font-size: 0.875rem; }
        .summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .card { background: white; border-radius: 8px; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .card.critical { border-left: 4px solid #dc2626; }
        .card.error { border-left: 4px solid #ef4444; }
        .card.warning { border-left: 4px solid #f59e0b; }
        .card.info { border-left: 4px solid #3b82f6; }
        .card h3 { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; color: #6b7280; margin-bottom: 0.5rem; }
        .card .value { font-size: 2rem; font-weight: 700; }
        .section { background: white; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .section h2 { font-size: 1.25rem; font-weight: 600; margin-bottom: 1rem; }
        .finding { border: 1px solid #e5e7eb; border-radius: 6px; padding: 1rem; margin-bottom: 1rem; }
        .finding.critical { border-left: 4px solid #dc2626; }
        .finding.error { border-left: 4px solid #ef4444; }
        .finding.warning { border-left: 4px solid #f59e0b; }
        .finding.info { border-left: 4px solid #3b82f6; }
        .finding-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; }
        .finding-title { font-weight: 600; }
        .finding-severity { font-size: 0.75rem; font-weight: 600; padding: 0.25rem 0.5rem; border-radius: 4px; text-transform: uppercase; }
        .finding-severity.critical { background: #fef2f2; color: #dc2626; }
        .finding-severity.error { background: #fef2f2; color: #ef4444; }
        .finding-severity.warning { background: #fffbeb; color: #f59e0b; }
        .finding-severity.info { background: #eff6ff; color: #3b82f6; }
        .finding-message { color: #4b5563; margin-bottom: 0.5rem; }
        .finding-suggestion { background: #f3f4f6; padding: 0.75rem; border-radius: 4px; font-size: 0.875rem; }
        .finding-evidence { font-family: monospace; font-size: 0.75rem; background: #1f2937; color: #e5e7eb; padding: 0.75rem; border-radius: 4px; overflow-x: auto; margin-top: 0.5rem; }
        .analyzer-section { margin-bottom: 2rem; }
        .analyzer-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
        .no-findings { text-align: center; padding: 3rem; color: #6b7280; }
        .chart-placeholder { height: 300px; background: #f3f4f6; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #6b7280; }
    </style>
    {% if include_charts %}
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    {% endif %}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏥 Pipeline Doctor Report</h1>
            <div class="meta">
                <span>Pipeline: {{ report.pipeline_id }}</span>
                <span>Run: {{ report.run_id }}</span>
                <span>Platform: {{ report.platform }}</span>
                <span>Generated: {{ report.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') }}</span>
            </div>
        </div>

        <div class="summary-cards">
            <div class="card critical">
                <h3>Critical</h3>
                <div class="value">{{ findings_by_severity[FindingSeverity.CRITICAL] }}</div>
            </div>
            <div class="card error">
                <h3>Errors</h3>
                <div class="value">{{ findings_by_severity[FindingSeverity.ERROR] }}</div>
            </div>
            <div class="card warning">
                <h3>Warnings</h3>
                <div class="value">{{ findings_by_severity[FindingSeverity.WARNING] }}</div>
            </div>
            <div class="card info">
                <h3>Info</h3>
                <div class="value">{{ findings_by_severity[FindingSeverity.INFO] }}</div>
            </div>
        </div>

        {% if total_findings == 0 %}
        <div class="section">
            <div class="no-findings">
                <h2>✅ No Issues Found</h2>
                <p>Your pipeline looks healthy!</p>
            </div>
        </div>
        {% else %}
        {% for analyzer_name, findings in findings_by_analyzer.items() %}
        {% if findings %}
        <div class="section analyzer-section">
            <div class="analyzer-header">
                <h2>{{ analyzer_name.replace('_', ' ').title() }} Analyzer</h2>
                <span>{{ findings|length }} findings</span>
            </div>
            {% for finding in findings %}
            <div class="finding {{ finding.severity.value }}">
                <div class="finding-header">
                    <div class="finding-title">{{ finding.title }}</div>
                    <span class="finding-severity {{ finding.severity.value }}">{{ finding.severity.value }}</span>
                </div>
                <div class="finding-message">{{ finding.message }}</div>
                {% if finding.suggestion %}
                <div class="finding-suggestion"><strong>💡 Suggestion:</strong> {{ finding.suggestion }}</div>
                {% endif %}
                {% if include_raw_data and finding.evidence %}
                <div class="finding-evidence">{{ finding.evidence | tojson(indent=2) }}</div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
        {% endif %}
        {% endfor %}
        {% endif %}
    </div>
    {% if include_charts %}
    <script>
        // Chart.js initialization for severity distribution
        const ctx = document.getElementById('severityChart');
        if (ctx) {
            new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Critical', 'Error', 'Warning', 'Info'],
                    datasets: [{
                        data: [
                            {{ findings_by_severity[FindingSeverity.CRITICAL] }},
                            {{ findings_by_severity[FindingSeverity.ERROR] }},
                            {{ findings_by_severity[FindingSeverity.WARNING] }},
                            {{ findings_by_severity[FindingSeverity.INFO] }}
                        ],
                        backgroundColor: ['#dc2626', '#ef4444', '#f59e0b', '#3b82f6']
                    }]
                },
                options: { responsive: true, maintainAspectRatio: false }
            });
        }
    </script>
    {% endif %}
</body>
</html>
"""
