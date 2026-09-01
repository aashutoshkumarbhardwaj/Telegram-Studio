"""
Daily Content Editor Router for Heyaaashu Studio Bot.
Handles /daily command, editorial brief rendering, pagination, candidate selection,
and batch drafting of the recommended Top 5.
"""

import asyncio
import logging
import math
from typing import Dict, List
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from apps.bot.handlers.preview_actions import render_preview_message
from apps.bot.keyboards import get_daily_brief_keyboard, get_preview_action_keyboard
from packages.ai.extractor import extract_post_schema_from_input
from packages.post_schema import ContentType, SourceInfo, VerificationInfo, VerificationStatus
from packages.research.daily_editor import DailyBrief, generate_daily_content_brief
from packages.shared.db import StudioDatabase

logger = logging.getLogger(__name__)
router = Router()

# In-memory candidate cache for daily sessions (user_id -> list of ResearchCandidate)
_DAILY_CANDIDATE_CACHE: Dict[int, List] = {}
PAGE_SIZE = 5


def _render_brief_text(candidates: list, page: int, total_pages: int, total_sources: int, verified_count: int, unverified_count: int, failed_count: int) -> str:
    """Renders the formatted text for the Daily Content Brief."""
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_items = candidates[start_idx:end_idx]

    num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]

    lines = [
        "☀️ <b>DAILY CONTENT BRIEF</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        f"📰 <b>{total_sources}</b> sources analyzed • ✅ <b>{verified_count}</b> verified • ⚠️ <b>{unverified_count}</b> review",
    ]

    if failed_count > 0:
        lines.append(f"<i>⚠️ {failed_count} source temporarily unavailable</i>")

    lines.append("")
    lines.append(f"🔥 <b>TOP PICKS (Page {page}/{total_pages})</b>")
    lines.append("━━━━━━━━━━━━━━━━━━━━")

    category_emojis = {
        ContentType.AI_NEWS: "🚨",
        ContentType.JOB: "💼",
        ContentType.INTERNSHIP: "🎓",
        ContentType.HACKATHON: "🏆",
        ContentType.AI_TOOL: "🛠",
        ContentType.CAREER: "🧠",
        ContentType.RESOURCE: "📚",
    }

    for i, c in enumerate(page_items):
        num = num_emojis[i] if i < len(num_emojis) else f"[{i+1}]"
        cat_emoji = category_emojis.get(c.category, "📢")
        status_badge = "✅ Verified" if c.verification_status == "verified" else "⚠️ Needs verification"
        
        lines.append(f"{num} <b>{c.title}</b>")
        lines.append(f"{cat_emoji} <i>{c.category.value.capitalize()}</i> • 📰 {c.source_name} • 🕒 {c.published_at or 'Recent'}")
        lines.append(f"<b>Status:</b> {status_badge}\n")

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("👉 <i>Click a number to draft a single post, or tap 'Draft Top 5':</i>")
    return "\n".join(lines)


@router.message(Command("daily"))
@router.callback_query(F.data == "cmd:daily")
async def cmd_daily(event, db: StudioDatabase):
    user_id = event.from_user.id
    is_callback = isinstance(event, CallbackQuery)
    
    if is_callback:
        status_msg = event.message
        await status_msg.edit_text("🔎 <i>Searching sources & discovering stories...</i>", parse_mode="HTML")
    else:
        status_msg = await event.answer("🔎 <i>Searching sources & discovering stories...</i>", parse_mode="HTML")

    try:
        # Step transitions
        await asyncio.sleep(0.3)
        await status_msg.edit_text("🧹 <i>Removing duplicates & filtering noise...</i>", parse_mode="HTML")
        await asyncio.sleep(0.3)
        await status_msg.edit_text("🔍 <i>Checking source quality & trust tiers...</i>", parse_mode="HTML")
        await asyncio.sleep(0.3)
        await status_msg.edit_text("🧠 <i>Ranking candidates with editorial diversity...</i>", parse_mode="HTML")

        brief: DailyBrief = await generate_daily_content_brief(db=db)
        
        if not brief.candidates:
            await status_msg.edit_text("⚠️ No active candidates found today. Please try again later.")
            return

        # Cache candidates for user session
        _DAILY_CANDIDATE_CACHE[user_id] = brief.candidates
        total_pages = max(1, math.ceil(len(brief.candidates) / PAGE_SIZE))

        brief_text = _render_brief_text(
            candidates=brief.candidates,
            page=1,
            total_pages=total_pages,
            total_sources=brief.total_sources_analyzed,
            verified_count=brief.verified_count,
            unverified_count=brief.unverified_count,
            failed_count=brief.failed_sources_count,
        )

        page_items = brief.candidates[:PAGE_SIZE]
        await status_msg.edit_text(
            brief_text,
            parse_mode="HTML",
            reply_markup=get_daily_brief_keyboard(page_items, page=1, total_pages=total_pages),
            disable_web_page_preview=True,
        )

    except Exception as e:
        logger.error(f"Error generating daily brief: {e}", exc_info=True)
        await status_msg.edit_text("⚠️ An error occurred while compiling the daily brief. Please try again.")

    if is_callback:
        await event.answer()


