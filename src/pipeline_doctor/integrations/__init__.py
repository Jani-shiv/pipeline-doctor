"""Pipeline Doctor Integrations Package."""

from pipeline_doctor.integrations.azure import AzureDevOpsIntegration
from pipeline_doctor.integrations.base import BaseIntegration, IntegrationRegistry
from pipeline_doctor.integrations.circleci import CircleCIIntegration
from pipeline_doctor.integrations.github import GitHubIntegration
from pipeline_doctor.integrations.gitlab import GitLabIntegration
from pipeline_doctor.integrations.jenkins import JenkinsIntegration

__all__ = [
    "BaseIntegration",
    "IntegrationRegistry",
    "GitHubIntegration",
    "GitLabIntegration",
    "JenkinsIntegration",
    "AzureDevOpsIntegration",
    "CircleCIIntegration",
]

# Ensure all integrations are registered
def register_all() -> None:
    """Register all built-in integrations."""
    pass


def get_available_integrations() -> list:
    """Get list of available integration platforms."""
    return IntegrationRegistry.list_available()
