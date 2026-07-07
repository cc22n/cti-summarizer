"""Tests for the Elasticsearch alert forwarding service."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_alert(**kwargs):
    alert = MagicMock()
    alert.id = kwargs.get("id", 1)
    alert.title = kwargs.get("title", "CVE-2026-Test")
    alert.description = kwargs.get("description", "A test alert description")
    alert.severity = kwargs.get("severity", "high")
    alert.source_name = kwargs.get("source_name", "NVD")
    alert.cvss_score = kwargs.get("cvss_score", Decimal("7.5"))
    alert.iocs = kwargs.get("iocs", {})
    alert.mitre_techniques = kwargs.get("mitre_techniques", {})
    alert.affected_products = kwargs.get("affected_products", {})
    alert.published_date = kwargs.get(
        "published_date", datetime(2026, 3, 1, tzinfo=timezone.utc)
    )
    alert.normalized_at = kwargs.get(
        "normalized_at", datetime(2026, 3, 2, tzinfo=timezone.utc)
    )
    return alert


class TestAlertToDoc:
    def test_contains_all_expected_fields(self):
        from app.services.elasticsearch_service import _alert_to_doc

        doc = _alert_to_doc(_make_mock_alert())

        assert "@timestamp" in doc
        assert doc["title"] == "CVE-2026-Test"
        assert doc["severity"] == "high"
        assert doc["source_name"] == "NVD"
        assert doc["cvss_score"] == 7.5
        assert doc["alert_id"] == 1

    def test_uses_published_date_for_timestamp(self):
        from app.services.elasticsearch_service import _alert_to_doc

        alert = _make_mock_alert(
            published_date=datetime(2026, 3, 15, tzinfo=timezone.utc)
        )
        doc = _alert_to_doc(alert)
        assert "2026-03-15" in doc["@timestamp"]

    def test_falls_back_to_normalized_at_when_no_published_date(self):
        from app.services.elasticsearch_service import _alert_to_doc

        alert = _make_mock_alert(
            published_date=None,
            normalized_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        doc = _alert_to_doc(alert)
        assert "2026-06-01" in doc["@timestamp"]

    def test_description_truncated_to_2000_chars(self):
        from app.services.elasticsearch_service import _alert_to_doc

        alert = _make_mock_alert(description="x" * 3000)
        doc = _alert_to_doc(alert)
        assert len(doc["description"]) == 2000

    def test_none_cvss_score_maps_to_none(self):
        from app.services.elasticsearch_service import _alert_to_doc

        alert = _make_mock_alert(cvss_score=None)
        doc = _alert_to_doc(alert)
        assert doc["cvss_score"] is None


class TestEnsureIndex:
    @pytest.mark.asyncio
    async def test_returns_false_when_elasticsearch_url_is_empty(self):
        from app.services.elasticsearch_service import ensure_index

        mock_settings = MagicMock()
        mock_settings.elasticsearch_url = ""

        with patch("app.services.elasticsearch_service.settings", mock_settings):
            result = await ensure_index()

        assert result is False


class TestIndexAlert:
    @pytest.mark.asyncio
    async def test_returns_false_when_elasticsearch_url_is_empty(self):
        from app.services.elasticsearch_service import index_alert

        mock_settings = MagicMock()
        mock_settings.elasticsearch_url = ""

        with patch("app.services.elasticsearch_service.settings", mock_settings):
            result = await index_alert(_make_mock_alert())

        assert result is False


class TestBulkIndexAlerts:
    @pytest.mark.asyncio
    async def test_returns_zero_when_elasticsearch_url_is_empty(self):
        from app.services.elasticsearch_service import bulk_index_alerts

        mock_settings = MagicMock()
        mock_settings.elasticsearch_url = ""

        with patch("app.services.elasticsearch_service.settings", mock_settings):
            result = await bulk_index_alerts([_make_mock_alert()])

        assert result == 0

    @pytest.mark.asyncio
    async def test_returns_zero_for_empty_alert_list(self):
        from app.services.elasticsearch_service import bulk_index_alerts

        mock_settings = MagicMock()
        mock_settings.elasticsearch_url = "http://localhost:9200"
        mock_settings.elasticsearch_index = "cti-alerts"

        with patch("app.services.elasticsearch_service.settings", mock_settings):
            result = await bulk_index_alerts([])

        assert result == 0
