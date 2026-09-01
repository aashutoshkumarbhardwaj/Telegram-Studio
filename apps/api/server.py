"""
Heyaaashu Studio Backend API Server.
Provides canonical PostSchema validation, draft management, formatting, preview, publishing,
and Telegram Webhook routing for free cloud deployments (Render).
Built on aiohttp.web with authentication, CORS restriction, and zero external web framework overhead.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from aiohttp import web
from pydantic import ValidationError

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update

from apps.bot.handlers.daily import router as daily_router
from apps.bot.handlers.new_post import router as new_post_router
from apps.bot.handlers.preview_actions import router as preview_actions_router
from apps.bot.handlers.research import router as research_router
from apps.bot.handlers.start import router as start_router

from packages.formatter import format_post_text, generate_telegram_payload, validate_telegram_constraints
from packages.post_schema import PostSchema
from packages.shared.config import (
    ALLOWED_ORIGINS,
    BOT_TOKEN,
    DATABASE_PATH,
    DATABASE_URL,
    PUBLIC_APP_URL,
    STUDIO_AUTH_TOKEN,
    TELEGRAM_WEBHOOK_SECRET,
    get_target_channel_id,
)
from packages.shared.db import StudioDatabase
from packages.telegram.publisher import publish_post_to_telegram

logger = logging.getLogger(__name__)


def _get_cors_headers(request: Optional[web.Request] = None) -> dict:
    """Calculates CORS headers restricted to allowed production origins."""
    origin = request.headers.get("Origin") if request else None
    allowed_origin = "*"

    if origin:
        if "*" in ALLOWED_ORIGINS or origin in ALLOWED_ORIGINS:
            allowed_origin = origin
        elif any(origin.startswith(ao) for ao in ALLOWED_ORIGINS):
            allowed_origin = origin

    return {
        "Access-Control-Allow-Origin": allowed_origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Studio-Auth, X-Telegram-Bot-Api-Secret-Token, Accept",
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }


def verify_request_auth(request: web.Request) -> bool:
    """
    Verifies authentication token if STUDIO_AUTH_TOKEN is configured.
    If STUDIO_AUTH_TOKEN is not set (e.g. initial dev), permits request.
    """
    if not STUDIO_AUTH_TOKEN:
        return True

    auth_header = request.headers.get("Authorization", "")
    token = ""
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
    elif request.headers.get("X-Studio-Auth"):
        token = request.headers.get("X-Studio-Auth", "").strip()
    elif "token" in request.query:
        token = request.query.get("token", "").strip()

    return token == STUDIO_AUTH_TOKEN


@web.middleware
async def auth_middleware(request: web.Request, handler) -> web.Response:
    """Enforces authentication across protected studio API endpoints while keeping webhooks & health public."""
    if request.method == "OPTIONS":
        return await handler(request)

    # Public unauthenticated endpoints (Health, Telegram Webhook, Login)
    if request.path in ["/api/health", "/api/auth/login", "/api/telegram/webhook"]:
        return await handler(request)

    # Static assets and SPA routes are public
    if not request.path.startswith("/api/"):
        return await handler(request)

    # Verify studio authentication token
    if STUDIO_AUTH_TOKEN and not verify_request_auth(request):
        return web.json_response(
            {"success": False, "error": "Unauthorized: Invalid or missing studio authentication token"},
            status=401,
            headers=_get_cors_headers(request),
        )

    return await handler(request)


async def handle_options(request: web.Request) -> web.Response:
    return web.Response(headers=_get_cors_headers(request))


async def health_check(request: web.Request) -> web.Response:
    """GET /api/health — Health check endpoint for Render & Docker."""
    db: StudioDatabase = request.app.get("db")
    return web.json_response({
        "status": "healthy",
        "service": "heyaaashu-studio-api",
        "database": "postgresql" if getattr(db, "is_postgres", False) else "sqlite",
        "webhook_enabled": bool(request.app.get("bot")),
        "version": "1.0.0",
    }, headers=_get_cors_headers(request))


async def login_endpoint(request: web.Request) -> web.Response:
    """POST /api/auth/login — Authenticates studio user with password/token."""
    cors = _get_cors_headers(request)
    try:
        body = await request.json()
        token = body.get("token") or body.get("password") or ""
        if not STUDIO_AUTH_TOKEN or token == STUDIO_AUTH_TOKEN:
            return web.json_response({
                "success": True,
                "message": "Authenticated successfully",
                "token": STUDIO_AUTH_TOKEN or "local_dev_token",
            }, headers=cors)
        return web.json_response({"success": False, "error": "Invalid authentication token"}, status=401, headers=cors)
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=400, headers=cors)


# ─── TELEGRAM WEBHOOK HANDLERS ──────────────────────────────────────────────────

async def telegram_webhook_endpoint(request: web.Request) -> web.Response:
    """POST /api/telegram/webhook — Routes incoming Telegram updates into aiogram dispatcher."""
    cors = _get_cors_headers(request)

    # 1. Verify Webhook Secret Token if configured
    if TELEGRAM_WEBHOOK_SECRET:
        secret_header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if secret_header != TELEGRAM_WEBHOOK_SECRET:
            logger.warning("Rejected Telegram webhook request: secret token mismatch.")
            return web.json_response({"error": "Forbidden: Invalid secret token"}, status=403, headers=cors)

    bot: Optional[Bot] = request.app.get("bot")
    dp: Optional[Dispatcher] = request.app.get("dp")

    if not bot or not dp:
        logger.error("Telegram bot or dispatcher not initialized on API server.")
        return web.json_response({"error": "Bot service unavailable"}, status=503, headers=cors)

    try:
        data = await request.json()
        update = Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot=bot, update=update)
        return web.json_response({"ok": True}, headers=cors)
    except Exception as e:
        logger.error(f"Error processing Telegram webhook update: {e}", exc_info=True)
        return web.json_response({"ok": False, "error": str(e)}, status=500, headers=cors)


async def set_telegram_webhook_endpoint(request: web.Request) -> web.Response:
    """POST /api/telegram/set-webhook — Configures the Telegram webhook URL."""
    cors = _get_cors_headers(request)
    bot: Optional[Bot] = request.app.get("bot")

    if not bot:
        return web.json_response({"success": False, "error": "Bot token not configured"}, status=400, headers=cors)

    try:
        body = await request.json() if request.can_read_body else {}
    except Exception:
        body = {}

    webhook_url = body.get("webhook_url") or (f"{PUBLIC_APP_URL}/api/telegram/webhook" if PUBLIC_APP_URL else None)

    if not webhook_url:
        return web.json_response({
            "success": False,
            "error": "Missing webhook_url parameter and PUBLIC_APP_URL environment variable is not set."
        }, status=400, headers=cors)

    try:
        await bot.set_webhook(
            url=webhook_url,
            secret_token=TELEGRAM_WEBHOOK_SECRET or None,
            drop_pending_updates=True,
        )
        info = await bot.get_webhook_info()
        logger.info(f"Telegram webhook configured to: {info.url}")
        return web.json_response({
            "success": True,
            "webhook_url": info.url,
            "pending_update_count": info.pending_update_count,
        }, headers=cors)
    except Exception as e:
        logger.error(f"Failed to set Telegram webhook: {e}", exc_info=True)
        return web.json_response({"success": False, "error": str(e)}, status=500, headers=cors)


# ─── DRAFT & PUBLISH ENDPOINTS ──────────────────────────────────────────────────

async def get_drafts(request: web.Request) -> web.Response:
    """GET /api/drafts — Lists all stored drafts."""
    db: StudioDatabase = request.app["db"]
    cors = _get_cors_headers(request)
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT post_id, user_id, channel_id, content_type, title, text, status, created_at, published_at, raw_schema_json
            FROM posts
            ORDER BY post_id DESC
            LIMIT 50
        """)
        rows = [dict(r) for r in cursor.fetchall()]
        return web.json_response({"success": True, "drafts": rows}, headers=cors)


