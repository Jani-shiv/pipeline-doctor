"""Tests for security analyzer."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from pipeline_doctor.analyzers.security import SecurityAnalyzer
from pipeline_doctor.core.models import (
    PipelineJob,
    PipelineRun,
    PipelineStatus,
    PipelineStep,
)


@pytest.fixture
def security_analyzer():
    return SecurityAnalyzer()


@pytest.fixture
def secret_in_logs_run():
    """Run with secrets in logs."""
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
            name="deploy-job",
            status=PipelineStatus.SUCCESS,
            steps=[
                PipelineStep(
                    id=uuid4(),
                    name="deploy",
                    status=PipelineStatus.SUCCESS,
                    logs="Deploying with API_KEY=sk-1234567890abcdef1234567890abcdef\nDeploy successful",
                ),
            ],
        ),
    ]
    return run


@pytest.fixture
def github_token_in_logs_run():
    """Run with GitHub token in logs."""
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
            name="release-job",
            status=PipelineStatus.SUCCESS,
            steps=[
                PipelineStep(
                    id=uuid4(),
                    name="release",
                    status=PipelineStatus.SUCCESS,
                    logs="Pushing to registry with token ghp_1234567890abcdef1234567890abcdef123456",
                ),
            ],
        ),
    ]
    return run


class TestSecurityAnalyzer:
    """Tests for SecurityAnalyzer."""

    @pytest.mark.asyncio
    async def test_detects_generic_api_key(self, security_analyzer, secret_in_logs_run):
        result = await security_analyzer.analyze(secret_in_logs_run)

        assert result.has_findings
        secret_findings = [f for f in result.findings if "api" in f.title.lower() or "key" in f.title.lower()]
        assert len(secret_findings) >= 1
        assert secret_findings[0].severity.value == "critical"

    @pytest.mark.asyncio
    async def test_detects_github_token(self, security_analyzer, github_token_in_logs_run):
        result = await security_analyzer.analyze(github_token_in_logs_run)

        assert result.has_findings
        token_findings = [f for f in result.findings if "github" in f.title.lower() or "token" in f.title.lower()]
        assert len(token_findings) >= 1
        assert token_findings[0].severity.value == "critical"

    @pytest.mark.asyncio
    async def test_detects_misconfigurations(self, security_analyzer):
        run = PipelineRun(
            id=uuid4(),
            pipeline_id=uuid4(),
            number=1,
            status=PipelineStatus.SUCCESS,
        )
        run.jobs = [
            PipelineJob(
                id=uuid4(),
                name="insecure-job",
                status=PipelineStatus.SUCCESS,
                metadata={"privileged": "true", "user": "root"},
                steps=[],
            ),
        ]

        result = await security_analyzer.analyze(run)

        assert result.has_findings
        misconfig_findings = [f for f in result.findings if "misconfiguration" in f.title.lower() or "privileged" in f.title.lower() or "root" in f.title.lower()]
        assert len(misconfig_findings) >= 1

    @pytest.mark.asyncio
    async def test_custom_secret_patterns(self):
        analyzer = SecurityAnalyzer(config={
            "secret_patterns": [
                {
                    "pattern": "my_custom_secret_[a-zA-Z0-9]{20,}",
                    "description": "Custom Secret",
                }
            ]
        })

        run = PipelineRun(
            id=uuid4(),
            pipeline_id=uuid4(),
            number=1,
            status=PipelineStatus.SUCCESS,
        )
        run.jobs = [
            PipelineJob(
                id=uuid4(),
                name="test-job",
                status=PipelineStatus.SUCCESS,
                steps=[
                    PipelineStep(
                        id=uuid4(),
                        name="test-step",
                        status=PipelineStatus.SUCCESS,
                        logs="Using secret my_custom_secret_abcdefghijklmnopqrstuvwxyz",
                    ),
                ],
            ),
        ]

        result = await analyzer.analyze(run)
        assert result.has_findings
        custom_findings = [f for f in result.findings if "custom" in f.title.lower()]
        assert len(custom_findings) >= 1
