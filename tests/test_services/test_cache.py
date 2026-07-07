"""Tests for the Redis cache helpers."""

import json
from unittest.mock import MagicMock, patch


class TestGetCached:
    def test_redis_unavailable_returns_none(self):
        from app.cache import get_cached

        with patch("app.cache._client", return_value=None):
            assert get_cached("some:key") is None

    def test_key_miss_returns_none(self):
        from app.cache import get_cached

        mock_r = MagicMock()
        mock_r.get.return_value = None
        with patch("app.cache._client", return_value=mock_r):
            assert get_cached("missing:key") is None

    def test_returns_parsed_json_on_hit(self):
        from app.cache import get_cached

        mock_r = MagicMock()
        mock_r.get.return_value = json.dumps({"total": 42})
        with patch("app.cache._client", return_value=mock_r):
            result = get_cached("dashboard:overview")
        assert result == {"total": 42}


class TestSetCached:
    def test_redis_unavailable_is_noop(self):
        from app.cache import set_cached

        with patch("app.cache._client", return_value=None):
            set_cached("key", {"data": 1})  # must not raise

    def test_stores_serialized_json_with_ttl(self):
        from app.cache import set_cached

        mock_r = MagicMock()
        with patch("app.cache._client", return_value=mock_r):
            set_cached("alerts:stats", {"count": 5}, ttl=30)

        mock_r.setex.assert_called_once()
        key, ttl, payload = mock_r.setex.call_args[0]
        assert key == "alerts:stats"
        assert ttl == 30
        assert json.loads(payload) == {"count": 5}


class TestInvalidate:
    def test_redis_unavailable_is_noop(self):
        from app.cache import invalidate

        with patch("app.cache._client", return_value=None):
            invalidate("alerts:stats")  # must not raise

    def test_deletes_the_key(self):
        from app.cache import invalidate

        mock_r = MagicMock()
        with patch("app.cache._client", return_value=mock_r):
            invalidate("dashboard:overview")

        mock_r.delete.assert_called_once_with("dashboard:overview")
