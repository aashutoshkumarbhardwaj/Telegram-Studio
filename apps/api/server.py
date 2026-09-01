"""
Heyaaashu Studio Backend API Server.
Provides canonical PostSchema validation, draft management, formatting, preview, and publishing endpoints.
Built on aiohttp.web with authentication middleware, origin restriction, and zero external dependencies.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from aiohttp import web
from pydantic import ValidationError

from packages.formatter import format_post_text, generate_telegram_payload, validate_telegram_constraints
from packages.post_schema import PostSchema
from packages.shared.config import (
    ALLOWED_ORIGINS,
    BOT_TOKEN,
    STUDIO_AUTH_TOKEN,
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
        "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Studio-Auth, Accept",
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
    """Enforces authentication across all protected studio API endpoints."""
    if request.method == "OPTIONS":
        return await handler(request)

    # Public unauthenticated endpoints
    if request.path in ["/api/health", "/api/auth/login"]:
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
    """GET /api/health — Health check endpoint for Docker & reverse proxy."""
    return web.json_response({
        "status": "healthy",
        "service": "heyaaashu-studio-api",
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
        row = conn.cursor().execute("SELECT status, post_id, created_at FROM posts WHERE post_id = ?", (draft_id,)).fetchone()
        status = row["status"] if row else "draft"

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
        conn.cursor().execute("DELETE FROM posts WHERE post_id = ?", (draft_id,))
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


def create_app(db: Optional[StudioDatabase] = None) -> web.Application:
    """Creates the aiohttp web application with authentication and CORS."""
    app = web.Application(middlewares=[auth_middleware])
    app["db"] = db or StudioDatabase()

    app.router.add_options("/{tail:.*}", handle_options)
    app.router.add_get("/api/health", health_check)
    app.router.add_post("/api/auth/login", login_endpoint)
    app.router.add_get("/api/drafts", get_drafts)
    app.router.add_get("/api/drafts/{id}", get_draft_by_id)
    app.router.add_post("/api/drafts", create_draft)
    app.router.add_put("/api/drafts/{id}", update_draft)
    app.router.add_delete("/api/drafts/{id}", delete_draft)
    app.router.add_post("/api/preview", generate_preview)
    app.router.add_post("/api/publish", publish_post_endpoint)

    return app


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app = create_app()
    web.run_app(app, host=None, port=8000)
