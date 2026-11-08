"""Base reporter class."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pipeline_doctor.core.exceptions import ReporterError
from pipeline_doctor.core.models import AnalysisReport


class BaseReporter(ABC):
    """Base class for all reporters."""

    name: str = "base"
    description: str = "Base reporter"

    def __init__(self, config: dict[str, Any] = None, output_dir: str = "./reports"):
        self.config = config or {}
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    async def generate(self, report: AnalysisReport, output_path: Path | None = None) -> Path:
        """Generate report and return output path."""
        pass

    def get_output_path(self, report: AnalysisReport, extension: str) -> Path:
        """Generate default output path."""
        timestamp = report.started_at.strftime("%Y%m%d_%H%M%S")
        filename = f"{self.name}_report_{timestamp}.{extension}"
        return self.output_dir / filename

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    @classmethod
    def get_default_config(cls) -> dict[str, Any]:
        """Get default configuration for this reporter."""
        return {}


class ReporterRegistry:
    """Registry for managing reporters."""

    _reporters: dict[str, type] = {}

    @classmethod
    def register(cls, reporter_class: type) -> type:
        """Register a reporter class."""
        if not issubclass(reporter_class, BaseReporter):
            raise ReporterError(f"{reporter_class} is not a BaseReporter")
        cls._reporters[reporter_class.name] = reporter_class
        return reporter_class

    @classmethod
    def get(cls, name: str) -> type | None:
        """Get reporter class by name."""
        return cls._reporters.get(name)

    @classmethod
    def create(cls, name: str, config: dict[str, Any] = None, output_dir: str = "./reports") -> BaseReporter | None:
        """Create reporter instance."""
        reporter_class = cls.get(name)
        if not reporter_class:
            return None
        return reporter_class(config, output_dir)

    @classmethod
    def list_available(cls) -> list:
        """List all registered reporter names."""
        return list(cls._reporters.keys())
