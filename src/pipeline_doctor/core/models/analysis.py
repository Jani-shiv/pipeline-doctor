"""Analysis result models."""

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class FindingSeverity(StrEnum):
    """Severity levels for findings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FindingCategory(StrEnum):
    """Categories of findings."""

    FAILURE_PATTERN = "failure_pattern"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COST = "cost"
    RELIABILITY = "reliability"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    CUSTOM = "custom"


class Finding(BaseModel):
    """A single finding from analysis."""

    id: UUID = Field(default_factory=uuid4)
    analyzer_name: str
    category: FindingCategory
    severity: FindingSeverity
    title: str
    message: str
    suggestion: str | None = None
    affected_job: str | None = None
    affected_step: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)
    references: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class AnalysisResult(BaseModel):
    """Result from a single analyzer."""

    analyzer_name: str
    analyzer_version: str = "1.0.0"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    findings: list[Finding] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def has_findings(self) -> bool:
        return len(self.findings) > 0

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def critical_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == FindingSeverity.CRITICAL]

    @property
    def error_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == FindingSeverity.ERROR]

    @property
    def warning_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == FindingSeverity.WARNING]

    @property
    def info_findings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == FindingSeverity.INFO]

    def add_finding(self, finding: Finding) -> None:
        self.findings.append(finding)

    def add_error(self, error: str) -> None:
        self.errors.append(error)


class AnalysisReport(BaseModel):
    """Complete analysis report for a pipeline run."""

    id: UUID = Field(default_factory=uuid4)
    pipeline_id: UUID
    run_id: UUID
    platform: str
    analyzer_results: list[AnalysisResult] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    duration_seconds: float | None = None
    summary: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def all_findings(self) -> list[Finding]:
        findings = []
        for result in self.analyzer_results:
            findings.extend(result.findings)
        return findings

    @property
    def total_findings(self) -> int:
        return len(self.all_findings)

    @property
    def findings_by_severity(self) -> dict[FindingSeverity, int]:
        counts = dict.fromkeys(FindingSeverity, 0)
        for finding in self.all_findings:
            counts[finding.severity] += 1
        return counts

    @property
    def findings_by_category(self) -> dict[FindingCategory, int]:
        counts = dict.fromkeys(FindingCategory, 0)
        for finding in self.all_findings:
            counts[finding.category] += 1
        return counts

    @property
    def has_critical_findings(self) -> bool:
        return any(f.severity == FindingSeverity.CRITICAL for f in self.all_findings)

    @property
    def has_errors(self) -> bool:
        return any(r.has_errors for r in self.analyzer_results)

    def add_analyzer_result(self, result: AnalysisResult) -> None:
        self.analyzer_results.append(result)

    def get_findings_by_analyzer(self, analyzer_name: str) -> list[Finding]:
        for result in self.analyzer_results:
            if result.analyzer_name == analyzer_name:
                return result.findings
        return []
