"""Tests for performance analyzer."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from pipeline_doctor.analyzers.performance import PerformanceAnalyzer
from pipeline_doctor.core.models import (
    PipelineJob,
    PipelineRun,
    PipelineStatus,
)


@pytest.fixture
def performance_analyzer():
    return PerformanceAnalyzer()


@pytest.fixture
def slow_pipeline_run():
    """Run with slow overall duration."""
    run = PipelineRun(
        id=uuid4(),
        pipeline_id=uuid4(),
        number=1,
        status=PipelineStatus.SUCCESS,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_seconds=4000,
    )
    run.jobs = [
        PipelineJob(
            id=uuid4(),
            name="job1",
            status=PipelineStatus.SUCCESS,
            duration_seconds=1000,
        ),
        PipelineJob(
            id=uuid4(),
            name="job2",
            status=PipelineStatus.SUCCESS,
            duration_seconds=3000,
        ),
    ]
    return run


@pytest.fixture
def slow_job_run():
    """Run with slow individual job."""
    run = PipelineRun(
        id=uuid4(),
        pipeline_id=uuid4(),
        number=1,
        status=PipelineStatus.SUCCESS,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_seconds=1000,
    )
    run.jobs = [
        PipelineJob(
            id=uuid4(),
            name="fast-job",
            status=PipelineStatus.SUCCESS,
            duration_seconds=100,
        ),
        PipelineJob(
            id=uuid4(),
            name="slow-job",
            status=PipelineStatus.SUCCESS,
            duration_seconds=900,
        ),
    ]
    return run


@pytest.fixture
def cancelled_job_run():
    """Run with cancelled job that ran for a while."""
    run = PipelineRun(
        id=uuid4(),
        pipeline_id=uuid4(),
        number=1,
        status=PipelineStatus.SUCCESS,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_seconds=500,
    )
    run.jobs = [
        PipelineJob(
            id=uuid4(),
            name="cancelled-job",
            status=PipelineStatus.CANCELLED,
            duration_seconds=800,
        ),
    ]
    return run


class TestPerformanceAnalyzer:
    """Tests for PerformanceAnalyzer."""

    @pytest.mark.asyncio
    async def test_detects_slow_pipeline(self, performance_analyzer, slow_pipeline_run):
        result = await performance_analyzer.analyze(slow_pipeline_run)

        assert result.has_findings
        pipeline_findings = [f for f in result.findings if "pipeline" in f.title.lower()]
        assert len(pipeline_findings) >= 1
        assert pipeline_findings[0].severity.value in ("warning", "critical")

    @pytest.mark.asyncio
    async def test_detects_slow_job(self, performance_analyzer, slow_job_run):
        result = await performance_analyzer.analyze(slow_job_run)

        assert result.has_findings
        job_findings = [
            f for f in result.findings if "job" in f.title.lower() and "slow" in f.title.lower()
        ]
        assert len(job_findings) >= 1
        assert job_findings[0].affected_job == "slow-job"

    @pytest.mark.asyncio
    async def test_detects_waste(self, performance_analyzer, cancelled_job_run):
        result = await performance_analyzer.analyze(cancelled_job_run)

        assert result.has_findings
        waste_findings = [f for f in result.findings if f.category.value == "cost"]
        assert len(waste_findings) >= 1
        assert waste_findings[0].category.value == "cost"

    @pytest.mark.asyncio
    async def test_custom_thresholds(self):
        analyzer = PerformanceAnalyzer(
            config={
                "thresholds": {
                    "job_duration_warn": 100,
                    "job_duration_critical": 200,
                }
            }
        )

        run = PipelineRun(
            id=uuid4(),
            pipeline_id=uuid4(),
            number=1,
            status=PipelineStatus.SUCCESS,
            duration_seconds=500,
        )
        run.jobs = [
            PipelineJob(
                id=uuid4(),
                name="medium-job",
                status=PipelineStatus.SUCCESS,
                duration_seconds=150,
            ),
        ]

        result = await analyzer.analyze(run)
        assert result.has_findings
        warning_findings = [f for f in result.findings if f.severity.value == "warning"]
        assert len(warning_findings) >= 1