async def get_draft_by_id(request: web.Request) -> web.Response:
    """GET /api/drafts/{id} — Retrieves a single PostSchema draft."""
    db: StudioDatabase = request.app["db"]
    cors = _get_cors_headers(request)
    draft_id = int(request.match_info["id"])
    post = db.get_post_schema(draft_id)
    if not post:
        return web.json_response({"success": False, "error": "Draft not found"}, status=404, headers=cors)

    with db.get_connection() as conn:
        cursor = conn.cursor()
        query = "SELECT status, post_id, created_at FROM posts WHERE post_id = " + ("%s" if db.is_postgres else "?")
        cursor.execute(query, (draft_id,))
        row = cursor.fetchone()
        status = dict(row)["status"] if row else "draft"

    return web.json_response({
        "success": True,
        "draft_id": draft_id,
        "status": status,
        "schema": post.model_dump(),
    }, headers=cors)


async def create_draft(request: web.Request) -> web.Response:
    """POST /api/drafts — Validates canonical PostSchema and creates draft in DB."""
    db: StudioDatabase = request.app["db"]
    cors = _get_cors_headers(request)
    try:
        body = await request.json()
        raw_schema = body.get("schema") or body
        post = PostSchema.model_validate(raw_schema)
        user_id = body.get("user_id", 1)

        draft_id = db.save_draft(user_id=user_id, post=post, status="draft")
        return web.json_response({
            "success": True,
            "draft_id": draft_id,
            "schema": post.model_dump(),
        }, status=201, headers=cors)
    except ValidationError as e:
        return web.json_response({"success": False, "error": "Schema validation failed", "details": e.errors()}, status=400, headers=cors)
    except Exception as e:
        logger.error(f"Failed to create draft: {e}", exc_info=True)
        return web.json_response({"success": False, "error": str(e)}, status=500, headers=cors)


