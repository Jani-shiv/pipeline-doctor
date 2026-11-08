"""Tests for core models."""

from datetime import UTC, datetime
from uuid import uuid4

from pipeline_doctor.core.models import (
    AnalysisReport,
    AnalysisResult,
    Finding,
    FindingCategory,
    FindingSeverity,
    Pipeline,
    PipelineJob,
    PipelinePlatform,
    PipelineRun,
    PipelineStatus,
    PipelineStep,
)

# Test constants
EXPECTED_FAILED_STEPS = 2
EXPECTED_TOTAL_FINDINGS = 3
EXPECTED_CRITICAL_COUNT = 1
EXPECTED_ERROR_COUNT = 1
EXPECTED_WARNING_COUNT = 1
EXPECTED_INFO_COUNT = 0


class TestPipelineModels:
    """Tests for pipeline domain models."""

    def test_pipeline_creation(self):
        pipeline = Pipeline(
            name="test",
            platform=PipelinePlatform.GITHUB,
            repository="owner/repo",
        )

        assert pipeline.name == "test"
        assert pipeline.platform == PipelinePlatform.GITHUB
        assert pipeline.repository == "owner/repo"
        assert pipeline.branch == "main"

    def test_pipeline_success_rate(self):
        pipeline = Pipeline(
            name="test",
            platform=PipelinePlatform.GITHUB,
            repository="owner/repo",
        )

        # Add runs
        run1 = PipelineRun(
            id=uuid4(),
            pipeline_id=pipeline.id,
            number=1,
            status=PipelineStatus.SUCCESS,
        )
        run2 = PipelineRun(
            id=uuid4(),
            pipeline_id=pipeline.id,
            number=2,
            status=PipelineStatus.FAILURE,
        )
        run3 = PipelineRun(
            id=uuid4(),
            pipeline_id=pipeline.id,
            number=3,
            status=PipelineStatus.SUCCESS,
        )

        pipeline.runs = [run1, run2, run3]

        assert pipeline.success_rate == 2/3

    def test_run_duration_calculation(self):
        started = datetime.now(UTC)
        completed = datetime.now(UTC)

        run = PipelineRun(
            id=uuid4(),
            pipeline_id=uuid4(),
            number=1,
            status=PipelineStatus.SUCCESS,
            started_at=started,
            completed_at=completed,
        )

        # Duration should be calculated automatically
        assert run.computed_duration is not None
        assert run.computed_duration >= 0

    def test_job_failed_steps(self):
        job = PipelineJob(
            id=uuid4(),
            name="test-job",
            status=PipelineStatus.FAILURE,
            steps=[
                PipelineStep(id=uuid4(), name="step1", status=PipelineStatus.SUCCESS),
                PipelineStep(id=uuid4(), name="step2", status=PipelineStatus.FAILURE),
                PipelineStep(id=uuid4(), name="step3", status=PipelineStatus.FAILURE),
            ],
        )

        failed = job.failed_steps
        assert len(failed) == EXPECTED_FAILED_STEPS
        assert all(s.status == PipelineStatus.FAILURE for s in failed)


class TestFindingModels:
    """Tests for finding models."""

    def test_finding_creation(self):
        finding = Finding(
            analyzer_name="test",
            category=FindingCategory.FAILURE_PATTERN,
            severity=FindingSeverity.ERROR,
            title="Test",
            message="Test message",
        )

        assert finding.analyzer_name == "test"
        assert finding.category == FindingCategory.FAILURE_PATTERN
        assert finding.severity == FindingSeverity.ERROR

    def test_finding_to_dict(self):
        finding = Finding(
            analyzer_name="test",
            category=FindingCategory.SECURITY,
            severity=FindingSeverity.CRITICAL,
            title="Secret Found",
            message="API key detected",
        )

        data = finding.to_dict()
        assert data["analyzer_name"] == "test"
        assert data["category"] == "security"
        assert data["severity"] == "critical"


class TestAnalysisModels:
    """Tests for analysis models."""

    def test_analysis_result_properties(self):
        result = AnalysisResult(analyzer_name="test")

        finding1 = Finding(
            analyzer_name="test",
            category=FindingCategory.FAILURE_PATTERN,
            severity=FindingSeverity.CRITICAL,
            title="Critical",
            message="Critical issue",
        )
        finding2 = Finding(
            analyzer_name="test",
            category=FindingCategory.PERFORMANCE,
            severity=FindingSeverity.WARNING,
            title="Warning",
            message="Performance issue",
        )

        result.add_finding(finding1)
        result.add_finding(finding2)

        assert result.has_findings
        assert len(result.critical_findings) == EXPECTED_CRITICAL_COUNT
        assert len(result.warning_findings) == EXPECTED_WARNING_COUNT
        assert len(result.error_findings) == 0
        assert len(result.info_findings) == EXPECTED_INFO_COUNT

    def test_analysis_report_aggregation(self):
        report = AnalysisReport(
            pipeline_id=uuid4(),
            run_id=uuid4(),
            platform="github",
        )

        result1 = AnalysisResult(analyzer_name="analyzer1")
        result1.add_finding(Finding(
            analyzer_name="analyzer1",
            category=FindingCategory.FAILURE_PATTERN,
            severity=FindingSeverity.ERROR,
            title="Error 1",
            message="Error message",
        ))

        result2 = AnalysisResult(analyzer_name="analyzer2")
        result2.add_finding(Finding(
            analyzer_name="analyzer2",
            category=FindingCategory.SECURITY,
            severity=FindingSeverity.CRITICAL,
            title="Critical 1",
            message="Critical message",
        ))
        result2.add_finding(Finding(
            analyzer_name="analyzer2",
            category=FindingCategory.PERFORMANCE,
            severity=FindingSeverity.WARNING,
            title="Warning 1",
            message="Warning message",
        ))

        report.add_analyzer_result(result1)
        report.add_analyzer_result(result2)

        assert report.total_findings == EXPECTED_TOTAL_FINDINGS
        assert report.findings_by_severity[FindingSeverity.CRITICAL] == EXPECTED_CRITICAL_COUNT
        assert report.findings_by_severity[FindingSeverity.ERROR] == EXPECTED_ERROR_COUNT
        assert report.findings_by_severity[FindingSeverity.WARNING] == EXPECTED_WARNING_COUNT
        assert report.findings_by_severity[FindingSeverity.INFO] == EXPECTED_INFO_COUNT
        assert report.has_critical_findings
        assert not report.has_errors  # No analyzer errors
