"""Pipeline Doctor Analyzers Package."""

from pipeline_doctor.analyzers.base import AnalyzerRegistry, BaseAnalyzer
from pipeline_doctor.analyzers.cost import CostAnalyzer
from pipeline_doctor.analyzers.failure import FailureAnalyzer
from pipeline_doctor.analyzers.performance import PerformanceAnalyzer
from pipeline_doctor.analyzers.reliability import ReliabilityAnalyzer
from pipeline_doctor.analyzers.security import SecurityAnalyzer

__all__ = [
    "BaseAnalyzer",
    "AnalyzerRegistry",
    "FailureAnalyzer",
    "PerformanceAnalyzer",
    "SecurityAnalyzer",
    "CostAnalyzer",
    "ReliabilityAnalyzer",
]


# Ensure all analyzers are registered
def register_all() -> None:
    """Register all built-in analyzers."""
    # Registration happens via decorators at import time
    pass


def get_available_analyzers() -> list:
    """Get list of available analyzer names."""
    return AnalyzerRegistry.list_available()
