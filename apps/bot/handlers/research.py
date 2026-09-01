"""
Research Router for Heyaaashu Studio Bot.
Handles /research command, live source collection, deduplication, ranking,
candidate selection, AI post drafting, preview, and publication.
"""

import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from apps.bot.handlers.preview_actions import render_preview_message
from apps.bot.keyboards import (
    get_preview_action_keyboard,
    get_research_candidates_keyboard,
    get_research_category_keyboard,
)
from packages.ai.extractor import extract_post_schema_from_input
from packages.post_schema import ContentType
from packages.research.dedup_rank import collect_and_rank_candidates
from packages.shared.db import StudioDatabase

logger = logging.getLogger(__name__)
router = Router()

# In-memory candidate cache for active sessions (user_id -> {cand_id: cand_dict})
_CANDIDATE_CACHE = {}


class ResearchFSM(StatesGroup):
    browsing_candidates = State()


@router.message(Command("research"))
async def cmd_research(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🔍 <b>AI Research Studio</b>\n\n"
        "Select a domain to research, extract verified facts, and generate a post draft:",
        parse_mode="HTML",
        reply_markup=get_research_category_keyboard(),
    )


@router.callback_query(F.data.startswith("res_cat:"))
async def cb_research_category_selected(callback: CallbackQuery, state: FSMContext):
    cat_key = callback.data.split(":")[1]

    category_map = {
        "ai_news": (ContentType.AI_NEWS, "AI News"),
        "job": (ContentType.JOB, "Jobs & Hiring"),
        "internship": (ContentType.INTERNSHIP, "Internships"),
        "hackathon": (ContentType.HACKATHON, "Hackathons"),
        "ai_tool": (ContentType.AI_TOOL, "AI Tools"),
        "career": (ContentType.CAREER, "Career Insights"),
        "resource": (ContentType.RESOURCE, "Resources"),
    }

    ctype, label = category_map.get(cat_key, (ContentType.AI_NEWS, "AI News"))

    await callback.message.edit_text(
        f"🔍 <i>Collecting, deduplicating, and ranking current <b>{label}</b> sources...</i>",
        parse_mode="HTML",
    )

    try:
        candidates = await collect_and_rank_candidates(ctype, limit=3)

        if not candidates:
            await callback.message.edit_text(
                f"⚠️ No active candidates found for <b>{label}</b> right now.\n"
                "Please try another domain or refresh.",
                parse_mode="HTML",
                reply_markup=get_research_category_keyboard(),
            )
            await callback.answer()
            return

        # Cache candidates for user
        user_id = callback.from_user.id
        _CANDIDATE_CACHE[user_id] = {c.id: c for c in candidates}

        number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        body_lines = [
            f"🔍 <b>AI Research Candidates — {label}</b>",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        for i, c in enumerate(candidates):
            num = number_emojis[i] if i < len(number_emojis) else f"{i+1}."
            snippet = c.summary.splitlines()[0] if c.summary else c.title
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            body_lines.append(f"{num} <b>{c.title}</b>")
            body_lines.append(f"<i>{snippet}</i>")
            body_lines.append(f"🔗 Source: <code>{c.source_name}</code>\n")

        body_lines.append("━━━━━━━━━━━━━━━━━━━━")
        body_lines.append("👉 <i>Select a topic below to generate a publication-ready draft:</i>")

        text_content = "\n".join(body_lines)
        await callback.message.edit_text(
            text_content,
            parse_mode="HTML",
            reply_markup=get_research_candidates_keyboard(candidates, cat_key),
            disable_web_page_preview=True,
        )
        await state.set_state(ResearchFSM.browsing_candidates)

    except Exception as e:
        logger.error(f"Research source collection failed: {e}", exc_info=True)
        await callback.message.edit_text(
            "⚠️ Couldn't fetch research sources. Please try again.",
            reply_markup=get_research_category_keyboard(),
        )

    await callback.answer()


@router.callback_query(F.data.startswith("res_pick:"))
async def cb_research_candidate_picked(callback: CallbackQuery, state: FSMContext, db: StudioDatabase):
    cand_id = callback.data.split(":")[1]
    user_id = callback.from_user.id

    user_cands = _CANDIDATE_CACHE.get(user_id, {})
    candidate = user_cands.get(cand_id)

    if not candidate:
        await callback.answer("Candidate session expired. Please re-run /research.", show_alert=True)
        return

    await callback.message.edit_text(
        f"⏳ <i>AI writing <b>{candidate.category.value.capitalize()}</b> post for:</i>\n"
        f"<b>{candidate.title}</b>\n\n"
        "Structuring facts and applying editorial template...",
        parse_mode="HTML",
    )

    try:
        # Build composite raw input
        raw_input = f"{candidate.title}\n\n{candidate.summary}\n\n{candidate.source_url}"

        # Fast structured extraction into PostSchema
        post = await extract_post_schema_from_input(candidate.category, raw_input)

        # Save draft to DB
        draft_id = db.save_draft(user_id, post)
        await state.clear()

        # Format preview
        preview_content = render_preview_message(post, draft_id)

        await callback.message.edit_text(
            preview_content,
            parse_mode="HTML",
            reply_markup=get_preview_action_keyboard(draft_id),
            disable_web_page_preview=False,
        )

    except Exception as e:
        logger.error(f"Failed to generate post from candidate {cand_id}: {e}", exc_info=True)
        await callback.message.edit_text(
            "⚠️ Couldn't generate post from this candidate. Please try again.",
            reply_markup=get_research_category_keyboard(),
        )

    await callback.answer()
