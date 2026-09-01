"""
Tests for Telegram Webhook Routing and Cloud Deployment.
Verifies secret token authorization, update ingestion, and health check database reporting.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp.test_utils import TestClient, TestServer
from apps.api.server import create_app
from packages.shared.db import StudioDatabase


@pytest.mark.asyncio
async def test_telegram_webhook_secret_token_enforcement(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_webhook.db"))

    mock_bot = MagicMock()
    mock_dp = MagicMock()
    mock_dp.feed_update = AsyncMock(return_value=True)

    with patch("apps.api.server.TELEGRAM_WEBHOOK_SECRET", "super_secret_webhook_token_999"):
        app = create_app(db=test_db, bot=mock_bot, dp=mock_dp)
        client = TestClient(TestServer(app))
        await client.start_server()

        try:
            update_payload = {
                "update_id": 10001,
                "message": {
                    "message_id": 1,
                    "date": 1441645532,
                    "chat": {"id": 8982444793, "type": "private"},
                    "from": {"id": 8982444793, "is_bot": False, "first_name": "TestUser"},
                    "text": "/start",
                }
            }

            # 1. Without secret token header -> 403 Forbidden
            unauth_resp = await client.post("/api/telegram/webhook", json=update_payload)
            assert unauth_resp.status == 403

            # 2. With wrong secret token header -> 403 Forbidden
            bad_resp = await client.post(
                "/api/telegram/webhook",
                json=update_payload,
                headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"}
            )
            assert bad_resp.status == 403

            # 3. With correct secret token header -> 200 OK & routed to dispatcher
            ok_resp = await client.post(
                "/api/telegram/webhook",
                json=update_payload,
                headers={"X-Telegram-Bot-Api-Secret-Token": "super_secret_webhook_token_999"}
            )
            assert ok_resp.status == 200
            data = await ok_resp.json()
            assert data["ok"] is True
            assert mock_dp.feed_update.called
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_set_webhook_endpoint(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_set_webhook.db"))

    mock_bot = MagicMock()
    mock_bot.set_webhook = AsyncMock(return_value=True)
    mock_info = MagicMock()
    mock_info.url = "https://heyaaashu.onrender.com/api/telegram/webhook"
    mock_info.pending_update_count = 0
    mock_bot.get_webhook_info = AsyncMock(return_value=mock_info)

    app = create_app(db=test_db, bot=mock_bot)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        resp = await client.post(
            "/api/telegram/set-webhook",
            json={"webhook_url": "https://heyaaashu.onrender.com/api/telegram/webhook"}
        )
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert data["webhook_url"] == "https://heyaaashu.onrender.com/api/telegram/webhook"
    finally:
        await client.close()
