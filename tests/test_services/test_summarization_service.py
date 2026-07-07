"""Tests for the LLM summarization service."""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.alert import NormalizedAlert
from app.models.summary import Summary
from app.services.summarization_service import SummarizationService


def _make_alert(
    title: str = "CVE-2026-99999",
    severity: str = "high",
    source: str = "NVD",
) -> NormalizedAlert:
    """Build a minimal NormalizedAlert for testing."""
    alert = NormalizedAlert(
        id=1,
        title=title,
        description="A critical vulnerability in test software.",
        severity=severity,
        cvss_score=Decimal("8.5"),
        source_name=source,
    )
    return alert


def _mock_openai_client(content: str = "Test LLM summary."):
    """Build a mock AsyncOpenAI client that returns a completion."""
    mock_choice = MagicMock()
    mock_choice.message.content = content

    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
    return mock_client


@pytest.fixture
def service():
    """SummarizationService with mocked AsyncOpenAI and API key set."""
    with patch("app.services.summarization_service.settings") as mock_settings:
        mock_settings.xai_api_key = "fake-key"
        mock_settings.xai_base_url = "https://api.x.ai/v1"
        mock_settings.xai_model = "grok-4-1-fast"
        with patch("app.services.summarization_service.AsyncOpenAI") as mock_cls:
            mock_cls.return_value = _mock_openai_client()
            svc = SummarizationService()
            yield svc


@pytest.mark.asyncio
async def test_summarize_alert_returns_summary(service):
    """summarize_alert returns a Summary ORM object with content."""
    alert = _make_alert()
    result = await service.summarize_alert(alert)

    assert result is not None
    assert isinstance(result, Summary)
    assert result.summary_type == "alert"
    assert result.content == "Test LLM summary."


@pytest.mark.asyncio
async def test_summarize_alert_returns_none_without_api_key():
    """Without API key, summarize_alert returns None."""
    with patch("app.services.summarization_service.settings") as mock_settings:
        mock_settings.xai_api_key = ""
        mock_settings.xai_base_url = "https://api.x.ai/v1"
        mock_settings.xai_model = "grok-4-1-fast"
        with patch("app.services.summarization_service.AsyncOpenAI"):
            svc = SummarizationService()
            alert = _make_alert()
            result = await svc.summarize_alert(alert)

    assert result is None


@pytest.mark.asyncio
async def test_summarize_alert_handles_api_error(service):
    """LLM API error is caught; returns None without raising."""
    from openai import APIConnectionError

    service._client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=MagicMock())
    )
    alert = _make_alert()
    result = await service.summarize_alert(alert)

    assert result is None


@pytest.mark.asyncio
async def test_generate_digest_returns_summary(service):
    """generate_digest returns a Summary with summary_type=digest."""
    alerts = [_make_alert(title=f"CVE-2026-{i}") for i in range(5)]
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    period_start = now - timedelta(hours=24)

    result = await service.generate_digest(alerts, period_start, now)

    assert result is not None
    assert isinstance(result, Summary)
    assert result.summary_type == "digest"


@pytest.mark.asyncio
async def test_generate_digest_handles_connection_error(service):
    """APIConnectionError in digest generation returns None."""
    from openai import APIConnectionError

    service._client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=MagicMock())
    )
    alerts = [_make_alert()]
    now = datetime.now(timezone.utc)
    from datetime import timedelta

    result = await service.generate_digest(alerts, now - timedelta(hours=24), now)
    assert result is None