async def update_draft(request: web.Request) -> web.Response:
    """PUT /api/drafts/{id} — Validates and updates an existing draft."""
    db: StudioDatabase = request.app["db"]
    cors = _get_cors_headers(request)
    draft_id = int(request.match_info["id"])
    try:
        body = await request.json()
        raw_schema = body.get("schema") or body
        post = PostSchema.model_validate(raw_schema)

        db.update_draft_post(draft_id, post)
        if "status" in body:
            db.mark_post_status(draft_id, body["status"])

        return web.json_response({
            "success": True,
            "draft_id": draft_id,
            "schema": post.model_dump(),
        }, headers=cors)
    except ValidationError as e:
        return web.json_response({"success": False, "error": "Schema validation failed", "details": e.errors()}, status=400, headers=cors)
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500, headers=cors)


async def delete_draft(request: web.Request) -> web.Response:
    """DELETE /api/drafts/{id} — Deletes a draft."""
    db: StudioDatabase = request.app["db"]
    cors = _get_cors_headers(request)
    draft_id = int(request.match_info["id"])
    with db.get_connection() as conn:
        cursor = conn.cursor()
        query = "DELETE FROM posts WHERE post_id = " + ("%s" if db.is_postgres else "?")
        cursor.execute(query, (draft_id,))
        if not db.is_postgres:
            conn.commit()
    return web.json_response({"success": True, "deleted_id": draft_id}, headers=cors)


async def generate_preview(request: web.Request) -> web.Response:
    """POST /api/preview — Generates canonical formatted text and Telegram payload."""
    cors = _get_cors_headers(request)
    try:
        body = await request.json()
        raw_schema = body.get("schema") or body
        post = PostSchema.model_validate(raw_schema)

        formatted_text = format_post_text(post, include_header=True)
        payload = generate_telegram_payload(post, chat_id=get_target_channel_id())

        is_valid, err = validate_telegram_constraints(formatted_text, has_media=bool(post.media))

        return web.json_response({
            "success": True,
            "formatted_text": formatted_text,
            "char_count": len(formatted_text),
            "is_valid": is_valid,
            "constraint_error": err,
            "payload": payload,
        }, headers=cors)
    except ValidationError as e:
        return web.json_response({"success": False, "error": "Schema validation failed", "details": e.errors()}, status=400, headers=cors)
    except Exception as e:
        return web.json_response({"success": False, "error": str(e)}, status=500, headers=cors)


