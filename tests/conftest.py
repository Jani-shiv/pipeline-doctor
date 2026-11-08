"""Test configuration and fixtures."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

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


@pytest.fixture
def sample_pipeline():
    """Create a sample pipeline."""
    return Pipeline(
        id=uuid4(),
        name="test-pipeline",
        platform=PipelinePlatform.GITHUB,
        repository="owner/repo",
        branch="main",
    )


@pytest.fixture
def sample_run():
    """Create a sample pipeline run."""
    return PipelineRun(
        id=uuid4(),
        pipeline_id=uuid4(),
        number=1,
        status=PipelineStatus.SUCCESS,
        trigger="push",
        branch="main",
        commit_sha="abc123",
        commit_message="Test commit",
        author="test-user",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_seconds=300,
        url="https://github.com/owner/repo/actions/runs/1",
    )


@pytest.fixture
def failed_run():
    """Create a failed pipeline run with logs."""
    run = PipelineRun(
        id=uuid4(),
        pipeline_id=uuid4(),
        number=2,
        status=PipelineStatus.FAILURE,
        trigger="push",
        branch="main",
        commit_sha="def456",
        commit_message="Failed commit",
        author="test-user",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_seconds=120,
    )

    run.jobs = [
        PipelineJob(
            id=uuid4(),
            name="build",
            status=PipelineStatus.FAILURE,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_seconds=100,
            steps=[
                PipelineStep(
                    id=uuid4(),
                    name="install-deps",
                    status=PipelineStatus.SUCCESS,
                    duration_seconds=30,
                ),
                PipelineStep(
                    id=uuid4(),
                    name="run-tests",
                    status=PipelineStatus.FAILURE,
                    duration_seconds=70,
                    logs="Error: Connection timeout after 30s\nTest failed with exit code 1",
                ),
            ],
        ),
        PipelineJob(
            id=uuid4(),
            name="deploy",
            status=PipelineStatus.SKIPPED,
            steps=[],
        ),
    ]

    return run


@pytest.fixture
def slow_run():
    """Create a slow pipeline run."""
    run = PipelineRun(
        id=uuid4(),
        pipeline_id=uuid4(),
        number=3,
        status=PipelineStatus.SUCCESS,
        trigger="push",
        branch="main",
        commit_sha="ghi789",
        commit_message="Slow commit",
        author="test-user",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        duration_seconds=3600,  # 1 hour
    )

    run.jobs = [
        PipelineJob(
            id=uuid4(),
            name="slow-job",
            status=PipelineStatus.SUCCESS,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            duration_seconds=2000,  # Very slow job
            steps=[
                PipelineStep(
                    id=uuid4(),
                    name="slow-step",
                    status=PipelineStatus.SUCCESS,
                    duration_seconds=500,  # Slow step
                ),
            ],
        ),
    ]

    return run


@pytest.fixture
def sample_finding():
    """Create a sample finding."""
    return Finding(
        analyzer_name="test-analyzer",
        category=FindingCategory.FAILURE_PATTERN,
        severity=FindingSeverity.ERROR,
        title="Test Finding",
        message="This is a test finding",
        suggestion="Fix the issue",
        affected_job="test-job",
        affected_step="test-step",
        evidence={"key": "value"},
    )


@pytest.fixture
def sample_analysis_result(sample_finding):
    """Create a sample analysis result."""
    result = AnalysisResult(analyzer_name="test-analyzer")
    result.add_finding(sample_finding)
    return result


@pytest.fixture
def sample_report(sample_analysis_result):
    """Create a sample analysis report."""
    report = AnalysisReport(
        pipeline_id=uuid4(),
        run_id=uuid4(),
        platform="github",
    )
    report.add_analyzer_result(sample_analysis_result)
    return report


@pytest.fixture
def github_workflow_config():
    """Sample GitHub Actions workflow config."""
    return {
        "name": "CI",
        "on": {"push": {"branches": ["main"]}},
        "jobs": {
            "build": {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"},
                    {"name": "Install", "run": "npm ci"},
                    {"name": "Test", "run": "npm test"},
                ],
            },
        },
    }


@pytest.fixture
def gitlab_ci_config():
    """Sample GitLab CI config."""
    return {
        "stages": ["build", "test"],
        "build_job": {
            "stage": "build",
            "script": ["npm ci", "npm run build"],
        },
        "test_job": {
            "stage": "test",
            "script": ["npm test"],
        },
    }
