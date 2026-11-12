"""Pipeline Doctor CLI - Main entry point."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from pipeline_doctor import __version__
from pipeline_doctor.analyzers import get_available_analyzers
from pipeline_doctor.analyzers import register_all as register_analyzers
from pipeline_doctor.analyzers.base import AnalyzerRegistry
from pipeline_doctor.core.config import PipelineDoctorConfig, load_config
from pipeline_doctor.core.models import (
    PipelineJob,
    PipelinePlatform,
    PipelineRun,
    PipelineStatus,
    PipelineStep,
)
from pipeline_doctor.core.utils import load_yaml_file
from pipeline_doctor.integrations import get_available_integrations
from pipeline_doctor.integrations import register_all as register_integrations
from pipeline_doctor.reporters import get_available_reporters
from pipeline_doctor.reporters import register_all as register_reporters
from pipeline_doctor.reporters.base import ReporterRegistry
from pipeline_doctor.integrations.base import IntegrationRegistry

app = typer.Typer(
    name="pipeline-doctor",
    help="Pipeline Doctor - CI/CD Pipeline Diagnostics & Health Monitoring Tool",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


@app.callback()
def callback(
    ctx: typer.Context,
    config: Path | None = typer.Option(None, "--config", "-c", help="Configuration file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose output"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug mode"),
) -> None:
    """Pipeline Doctor - CI/CD Pipeline Diagnostics & Health Monitoring"""
    # Register all components
    register_analyzers()
    register_reporters()
    register_integrations()

    # Load configuration
    ctx.obj = load_config(str(config) if config else None)

    if verbose or debug:
        logging.getLogger().setLevel(logging.DEBUG if debug else logging.INFO)
        logging.getLogger().setLevel(logging.DEBUG if debug else logging.INFO)


@app.command()
def analyze(
    ctx: typer.Context,
    platform: PipelinePlatform = typer.Option(..., "--platform", "-p", help="CI/CD platform"),
    repo: str | None = typer.Option(
        None, "--repo", "-r", help="Repository (owner/repo or project path)"
    ),
    pipeline_id: str | None = typer.Option(None, "--pipeline", help="Pipeline/workflow ID"),
    run_id: str | None = typer.Option(None, "--run", help="Specific run/build ID"),
    config_file: Path | None = typer.Option(
        None, "--config-file", help="Local pipeline config file to analyze"
    ),
    analyzers: list[str] = typer.Option(
        None, "--analyzer", "-a", help="Analyzers to run (default: all)"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
    format: str = typer.Option(
        "html", "--format", "-f", help="Output format (html, json, markdown, pdf, jsonl)"
    ),
    days: int = typer.Option(30, "--days", "-d", help="Number of days of history to analyze"),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of runs to analyze"),
):
    """Analyze pipeline runs for issues."""
    config: PipelineDoctorConfig = ctx.obj

    async def _analyze():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing...", total=None)

            # Get integration
            integration = get_integration(platform, config)
            if not integration:
                console.print(f"[red]Error:[/red] Unsupported platform: {platform}")
                raise typer.Exit(1)

            await integration.connect()
            progress.update(task, description="Fetching pipeline data...")

            # Determine what to analyze
            if config_file:
                # Analyze local config file
                progress.update(task, description="Analyzing local config...")
                report = await analyze_local_config(config_file, platform, config, analyzers)
            elif repo and pipeline_id and run_id:
                # Analyze specific run
                progress.update(task, description=f"Fetching run {run_id}...")
                run = await integration.get_run(pipeline_id, run_id)
                report = await analyze_run(run, config, analyzers)
            elif repo and pipeline_id:
                # Analyze recent runs for a pipeline
                progress.update(task, description=f"Fetching recent runs for {pipeline_id}...")
                runs = await integration.get_pipeline_runs(pipeline_id, limit=limit)
                report = await analyze_runs(runs, config, analyzers)
            else:
                console.print(
                    "[red]Error:[/red] Must specify either --config-file or --repo with --pipeline (and optionally --run)"
                )
                raise typer.Exit(1)

            await integration.disconnect()
            progress.update(task, description="Generating report...")

            # Generate report
            reporter = get_reporter(format, config)
            if not reporter:
                console.print(f"[red]Error:[/red] Unsupported format: {format}")
                raise typer.Exit(1)

            output_path = output or reporter.get_output_path(report, format)
            await reporter.generate(report, output_path)

            progress.update(task, description="Done!")

        # Print summary
        print_summary(report, console)
        console.print(f"\n[green]Report saved to:[/green] {output_path}")

    asyncio.run(_analyze())


@app.command()
def monitor(
    ctx: typer.Context,
    platform: PipelinePlatform = typer.Option(..., "--platform", "-p", help="CI/CD platform"),
    repo: str = typer.Option(..., "--repo", "-r", help="Repository (owner/repo or project path)"),
    pipeline_id: str = typer.Option(..., "--pipeline", help="Pipeline/workflow ID"),
    webhook_url: str | None = typer.Option(None, "--webhook", help="Webhook URL for notifications"),
    interval: int = typer.Option(60, "--interval", "-i", help="Polling interval in seconds"),
    analyzers: list[str] = typer.Option(None, "--analyzer", "-a", help="Analyzers to run"),
):
    """Monitor pipeline runs in real-time."""
    config: PipelineDoctorConfig = ctx.obj

    async def _monitor():
        integration = get_integration(platform, config)
        if not integration:
            console.print(f"[red]Error:[/red] Unsupported platform: {platform}")
            raise typer.Exit(1)

        await integration.connect()
        console.print(f"[green]Monitoring {platform.value} pipeline {pipeline_id}...[/green]")
        console.print("Press Ctrl+C to stop\n")

        seen_runs = set()

        try:
            while True:
                runs = await integration.get_pipeline_runs(pipeline_id, limit=10)

                for run in runs:
                    if run.id not in seen_runs:
                        seen_runs.add(run.id)

                        if run.is_completed:
                            console.print(
                                f"\n[bold]New completed run:[/bold] #{run.number} - {run.status.value}"
                            )
                            report = await analyze_run(run, config, analyzers)
                            print_summary(report, console)

                            if webhook_url:
                                await send_webhook(webhook_url, report)

                await asyncio.sleep(interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring stopped.[/yellow]")
        finally:
            await integration.disconnect()

    asyncio.run(_monitor())


@app.command()
def report(
    ctx: typer.Context,
    platform: PipelinePlatform = typer.Option(..., "--platform", "-p", help="CI/CD platform"),
    repo: str = typer.Option(..., "--repo", "-r", help="Repository (owner/repo or project path)"),
    pipeline_id: str = typer.Option(..., "--pipeline", help="Pipeline/workflow ID"),
    days: int = typer.Option(30, "--days", "-d", help="Number of days of history"),
    format: str = typer.Option(
        "html", "--format", "-f", help="Output format (html, json, markdown, pdf)"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
    analyzers: list[str] = typer.Option(None, "--analyzer", "-a", help="Analyzers to include"),
):
    """Generate historical health report for a pipeline."""
    config: PipelineDoctorConfig = ctx.obj

    async def _report():
        integration = get_integration(platform, config)
        if not integration:
            console.print(f"[red]Error:[/red] Unsupported platform: {platform}")
            raise typer.Exit(1)

        await integration.connect()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Fetching historical data...", total=None)

            # Get runs from the last N days
            runs = await integration.get_pipeline_runs(pipeline_id, limit=500)

            # Filter by date
            cutoff = datetime.now(UTC) - timedelta(days=days)
            runs = [r for r in runs if r.started_at and r.started_at >= cutoff]

            progress.update(task, description=f"Analyzing {len(runs)} runs...")
            report = await analyze_runs(runs, config, analyzers)

            progress.update(task, description="Generating report...")
            reporter = get_reporter(format, config)
            output_path = output or reporter.get_output_path(report, format)
            await reporter.generate(report, output_path)

        await integration.disconnect()
        print_summary(report, console)
        console.print(f"\n[green]Report saved to:[/green] {output_path}")

    asyncio.run(_report())


@app.command()
def scan(
    ctx: typer.Context,
    config_file: Path = typer.Argument(..., help="Pipeline configuration file to scan"),
    platform: PipelinePlatform = typer.Option(
        PipelinePlatform.LOCAL, "--platform", "-p", help="Platform type"
    ),
    analyzers: list[str] = typer.Option(
        ["security", "configuration"], "--analyzer", "-a", help="Analyzers to run"
    ),
    format: str = typer.Option("markdown", "--format", "-f", help="Output format"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Scan local pipeline configuration for issues."""
    config: PipelineDoctorConfig = ctx.obj

    async def _scan():
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Scanning configuration...", total=None)
            report = await analyze_local_config(config_file, platform, config, analyzers)
            progress.update(task, description="Generating report...")

            reporter = get_reporter(format, config)
            output_path = output or reporter.get_output_path(report, format)
            await reporter.generate(report, output_path)

        print_summary(report, console)
        console.print(f"\n[green]Report saved to:[/green] {output_path}")

    asyncio.run(_scan())


