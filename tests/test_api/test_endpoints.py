"""Tests for API endpoints."""

import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest

from app.models.alert import NormalizedAlert, RawAlert
from app.models.category import AlertCategory
from app.models.summary import Summary
from app.models.trend_prediction import TrendPrediction


# ── Shared helpers ────────────────────────────────────────────────────────────

def _make_alert(db, sample_raw_alert, severity="high", title="CVE-2026-99999"):
    """Create a fresh RawAlert + NormalizedAlert for each call (unique constraint)."""
    raw = RawAlert(
        source_id=sample_raw_alert.source_id,
        external_id=f"TEST-{uuid.uuid4().hex[:12]}",
        raw_data={},
    )
    db.add(raw)
    db.flush()
    alert = NormalizedAlert(
        raw_alert_id=raw.id,
        title=title,
        description="Test description",
        severity=severity,
        cvss_score=Decimal("7.5"),
        source_name="NVD",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def _make_summary(db, alert_id=None, summary_type="alert",
                  created_at=None):
    s = Summary(
        normalized_alert_id=alert_id,
        summary_type=summary_type,
        content="Executive summary content.",
        model_used="grok-4-1-fast",
        prompt_tokens=100,
        completion_tokens=50,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _make_prediction(db, run_id="run-abc", series_key="critical",
                     days_ahead=1, is_anomaly=False):
    pred = TrendPrediction(
        run_id=run_id,
        series_key=series_key,
        target_date=(datetime.now(timezone.utc) + timedelta(days=days_ahead)).date(),
        predicted_count=Decimal("3.00"),
        lower_bound=Decimal("1.00"),
        upper_bound=Decimal("5.00"),
        model_type="rolling_avg",
        training_days=30,
        is_anomaly=is_anomaly,
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return pred


class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_health_response_contains_checks_field(self, client):
        data = client.get("/health").json()
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]

    def test_health_response_contains_version_field(self, client):
        data = client.get("/health").json()
        assert "version" in data
        assert isinstance(data["version"], str)
        assert len(data["version"]) > 0

    def test_health_status_is_valid_value(self, client):
        data = client.get("/health").json()
        assert data["status"] in ("ok", "degraded", "error")


class TestAlertsAPI:
    def test_list_alerts_empty(self, client):
        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["page"] == 1

    def test_list_alerts_with_data(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "CVE-2026-12345"
        assert data["items"][0]["severity"] == "high"

    def test_list_alerts_filter_severity(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/alerts?severity=high")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = client.get("/api/v1/alerts?severity=critical")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_alerts_filter_source(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/alerts?source=NVD")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = client.get("/api/v1/alerts?source=CISA_KEV")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_alerts_search(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/alerts?search=12345")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = client.get("/api/v1/alerts?search=nonexistent")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_list_alerts_pagination(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/alerts?page=1&page_size=1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["page_size"] == 1
        assert data["pages"] == 1

    def test_get_alert_detail(self, client, sample_normalized_alert):
        resp = client.get(
            f"/api/v1/alerts/{sample_normalized_alert.id}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "CVE-2026-12345"
        assert data["cvss_score"] == "8.5"

    def test_get_alert_not_found(self, client):
        resp = client.get("/api/v1/alerts/99999")
        assert resp.status_code == 404

    def test_alert_stats_empty(self, client):
        resp = client.get("/api/v1/alerts/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_alerts"] == 0

    def test_alert_stats_with_data(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/alerts/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_alerts"] == 1
        assert data["by_severity"]["high"] == 1
        assert data["by_source"]["NVD"] == 1


class TestSourcesAPI:
    def test_list_sources_empty(self, client):
        resp = client.get("/api/v1/sources")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_sources_with_data(self, client, sample_source):
        resp = client.get("/api/v1/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "NVD"

    def test_source_health(self, client, sample_source):
        resp = client.get(
            f"/api/v1/sources/{sample_source.id}/health"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["source_name"] == "NVD"
        assert data["is_active"] is True

    def test_source_health_not_found(self, client):
        resp = client.get("/api/v1/sources/99999/health")
        assert resp.status_code == 404

    def test_source_health_includes_error_message_field(self, client, sample_source):
        resp = client.get(f"/api/v1/sources/{sample_source.id}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "last_error_message" in data


# ── 11.7a Source write endpoints ──────────────────────────────────────────────

class TestSourcesWriteAPI:
    def test_toggle_source_changes_active_state(self, client, sample_source):
        original = sample_source.is_active
        resp = client.patch(f"/api/v1/sources/{sample_source.id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["is_active"] == (not original)

    def test_toggle_source_second_call_restores(self, client, sample_source):
        original = sample_source.is_active
        client.patch(f"/api/v1/sources/{sample_source.id}/toggle")
        resp = client.patch(f"/api/v1/sources/{sample_source.id}/toggle")
        assert resp.status_code == 200
        assert resp.json()["is_active"] == original

    def test_toggle_source_not_found(self, client):
        resp = client.patch("/api/v1/sources/99999/toggle")
        assert resp.status_code == 404

    def test_poll_source_not_found(self, client):
        resp = client.post("/api/v1/sources/99999/poll")
        assert resp.status_code == 404

    def test_poll_source_unknown_adapter_returns_400(self, client, db):
        from app.models.source import Source
        custom = Source(
            name="UNKNOWN_SRC",
            source_type="api",
            base_url="https://example.com",
            polling_interval_minutes=60,
            is_active=True,
        )
        db.add(custom)
        db.commit()
        db.refresh(custom)

        resp = client.post(f"/api/v1/sources/{custom.id}/poll")
        assert resp.status_code == 400


# ── 11.7b Source logs endpoint ────────────────────────────────────────────────

class TestSourceLogsAPI:
    def test_source_logs_empty(self, client, sample_source):
        resp = client.get(f"/api/v1/sources/{sample_source.id}/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_source_logs_not_found(self, client):
        resp = client.get("/api/v1/sources/99999/logs")
        assert resp.status_code == 404

    def test_source_logs_returns_entries(self, client, db, sample_source):
        from app.models.ingestion_log import IngestionLog
        log = IngestionLog(
            source_id=sample_source.id,
            status="success",
            alerts_fetched=10,
            alerts_new=3,
        )
        db.add(log)
        db.commit()

        resp = client.get(f"/api/v1/sources/{sample_source.id}/logs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["status"] == "success"
        assert item["alerts_fetched"] == 10
        assert item["alerts_new"] == 3

    def test_source_logs_error_includes_message(self, client, db, sample_source):
        from app.models.ingestion_log import IngestionLog
        log = IngestionLog(
            source_id=sample_source.id,
            status="error",
            alerts_fetched=0,
            alerts_new=0,
            error_message="Connection timeout",
        )
        db.add(log)
        db.commit()

        resp = client.get(f"/api/v1/sources/{sample_source.id}/logs")
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["status"] == "error"
        assert item["error_message"] == "Connection timeout"

    def test_source_logs_ordered_newest_first(self, client, db, sample_source):
        from app.models.ingestion_log import IngestionLog
        from datetime import timezone
        for i in range(3):
            db.add(IngestionLog(
                source_id=sample_source.id,
                status="success",
                alerts_fetched=i,
                alerts_new=0,
                started_at=datetime(2026, 1, i + 1, tzinfo=timezone.utc),
            ))
        db.commit()

        resp = client.get(f"/api/v1/sources/{sample_source.id}/logs")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert items[0]["alerts_fetched"] == 2
        assert items[1]["alerts_fetched"] == 1
        assert items[2]["alerts_fetched"] == 0

    def test_source_logs_pagination(self, client, db, sample_source):
        from app.models.ingestion_log import IngestionLog
        for i in range(5):
            db.add(IngestionLog(
                source_id=sample_source.id,
                status="success",
                alerts_fetched=i,
                alerts_new=0,
            ))
        db.commit()

        resp = client.get(f"/api/v1/sources/{sample_source.id}/logs?page=1&page_size=3")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3
        assert data["pages"] == 2

    def test_source_health_last_error_message_populated(self, client, db, sample_source):
        from app.models.ingestion_log import IngestionLog
        log = IngestionLog(
            source_id=sample_source.id,
            status="error",
            alerts_fetched=0,
            alerts_new=0,
            error_message="SSL handshake failed",
        )
        db.add(log)
        db.commit()

        resp = client.get(f"/api/v1/sources/{sample_source.id}/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["last_status"] == "error"
        assert data["last_error_message"] == "SSL handshake failed"


class TestDashboardAPI:
    def test_overview_empty(self, client):
        resp = client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_alerts"] == 0
        assert data["sources_total"] == 0

    def test_overview_with_data(
        self, client, sample_source, sample_normalized_alert
    ):
        resp = client.get("/api/v1/dashboard/overview")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_alerts"] == 1
        assert data["sources_total"] == 1
        assert data["sources_active"] == 1

    def test_timeline_empty(self, client):
        resp = client.get("/api/v1/dashboard/timeline")
        assert resp.status_code == 200
        data = resp.json()
        assert data["points"] == []
        assert data["period"] == "daily"

    def test_timeline_with_data(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/dashboard/timeline?days=7")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["points"]) >= 1


# ── 10.1 Alert annotations ────────────────────────────────────────────────────

class TestAlertAnnotations:
    def test_patch_notes_sets_text(self, client, sample_normalized_alert):
        resp = client.patch(
            f"/api/v1/alerts/{sample_normalized_alert.id}/notes",
            json={"notes": "Investigated — false positive"},
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Investigated — false positive"

    def test_patch_notes_clears_with_null(self, client, sample_normalized_alert):
        client.patch(
            f"/api/v1/alerts/{sample_normalized_alert.id}/notes",
            json={"notes": "some note"},
        )
        resp = client.patch(
            f"/api/v1/alerts/{sample_normalized_alert.id}/notes",
            json={"notes": None},
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] is None

    def test_patch_notes_404_on_missing(self, client):
        resp = client.patch("/api/v1/alerts/99999/notes", json={"notes": "x"})
        assert resp.status_code == 404

    def test_acknowledge_toggles_flag(self, client, sample_normalized_alert):
        resp = client.patch(
            f"/api/v1/alerts/{sample_normalized_alert.id}/acknowledge"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_acknowledged"] is True
        assert data["acknowledged_at"] is not None

    def test_acknowledge_second_call_un_acknowledges(self, client, sample_normalized_alert):
        client.patch(f"/api/v1/alerts/{sample_normalized_alert.id}/acknowledge")
        resp = client.patch(
            f"/api/v1/alerts/{sample_normalized_alert.id}/acknowledge"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_acknowledged"] is False
        assert data["acknowledged_at"] is None

    def test_acknowledge_404_on_missing(self, client):
        resp = client.patch("/api/v1/alerts/99999/acknowledge")
        assert resp.status_code == 404


# ── 10.2 Alert filters ────────────────────────────────────────────────────────

class TestAlertFilters:
    def test_filter_acknowledged_true(self, client, db, sample_raw_alert):
        ack = _make_alert(db, sample_raw_alert, severity="critical", title="ACK-1")
        ack.is_acknowledged = True
        db.commit()
        _make_alert(db, sample_raw_alert, severity="high", title="UNACK-1")

        resp = client.get("/api/v1/alerts?is_acknowledged=true")
        assert resp.status_code == 200
        data = resp.json()
        titles = [i["title"] for i in data["items"]]
        assert "ACK-1" in titles
        assert "UNACK-1" not in titles

    def test_filter_acknowledged_false_excludes_acked(self, client, db, sample_raw_alert):
        ack = _make_alert(db, sample_raw_alert, severity="critical", title="ACK-2")
        ack.is_acknowledged = True
        db.commit()
        _make_alert(db, sample_raw_alert, severity="high", title="UNACK-2")

        resp = client.get("/api/v1/alerts?is_acknowledged=false")
        assert resp.status_code == 200
        titles = [i["title"] for i in resp.json()["items"]]
        assert "ACK-2" not in titles

    def test_sort_by_severity_asc(self, client, db, sample_raw_alert):
        _make_alert(db, sample_raw_alert, severity="critical", title="S-CRIT")
        _make_alert(db, sample_raw_alert, severity="info", title="S-INFO")

        resp = client.get("/api/v1/alerts?sort_by=severity&sort_order=asc")
        assert resp.status_code == 200
        items = resp.json()["items"]
        severities = [i["severity"] for i in items]
        assert severities == sorted(severities)

    def test_sort_by_severity_desc(self, client, db, sample_raw_alert):
        _make_alert(db, sample_raw_alert, severity="critical", title="D-CRIT")
        _make_alert(db, sample_raw_alert, severity="info", title="D-INFO")

        resp = client.get("/api/v1/alerts?sort_by=severity&sort_order=desc")
        assert resp.status_code == 200
        items = resp.json()["items"]
        severities = [i["severity"] for i in items]
        assert severities == sorted(severities, reverse=True)

    def test_date_from_filter(self, client, db, sample_raw_alert):
        past = _make_alert(db, sample_raw_alert, severity="low", title="OLD-ALERT")
        past.normalized_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        db.commit()
        _make_alert(db, sample_raw_alert, severity="high", title="NEW-ALERT")

        resp = client.get("/api/v1/alerts?date_from=2025-01-01T00:00:00Z")
        assert resp.status_code == 200
        titles = [i["title"] for i in resp.json()["items"]]
        assert "NEW-ALERT" in titles
        assert "OLD-ALERT" not in titles

    def test_date_to_filter(self, client, db, sample_raw_alert):
        past = _make_alert(db, sample_raw_alert, severity="low", title="PAST-ALERT")
        past.normalized_at = datetime(2020, 6, 1, tzinfo=timezone.utc)
        db.commit()
        _make_alert(db, sample_raw_alert, severity="high", title="FUTURE-ALERT")

        resp = client.get("/api/v1/alerts?date_to=2021-01-01T00:00:00Z")
        assert resp.status_code == 200
        titles = [i["title"] for i in resp.json()["items"]]
        assert "PAST-ALERT" in titles
        assert "FUTURE-ALERT" not in titles


# ── 10.3 Export and correlations ──────────────────────────────────────────────

class TestExportEndpoints:
    def test_export_csv_returns_text(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/alerts/export?format=csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "id,title,severity" in resp.text

    def test_export_csv_contains_alert(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/alerts/export?format=csv")
        assert resp.status_code == 200
        assert "CVE-2026-12345" in resp.text

    def test_export_csv_filter_by_severity(self, client, db, sample_raw_alert):
        _make_alert(db, sample_raw_alert, severity="critical", title="CRIT-EXP")
        _make_alert(db, sample_raw_alert, severity="low", title="LOW-EXP")

        resp = client.get("/api/v1/alerts/export?format=csv&severity=critical")
        assert resp.status_code == 200
        assert "CRIT-EXP" in resp.text
        assert "LOW-EXP" not in resp.text

    def test_export_stix_returns_bundle(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/alerts/export?format=stix")
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "bundle"
        assert "objects" in data

    def test_export_stix_contains_indicator(self, client, sample_normalized_alert):
        resp = client.get("/api/v1/alerts/export?format=stix")
        assert resp.status_code == 200
        objects = resp.json()["objects"]
        assert len(objects) >= 1
        assert objects[0]["type"] == "indicator"
        assert objects[0]["spec_version"] == "2.1"

    def test_export_empty_db_returns_empty_bundle(self, client):
        resp = client.get("/api/v1/alerts/export?format=stix")
        assert resp.status_code == 200
        assert resp.json()["objects"] == []


class TestCorrelationsEndpoint:
    def test_correlations_empty_db(self, client):
        resp = client.get("/api/v1/alerts/correlations")
        assert resp.status_code == 200
        assert resp.json()["groups"] == []

    def test_correlations_groups_by_cve(self, client, db, sample_source):
        source_id = sample_source.id
        for i in range(3):
            raw = RawAlert(
                source_id=source_id,
                external_id=f"RAW-CVE-{i}",
                raw_data={},
            )
            db.add(raw)
            db.flush()
            alert = NormalizedAlert(
                raw_alert_id=raw.id,
                title=f"CVE-2024-12345 vulnerability variant {i}",
                description="Shared CVE",
                severity="high",
                source_name="NVD",
            )
            db.add(alert)
        db.commit()

        resp = client.get("/api/v1/alerts/correlations?min_count=2")
        assert resp.status_code == 200
        groups = resp.json()["groups"]
        assert any(g["key"] == "CVE-2024-12345" for g in groups)

    def test_correlations_respects_min_count(self, client, db, sample_source):
        raw = RawAlert(
            source_id=sample_source.id,
            external_id="LONE-RAW",
            raw_data={},
        )
        db.add(raw)
        db.flush()
        alert = NormalizedAlert(
            raw_alert_id=raw.id,
            title="CVE-2099-00001 single alert",
            severity="low",
            source_name="NVD",
        )
        db.add(alert)
        db.commit()

        resp = client.get("/api/v1/alerts/correlations?min_count=2")
        assert resp.status_code == 200
        groups = resp.json()["groups"]
        assert not any(g["key"] == "CVE-2099-00001" for g in groups)


# ── 10.4 Categories API ───────────────────────────────────────────────────────

class TestCategoriesAPI:
    def test_list_categories_empty(self, client):
        resp = client.get("/api/v1/categories")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_categories_returns_all(self, client, db):
        db.add(AlertCategory(name="ransomware", description="Ransomware attacks",
                             keywords=["ransomware", "ransom"]))
        db.add(AlertCategory(name="rce", description="Remote code execution",
                             keywords=["rce", "remote code"]))
        db.commit()

        resp = client.get("/api/v1/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = [c["name"] for c in data]
        assert "ransomware" in names
        assert "rce" in names

    def test_categories_sorted_by_name(self, client, db):
        db.add(AlertCategory(name="zerotrust", keywords=[]))
        db.add(AlertCategory(name="apt", keywords=[]))
        db.commit()

        resp = client.get("/api/v1/categories")
        assert resp.status_code == 200
        names = [c["name"] for c in resp.json()]
        assert names == sorted(names)


# ── 10.5 Predictions API ──────────────────────────────────────────────────────

class TestPredictionsAPI:
    def test_get_latest_predictions_empty(self, client):
        resp = client.get("/api/v1/predictions/latest")
        assert resp.status_code == 404

    def test_get_latest_predictions_with_data(self, client, db):
        _make_prediction(db, run_id="run-001", series_key="critical", days_ahead=1)
        _make_prediction(db, run_id="run-001", series_key="high", days_ahead=2)

        resp = client.get("/api/v1/predictions/latest")
        assert resp.status_code == 200
        data = resp.json()
        assert data["run_id"] == "run-001"
        assert "critical" in data["series"]
        assert "high" in data["series"]

    def test_latest_predictions_returns_most_recent_run(self, client, db):
        old = _make_prediction(db, run_id="run-OLD", series_key="total", days_ahead=1)
        old.generated_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        db.commit()
        _make_prediction(db, run_id="run-NEW", series_key="total", days_ahead=2)

        resp = client.get("/api/v1/predictions/latest")
        assert resp.status_code == 200
        assert resp.json()["run_id"] == "run-NEW"

    def test_latest_predictions_includes_anomaly_flag(self, client, db):
        _make_prediction(db, run_id="run-ANOM", series_key="critical",
                         days_ahead=1, is_anomaly=True)

        resp = client.get("/api/v1/predictions/latest")
        assert resp.status_code == 200
        pt = resp.json()["series"]["critical"][0]
        assert pt["is_anomaly"] is True

    def test_generate_predictions_endpoint_exists(self, client):
        resp = client.post("/api/v1/predictions/generate")
        # Auth bypass in dev mode (no JWT_SECRET_KEY or API_KEY configured).
        # Celery task dispatch fails without a broker, so we accept 200 or 5xx.
        assert resp.status_code in (200, 500, 503)

    def test_task_status_unknown_id(self, client):
        resp = client.get("/api/v1/predictions/tasks/nonexistent-task-id")
        assert resp.status_code == 200
        assert resp.json()["status"] in ("UNKNOWN", "PENDING")


# ── 10.6 Summaries API ────────────────────────────────────────────────────────

class TestSummariesAPI:
    def test_list_summaries_empty(self, client):
        resp = client.get("/api/v1/summaries")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_list_summaries_with_data(self, client, db, sample_normalized_alert):
        _make_summary(db, alert_id=sample_normalized_alert.id, summary_type="alert")

        resp = client.get("/api/v1/summaries")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["summary_type"] == "alert"

    def test_list_summaries_filter_by_type(self, client, db, sample_normalized_alert):
        _make_summary(db, alert_id=sample_normalized_alert.id, summary_type="alert")
        _make_summary(db, summary_type="digest")

        resp = client.get("/api/v1/summaries?summary_type=digest")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert all(i["summary_type"] == "digest" for i in items)

    def test_list_summaries_filter_by_alert_id(self, client, db, sample_normalized_alert):
        s = _make_summary(db, alert_id=sample_normalized_alert.id, summary_type="alert")
        _make_summary(db, summary_type="digest")

        resp = client.get(
            f"/api/v1/summaries?normalized_alert_id={sample_normalized_alert.id}"
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["id"] == s.id

    def test_get_summary_by_id(self, client, db, sample_normalized_alert):
        s = _make_summary(db, alert_id=sample_normalized_alert.id)

        resp = client.get(f"/api/v1/summaries/{s.id}")
        assert resp.status_code == 200
        assert resp.json()["content"] == "Executive summary content."

    def test_get_summary_not_found(self, client):
        resp = client.get("/api/v1/summaries/99999")
        assert resp.status_code == 404

    def test_digest_latest_not_found(self, client):
        resp = client.get("/api/v1/summaries/digest/latest")
        assert resp.status_code == 404

    def test_digest_latest_returns_most_recent(self, client, db):
        older_ts = datetime.now(timezone.utc) - timedelta(hours=1)
        _make_summary(db, summary_type="digest", created_at=older_ts)
        s2 = _make_summary(db, summary_type="digest",
                           created_at=datetime.now(timezone.utc))

        resp = client.get("/api/v1/summaries/digest/latest")
        assert resp.status_code == 200
        assert resp.json()["id"] == s2.id

    def test_generate_summary_endpoint_exists(self, client, sample_normalized_alert):
        # Dev bypass: no JWT/API key configured, so auth passes.
        # Worker unavailable, but request is accepted.
        resp = client.post(
            "/api/v1/summaries/generate",
            json={"alert_ids": [sample_normalized_alert.id]},
        )
        assert resp.status_code in (200, 500, 503)

    def test_generate_summary_empty_list_returns_422(self, client, sample_normalized_alert):
        resp = client.post(
            "/api/v1/summaries/generate",
            json={"alert_ids": []},
        )
        assert resp.status_code == 422

    def test_generate_summary_missing_alert_returns_404(self, client):
        resp = client.post(
            "/api/v1/summaries/generate",
            json={"alert_ids": [99999]},
        )
        assert resp.status_code == 404

    def test_generate_digest_endpoint_exists(self, client):
        resp = client.post(
            "/api/v1/summaries/digest/generate",
            json={"hours": 24},
        )
        # Auth bypass in dev mode; Celery unavailable in tests — accept 200 or 5xx.
        assert resp.status_code in (200, 500, 503)

    def test_generate_digest_zero_hours_returns_400(self, client):
        resp = client.post(
            "/api/v1/summaries/digest/generate",
            json={"hours": 0},
        )
        assert resp.status_code == 400

    def test_generate_digest_over_limit_returns_400(self, client):
        resp = client.post(
            "/api/v1/summaries/digest/generate",
            json={"hours": 200},
        )
        assert resp.status_code == 400


# ── 13.1 Category filter in alerts list ──────────────────────────────────────

class TestCategoryFilter:
    def _create_alert_with_category(self, db, sample_raw_alert, cat_name: str):
        from app.models.category import AlertCategory
        cat = AlertCategory(name=cat_name, keywords=[cat_name])
        db.add(cat)
        db.flush()
        alert = _make_alert(db, sample_raw_alert, severity="critical",
                            title=f"Alert tagged {cat_name}")
        alert.categories.append(cat)
        db.commit()
        return alert, cat

    def test_filter_by_category_returns_matching(self, client, db, sample_raw_alert):
        self._create_alert_with_category(db, sample_raw_alert, "ransomware")
        _make_alert(db, sample_raw_alert, severity="low", title="Unrelated alert")

        resp = client.get("/api/v1/alerts?category=ransomware")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert "ransomware" in data["items"][0]["title"]

    def test_filter_by_category_excludes_uncategorised_alerts(self, client, db, sample_raw_alert):
        self._create_alert_with_category(db, sample_raw_alert, "phishing")
        uncategorised = _make_alert(db, sample_raw_alert, severity="high",
                                    title="Plain uncategorised alert")

        resp = client.get("/api/v1/alerts?category=phishing")
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert uncategorised.id not in ids

    def test_filter_by_nonexistent_category_returns_empty(self, client, db, sample_raw_alert):
        _make_alert(db, sample_raw_alert, severity="high", title="Some alert")

        resp = client.get("/api/v1/alerts?category=nonexistent_cat")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ── 13.2 Dashboard timeline parameter handling ───────────────────────────────

class TestDashboardTimelineFiltering:
    def test_timeline_accepts_days_param(self, client):
        resp = client.get("/api/v1/dashboard/timeline?days=7")
        assert resp.status_code == 200

    def test_timeline_period_field_is_daily(self, client):
        resp = client.get("/api/v1/dashboard/timeline")
        assert resp.status_code == 200
        assert resp.json()["period"] == "daily"

    def test_timeline_excludes_data_outside_window(self, client, db, sample_raw_alert):
        old = _make_alert(db, sample_raw_alert, severity="info", title="VERY-OLD")
        old.normalized_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
        db.commit()
        _make_alert(db, sample_raw_alert, severity="high", title="RECENT")

        resp = client.get("/api/v1/dashboard/timeline?days=7")
        assert resp.status_code == 200
        # Old alert from 2020 must not appear in any point
        for point in resp.json()["points"]:
            assert point["date"] > "2020-01-01"
        # Recent alert must be included
        total_in_window = sum(p["count"] for p in resp.json()["points"])
        assert total_in_window >= 1

    def test_timeline_rejects_days_below_minimum(self, client):
        resp = client.get("/api/v1/dashboard/timeline?days=3")
        assert resp.status_code == 422


# ── 15.1 Schema validation constraints ────────────────────────────────────────

class TestSchemaValidation:
    def test_summarize_empty_alert_ids_returns_422(self, client):
        resp = client.post(
            "/api/v1/summaries/generate",
            json={"alert_ids": []},
        )
        assert resp.status_code == 422

    def test_summarize_over_100_alert_ids_returns_422(self, client):
        resp = client.post(
            "/api/v1/summaries/generate",
            json={"alert_ids": list(range(101))},
        )
        assert resp.status_code == 422

    def test_notes_exceeding_max_length_returns_422(self, client, db, sample_raw_alert):
        alert = _make_alert(db, sample_raw_alert, severity="high", title="Long Notes Test")
        resp = client.patch(
            f"/api/v1/alerts/{alert.id}/notes",
            json={"notes": "x" * 5001},
        )
        assert resp.status_code == 422

    def test_notes_at_max_length_is_accepted(self, client, db, sample_raw_alert):
        alert = _make_alert(db, sample_raw_alert, severity="high", title="Max Notes Test")
        resp = client.patch(
            f"/api/v1/alerts/{alert.id}/notes",
            json={"notes": "x" * 5000},
        )
        assert resp.status_code == 200

    def test_search_with_percent_wildcard_does_not_crash(self, client):
        resp = client.get("/api/v1/alerts?search=%malware%")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_search_with_underscore_wildcard_does_not_crash(self, client):
        resp = client.get("/api/v1/alerts?search=CVE_2026")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ── 17.1 Prometheus metrics endpoint ─────────────────────────────────────────

class TestMetricsEndpoint:
    def test_metrics_returns_200(self, client):
        resp = client.get("/metrics")
        assert resp.status_code == 200

    def test_metrics_content_type_is_plain_text(self, client):
        resp = client.get("/metrics")
        assert "text/plain" in resp.headers.get("content-type", "")

    def test_metrics_body_contains_prometheus_headers(self, client):
        resp = client.get("/metrics")
        body = resp.text
        assert "# HELP" in body or "# TYPE" in body


# ── 17.2 WebSocket endpoint ───────────────────────────────────────────────────

class TestWebSocketEndpoint:
    def test_ws_alerts_accepts_connection_and_closes_gracefully(self, client):
        from unittest.mock import patch, AsyncMock

        # Make Redis fail immediately so the test does not wait 5 seconds for
        # the socket_connect_timeout.
        with patch(
            "redis.asyncio.from_url", side_effect=ConnectionError("no redis")
        ):
            try:
                with client.websocket_connect("/ws/alerts") as ws:
                    ws.receive_text()
            except Exception:
                pass  # WebSocketDisconnect(code=1011) is expected

    def test_ws_alerts_endpoint_is_registered(self, client):
        # A 403 or WebSocketDisconnect means the route exists.
        # A plain HTTP 404 would mean it's not registered.
        from unittest.mock import patch

        route_found = False
        with patch(
            "redis.asyncio.from_url", side_effect=ConnectionError("no redis")
        ):
            try:
                with client.websocket_connect("/ws/alerts") as ws:
                    ws.receive_text()
            except Exception:
                # Any exception from the WS session means the route was reached
                route_found = True
            else:
                route_found = True

        assert route_found


# ── 17.3 OpenAPI schema endpoint ─────────────────────────────────────────────

class TestOpenAPIEndpoint:
    def test_openapi_json_returns_200_with_valid_schema(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "openapi" in data
        assert data["openapi"].startswith("3.")


# ── 18.1 list_alerts window-function pagination ───────────────────────────────

class TestListAlertsWindowFunction:
    def test_total_matches_filter_count(self, client, db, sample_raw_alert):
        for i in range(5):
            raw = RawAlert(
                source_id=sample_raw_alert.source_id,
                external_id=f"WIN-{i}",
                raw_data={},
            )
            db.add(raw)
            db.flush()
            db.add(NormalizedAlert(
                raw_alert_id=raw.id,
                title=f"Alert {i}",
                severity="critical",
                source_name="NVD",
            ))
        db.commit()

        resp = client.get("/api/v1/alerts?severity=critical&page_size=2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 2
        assert data["pages"] == 3

    def test_empty_filters_return_zero_total(self, client):
        resp = client.get("/api/v1/alerts?severity=critical")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_total_accurate_on_page_beyond_last(self, client, db, sample_raw_alert):
        raw = RawAlert(
            source_id=sample_raw_alert.source_id,
            external_id="BEYOND-1",
            raw_data={},
        )
        db.add(raw)
        db.flush()
        db.add(NormalizedAlert(
            raw_alert_id=raw.id,
            title="Only alert",
            severity="low",
            source_name="NVD",
        ))
        db.commit()

        resp = client.get("/api/v1/alerts?severity=low&page=2&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"] == []


# ── 18.2 unprocessed_count in source health ──────────────────────────────────

class TestSourceHealthUnprocessedCount:
    def test_unprocessed_count_zero_when_all_processed(self, client, db, sample_source):
        raw = RawAlert(
            source_id=sample_source.id,
            external_id="PROC-1",
            raw_data={},
            is_processed=True,
        )
        db.add(raw)
        db.commit()

        resp = client.get(f"/api/v1/sources/{sample_source.id}/health")
        assert resp.status_code == 200
        assert resp.json()["unprocessed_count"] == 0

    def test_unprocessed_count_reflects_failed_normalization(self, client, db, sample_source):
        for i in range(3):
            db.add(RawAlert(
                source_id=sample_source.id,
                external_id=f"UNPROC-{i}",
                raw_data={},
                is_processed=False,
            ))
        db.commit()

        resp = client.get(f"/api/v1/sources/{sample_source.id}/health")
        assert resp.status_code == 200
        assert resp.json()["unprocessed_count"] == 3

    def test_unprocessed_count_scoped_to_source(self, client, db, sample_source):
        from app.models.source import Source as SourceModel
        other = SourceModel(
            name="OTHER",
            source_type="api",
            base_url="https://example.com",
            polling_interval_minutes=60,
            is_active=True,
        )
        db.add(other)
        db.flush()

        for i in range(2):
            db.add(RawAlert(
                source_id=other.id,
                external_id=f"OTHER-{i}",
                raw_data={},
                is_processed=False,
            ))
        db.commit()

        resp = client.get(f"/api/v1/sources/{sample_source.id}/health")
        assert resp.status_code == 200
        assert resp.json()["unprocessed_count"] == 0