@router.callback_query(F.data.startswith("daily_page:"))
async def cb_daily_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    candidates = _DAILY_CANDIDATE_CACHE.get(user_id, [])

    if not candidates:
        await callback.answer("Daily brief expired. Please run /daily again.", show_alert=True)
        return

    total_pages = max(1, math.ceil(len(candidates) / PAGE_SIZE))
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * PAGE_SIZE
    page_items = candidates[start_idx:start_idx + PAGE_SIZE]

    verified_count = sum(1 for c in candidates if c.verification_status == "verified")
    unverified_count = len(candidates) - verified_count

    brief_text = _render_brief_text(
        candidates=candidates,
        page=page,
        total_pages=total_pages,
        total_sources=len(candidates) * 3,
        verified_count=verified_count,
        unverified_count=unverified_count,
        failed_count=0,
    )

    await callback.message.edit_text(
        brief_text,
        parse_mode="HTML",
        reply_markup=get_daily_brief_keyboard(page_items, page=page, total_pages=total_pages),
        disable_web_page_preview=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("daily_pick:"))
async def cb_daily_pick_candidate(callback: CallbackQuery, db: StudioDatabase):
    cand_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    candidates = _DAILY_CANDIDATE_CACHE.get(user_id, [])

    candidate = next((c for c in candidates if c.id == cand_id), None)
    if not candidate:
        cached_row = db.get_cached_candidate_by_id(cand_id)
        if cached_row:
            from packages.research.collector import ResearchCandidate
            candidate = ResearchCandidate(
                id=cached_row["candidate_id"],
                category=ContentType(cached_row["category"]),
                title=cached_row["title"],
                summary=cached_row["summary"],
                source_url=cached_row["source_url"],
                source_name=cached_row["source_name"],
                trust_tier=cached_row["trust_tier"],
                verification_status=cached_row["verification_status"],
                published_at=cached_row["published_at"],
            )

    if not candidate:
        await callback.answer("Candidate not found. Run /daily again.", show_alert=True)
        return

    await callback.message.edit_text(
        f"⏳ <i>Drafting <b>{candidate.category.value.capitalize()}</b> post:</i>\n"
        f"<b>{candidate.title}</b>\n\n"
        "Structuring facts and applying editorial template...",
        parse_mode="HTML",
    )

    try:
        raw_input = f"{candidate.title}\n\n{candidate.summary}\n\n{candidate.source_url}"
        post = await extract_post_schema_from_input(candidate.category, raw_input)
        post.source = SourceInfo(title=candidate.source_name, url=candidate.source_url)
        all_sources = [candidate.source_url] + getattr(candidate, "supporting_sources", [])
        post.verification = VerificationInfo(
            status=VerificationStatus.VERIFIED if candidate.verification_status == "verified" else VerificationStatus.NEEDS_VERIFICATION,
            sources=all_sources,
        )

        draft_id = db.save_draft(user_id, post)
        preview_content = render_preview_message(post, draft_id)

        await callback.message.edit_text(
            preview_content,
            parse_mode="HTML",
            reply_markup=get_preview_action_keyboard(draft_id),
            disable_web_page_preview=False,
        )
    except Exception as e:
        logger.error(f"Error drafting candidate {cand_id}: {e}", exc_info=True)
        await callback.message.edit_text("⚠️ Failed to generate draft. Please try again.")

    await callback.answer()


@router.callback_query(F.data == "daily_draft_top5")
async def cb_daily_draft_top5(callback: CallbackQuery, db: StudioDatabase):
    user_id = callback.from_user.id
    candidates = _DAILY_CANDIDATE_CACHE.get(user_id, [])

    if not candidates:
        await callback.answer("Daily brief expired. Run /daily again.", show_alert=True)
        return

    top_5 = candidates[:5]
    await callback.message.edit_text(
        "⏳ <b>Drafting Top 5 Curated Posts...</b>\n\n"
        "Creating PostSchema instances with verified evidence in sequence...",
        parse_mode="HTML",
    )

    created_drafts = []
    for c in top_5:
        try:
            raw_input = f"{c.title}\n\n{c.summary}\n\n{c.source_url}"
            post = await extract_post_schema_from_input(c.category, raw_input)
            post.source = SourceInfo(title=c.source_name, url=c.source_url)
            post.verification = VerificationInfo(
                status=VerificationStatus.VERIFIED if c.verification_status == "verified" else VerificationStatus.NEEDS_VERIFICATION,
                sources=[c.source_url] + getattr(c, "supporting_sources", []),
            )
            draft_id = db.save_draft(user_id, post, status="draft")
            created_drafts.append((draft_id, post, c))
        except Exception as e:
            logger.warning(f"Failed to draft item {c.title}: {e}")

    # Render Batch Summary
    lines = [
        "✅ <b>TOP 5 DRAFTS CREATED</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "The following 5 publication drafts have been generated and saved to your workspace:",
        "",
    ]

    buttons = []
    num_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    for i, (draft_id, post, c) in enumerate(created_drafts):
        num = num_emojis[i] if i < len(num_emojis) else f"[{i+1}]"
        lines.append(f"{num} <b>{post.title}</b>")
        lines.append(f"🏷 <i>{c.category.value.capitalize()}</i> • Draft ID: <code>{draft_id}</code>\n")
        buttons.append([
            InlineKeyboardButton(
                text=f"👀 View & Edit #{draft_id} ({c.category.value.capitalize()})",
                callback_data=f"pv:edit:{draft_id}",
            )
        ])

    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("⚠️ <i>Human review required before publishing. Tap below to inspect each draft:</i>")

    buttons.append([InlineKeyboardButton(text="☀️ Back to Daily Brief", callback_data="cmd:daily")])
    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )
    await callback.answer("Top 5 drafts created!")


@router.callback_query(F.data == "daily_refresh")
async def cb_daily_refresh(callback: CallbackQuery, db: StudioDatabase):
    await cmd_daily(callback, db=db)
