"""Tests for core utilities."""

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
        assert parse_duration("30s") == 30
        assert parse_duration("5m") == 300
        assert parse_duration("1h") == 3600
        assert parse_duration("1h30m") == 5400
        assert parse_duration("2h15m30s") == 8130

    def test_parse_duration_invalid(self):
        with pytest.raises(ValueError):
            parse_duration("invalid")

    def test_format_duration(self):
        assert format_duration(30) == "30.0s"
        assert format_duration(90) == "1.5m"
        assert format_duration(3600) == "1.0h"
        assert format_duration(7200) == "2.0h"

    def test_format_bytes(self):
        assert format_bytes(500) == "500.0B"
        assert format_bytes(1024) == "1.0KB"
        assert format_bytes(1024 * 1024) == "1.0MB"
        assert format_bytes(1024 * 1024 * 1024) == "1.0GB"


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
        items = list(range(10))
        chunks = chunk_list(items, 3)

        assert len(chunks) == 4
        assert chunks[0] == [0, 1, 2]
        assert chunks[1] == [3, 4, 5]
        assert chunks[2] == [6, 7, 8]
        assert chunks[3] == [9]

    def test_deep_merge(self):
        base = {"a": 1, "b": {"c": 2, "d": 3}}
        override = {"b": {"c": 20}, "e": 4}

        merged = deep_merge(base, override)

        assert merged["a"] == 1
        assert merged["b"]["c"] == 20
        assert merged["b"]["d"] == 3
        assert merged["e"] == 4

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
        import time
        start = time.time()
        await limiter.acquire()
        elapsed = time.time() - start

        # Should have waited approximately 0.2 seconds
        assert elapsed >= 0.15


class TestRetryDecorator:
    """Tests for retry decorator."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_eventually(self):
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"

        result = await flaky_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausts_attempts(self):
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")

        with pytest.raises(ValueError):
            await always_fails()
        assert call_count == 3