@app.command()
def list_analyzers():
    """List available analyzers."""
    register_analyzers()
    analyzers = get_available_analyzers()

    table = Table(title="Available Analyzers")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for name in sorted(analyzers):
        # Get description from registry
        cls = AnalyzerRegistry.get(name)
        desc = cls.description if cls else "No description"
        table.add_row(name, desc)

    console.print(table)


@app.command()
def list_reporters():
    """List available reporters."""
    register_reporters()
    reporters = get_available_reporters()

    table = Table(title="Available Reporters")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for name in sorted(reporters):
        cls = ReporterRegistry.get(name)
        desc = cls.description if cls else "No description"
        table.add_row(name, desc)

    console.print(table)


@app.command()
def list_integrations():
    """List available platform integrations."""
    register_integrations()
    integrations = get_available_integrations()

    table = Table(title="Available Platform Integrations")
    table.add_column("Platform", style="cyan")
    table.add_column("Description")

    descriptions = {
        "github": "GitHub Actions",
        "gitlab": "GitLab CI/CD",
        "jenkins": "Jenkins",
        "azure_devops": "Azure DevOps Pipelines",
        "circleci": "CircleCI",
    }

    for name in sorted(integrations):
        table.add_row(name, descriptions.get(name, "No description"))

    console.print(table)


