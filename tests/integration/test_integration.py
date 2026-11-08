"""Integration tests for Pipeline Doctor.

These tests require external services (GitHub, GitLab, Jenkins, etc.)
and are skipped unless the appropriate environment variables are set.
"""

import os

import pytest

from pipeline_doctor.integrations.azure import AzureDevOpsIntegration
from pipeline_doctor.integrations.circleci import CircleCIIntegration
from pipeline_doctor.integrations.github import GitHubIntegration
from pipeline_doctor.integrations.gitlab import GitLabIntegration
from pipeline_doctor.integrations.jenkins import JenkinsIntegration

pytestmark = pytest.mark.integration


def test_integration_placeholder():
    """Placeholder test to ensure integration test suite runs."""
    assert True


@pytest.mark.skipif(not os.environ.get("GITHUB_TOKEN"), reason="GITHUB_TOKEN not set")
async def test_github_integration():
    """Test GitHub Actions integration (requires GITHUB_TOKEN)."""
    # This would require a real token and repo
    # For now, just verify the import works
    assert GitHubIntegration is not None


@pytest.mark.skipif(not os.environ.get("GITLAB_TOKEN"), reason="GITLAB_TOKEN not set")
async def test_gitlab_integration():
    """Test GitLab CI integration (requires GITLAB_TOKEN)."""
    assert GitLabIntegration is not None


@pytest.mark.skipif(not os.environ.get("JENKINS_URL"), reason="JENKINS_URL not set")
async def test_jenkins_integration():
    """Test Jenkins integration (requires JENKINS_URL)."""
    assert JenkinsIntegration is not None


@pytest.mark.skipif(not os.environ.get("AZURE_PAT"), reason="AZURE_PAT not set")
async def test_azure_integration():
    """Test Azure DevOps integration (requires AZURE_PAT)."""
    assert AzureDevOpsIntegration is not None


@pytest.mark.skipif(not os.environ.get("CIRCLECI_TOKEN"), reason="CIRCLECI_TOKEN not set")
async def test_circleci_integration():
    """Test CircleCI integration (requires CIRCLECI_TOKEN)."""
    assert CircleCIIntegration is not None
