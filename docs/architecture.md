# Architecture

This document describes the internal architecture of Pipeline Doctor.

## Overview

Pipeline Doctor follows a modular, plugin-based architecture designed for extensibility and maintainability.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Pipeline Doctor                          │
├─────────────────────────────────────────────────────────────────┤
│  CLI Layer                    │  Core Layer                     │
│  ┌─────────────────────────┐  │  ┌─────────────────────────────┐ │
│  │ Commands                │  │  │ Models                      │ │
│  │   - analyze             │  │  │   - Pipeline, Run, Job, Step│ │
│  │   - monitor             │  │  │   - AnalysisReport, Finding │ │
│  │   - report              │  │  │   - Configuration           │ │
│  │   - scan                │  │  │                             │ │
│  └─────────────────────────┘  │  └─────────────────────────────┘ │
│                               │  ┌─────────────────────────────┐ │
│  Integration Layer           │  │ Analyzers                    │ │
│  ┌─────────────────────────┐  │  │   - Failure                │ │
│  │ Platform Integrations   │  │  │   - Performance            │ │
│  │   - GitHub Actions      │  │  │   - Security               │ │
│  │   - GitLab CI           │  │  │   - Cost                   │ │
│  │   - Jenkins             │  │  │   - Reliability            │ │
│  │   - Azure DevOps        │  │  │   - Custom (pluggable)     │ │
│  │   - CircleCI            │  │  │                             │ │
│  └─────────────────────────┘  │  └─────────────────────────────┘ │
│                               │  ┌─────────────────────────────┐ │
│  Reporter Layer             │  │ Reporters                    │ │
│  ┌─────────────────────────┐  │  │   - HTML                   │ │
│  │ Report Generators       │  │  │   - JSON / JSONL           │ │
│  │   - HTML                │  │  │   - Markdown               │ │
│  │   - JSON                │  │  │   - PDF                    │ │
│  │   - Markdown            │  │  │   - Custom (pluggable)     │ │
│  │   - PDF                 │  │  │                             │ │
│  └─────────────────────────┘  │  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### Models (`pipeline_doctor.core.models`)

Domain models representing CI/CD concepts:

- **Pipeline**: A CI/CD pipeline definition
- **PipelineRun**: A single pipeline execution
- **PipelineJob**: A job within a run
- **PipelineStep**: A step within a job
- **AnalysisReport**: Aggregated analysis results
- **AnalysisResult**: Results from a single analyzer
- **Finding**: Individual finding with severity, category, suggestion

### Configuration (`pipeline_doctor.core.config`)

- `PipelineDoctorConfig`: Main configuration class using Pydantic Settings
- Environment variable support with nested delimiter `__`
- Platform, analyzer, reporter, notification, and storage configs

### Exceptions (`pipeline_doctor.core.exceptions`)

Custom exception hierarchy:
- `PipelineDoctorError`: Base exception
- `ConfigurationError`: Configuration issues
- `PlatformError`: Platform integration errors
- `AuthenticationError`: Auth failures
- `RateLimitError`: Rate limiting
- `AnalyzerError`: Analyzer execution errors
- `ReporterError`: Report generation errors

### Utilities (`pipeline_doctor.core.utils`)

Common utilities:
- ID generation, string manipulation
- Duration parsing/formatting
- Logging sanitization
- Async rate limiting
- Retry with exponential backoff
- File I/O helpers

## Plugin Architecture

### Analyzer Plugin System

```python
# Base class
class BaseAnalyzer(ABC):
    name: str
    description: str
    version: str
    
    @abstractmethod
    async def analyze(self, run: PipelineRun) -> AnalysisResult:
        pass

# Registry
class AnalyzerRegistry:
    _analyzers: Dict[str, type] = {}
    
    @classmethod
    def register(cls, analyzer_class: type) -> type:
        cls._analyzers[analyzer_class.name] = analyzer_class
        return analyzer_class
```

### Integration Plugin System

```python
# Base class
class BaseIntegration(ABC):
    platform: PipelinePlatform
    
    @abstractmethod
    async def connect(self) -> None:
        pass
    
    @abstractmethod
    async def get_pipeline_runs(...) -> List[PipelineRun]:
        pass
    
    # ... other abstract methods
```

### Reporter Plugin System

```python
# Base class
class BaseReporter(ABC):
    name: str
    description: str
    
    @abstractmethod
    async def generate(self, report: AnalysisReport, output_path: Path) -> Path:
        pass
```

## Data Flow

### Analysis Pipeline

```
1. CLI Command (analyze/report/monitor)
       │
       ▼
2. Load Configuration
       │
       ▼
3. Initialize Platform Integration
       │
       ▼
4. Fetch Pipeline Runs
       │
       ▼
5. Run Analyzers (parallel)
       │
       ├── Failure Analyzer
       ├── Performance Analyzer
       ├── Security Analyzer
       ├── Cost Analyzer
       └── Reliability Analyzer
       │
       ▼
6. Aggregate AnalysisResults → AnalysisReport
       │
       ▼
7. Generate Reports (selected formatters)
       │
       ├── HTML Reporter
       ├── JSON Reporter
       ├── Markdown Reporter
       └── PDF Reporter
       │
       ▼
8. Send Notifications (if configured)
       │
       ▼
9. Store Results (if configured)
```

### Monitor Pipeline

```
1. CLI Command (monitor)
       │
       ▼
2. Load Configuration
       │
       ▼
3. Initialize Platform Integration
       │
       ▼
4. Loop (every N seconds):
       │
       ├── Fetch Recent Runs
       ├── Check for New Completed Runs
       ├── Analyze New Runs
       ├── Generate Report
       └── Send Webhook/Notification
```

## Concurrency Model

- **Analyzers**: Run in parallel using `asyncio.gather()` with semaphore limiting
- **Platform API calls**: Rate limited per-platform using `AsyncRateLimiter`
- **Reporters**: Run sequentially (typically fast)

## Extensibility Points

### Adding a New Analyzer

1. Create `pipeline_doctor/analyzers/my_analyzer.py`
2. Extend `BaseAnalyzer`
3. Implement `analyze()` method
4. Decorate with `@AnalyzerRegistry.register`
5. Add default config in `get_default_config()`
6. Register in `analyzers/__init__.py`

### Adding a New Platform Integration

1. Create `pipeline_doctor/integrations/my_platform.py`
2. Extend `BaseIntegration`
3. Implement all abstract methods
3. Decorate with `@IntegrationRegistry.register`
4. Add platform to `PipelinePlatform` enum
5. Register in `integrations/__init__.py`

### Adding a New Reporter

1. Create `pipeline_doctor/reporters/my_reporter.py`
2. Extend `BaseReporter`
3. Implement `generate()` method
4. Decorate with `@ReporterRegistry.register`
5. Register in `reporters/__init__.py`

## Security Considerations

- **Secrets**: Never logged; sanitized via `sanitize_for_logging()`
- **Tokens**: Loaded from environment variables only
- **SSL**: Verification enabled by default
- **Rate Limiting**: Prevents API abuse
- **Input Validation**: Pydantic models for all inputs

## Performance Considerations

- **Async I/O**: All platform calls are async
- **Connection Pooling**: HTTP clients reused
- **Caching**: Configurable TTL for API responses
- **Parallel Analysis**: Multiple analyzers run concurrently
- **Streaming Reports**: JSONL reporter for large datasets