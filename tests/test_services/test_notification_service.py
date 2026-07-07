"""Tests for the webhook notification service."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestSendWebhook:
    @pytest.mark.asyncio
    async def test_no_webhook_url_returns_silently(self):
        from app.services.notification_service import send_webhook

        mock_settings = MagicMock()
        mock_settings.webhook_url = ""
        with patch("app.services.notification_service.settings", mock_settings):
            await send_webhook({"event": "critical_alert"})  # must not raise

    @pytest.mark.asyncio
    async def test_posts_payload_to_configured_url(self):
        from app.services.notification_service import send_webhook

        mock_settings = MagicMock()
        mock_settings.webhook_url = "https://hooks.example.com/notify"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.notification_service.settings", mock_settings):
            with patch(
                "app.services.notification_service.httpx.AsyncClient",
                return_value=mock_client,
            ):
                await send_webhook({"event": "test"})

        mock_client.post.assert_called_once_with(
            "https://hooks.example.com/notify",
            json={"event": "test"},
        )

    @pytest.mark.asyncio
    async def test_http_error_does_not_raise(self):
        import httpx
        from app.services.notification_service import send_webhook

        mock_settings = MagicMock()
        mock_settings.webhook_url = "https://hooks.example.com/notify"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("connection refused")
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.notification_service.settings", mock_settings):
            with patch(
                "app.services.notification_service.httpx.AsyncClient",
                return_value=mock_client,
            ):
                await send_webhook({"event": "test"})  # must not raise
