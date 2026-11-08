"""Tests for failure analyzer."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from pipeline_doctor.analyzers.failure import FailureAnalyzer
from pipeline_doctor.core.models import (
    PipelineJob,
    PipelineRun,
    PipelineStatus,
    PipelineStep,
)


@pytest.fixture
def failure_analyzer():
    return FailureAnalyzer()


@pytest.fixture
def timeout_run():
    """Run with timeout failure."""
    run = PipelineRun(
        id=uuid4(),
        pipeline_id=uuid4(),
        number=1,
        status=PipelineStatus.FAILURE,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    run.jobs = [
        PipelineJob(
            id=uuid4(),
            name="test-job",
            status=PipelineStatus.FAILURE,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            steps=[
                PipelineStep(
                    id=uuid4(),
                    name="test-step",
                    status=PipelineStatus.FAILURE,
                    logs="Error: Timeout after 300 seconds\nProcess timed out",
                ),
            ],
        ),
    ]
    return run


@pytest.fixture
def oom_run():
    """Run with out of memory failure."""
    run = PipelineRun(
        id=uuid4(),
        pipeline_id=uuid4(),
        number=1,
        status=PipelineStatus.FAILURE,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    run.jobs = [
        PipelineJob(
            id=uuid4(),
            name="build-job",
            status=PipelineStatus.FAILURE,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            steps=[
                PipelineStep(
                    id=uuid4(),
                    name="compile",
                    status=PipelineStatus.FAILURE,
                    logs="java.lang.OutOfMemoryError: Java heap space\nGC overhead limit exceeded",
                ),
            ],
        ),
    ]
    return run


@pytest.fixture
def permission_run():
    """Run with permission denied failure."""
    run = PipelineRun(
        id=uuid4(),
        pipeline_id=uuid4(),
        number=1,
        status=PipelineStatus.FAILURE,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    run.jobs = [
        PipelineJob(
            id=uuid4(),
            name="deploy-job",
            status=PipelineStatus.FAILURE,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            steps=[
                PipelineStep(
                    id=uuid4(),
                    name="deploy",
                    status=PipelineStatus.FAILURE,
                    logs="Permission denied: cannot write to /opt/app\nError 403: Forbidden",
                ),
            ],
        ),
    ]
    return run


class TestFailureAnalyzer:
    """Tests for FailureAnalyzer."""

    @pytest.mark.asyncio
    async def test_detects_timeout(self, failure_analyzer, timeout_run):
        result = await failure_analyzer.analyze(timeout_run)

        assert result.has_findings
        timeout_findings = [f for f in result.findings if "timeout" in f.title.lower()]
        assert len(timeout_findings) >= 1
        assert timeout_findings[0].severity.value in ("error", "critical")
        assert "timeout" in timeout_findings[0].suggestion.lower()

    @pytest.mark.asyncio
    async def test_detects_oom(self, failure_analyzer, oom_run):
        result = await failure_analyzer.analyze(oom_run)

        assert result.has_findings
        oom_findings = [f for f in result.findings if "memory" in f.title.lower() or "oom" in f.title.lower()]
        assert len(oom_findings) >= 1
        assert oom_findings[0].severity.value in ("error", "critical")

    @pytest.mark.asyncio
    async def test_detects_permission_denied(self, failure_analyzer, permission_run):
        result = await failure_analyzer.analyze(permission_run)

        assert result.has_findings
        perm_findings = [f for f in result.findings if "permission" in f.title.lower() or "denied" in f.title.lower()]
        assert len(perm_findings) >= 1

    @pytest.mark.asyncio
    async def test_ignores_successful_runs(self, failure_analyzer):
        run = PipelineRun(
            id=uuid4(),
            pipeline_id=uuid4(),
            number=1,
            status=PipelineStatus.SUCCESS,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        run.jobs = [
            PipelineJob(
                id=uuid4(),
                name="test-job",
                status=PipelineStatus.SUCCESS,
                steps=[
                    PipelineStep(id=uuid4(), name="step1", status=PipelineStatus.SUCCESS),
                ],
            ),
        ]

        result = await failure_analyzer.analyze(run)
        assert not result.has_findings

    @pytest.mark.asyncio
    async def test_custom_patterns(self):
        analyzer = FailureAnalyzer(config={
            "custom_patterns": [
                {
                    "pattern": "custom_error_pattern",
                    "severity": "warning",
                    "suggestion": "Check custom error",
                    "category": "custom",
                }
            ]
        })

        run = PipelineRun(
            id=uuid4(),
            pipeline_id=uuid4(),
            number=1,
            status=PipelineStatus.FAILURE,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        run.jobs = [
            PipelineJob(
                id=uuid4(),
                name="test-job",
                status=PipelineStatus.FAILURE,
                steps=[
                    PipelineStep(
                        id=uuid4(),
                        name="test-step",
                        status=PipelineStatus.FAILURE,
                        logs="custom_error_pattern occurred",
                    ),
                ],
            ),
        ]

        result = await analyzer.analyze(run)
        assert result.has_findings
        custom_findings = [f for f in result.findings if f.category.value == "custom"]
        assert len(custom_findings) >= 1
        assert custom_findings[0].severity.value == "warning"
