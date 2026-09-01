"""
Tests for Heyaaashu Studio API Server.
Verifies canonical PostSchema validation on writes, draft CRUD, preview generation, health checks, authentication, and publish validation.
"""

import pytest
from unittest.mock import patch
from aiohttp.test_utils import TestClient, TestServer
from apps.api.server import create_app
from packages.post_schema import ContentType, PostSchema
from packages.shared.db import StudioDatabase


@pytest.mark.asyncio
async def test_health_endpoint(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_api_health.db"))
    app = create_app(db=test_db)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        resp = await client.get("/api/health")
        assert resp.status == 200
        data = await resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "heyaaashu-studio-api"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_authentication_protection(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_api_auth.db"))
    with patch("apps.api.server.STUDIO_AUTH_TOKEN", "super_secret_test_token_123"):
        app = create_app(db=test_db)
        client = TestClient(TestServer(app))
        await client.start_server()

        try:
            # 1. Health is always public
            h_resp = await client.get("/api/health")
            assert h_resp.status == 200

            # 2. Login endpoint allows valid token
            login_resp = await client.post("/api/auth/login", json={"token": "super_secret_test_token_123"})
            assert login_resp.status == 200
            login_data = await login_resp.json()
            assert login_data["success"] is True

            # 3. Login endpoint rejects bad token
            bad_login = await client.post("/api/auth/login", json={"token": "wrong_token"})
            assert bad_login.status == 401

            # 4. Drafts endpoint without auth returns 401
            unauth_resp = await client.get("/api/drafts")
            assert unauth_resp.status == 401
            unauth_data = await unauth_resp.json()
            assert unauth_data["success"] is False
            assert "Unauthorized" in unauth_data["error"]

            # 5. Drafts endpoint with Bearer auth succeeds
            auth_resp = await client.get(
                "/api/drafts",
                headers={"Authorization": "Bearer super_secret_test_token_123"}
            )
            assert auth_resp.status == 200
            auth_data = await auth_resp.json()
            assert auth_data["success"] is True

            # 6. Drafts endpoint with X-Studio-Auth header succeeds
            header_auth_resp = await client.get(
                "/api/drafts",
                headers={"X-Studio-Auth": "super_secret_test_token_123"}
            )
            assert header_auth_resp.status == 200
        finally:
            await client.close()


@pytest.mark.asyncio
async def test_create_and_get_draft(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_api.db"))
    app = create_app(db=test_db)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        post_data = {
            "content_type": "ai_news",
            "title": "Gemini 2.5 Released",
            "body": "Google launches next generation reasoning model.",
            "buttons": [{"text": "Read More", "url": "https://blog.google"}],
        }

        # 1. Create draft
        resp = await client.post("/api/drafts", json={"schema": post_data})
        assert resp.status == 201
        data = await resp.json()
        assert data["success"] is True
        draft_id = data["draft_id"]
        assert draft_id > 0

        # 2. Get draft
        get_resp = await client.get(f"/api/drafts/{draft_id}")
        assert get_resp.status == 200
        get_data = await get_resp.json()
        assert get_data["schema"]["title"] == "Gemini 2.5 Released"
        assert get_data["schema"]["content_type"] == "ai_news"
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_schema_validation_rejection(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_api_bad.db"))
    app = create_app(db=test_db)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        # Invalid content_type
        bad_data = {
            "content_type": "invalid_type",
            "title": "Bad Type",
            "body": "Body",
        }
        resp = await client.post("/api/drafts", json={"schema": bad_data})
        assert resp.status == 400
        data = await resp.json()
        assert data["success"] is False
        assert "Schema validation failed" in data["error"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_preview_generation(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_api_prev.db"))
    app = create_app(db=test_db)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        post_data = {
            "content_type": "job",
            "title": "Staff AI Engineer",
            "body": "Role: Staff AI Engineer\nCompany: Modal\nLocation: Remote",
            "metadata": {
                "company": "Modal",
                "location": "Remote",
                "salary": "$250,000",
            },
            "buttons": [{"text": "Apply", "url": "https://modal.com/careers"}],
        }
        resp = await client.post("/api/preview", json={"schema": post_data})
        assert resp.status == 200
        data = await resp.json()
        assert data["success"] is True
        assert "JOB ALERT" in data["formatted_text"]
        assert "Modal" in data["formatted_text"]
        assert data["is_valid"] is True
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_publish_endpoint_validation_and_response(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_api_pub.db"))
    app = create_app(db=test_db)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        # Bad schema publish rejection
        bad_resp = await client.post("/api/publish", json={"schema": {"title": ""}})
        assert bad_resp.status == 400
        bad_data = await bad_resp.json()
        assert bad_data["success"] is False

        # Valid schema publish check
        valid_post = {
            "content_type": "ai_news",
            "title": "Gemini 2.5 Release Test",
            "body": "Multimodal reasoning test.",
            "buttons": [{"text": "Read Source", "url": "https://blog.google"}],
        }
        pub_resp = await client.post("/api/publish", json={"schema": valid_post})
        assert pub_resp.status == 200
        pub_data = await pub_resp.json()
        assert pub_data["success"] is True
        assert "message_id" in pub_data
        assert "channel_id" in pub_data
    finally:
        await client.close()
