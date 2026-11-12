"""Markdown reporter."""

from pathlib import Path
from typing import Any

from pipeline_doctor.core.models import AnalysisReport, FindingSeverity
from pipeline_doctor.reporters.base import BaseReporter, ReporterRegistry


@ReporterRegistry.register
class MarkdownReporter(BaseReporter):
    """Generates Markdown reports."""

    name = "markdown"
    description = "Generates Markdown reports for documentation and GitHub"

    def __init__(self, config: dict[str, Any] | None = None, output_dir: str = "./reports"):
        super().__init__(config, output_dir)
        self.include_summary = self.get_config("include_summary", True)
        self.include_details = self.get_config("include_details", True)
        self.table_format = self.get_config("table_format", "github")

    async def generate(self, report: AnalysisReport, output_path: Path | None = None) -> Path:
        """Generate Markdown report."""
        if output_path is None:
            output_path = self.get_output_path(report, "md")

        content = self._generate_markdown(report)
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _generate_markdown(self, report: AnalysisReport) -> str:
        """Generate Markdown content."""
        lines = []

        # Header
        lines.append("# 🏥 Pipeline Doctor Report")
        lines.append("")
        lines.append(f"**Pipeline:** `{report.pipeline_id}`  ")
        lines.append(f"**Run:** `{report.run_id}`  ")
        lines.append(f"**Platform:** {report.platform}  ")
        lines.append(
            f"**Generated:** {report.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') if report.started_at else 'N/A'}  "
        )
        lines.append("")

        # Summary
        if self.include_summary:
            lines.append("## 📊 Summary")
            lines.append("")

            severity_counts = report.findings_by_severity
            total = report.total_findings

            lines.append(f"**Total Findings:** {total}")
            lines.append("")

            lines.append("| Severity | Count |")
            lines.append("|----------|-------|")
            for severity in [
                FindingSeverity.CRITICAL,
                FindingSeverity.ERROR,
                FindingSeverity.WARNING,
                FindingSeverity.INFO,
            ]:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    icon = self._severity_icon(severity)
                    lines.append(f"| {icon} {severity.value.title()} | {count} |")
            lines.append("")

            lines.append("| Category | Count |")
            lines.append("|----------|-------|")
            for category, count in report.findings_by_category.items():
                if count > 0:
                    lines.append(f"| {category.value.replace('_', ' ').title()} | {count} |")
            lines.append("")

        # Details
        if self.include_details and report.total_findings > 0:
            lines.append("## 🔍 Detailed Findings")
            lines.append("")

            for analyzer_result in report.analyzer_results:
                if not analyzer_result.findings:
                    continue

                lines.append(
                    f"### {analyzer_result.analyzer_name.replace('_', ' ').title()} Analyzer"
                )
                lines.append("")

                for finding in analyzer_result.findings:
                    lines.append(f"#### {self._severity_icon(finding.severity)} {finding.title}")
                    lines.append("")
                    lines.append(f"**Severity:** {finding.severity.value.title()}  ")
                    lines.append(
                        f"**Category:** {finding.category.value.replace('_', ' ').title()}  "
                    )
                    if finding.affected_job:
                        lines.append(f"**Job:** `{finding.affected_job}`  ")
                    if finding.affected_step:
                        lines.append(f"**Step:** `{finding.affected_step}`  ")
                    lines.append("")
                    lines.append(f"{finding.message}")
                    lines.append("")

                    if finding.suggestion:
                        lines.append(f"> 💡 **Suggestion:** {finding.suggestion}")
                        lines.append("")

                    if finding.evidence:
                        lines.append("<details>")
                        lines.append("<summary>Evidence</summary>")
                        lines.append("")
                        lines.append("```json")
                        for key, value in finding.evidence.items():
                            lines.append(f'  "{key}": {value!r}')
                        lines.append("```")
                        lines.append("")
                        lines.append("</details>")
                        lines.append("")

                    lines.append("---")
                    lines.append("")

        # No findings message
        if report.total_findings == 0:
            lines.append("## ✅ No Issues Found")
            lines.append("")
            lines.append("Your pipeline looks healthy! 🎉")
            lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append(
            f"*Report generated by [Pipeline Doctor](https://github.com/your-org/pipeline-doctor) at {report.started_at.strftime('%Y-%m-%d %H:%M:%S UTC') if report.started_at else 'unknown time'}*"
        )

        return "\n".join(lines)

    def _severity_icon(self, severity: FindingSeverity) -> str:
        icons = {
            FindingSeverity.CRITICAL: "🔴",
            FindingSeverity.ERROR: "🟠",
            FindingSeverity.WARNING: "🟡",
            FindingSeverity.INFO: "🔵",
        }
        return icons.get(severity, "⚪")


