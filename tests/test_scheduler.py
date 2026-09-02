"""
Unit and Integration Tests for Heyaaashu Studio Phase 12A Scheduling.
Covers creating schedule, rejecting past dates, duplicate scheduling prevention,
rescheduling, cancellation, publish now, background scheduler execution, failure handling,
stale recovery, and duplicate-publish protection.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

from apps.api.server import create_app
from packages.post_schema import ContentType, ParseMode, PostSchema
from packages.scheduler import PublisherScheduler
from packages.shared.db import StudioDatabase


@pytest.fixture
def sample_post():
    return PostSchema(
        schema_version="1.0.0",
        content_type=ContentType.AI_NEWS,
        title="Anthropic Launches Claude 3.7 Sonnet with Hybrid Reasoning",
        body="Anthropic announced Claude 3.7 Sonnet, combining fast thinking and extended reasoning in a single model.",
        summary="Anthropic launches Claude 3.7 Sonnet.",
        takeaways=["Hybrid architecture", "Crosses math and coding benchmarks"],
        why_it_matters="Offers granular control over latency versus reasoning depth.",
        parse_mode=ParseMode.HTML,
    )


# ─── 1. DATABASE SCHEDULING PERSISTENCE TESTS ────────────────────────────────

def test_database_create_and_get_scheduled(tmp_path, sample_post):
    db = StudioDatabase(db_path=str(tmp_path / "test_sched_db.db"))
    future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    # Create schedule
    post_id = db.create_scheduled_post(post=sample_post, scheduled_at=future_time)
    assert post_id > 0

    item = db.get_scheduled_post_by_id(post_id)
    assert item is not None
    assert item["status"] == "scheduled"
    assert item["scheduled_at"] == future_time
    assert item["title"] == sample_post.title
    assert item["schema"]["title"] == sample_post.title

    # Retrieve all scheduled
    all_scheduled = db.get_scheduled_posts()
    assert len(all_scheduled) == 1
    assert all_scheduled[0]["post_id"] == post_id


def test_database_prevent_duplicate_scheduling(tmp_path, sample_post):
    db = StudioDatabase(db_path=str(tmp_path / "test_dup_sched.db"))
    future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    post_id = db.create_scheduled_post(post=sample_post, scheduled_at=future_time)

    # Attempting to schedule the same post_id again while in 'scheduled' status must raise ValueError
    with pytest.raises(ValueError) as exc_info:
        db.create_scheduled_post(post=sample_post, scheduled_at=future_time, post_id=post_id)
    assert "already in 'scheduled' status" in str(exc_info.value)


def test_database_reschedule_and_cancel(tmp_path, sample_post):
    db = StudioDatabase(db_path=str(tmp_path / "test_resched.db"))
    time_1 = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    time_2 = (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat()

    post_id = db.create_scheduled_post(post=sample_post, scheduled_at=time_1)

    # Reschedule to time_2
    ok = db.update_scheduled_post(post_id=post_id, scheduled_at=time_2)
    assert ok is True

    item = db.get_scheduled_post_by_id(post_id)
    assert item["scheduled_at"] == time_2

    # Cancel schedule
    cancelled = db.cancel_scheduled_post(post_id)
    assert cancelled is True

    item_cancelled = db.get_scheduled_post_by_id(post_id)
    assert item_cancelled["status"] == "cancelled"


def test_database_atomic_acquisition_and_stale_recovery(tmp_path, sample_post):
    db = StudioDatabase(db_path=str(tmp_path / "test_acquire.db"))
    past_due = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    post_id = db.create_scheduled_post(post=sample_post, scheduled_at=past_due)

    # Acquire due post
    now_iso = datetime.now(timezone.utc).isoformat()
    acquired = db.acquire_due_scheduled_posts(now_iso)
    assert len(acquired) == 1
    assert acquired[0]["post_id"] == post_id
    assert acquired[0]["status"] == "publishing"

    # Second acquisition immediately returns empty (duplicate publish protection)
    acquired_second = db.acquire_due_scheduled_posts(now_iso)
    assert len(acquired_second) == 0

    # Simulate stale recovery: post stuck in publishing longer than threshold
    recovered = db.recover_stale_publishing_posts(stale_seconds=0)
    assert recovered == 1

    item = db.get_scheduled_post_by_id(post_id)
    assert item["status"] == "scheduled"


# ─── 2. API ENDPOINT INTEGRATION TESTS ────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_schedule_creation_success(tmp_path, sample_post):
    db = StudioDatabase(db_path=str(tmp_path / "test_api_sched.db"))
    app = create_app(db=db, enable_scheduler=False)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        future_time = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        payload = {
            "schema": sample_post.model_dump(),
            "scheduled_at": future_time,
        }

        resp = await client.post("/api/schedule", json=payload)
        assert resp.status == 200
        data = await resp.json()

        assert data["success"] is True
        post_record = data["scheduled_post"]
        assert post_record["post_id"] > 0
        assert post_record["status"] == "scheduled"
        assert post_record["title"] == sample_post.title
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_api_reject_past_schedule_date(tmp_path, sample_post):
    db = StudioDatabase(db_path=str(tmp_path / "test_past_date.db"))
    app = create_app(db=db, enable_scheduler=False)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        payload = {
            "schema": sample_post.model_dump(),
            "scheduled_at": past_time,
        }

        resp = await client.post("/api/schedule", json=payload)
        assert resp.status == 400
        data = await resp.json()

        assert data["success"] is False
        assert "must be in the future" in data["error"]
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_api_scheduled_crud_and_cancel(tmp_path, sample_post):
    db = StudioDatabase(db_path=str(tmp_path / "test_crud_sched.db"))
    app = create_app(db=db, enable_scheduler=False)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        future_1 = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
        create_resp = await client.post("/api/schedule", json={
            "schema": sample_post.model_dump(),
            "scheduled_at": future_1,
        })
        post_id = (await create_resp.json())["scheduled_post"]["post_id"]

        # 1. GET /api/scheduled
        list_resp = await client.get("/api/scheduled")
        assert list_resp.status == 200
        items = (await list_resp.json())["scheduled_posts"]
        assert len(items) == 1
        assert items[0]["post_id"] == post_id

        # 2. GET /api/scheduled/{id}
        get_resp = await client.get(f"/api/scheduled/{post_id}")
        assert get_resp.status == 200
        assert (await get_resp.json())["scheduled_post"]["post_id"] == post_id

        # 3. PUT /api/scheduled/{id} (Reschedule)
        future_2 = (datetime.now(timezone.utc) + timedelta(hours=10)).isoformat()
        put_resp = await client.put(f"/api/scheduled/{post_id}", json={
            "scheduled_at": future_2,
        })
        assert put_resp.status == 200
        assert (await put_resp.json())["scheduled_post"]["scheduled_at"] == future_2

        # 4. POST /api/scheduled/{id}/cancel
        cancel_resp = await client.post(f"/api/scheduled/{post_id}/cancel")
        assert cancel_resp.status == 200
        assert (await cancel_resp.json())["status"] == "cancelled"

        # 5. DELETE /api/scheduled/{id}
        del_resp = await client.delete(f"/api/scheduled/{post_id}")
        assert del_resp.status == 200
        assert (await del_resp.json())["deleted_id"] == post_id
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_api_publish_scheduled_now(tmp_path, sample_post):
    db = StudioDatabase(db_path=str(tmp_path / "test_pub_now.db"))
    app = create_app(db=db, enable_scheduler=False)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        future_time = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        create_resp = await client.post("/api/schedule", json={
            "schema": sample_post.model_dump(),
            "scheduled_at": future_time,
        })
        post_id = (await create_resp.json())["scheduled_post"]["post_id"]

        with patch("apps.api.server.publish_post_to_telegram", new_callable=AsyncMock) as mock_pub:
            mock_pub.return_value = {"success": True, "message_id": 9988, "chat_id": -100123456}

            resp = await client.post(f"/api/scheduled/{post_id}/publish")
            assert resp.status == 200
            data = await resp.json()

            assert data["success"] is True
            assert data["message_id"] == 9988
            assert data["status"] == "posted"

            # Check DB updated
            item = db.get_scheduled_post_by_id(post_id)
            assert item["status"] == "posted"
            assert item["telegram_message_id"] == 9988
    finally:
        await client.close()


# ─── 3. SCHEDULER ENGINE TESTS ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scheduler_worker_picks_up_and_publishes(tmp_path, sample_post):
    db = StudioDatabase(db_path=str(tmp_path / "test_worker_exec.db"))
    past_due = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    post_id = db.create_scheduled_post(post=sample_post, scheduled_at=past_due)

    mock_pub = AsyncMock(return_value={"success": True, "message_id": 7744, "chat_id": -100123456})
    scheduler = PublisherScheduler(db=db, publish_fn=mock_pub, poll_interval=0.1)

    processed = await scheduler.tick()
    assert processed == 1

    item = db.get_scheduled_post_by_id(post_id)
    assert item["status"] == "posted"
    assert item["telegram_message_id"] == 7744
    mock_pub.assert_called_once()


@pytest.mark.asyncio
async def test_scheduler_worker_records_failure(tmp_path, sample_post):
    db = StudioDatabase(db_path=str(tmp_path / "test_worker_fail.db"))
    past_due = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    post_id = db.create_scheduled_post(post=sample_post, scheduled_at=past_due)

    mock_pub = AsyncMock(return_value={"success": False, "error": "Telegram Bad Request: chat not found"})
    scheduler = PublisherScheduler(db=db, publish_fn=mock_pub, poll_interval=0.1)

    processed = await scheduler.tick()
    assert processed == 1

    item = db.get_scheduled_post_by_id(post_id)
    assert item["status"] == "failed"
    assert "chat not found" in item["error_message"]
