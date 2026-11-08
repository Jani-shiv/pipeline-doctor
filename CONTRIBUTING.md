# Contributing to Pipeline Doctor

Thank you for your interest in contributing to Pipeline Doctor! This document provides guidelines for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [Reporting Issues](#reporting-issues)
- [Adding New Features](#adding-new-features)

## 🤝 Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or higher
- Git
- Docker (optional, for containerized development)

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/pipeline-doctor.git
   cd pipeline-doctor
   ```
3. Add the upstream remote:
   ```bash
   git remote add upstream https://github.com/your-org/pipeline-doctor.git
   ```

## 🛠️ Development Setup

### Using Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Using Docker

```bash
# Build development image
docker build -t pipeline-doctor:dev .

# Run development container
docker run -it --rm -v $(pwd):/app pipeline-doctor:dev bash
```

### Configuration

Copy the example configuration and customize it:

```bash
cp config/example.yaml config/pipeline-doctor.yaml
# Edit config/pipeline-doctor.yaml with your settings
```

## 🔧 Making Changes

### Branch Naming

Use descriptive branch names:
- `feature/description-of-feature`
- `fix/description-of-bug`
- `docs/description-of-docs-change`
- `refactor/description-of-refactor`

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding missing tests
- `chore`: Maintenance tasks

Examples:
```
feat(analyzer): add new security pattern detection
fix(github): handle rate limiting correctly
docs: update installation instructions
```

## ✅ Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pipeline_doctor --cov-report=html

# Run specific test types
pytest tests/unit -v
pytest tests/integration -v -m integration

# Run tests for specific Python version
tox
```

### Writing Tests

- Place unit tests in `tests/unit/`
- Place integration tests in `tests/integration/`
- Use descriptive test names: `test_<function>_<scenario>_<expected>`
- Follow AAA pattern: Arrange, Act, Assert
- Mock external dependencies

Example:
```python
# tests/unit/analyzers/test_failure.py
import pytest
from pipeline_doctor.analyzers.failure import FailureAnalyzer
from pipeline_doctor.core.models import PipelineRun, PipelineJob, PipelineStep, PipelineStatus

class TestFailureAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return FailureAnalyzer()
    
    @pytest.fixture
    def failed_run(self):
        run = PipelineRun(...)
        run.jobs = [
            PipelineJob(
                name="test-job",
                status=PipelineStatus.FAILURE,
                steps=[
                    PipelineStep(name="step1", status=PipelineStatus.FAILURE, logs="Error: timeout occurred")
                ]
            )
        ]
        return run
    
    @pytest.mark.asyncio
    async def test_detects_timeout_pattern(self, analyzer, failed_run):
        result = await analyzer.analyze(failed_run)
        
        assert result.has_findings
        timeout_findings = [f for f in result.findings if "timeout" in f.title.lower()]
        assert len(timeout_findings) == 1
```

## 🎨 Code Style

### Python Style Guide

We use:
- **Ruff** for linting and formatting
- **MyPy** for type checking
- **Black** compatible formatting (via Ruff)

Run style checks:
```bash
# Check style
ruff check src tests

# Auto-fix style issues
ruff check --fix src tests

# Format code
ruff format src tests

# Type check
mypy src
```

### Key Guidelines

1. **Type Hints**: All public functions must have type hints
2. **Docstrings**: Use Google-style docstrings for public APIs
3. **Async**: Use `async/await` for I/O operations
4. **Error Handling**: Use custom exceptions from `pipeline_doctor.core.exceptions`
5. **Logging**: Use `structlog` for structured logging

### Example Code Style

```python
"""Module docstring."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from pipeline_doctor.core.exceptions import PipelineDoctorError
from pipeline_doctor.core.models import PipelineRun


class MyConfig(BaseModel):
    """Configuration for my feature."""
    
    enabled: bool = True
    threshold: int = Field(default=100, ge=0)
    name: Optional[str] = None


async def analyze_something(run: PipelineRun, config: MyConfig) -> AnalysisResult:
    """Analyze a pipeline run for something.
    
    Args:
        run: The pipeline run to analyze.
        config: Configuration for the analysis.
    
    Returns:
        AnalysisResult with findings.
    
    Raises:
        AnalyzerError: If analysis fails.
    """
    if not config.enabled:
        return AnalysisResult(analyzer_name="my-analyzer")
    
    # Implementation here
    ...
```

## 📥 Pull Request Process

1. **Create a feature branch** from `main`
2. **Make your changes** with tests
3. **Run the full test suite** locally
4. **Update documentation** if needed
5. **Push to your fork** and create a PR

### PR Requirements

- [ ] All tests pass
- [ ] Code follows style guidelines
- [ ] Type checking passes (`mypy src`)
- [ ] New features have tests
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (for significant changes)
- [ ] PR description explains the changes

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
```

## 🐛 Reporting Issues

Use the GitHub issue templates:
- [Bug Report](.github/ISSUE_TEMPLATE/bug_report.yml)
- [Feature Request](.github/ISSUE_TEMPLATE/feature_request.yml)

Provide as much detail as possible:
- Steps to reproduce
- Expected vs actual behavior
- Environment details
- Logs/error messages

## 🌟 Adding New Features

### New Analyzer

1. Create `src/pipeline_doctor/analyzers/new_analyzer.py`
2. Extend `BaseAnalyzer` class
3. Register with `@AnalyzerRegistry.register`
4. Add default config in `get_default_config()`
5. Add tests in `tests/unit/analyzers/test_new_analyzer.py`
6. Update documentation in `docs/analyzers.md`

### New Platform Integration

1. Create `src/pipeline_doctor/integrations/new_platform.py`
2. Extend `BaseIntegration` class
3. Implement all abstract methods
4. Register with `@IntegrationRegistry.register`
5. Add tests in `tests/integration/test_new_platform.py`
6. Update documentation in `docs/platforms/new_platform.md`

### New Reporter

1. Create `src/pipeline_doctor/reporters/new_reporter.py`
2. Extend `BaseReporter` class
3. Implement `generate()` method
4. Register with `@ReporterRegistry.register`
5. Add tests in `tests/unit/reporters/test_new_reporter.py`

## 📚 Documentation

Documentation is in the `docs/` directory:
- `getting-started.md` - Installation and first steps
- `configuration.md` - Configuration reference
- `platforms/` - Platform-specific guides
- `analyzers.md` - Built-in analyzers
- `reporters.md` - Output formats
- `integrations.md` - Notification integrations
- `api-reference.md` - Python API docs
- `architecture.md` - System design

Build docs locally:
```bash
pip install -e ".[docs]"
mkdocs serve
```

## 🏷️ Versioning

We use [Semantic Versioning](https://semver.org/):
- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes (backward compatible)

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 💬 Getting Help

- [GitHub Discussions](https://github.com/your-org/pipeline-doctor/discussions)
- [Discord Community](https://discord.gg/pipeline-doctor)
- Email: team@pipeline-doctor.io

---

Thank you for contributing! 🎉