"""Pipeline Doctor Reporters Package."""

from pipeline_doctor.reporters.base import BaseReporter, ReporterRegistry
from pipeline_doctor.reporters.html import HTMLReporter
from pipeline_doctor.reporters.json import JSONLinesReporter, JSONReporter
from pipeline_doctor.reporters.markdown import GitHubMarkdownReporter, MarkdownReporter
from pipeline_doctor.reporters.pdf import PDFReporter

__all__ = [
    "BaseReporter",
    "ReporterRegistry",
    "HTMLReporter",
    "JSONReporter",
    "JSONLinesReporter",
    "MarkdownReporter",
    "GitHubMarkdownReporter",
    "PDFReporter",
]


# Ensure all reporters are registered
def register_all() -> None:
    """Register all built-in reporters."""
    pass


def get_available_reporters() -> list:
    """Get list of available reporter names."""
    return ReporterRegistry.list_available()
