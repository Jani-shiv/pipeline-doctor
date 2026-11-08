"""Tests for core utilities."""

import time
from datetime import UTC, datetime

import pytest

from pipeline_doctor.core.utils import (
    AsyncRateLimiter,
    chunk_list,
    deep_merge,
    ensure_dir,
    format_bytes,
    format_duration,
    generate_id,
    get_current_timestamp,
    mask_sensitive_value,
    parse_duration,
    retry_with_backoff,
    sanitize_for_logging,
    slugify,
    truncate,
    validate_uuid,
)

# Test constants
EXPECTED_CHUNKS = 4
EXPECTED_CALLS = 3
EXPECTED_ITEMS = 10
EXPECTED_CHUNK_SIZE = 3
EXPECTED_MERGED_C = 20
EXPECTED_MERGED_D = 3
EXPECTED_MERGED_E = 4
EXPECTED_MERGED_A = 1
EXPECTED_FIRST_CHUNK = [0, 1, 2]
EXPECTED_SECOND_CHUNK = [3, 4, 5]
EXPECTED_THIRD_CHUNK = [6, 7, 8]
EXPECTED_FOURTH_CHUNK = [9]
EXPECTED_SECONDS_30 = 30
EXPECTED_SECONDS_5M = 300
EXPECTED_SECONDS_1H = 3600
EXPECTED_SECONDS_1H30M = 5400
EXPECTED_SECONDS_2H15M30S = 8130
EXPECTED_FORMAT_30S = "30.0s"
EXPECTED_FORMAT_90S = "1.5m"
EXPECTED_FORMAT_3600S = "1.0h"
EXPECTED_FORMAT_7200S = "2.0h"
EXPECTED_BYTES_500 = "500.0B"
EXPECTED_BYTES_1KB = "1.0KB"
EXPECTED_BYTES_1MB = "1.0MB"
EXPECTED_BYTES_1GB = "1.0GB"
EXPECTED_THROTTLE_WAIT = 0.15
MAX_ATTEMPTS = 3


class TestStringUtils:
    """Tests for string utilities."""

    def test_generate_id(self):
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2
        assert len(id1) > 0

    def test_generate_id_with_prefix(self):
        id1 = generate_id("test")
        assert id1.startswith("test_")

    def test_slugify(self):
        assert slugify("Hello World") == "hello-world"
        assert slugify("Test_Case") == "test-case"
        assert slugify("Special!@#Chars") == "special-chars"
        assert slugify("  leading trailing  ") == "leading-trailing"

    def test_truncate(self):
        assert truncate("short", 10) == "short"
        assert truncate("very long string", 10) == "very lo..."
        assert truncate("exactly10", 10) == "exactly10"
        assert truncate("exactly10", 8) == "exact..."

    def test_parse_duration(self):
        assert parse_duration("30s") == EXPECTED_SECONDS_30
        assert parse_duration("5m") == EXPECTED_SECONDS_5M
        assert parse_duration("1h") == EXPECTED_SECONDS_1H
        assert parse_duration("1h30m") == EXPECTED_SECONDS_1H30M
        assert parse_duration("2h15m30s") == EXPECTED_SECONDS_2H15M30S

    def test_parse_duration_invalid(self):
        with pytest.raises(ValueError):
            parse_duration("invalid")

    def test_format_duration(self):
        assert format_duration(30) == EXPECTED_FORMAT_30S
        assert format_duration(90) == EXPECTED_FORMAT_90S
        assert format_duration(3600) == EXPECTED_FORMAT_3600S
        assert format_duration(7200) == EXPECTED_FORMAT_7200S

    def test_format_bytes(self):
        assert format_bytes(500) == EXPECTED_BYTES_500
        assert format_bytes(1024) == EXPECTED_BYTES_1KB
        assert format_bytes(1024 * 1024) == EXPECTED_BYTES_1MB
        assert format_bytes(1024 * 1024 * 1024) == EXPECTED_BYTES_1GB


