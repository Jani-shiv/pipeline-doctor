"""Base analyzer class."""

from abc import ABC, abstractmethod
from typing import Any

from pipeline_doctor.core.exceptions import AnalyzerError
from pipeline_doctor.core.models import (
    AnalysisResult,
    Finding,
    FindingCategory,
    FindingSeverity,
    PipelineRun,
)


class BaseAnalyzer(ABC):
    """Base class for all analyzers."""

    name: str = "base"
    description: str = "Base analyzer"
    version: str = "1.0.0"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self._results: list[AnalysisResult] = []

    @abstractmethod
    async def analyze(self, run: PipelineRun) -> AnalysisResult:
        """Analyze a pipeline run and return findings."""
        pass

    async def analyze_with_error_handling(self, run: PipelineRun) -> AnalysisResult:
        """Analyze with error handling."""
        result = AnalysisResult(analyzer_name=self.name, analyzer_version=self.version)
        try:
            result = await self.analyze(run)
        except Exception as e:
            result.add_error(f"Analyzer {self.name} failed: {str(e)}")
            # Don't raise, let the orchestrator handle it
        return result

    def create_finding(
        self,
        category: FindingCategory,
        severity: FindingSeverity,
        title: str,
        message: str,
        *,
        suggestion: str | None = None,
        affected_job: str | None = None,
        affected_step: str | None = None,
        evidence: dict[str, Any] | None = None,
        references: list[str] | None = None,
    ) -> Finding:
        """Helper to create a finding."""
        return Finding(
            analyzer_name=self.name,
            category=category,
            severity=severity,
            title=title,
            message=message,
            suggestion=suggestion,
            affected_job=affected_job,
            affected_step=affected_step,
            evidence=evidence or {},
            references=references or [],
        )

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    @classmethod
    def get_default_config(cls) -> dict[str, Any]:
        """Get default configuration for this analyzer."""
        return {}

    def validate_config(self) -> list[str]:
        """Validate configuration and return list of errors."""
        return []


class AnalyzerRegistry:
    """Registry for managing analyzers."""

    _analyzers: dict[str, type] = {}
    _instances: dict[str, BaseAnalyzer] = {}

    @classmethod
    def register(cls, analyzer_class: type) -> type:
        """Register an analyzer class."""
        if not issubclass(analyzer_class, BaseAnalyzer):
            raise AnalyzerError(f"{analyzer_class} is not a BaseAnalyzer")
        cls._analyzers[analyzer_class.name] = analyzer_class
        return analyzer_class

    @classmethod
    def get(cls, name: str) -> type | None:
        """Get analyzer class by name."""
        return cls._analyzers.get(name)

    @classmethod
    def create(cls, name: str, config: dict[str, Any] | None = None) -> BaseAnalyzer | None:
        """Create analyzer instance."""
        analyzer_class = cls.get(name)
        if not analyzer_class:
            return None
        return analyzer_class(config)  # type: ignore[no-any-return]

    @classmethod
    def create_all(cls, configs: dict[str, dict[str, Any]]) -> dict[str, BaseAnalyzer]:
        """Create all configured analyzers."""
        instances = {}
        for name, config in configs.items():
            if config.get("enabled", True):
                analyzer = cls.create(name, config.get("config", {}))
                if analyzer:
                    instances[name] = analyzer
                else:
                    # Try to instantiate built-in analyzer
                    analyzer_class = cls.get(name)
                    if analyzer_class:
                        instances[name] = analyzer_class(config.get("config", {}))
        return instances

    @classmethod
    def list_available(cls) -> list[str]:
        """List all registered analyzer names."""
        return list(cls._analyzers.keys())

    @classmethod
    def clear(cls) -> None:
        """Clear registry."""
        cls._analyzers.clear()
        cls._instances.clear()
