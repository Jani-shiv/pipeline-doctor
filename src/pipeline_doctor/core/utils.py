"""Shared utilities."""

import asyncio
import json
import re
import time
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, TypeVar
from uuid import UUID

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    import uuid
    timestamp = int(time.time() * 1000)
    random_part = uuid.uuid4().hex[:8]
    if prefix:
        return f"{prefix}_{timestamp}_{random_part}"
    return f"{timestamp}_{random_part}"


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "-", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    if max_length <= len(suffix):
        return suffix[:max_length]
    return text[: max_length - len(suffix)] + suffix


def parse_duration(duration_str: str) -> float:
    """Parse duration string (e.g., '1h30m', '90m', '5400s') to seconds."""
    pattern = r"^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$"
    match = re.match(pattern, duration_str.strip())
    if not match or not any(match.groups()):
        raise ValueError(f"Invalid duration format: {duration_str}")

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)

    return hours * 3600 + minutes * 60 + seconds


def format_duration(seconds: float) -> str:
    """Format seconds to human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_bytes(bytes_value: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_value < 1024:
            return f"{bytes_value:.1f}{unit}"
        bytes_value /= 1024
    return f"{bytes_value:.1f}PB"


def sanitize_for_logging(data: Any, sensitive_keys: list[str] = None) -> Any:
    """Remove sensitive data from logs."""
    if sensitive_keys is None:
        sensitive_keys = [
            "token", "password", "secret", "key", "auth",
            "api_key", "access_token", "refresh_token",
        ]

    if isinstance(data, dict):
        return {
            k: "***REDACTED***" if any(sk in k.lower() for sk in sensitive_keys) else sanitize_for_logging(v, sensitive_keys)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [sanitize_for_logging(item, sensitive_keys) for item in data]
    return data


def load_json_file(path: Path) -> dict[str, Any]:
    """Load JSON file with error handling."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.exception("failed_to_parse_json", path=str(path), error=str(e))
        raise
    except FileNotFoundError:
        logger.exception("file_not_found", path=str(path))
        raise


def save_json_file(path: Path, data: dict[str, Any], indent: int = 2) -> None:
    """Save JSON file with error handling."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, default=str)
    except Exception as e:
        logger.exception("failed_to_save_json", path=str(path), error=str(e))
        raise


def load_yaml_file(path: Path) -> dict[str, Any]:
    """Load YAML file with error handling."""
    import yaml
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.exception("failed_to_parse_yaml", path=str(path), error=str(e))
        raise
    except FileNotFoundError:
        logger.exception("file_not_found", path=str(path))
        raise


def save_yaml_file(path: Path, data: dict[str, Any]) -> None:
    """Save YAML file with error handling."""
    import yaml
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logger.exception("failed_to_save_yaml", path=str(path), error=str(e))
        raise


async def run_with_timeout(
    coro: Callable[..., T],
    timeout: float,
    *args: Any,
    **kwargs: Any,
) -> T:
    """Run coroutine with timeout."""
    try:
        return await asyncio.wait_for(coro(*args, **kwargs), timeout=timeout)
    except TimeoutError:
        raise TimeoutError(f"Operation timed out after {timeout}s")


@asynccontextmanager
async def timer(name: str) -> AsyncGenerator[None, None]:
    """Context manager for timing operations."""
    start = time.perf_counter()
    logger.debug("timer_started", timer=name)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.debug("timer_completed", timer=name, duration_seconds=elapsed)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Callable:
    """Decorator for retry with exponential backoff."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)
            raise last_exception

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_attempts - 1:
                        break
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e),
                    )
                    time.sleep(delay)
            raise last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def validate_uuid(value: str) -> UUID:
    """Validate and parse UUID string."""
    try:
        return UUID(value)
    except ValueError:
        raise ValueError(f"Invalid UUID: {value}")


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp."""
    return datetime.now(UTC)


def mask_sensitive_value(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive value for logging."""
    if len(value) <= visible_chars * 2:
        return "*" * len(value)
    return value[:visible_chars] + "*" * (len(value) - visible_chars * 2) + value[-visible_chars:]


class AsyncRateLimiter:
    """Async rate limiter using token bucket algorithm."""

    def __init__(self, rate: int, per: float = 60.0):
        self.rate = rate
        self.per = per
        self._tokens = rate
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update
            self._tokens = min(self.rate, self._tokens + elapsed * self.rate / self.per)

            if self._tokens >= 1:
                self._tokens -= 1
                self._last_update = now
                return

            wait_time = (1 - self._tokens) * self.per / self.rate
            await asyncio.sleep(wait_time)
            self._tokens = 0
            self._last_update = time.monotonic()


def chunk_list(lst: list[T], chunk_size: int) -> list[list[T]]:
    """Split list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def setup_logging() -> None:
    """Setup logging configuration."""
    import structlog

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
