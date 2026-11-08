"""JSON reporter."""

import json
from pathlib import Path
from typing import Any

from pipeline_doctor.core.models import AnalysisReport
from pipeline_doctor.reporters.base import BaseReporter, ReporterRegistry


@ReporterRegistry.register
class JSONReporter(BaseReporter):
    """Generates JSON reports."""

    name = "json"
    description = "Generates machine-readable JSON reports"

    def __init__(self, config: dict[str, Any] = None, output_dir: str = "./reports"):
        super().__init__(config, output_dir)
        self.pretty = self.get_config("pretty", True)
        self.include_metadata = self.get_config("include_metadata", True)

    async def generate(self, report: AnalysisReport, output_path: Path | None = None) -> Path:
        """Generate JSON report."""
        if output_path is None:
            output_path = self.get_output_path(report, "json")

        data = self._prepare_data(report)

        indent = 2 if self.pretty else None
        output_path.write_text(
            json.dumps(data, indent=indent, default=str),
            encoding="utf-8"
        )
        return output_path

    def _prepare_data(self, report: AnalysisReport) -> dict[str, Any]:
        """Prepare data for JSON serialization."""
        data = {
            "report_id": str(report.id),
            "pipeline_id": str(report.pipeline_id),
            "run_id": str(report.run_id),
            "platform": report.platform,
            "generated_at": report.started_at.isoformat() if report.started_at else None,
            "completed_at": report.completed_at.isoformat() if report.completed_at else None,
            "duration_seconds": report.duration_seconds,
            "summary": {
                "total_findings": report.total_findings,
                "by_severity": {k.value: v for k, v in report.findings_by_severity.items()},
                "by_category": {k.value: v for k, v in report.findings_by_category.items()},
                "has_critical_findings": report.has_critical_findings,
                "has_errors": report.has_errors,
            },
            "analyzers": [],
        }

        if self.include_metadata:
            data["metadata"] = report.metadata

        for analyzer_result in report.analyzer_results:
            analyzer_data = {
                "name": analyzer_result.analyzer_name,
                "version": analyzer_result.analyzer_version,
                "started_at": analyzer_result.started_at.isoformat() if analyzer_result.started_at else None,
                "completed_at": analyzer_result.completed_at.isoformat() if analyzer_result.completed_at else None,
                "duration_seconds": analyzer_result.duration_seconds,
                "findings": [],
                "errors": analyzer_result.errors,
            }

            if self.include_metadata:
                analyzer_data["metadata"] = analyzer_result.metadata

            for finding in analyzer_result.findings:
                analyzer_data["findings"].append({
                    "id": str(finding.id),
                    "category": finding.category.value,
                    "severity": finding.severity.value,
                    "title": finding.title,
                    "message": finding.message,
                    "suggestion": finding.suggestion,
                    "affected_job": finding.affected_job,
                    "affected_step": finding.affected_step,
                    "evidence": finding.evidence,
                    "references": finding.references,
                    "created_at": finding.created_at.isoformat() if finding.created_at else None,
                })

            data["analyzers"].append(analyzer_data)

        return data


@ReporterRegistry.register
class JSONLinesReporter(BaseReporter):
    """Generates JSON Lines (NDJSON) reports for streaming."""

    name = "jsonl"
    description = "Generates newline-delimited JSON for streaming/log aggregation"

    async def generate(self, report: AnalysisReport, output_path: Path | None = None) -> Path:
        """Generate JSON Lines report."""
        if output_path is None:
            output_path = self.get_output_path(report, "jsonl")

        lines = []

        # Report header
        lines.append(json.dumps({
            "type": "report_header",
            "report_id": str(report.id),
            "pipeline_id": str(report.pipeline_id),
            "run_id": str(report.run_id),
            "platform": report.platform,
            "generated_at": report.started_at.isoformat() if report.started_at else None,
        }))

        # Analyzer results
        for analyzer_result in report.analyzer_results:
            lines.append(json.dumps({
                "type": "analyzer_result",
                "analyzer": analyzer_result.analyzer_name,
                "version": analyzer_result.analyzer_version,
                "duration_seconds": analyzer_result.duration_seconds,
                "errors": analyzer_result.errors,
            }))

            for finding in analyzer_result.findings:
                lines.append(json.dumps({
                    "type": "finding",
                    "id": str(finding.id),
                    "analyzer": analyzer_result.analyzer_name,
                    "category": finding.category.value,
                    "severity": finding.severity.value,
                    "title": finding.title,
                    "message": finding.message,
                    "suggestion": finding.suggestion,
                    "affected_job": finding.affected_job,
                    "affected_step": finding.affected_step,
                    "evidence": finding.evidence,
                    "references": finding.references,
                }))

        # Report footer
        lines.append(json.dumps({
            "type": "report_footer",
            "total_findings": report.total_findings,
            "by_severity": {k.value: v for k, v in report.findings_by_severity.items()},
            "by_category": {k.value: v for k, v in report.findings_by_category.items()},
        }))

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path