@app.command()
def version():
    """Show version information."""
    console.print(f"Pipeline Doctor v{__version__}")


# Helper functions


def get_integration(platform: PipelinePlatform, config: PipelineDoctorConfig):
    """Get integration instance for platform."""

    platform_config = config.platforms.get(platform.value, {})
    platform_config = (
        platform_config.config if hasattr(platform_config, "config") else platform_config
    )

    integration_class = IntegrationRegistry.get(platform.value)
    if not integration_class:
        return None

    return integration_class(platform_config)


def get_reporter(format: str, config: PipelineDoctorConfig):
    """Get reporter instance for format."""

    reporter_config = config.reporters.get(format, {})
    reporter_config = (
        reporter_config.config if hasattr(reporter_config, "config") else reporter_config
    )
    output_dir = (
        reporter_config.get("output_dir", "./reports")
        if isinstance(reporter_config, dict)
        else "./reports"
    )

    reporter_class = ReporterRegistry.get(format)
    if not reporter_class:
        return None

    return reporter_class(reporter_config, output_dir)


async def analyze_run(run, config: PipelineDoctorConfig, analyzer_names: list[str] = None):
    """Analyze a single pipeline run."""

    report = AnalysisReport(
        pipeline_id=run.pipeline_id,
        run_id=run.id,
        platform=run.metadata.get("platform", "unknown"),
    )

    # Get analyzers to run
    if analyzer_names:
        analyzers = {}
        for name in analyzer_names:
            cls = AnalyzerRegistry.get(name)
            if cls:
                analyzer_config = config.analyzers.get(name, {})
                analyzer_config = (
                    analyzer_config.config
                    if hasattr(analyzer_config, "config")
                    else analyzer_config
                )
                analyzers[name] = cls(analyzer_config)
    else:
        analyzers = {}
        for name, analyzer_config in config.analyzers.items():
            if analyzer_config.enabled:
                cls = AnalyzerRegistry.get(name)
                if cls:
                    ac = (
                        analyzer_config.config
                        if hasattr(analyzer_config, "config")
                        else analyzer_config
                    )
                    analyzers[name] = cls(ac)

    # Run analyzers
    for name, analyzer in analyzers.items():
        result = await analyzer.analyze_with_error_handling(run)
        report.add_analyzer_result(result)

    return report


async def analyze_runs(runs, config: PipelineDoctorConfig, analyzer_names: list[str] = None):
    """Analyze multiple pipeline runs."""

    if not runs:
        return AnalysisReport(
            pipeline_id=runs[0].pipeline_id if runs else None,
            run_id=None,
            platform="unknown",
        )

    # Use first run's pipeline ID
    pipeline_id = runs[0].pipeline_id
    platform = runs[0].metadata.get("platform", "unknown")

    report = AnalysisReport(
        pipeline_id=pipeline_id,
        run_id=None,  # Multi-run report
        platform=platform,
    )

    # Get analyzers
    if analyzer_names:
        analyzers = {}
        for name in analyzer_names:
            cls = AnalyzerRegistry.get(name)
            if cls:
                analyzer_config = config.analyzers.get(name, {})
                analyzer_config = (
                    analyzer_config.config
                    if hasattr(analyzer_config, "config")
                    else analyzer_config
                )
                analyzers[name] = cls(analyzer_config)
    else:
        analyzers = {}
        for name, analyzer_config in config.analyzers.items():
            if analyzer_config.enabled:
                cls = AnalyzerRegistry.get(name)
                if cls:
                    ac = (
                        analyzer_config.config
                        if hasattr(analyzer_config, "config")
                        else analyzer_config
                    )
                    analyzers[name] = cls(ac)

    # Run analyzers on each run
    for run in runs:
        for name, analyzer in analyzers.items():
            result = await analyzer.analyze_with_error_handling(run)
            report.add_analyzer_result(result)

    # Run reliability analyzer on all runs if available
    if "reliability" in analyzers:
        reliability_result = analyzers["reliability"].analyze_historical(runs)
        report.add_analyzer_result(reliability_result)

    return report


