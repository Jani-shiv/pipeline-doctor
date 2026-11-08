# Built-in Analyzers

Pipeline Doctor includes several built-in analyzers for common CI/CD diagnostics.

## Failure Pattern Analyzer (`failure`)

Detects common failure patterns in pipeline logs and outputs.

### Detected Patterns

| Pattern | Severity | Description |
|---------|----------|-------------|
| Timeout | Error | Process timed out, execution exceeded time limit |
| Out of Memory | Error | OOM kills, heap space errors, GC overhead |
| Permission Denied | Error | Access denied, unauthorized, forbidden |
| Connection Refused | Error | Network connectivity issues |
| Disk Full | Critical | No space left on device |
| Dependency Failure | Error | Package not found, import errors |
| Test Failure | Error | Unit/integration test failures |
| Build Failure | Error | Compilation/build errors |
| Container Failure | Error | Docker/Kubernetes container issues |
| Segmentation Fault | Critical | Native code crashes |
| Process Killed | Error | SIGKILL, OOMKilled, exit code 137 |

### Configuration

```yaml
analyzers:
  failure:
    enabled: true
    config:
      patterns:
        - "timeout"
        - "out of memory"
        - "permission denied"
      custom_patterns:
        - pattern: "my_custom_error"
          severity: "warning"
          suggestion: "Check custom error"
          category: "custom"
```

### Example Findings

```
🔴 CRITICAL: Failure pattern detected: out_of_memory
   Job: build
   Step: compile
   Message: Found 'out_of_memory' pattern in step 'compile' in job 'build'
   Suggestion: Increase memory limits or optimize memory usage
   Evidence: {"pattern": "out_of_memory", "match": "OutOfMemoryError", "match_count": 1}
```

## Performance Analyzer (`performance`)

Identifies performance bottlenecks and slow-running jobs/steps.

### Checks

- **Pipeline Duration**: Overall pipeline execution time
- **Job Duration**: Individual job execution time
- **Step Duration**: Individual step execution time
- **Queue Time**: Time waiting for runner availability
- **Resource Waste**: Cancelled/skipped jobs that consumed resources

### Configuration

```yaml
analyzers:
  performance:
    enabled: true
    config:
      thresholds:
        pipeline_duration_warn: 1800      # 30 minutes
        pipeline_duration_critical: 3600  # 1 hour
        job_duration_warn: 300            # 5 minutes
        job_duration_critical: 600        # 10 minutes
        step_duration_warn: 60            # 1 minute
        step_duration_critical: 180       # 3 minutes
        queue_time_warn: 120              # 2 minutes
        queue_time_critical: 300          # 5 minutes
        waste_threshold_minutes: 10
      compare_baseline: true
      baseline_runs: 10
```

### Example Findings

```
🟡 WARNING: Pipeline duration above warning threshold
   Message: Pipeline took 2500s (>1800s threshold)
   Suggestion: Consider optimizing slow jobs or increasing parallelism
```

## Security Analyzer (`security`)

Scans for secrets, vulnerable dependencies, and security misconfigurations.

### Checks

- **Secrets Detection**: API keys, tokens, passwords, private keys
- **Dependency Vulnerabilities**: Known CVEs in dependencies
- **Misconfigurations**: Privileged containers, root user, host network

### Detected Secret Types

- Generic API Keys
- AWS Credentials
- GitHub Tokens (ghp_, ghs_, gho_)
- GitLab Tokens (glpat-)
- Slack Tokens (xoxb-, xoxp-)
- Docker Credentials
- NPM Tokens
- Private Keys (RSA, DSA, EC, OPENSSH)
- JWT Tokens

### Configuration

```yaml
analyzers:
  security:
    enabled: true
    config:
      scan_secrets: true
      scan_dependencies: true
      scan_misconfigurations: true
      secret_patterns:
        - "(?i)(custom_secret)\\s*[:=]\\s*['\"]?[a-zA-Z0-9_\\-]{20,}['\"]?"
```

### Example Findings

```
🔴 CRITICAL: Potential secret detected: GitHub Token
   Job: release
   Step: publish
   Message: Found potential github token in step 'publish' in job 'release'
   Suggestion: Remove secret from logs/configuration and rotate the credential
```

## Cost Analyzer (`cost`)

Calculates pipeline costs and identifies optimization opportunities.

### Checks

- **Compute Cost**: Estimated cost based on duration
- **Waste Detection**: Cancelled/failed jobs that ran long
- **Parallelization Opportunities**: Sequential jobs that could run in parallel
- **Caching Opportunities**: Missing dependency caching

### Configuration

```yaml
analyzers:
  cost:
    enabled: true
    config:
      currency: "USD"
      compute_cost_per_minute: 0.008
      storage_cost_per_gb_month: 0.10
      network_cost_per_gb: 0.09
      track_waste: true
      waste_threshold_minutes: 10
```

### Example Findings

```
🔵 INFO: Pipeline compute cost
   Message: Estimated compute cost: 0.0400 USD
   Suggestion: Consider optimizing long-running jobs to reduce costs
```

## Reliability Analyzer (`reliability`)

Detects flaky tests, unreliable jobs, and stability issues.

### Checks

- **Job/Step Retries**: Automatic retry detection
- **Timeouts**: Jobs/steps that timed out
- **Flakiness**: Historical failure rate analysis (requires multiple runs)

### Configuration

```yaml
analyzers:
  reliability:
    enabled: true
    config:
      flaky_threshold: 0.1          # 10% failure rate
      min_runs_for_flaky: 10        # Minimum runs for flakiness detection
      check_retries: true
      check_timeouts: true
```

### Example Findings

```
🟡 WARNING: Flaky job detected: integration-tests
   Message: Job 'integration-tests' has 15.0% failure rate over 20 runs (intermittent)
   Suggestion: Investigate and fix flaky job - check for race conditions, timing issues, or external dependencies
```

## Enabling/Disabling Analyzers

```yaml
analyzers:
  failure:
    enabled: true
  performance:
    enabled: true
  security:
    enabled: false  # Disable if not needed
  cost:
    enabled: true
  reliability:
    enabled: true
```

## Custom Analyzers

You can create custom analyzers by extending `BaseAnalyzer`:

```python
from pipeline_doctor.analyzers.base import BaseAnalyzer, AnalyzerRegistry
from pipeline_doctor.core.models import AnalysisResult, Finding, PipelineRun

@AnalyzerRegistry.register
class MyCustomAnalyzer(BaseAnalyzer):
    name = "my-custom"
    description = "Custom analysis logic"
    
    async def analyze(self, run: PipelineRun) -> AnalysisResult:
        result = AnalysisResult(analyzer_name=self.name)
        # Your analysis logic
        return result
```

Then enable in config:

```yaml
analyzers:
  my-custom:
    enabled: true
    config:
      custom_setting: "value"
```