async def publish_post_endpoint(request: web.Request) -> web.Response:
    """POST /api/publish — Validates PostSchema and dispatches to Telegram publisher."""
    db: StudioDatabase = request.app["db"]
    cors = _get_cors_headers(request)
    try:
        body = await request.json()
        raw_schema = body.get("schema") or body
        post = PostSchema.model_validate(raw_schema)
        draft_id = body.get("draft_id")

        channel_id = body.get("channel_id") or get_target_channel_id()
        res = await publish_post_to_telegram(post, channel_id=channel_id)

        if res.get("success") and draft_id:
            db.mark_post_published(
                post_id=draft_id,
                channel_id=int(channel_id) if str(channel_id).startswith("-100") else 0,
                message_id=res.get("message_id", 0),
            )

        message_id = res.get("message_id")
        target_chat_id = str(res.get("chat_id") or channel_id)

        return web.json_response({
            "success": True,
            "message_id": message_id,
            "channel_id": target_chat_id,
            "publish_result": res,
        }, headers=cors)
    except ValidationError as e:
        return web.json_response({"success": False, "error": "Schema validation failed", "details": e.errors()}, status=400, headers=cors)
    except Exception as e:
        logger.error(f"Publish failed: {e}", exc_info=True)
        return web.json_response({"success": False, "error": str(e)}, status=500, headers=cors)


# ─── SPA STATIC ASSETS FALLBACK ─────────────────────────────────────────────────

async def serve_spa_index(request: web.Request) -> web.Response:
    """Serves index.html for root and SPA client routes in single-container mode."""
    possible_paths = [
        Path(__file__).resolve().parent.parent / "message-builder" / "dist" / "index.html",
        Path("/app/apps/message-builder/dist/index.html"),
        Path("/app/dist/index.html"),
        Path("apps/message-builder/dist/index.html"),
    ]
    for p in possible_paths:
        if p.exists():
            return web.FileResponse(p)
    return web.json_response({"status": "healthy", "message": "Heyaaashu Studio API is running"}, headers=_get_cors_headers(request))


def create_app(
    db: Optional[StudioDatabase] = None,
    bot: Optional[Bot] = None,
    dp: Optional[Dispatcher] = None,
) -> web.Application:
    """Creates the aiohttp web application with webhook routing and SPA serving."""
    app = web.Application(middlewares=[auth_middleware])
    database = db or StudioDatabase()
    app["db"] = database

    # Set up Telegram Bot
    if bot:
        app["bot"] = bot
    elif BOT_TOKEN and BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN":
        try:
            app["bot"] = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        except Exception as e:
            logger.warning(f"Could not initialize Telegram Bot: {e}")

    # Set up Telegram Dispatcher
    if dp:
        app["dp"] = dp
    elif app.get("bot"):
        try:
            dispatcher = Dispatcher()
            dispatcher.workflow_data.update(db=database)
            for r in [start_router, daily_router, new_post_router, preview_actions_router, research_router]:
                if r.parent_router is not None:
                    r._parent_router = None
                dispatcher.include_router(r)
            app["dp"] = dispatcher
        except Exception as e:
            logger.warning(f"Could not initialize Telegram Dispatcher: {e}")

    if app.get("bot"):
        async def on_cleanup(app):
            bot_inst = app.get("bot")
            if bot_inst and hasattr(bot_inst, "session") and hasattr(bot_inst.session, "close"):
                try:
                    res = bot_inst.session.close()
                    if asyncio.iscoroutine(res):
                        await res
                except Exception:
                    pass

        app.on_cleanup.append(on_cleanup)

    # API routes
    app.router.add_options("/{tail:.*}", handle_options)
    app.router.add_get("/api/health", health_check)
    app.router.add_post("/api/auth/login", login_endpoint)
    app.router.add_post("/api/telegram/webhook", telegram_webhook_endpoint)
    app.router.add_post("/api/telegram/set-webhook", set_telegram_webhook_endpoint)
    app.router.add_get("/api/drafts", get_drafts)
    app.router.add_get("/api/drafts/{id}", get_draft_by_id)
    app.router.add_post("/api/drafts", create_draft)
    app.router.add_put("/api/drafts/{id}", update_draft)
    app.router.add_delete("/api/drafts/{id}", delete_draft)
    app.router.add_post("/api/preview", generate_preview)
    app.router.add_post("/api/publish", publish_post_endpoint)

    # Static assets routes if compiled dist exists
    dist_dir = Path(__file__).resolve().parent.parent / "message-builder" / "dist"
    if not dist_dir.exists():
        dist_dir = Path("/app/apps/message-builder/dist")

    if dist_dir.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.router.add_static("/assets", path=str(assets_dir))
        app.router.add_get("/{tail:(?!api).*}", serve_spa_index)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(os.getenv("PORT", 8000))
    app = create_app()
    web.run_app(app, host=None, port=port)