async def analyze_local_config(
    config_file: Path,
    platform: PipelinePlatform,
    config: PipelineDoctorConfig,
    analyzer_names: list[str] = None,
):
    """Analyze a local pipeline configuration file."""
    # Parse config file
    data = load_yaml_file(config_file)

    # Create a mock run from the config
    run = PipelineRun(
        pipeline_id=uuid4(),
        number=0,
        status=PipelineStatus.UNKNOWN,
        metadata={
            "platform": platform.value,
            "config_file": str(config_file),
            "raw_config": data,
        },
    )

    # Extract jobs/steps from config (platform-specific)
    # This is simplified - real implementation would parse each platform's config format
    run.jobs = _parse_config_jobs(data, platform)

    return await analyze_run(run, config, analyzer_names)


def _parse_config_jobs(data: dict, platform: PipelinePlatform) -> list:
    """Parse jobs from pipeline config (simplified)."""

    jobs = []

    if platform == PipelinePlatform.GITHUB:
        # GitHub Actions format
        for job_name, job_data in data.get("jobs", {}).items():
            steps = []
            for step in job_data.get("steps", []):
                steps.append(
                    PipelineStep(
                        id=uuid4(),
                        name=step.get("name", step.get("uses", "unknown")),
                        status=PipelineStatus.UNKNOWN,
                        metadata={"github_step": step},
                    )
                )
            jobs.append(
                PipelineJob(
                    id=uuid4(),
                    name=job_name,
                    status=PipelineStatus.UNKNOWN,
                    steps=steps,
                    metadata={"github_job": job_data},
                )
            )
    elif platform == PipelinePlatform.GITLAB:
        # GitLab CI format - stages and jobs
        for job_name, job_data in data.items():
            if job_name in ("stages", "variables", "cache", "before_script", "after_script"):
                continue
            if isinstance(job_data, dict) and ("script" in job_data or "stage" in job_data):
                steps = []
                for i, cmd in enumerate(job_data.get("script", [])):
                    steps.append(
                        PipelineStep(
                            id=uuid4(),
                            name=f"Step {i + 1}",
                            status=PipelineStatus.UNKNOWN,
                            metadata={"command": cmd},
                        )
                    )
                jobs.append(
                    PipelineJob(
                        id=uuid4(),
                        name=job_name,
                        status=PipelineStatus.UNKNOWN,
                        steps=steps,
                        metadata={"gitlab_job": job_data},
                    )
                )

    return jobs


async def send_webhook(webhook_url: str, report):
    """Send report summary to webhook."""
    payload = {
        "report_id": str(report.id),
        "total_findings": report.total_findings,
        "by_severity": {k.value: v for k, v in report.findings_by_severity.items()},
        "pipeline_id": str(report.pipeline_id),
        "platform": report.platform,
    }

    try:
        async with httpx.AsyncClient() as client:
            await client.post(webhook_url, json=payload, timeout=10)
    except Exception:
        pass  # Silently fail webhook


def print_summary(report, console: Console):
    """Print analysis summary to console."""
    console.print("\n" + "=" * 60)
    console.print(
        Panel.fit(
            f"[bold]Pipeline Doctor Analysis Summary[/bold]\n"
            f"Pipeline: {report.pipeline_id}\n"
            f"Platform: {report.platform}\n"
            f"Total Findings: {report.total_findings}",
            title="Summary",
            border_style="blue",
        )
    )

    if report.total_findings > 0:
        table = Table(title="Findings by Severity")
        table.add_column("Severity", style="bold")
        table.add_column("Count", justify="right")

        severity_colors = {
            "critical": "red",
            "error": "red",
            "warning": "yellow",
            "info": "blue",
        }

        for severity, count in report.findings_by_severity.items():
            if count > 0:
                color = severity_colors.get(severity.value, "white")
                table.add_row(
                    f"[{color}]{severity.value.title()}[/{color}]",
                    str(count),
                )

        console.print(table)

        # Show top findings
        console.print("\n[bold]Top Findings:[/bold]")
        for analyzer_result in report.analyzer_results:
            for finding in analyzer_result.findings[:3]:
                if finding.severity in ["critical", "error"]:
                    console.print(
                        f"  [{severity_colors.get(finding.severity.value, 'white')}]"
                        f"{finding.severity.value.upper()}[/]: {finding.title}"
                    )
    else:
        console.print("[green]No issues found![/green]")


if __name__ == "__main__":
    app()