@ReporterRegistry.register
class GitHubMarkdownReporter(MarkdownReporter):
    """Generates GitHub-flavored Markdown for PR comments."""

    name = "github-md"
    description = "Generates GitHub-flavored Markdown for PR comments and issues"

    def __init__(self, config: dict[str, Any] | None = None, output_dir: str = "./reports"):
        super().__init__(config, output_dir)
        self.max_findings = self.get_config("max_findings", 50)
        self.collapse_details = self.get_config("collapse_details", True)

    async def generate(self, report: AnalysisReport, output_path: Path | None = None) -> Path:
        """Generate GitHub Markdown report."""
        if output_path is None:
            output_path = self.get_output_path(report, "md")

        content = self._generate_github_markdown(report)
        output_path.write_text(content, encoding="utf-8")
        return output_path

    def _generate_github_markdown(self, report: AnalysisReport) -> str:
        """Generate GitHub-flavored Markdown."""
        lines = []

        # Header with status badge
        status = "✅ Passing" if report.total_findings == 0 else "⚠️ Issues Found"
        if report.has_critical_findings:
            status = "🔴 Critical Issues"
        elif report.findings_by_severity.get(FindingSeverity.ERROR, 0) > 0:
            status = "🟠 Errors Found"

        lines.append(f"# Pipeline Doctor Analysis: {status}")
        lines.append("")

        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Pipeline | `{report.pipeline_id}` |")
        lines.append(f"| Run | `{report.run_id}` |")
        lines.append(f"| Platform | {report.platform} |")
        lines.append(f"| Total Findings | {report.total_findings} |")
        lines.append(
            f"| Critical | {report.findings_by_severity.get(FindingSeverity.CRITICAL, 0)} |"
        )
        lines.append(f"| Errors | {report.findings_by_severity.get(FindingSeverity.ERROR, 0)} |")
        lines.append(
            f"| Warnings | {report.findings_by_severity.get(FindingSeverity.WARNING, 0)} |"
        )
        lines.append(f"| Info | {report.findings_by_severity.get(FindingSeverity.INFO, 0)} |")
        lines.append("")

        # Findings grouped by severity
        if report.total_findings > 0:
            lines.append("## Findings")
            lines.append("")

            # Critical first
            for severity in [
                FindingSeverity.CRITICAL,
                FindingSeverity.ERROR,
                FindingSeverity.WARNING,
                FindingSeverity.INFO,
            ]:
                findings = [
                    f
                    for ar in report.analyzer_results
                    for f in ar.findings
                    if f.severity == severity
                ]

                if not findings:
                    continue

                lines.append(
                    f"### {self._severity_icon(severity)} {severity.value.title()} ({len(findings)})"
                )
                lines.append("")

                for _i, finding in enumerate(findings[: self.max_findings]):
                    if self.collapse_details:
                        lines.append("<details>")
                        lines.append(f"<summary>{finding.title}</summary>")
                        lines.append("")
                    else:
                        lines.append(f"#### {finding.title}")
                        lines.append("")

                    lines.append(f"**Analyzer:** {finding.analyzer_name}  ")
                    if finding.affected_job:
                        lines.append(f"**Job:** `{finding.affected_job}`  ")
                    if finding.affected_step:
                        lines.append(f"**Step:** `{finding.affected_step}`  ")
                    lines.append("")
                    lines.append(f"{finding.message}")
                    lines.append("")

                    if finding.suggestion:
                        lines.append(f"> 💡 **Suggestion:** {finding.suggestion}")
                        lines.append("")

                    if finding.evidence:
                        lines.append("```json")
                        lines.append(str(finding.evidence))
                        lines.append("```")
                        lines.append("")

                    if self.collapse_details:
                        lines.append("</details>")
                        lines.append("")

                if len(findings) > self.max_findings:
                    lines.append(
                        f"*... and {len(findings) - self.max_findings} more {severity.value} findings*"
                    )
                    lines.append("")

        # Collapsible raw data
        lines.append("<details>")
        lines.append("<summary>📄 Full JSON Report</summary>")
        lines.append("")
        lines.append("```json")
        lines.append(
            str(
                {
                    "report_id": str(report.id),
                    "total_findings": report.total_findings,
                    "by_severity": {k.value: v for k, v in report.findings_by_severity.items()},
                }
            )
        )
        lines.append("```")
        lines.append("")
        lines.append("</details>")

        return "\n".join(lines)