class TestSanitization:
    """Tests for data sanitization."""

    def test_sanitize_for_logging(self):
        data = {
            "username": "user",
            "password": "secret123",
            "api_key": "key123",
            "nested": {
                "token": "token123",
                "normal": "value",
            },
        }

        sanitized = sanitize_for_logging(data)

        assert sanitized["username"] == "user"
        assert sanitized["password"] == "***REDACTED***"
        assert sanitized["api_key"] == "***REDACTED***"
        assert sanitized["nested"]["token"] == "***REDACTED***"
        assert sanitized["nested"]["normal"] == "value"

    def test_mask_sensitive_value(self):
        assert mask_sensitive_value("abcdefghijklmnop") == "abcd********mnop"
        assert mask_sensitive_value("short") == "*****"
        assert mask_sensitive_value("12345678", visible_chars=2) == "12****78"


class TestCollectionUtils:
    """Tests for collection utilities."""

    def test_chunk_list(self):
        items = list(range(EXPECTED_ITEMS))
        chunks = chunk_list(items, EXPECTED_CHUNK_SIZE)

        assert len(chunks) == EXPECTED_CHUNKS
        assert chunks[0] == EXPECTED_FIRST_CHUNK
        assert chunks[1] == EXPECTED_SECOND_CHUNK
        assert chunks[2] == EXPECTED_THIRD_CHUNK
        assert chunks[3] == EXPECTED_FOURTH_CHUNK

    def test_deep_merge(self):
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"c": 20}, "e": 4}

        merged = deep_merge(base, override)

        assert merged["a"] == EXPECTED_MERGED_A
        assert merged["b"]["c"] == EXPECTED_MERGED_C
        assert merged["b"]["d"] == EXPECTED_MERGED_D
        assert merged["e"] == EXPECTED_MERGED_E

    def test_deep_merge_lists(self):
        base = {"items": [1, 2]}
        override = {"items": [3, 4]}

        merged = deep_merge(base, override)
        # Lists are replaced, not merged
        assert merged["items"] == [3, 4]


class TestValidation:
    """Tests for validation utilities."""

    def test_validate_uuid_valid(self):
        uuid_str = "12345678-1234-5678-1234-567812345678"
        result = validate_uuid(uuid_str)
        assert str(result) == uuid_str

    def test_validate_uuid_invalid(self):
        with pytest.raises(ValueError):
            validate_uuid("not-a-uuid")

    def test_ensure_dir(self, tmp_path):
        new_dir = tmp_path / "new" / "nested" / "dir"
        result = ensure_dir(new_dir)

        assert result == new_dir
        assert new_dir.exists()
        assert new_dir.is_dir()


class TestTimeUtils:
    """Tests for time utilities."""

    def test_get_current_timestamp(self):
        ts = get_current_timestamp()
        assert isinstance(ts, datetime)
        assert ts.tzinfo == UTC


class TestAsyncRateLimiter:
    """Tests for async rate limiter."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_burst(self):
        limiter = AsyncRateLimiter(rate=10, per=1.0)

        # Should allow up to rate requests quickly
        for _ in range(10):
            await limiter.acquire()

    @pytest.mark.asyncio
    async def test_rate_limiter_throttles(self):
        limiter = AsyncRateLimiter(rate=5, per=1.0)

        # First 5 should be fast
        for _ in range(5):
            await limiter.acquire()

        # Next should wait
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start

        # Should have waited approximately 0.2 seconds
        assert elapsed >= EXPECTED_THROTTLE_WAIT


class TestRetryDecorator:
    """Tests for retry decorator."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_eventually(self):
        call_count = 0

        @retry_with_backoff(max_attempts=MAX_ATTEMPTS, base_delay=0.01)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < MAX_ATTEMPTS:
                raise ValueError("Temporary error")
            return "success"

        result = await flaky_function()
        assert result == "success"
        assert call_count == MAX_ATTEMPTS

    @pytest.mark.asyncio
    async def test_retry_exhausts_attempts(self):
        call_count = 0

        @retry_with_backoff(max_attempts=MAX_ATTEMPTS, base_delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")

        with pytest.raises(ValueError):
            await always_fails()
        assert call_count == MAX_ATTEMPTS
