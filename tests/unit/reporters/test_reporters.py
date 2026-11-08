"""Tests for reporters."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from pipeline_doctor.core.models import (
    AnalysisReport,
    AnalysisResult,
    Finding,
    FindingCategory,
    FindingSeverity,
)
from pipeline_doctor.reporters.json import JSONReporter
from pipeline_doctor.reporters.markdown import GitHubMarkdownReporter, MarkdownReporter

# Test constants
EXPECTED_TOTAL_FINDINGS = 2
EXPECTED_ANALYZERS = 1
EXPECTED_FINDINGS_PER_ANALYZER = 2


@pytest.fixture
def sample_report():
    """Create a sample report for testing."""
    report = AnalysisReport(
        pipeline_id=uuid4(),
        run_id=uuid4(),
        platform="github",
        started_at=datetime.now(UTC),
    )

    result = AnalysisResult(analyzer_name="test-analyzer")
    result.add_finding(
        Finding(
            analyzer_name="test-analyzer",
            category=FindingCategory.FAILURE_PATTERN,
            severity=FindingSeverity.ERROR,
            title="Test Error",
            message="Test error message",
            suggestion="Fix the error",
            affected_job="test-job",
            evidence={"key": "value"},
        )
    )
    result.add_finding(
        Finding(
            analyzer_name="test-analyzer",
            category=FindingCategory.PERFORMANCE,
            severity=FindingSeverity.WARNING,
            title="Slow Job",
            message="Job took too long",
            suggestion="Optimize job",
        )
    )

    report.add_analyzer_result(result)
    return report


class TestJSONReporter:
    """Tests for JSONReporter."""

    @pytest.mark.asyncio
    async def test_generates_valid_json(self, sample_report, tmp_path):
        reporter = JSONReporter(config={"pretty": True}, output_dir=str(tmp_path))
        output_path = await reporter.generate(sample_report)

        assert output_path.exists()
        assert output_path.suffix == ".json"

        with output_path.open() as f:
            data = json.load(f)

        assert data["report_id"] == str(sample_report.id)
        assert data["platform"] == "github"
        assert data["summary"]["total_findings"] == EXPECTED_TOTAL_FINDINGS
        assert len(data["analyzers"]) == EXPECTED_ANALYZERS
        assert data["analyzers"][0]["name"] == "test-analyzer"
        assert len(data["analyzers"][0]["findings"]) == EXPECTED_FINDINGS_PER_ANALYZER

    @pytest.mark.asyncio
    async def test_generates_compact_json(self, sample_report, tmp_path):
        reporter = JSONReporter(config={"pretty": False}, output_dir=str(tmp_path))
        output_path = await reporter.generate(sample_report)

        content = output_path.read_text()

        # Compact JSON should not have newlines (except possibly at end)
        assert content.count("\n") <= 1


class TestMarkdownReporter:
    """Tests for MarkdownReporter."""

    @pytest.mark.asyncio
    async def test_generates_markdown(self, sample_report, tmp_path):
        reporter = MarkdownReporter(config={}, output_dir=str(tmp_path))
        output_path = await reporter.generate(sample_report)

        assert output_path.exists()
        assert output_path.suffix == ".md"

        content = output_path.read_text(encoding="utf-8")

        assert "Pipeline Doctor Report" in content
        assert "Test Error" in content
        assert "Slow Job" in content
        assert "Test error message" in content
        assert "Fix the error" in content

    @pytest.mark.asyncio
    async def test_generates_github_markdown(self, sample_report, tmp_path):
        reporter = GitHubMarkdownReporter(config={"max_findings": 10}, output_dir=str(tmp_path))
        output_path = await reporter.generate(sample_report)

        content = output_path.read_text(encoding="utf-8")

        assert "Pipeline Doctor Analysis" in content
        assert "## Summary" in content
        assert "## Findings" in content
        assert "<details>" in content  # Collapsible sections
