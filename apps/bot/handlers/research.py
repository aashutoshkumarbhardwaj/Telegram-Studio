"""
Research Router for Heyaaashu Studio Bot.
Handles /research command, category selection, pipeline generation, and human approval flow.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from apps.bot.keyboards import get_research_category_keyboard, get_preview_action_keyboard
from packages.ai.pipeline import run_ai_research_pipeline
from packages.formatter import format_post_text
from packages.post_schema import ContentType
from packages.shared.db import StudioDatabase

router = Router()


@router.message(Command("research"))
async def cmd_research(message: Message):
    await message.answer(
        "🔍 <b>AI Research Studio</b>\n\n"
        "Select a domain to research, extract verified facts, and generate a draft:",
        parse_mode="HTML",
        reply_markup=get_research_category_keyboard(),
    )


@router.callback_query(F.data.startswith("res:"))
async def cb_run_research_category(callback: CallbackQuery, db: StudioDatabase):
    cat_key = callback.data.split(":")[1]
    
    category_map = {
        "ai_news": (ContentType.AI_NEWS, "Next-Gen Foundation Models & Reasoning Architecture"),
        "job": (ContentType.JOB, "Staff Machine Learning Engineer — Distributed Training"),
        "internship": (ContentType.INTERNSHIP, "AI Research Summer Fellowship"),
        "hackathon": (ContentType.HACKATHON, "Global Generative AI Agent Hackathon 2026"),
        "ai_tool": (ContentType.AI_TOOL, "FastRL: High-throughput Reinforcement Learning Framework"),
        "github": (ContentType.AI_TOOL, "Trending GitHub Repositories in AI & Automation"),
        "career": (ContentType.CAREER, "Transitioning from Software Engineering to AI Engineering in 2026"),
    }
    
    ctype, default_topic = category_map.get(cat_key, (ContentType.AI_NEWS, "Trending AI Intelligence"))

    await callback.message.edit_text(
        f"⏳ <i>Running AI research pipeline for <b>{ctype.value.capitalize()}</b>...</i>\n"
        "Extracting verified facts and formatting draft...",
        parse_mode="HTML",
    )

    try:
        # Run AI Research Pipeline
        post = await run_ai_research_pipeline(topic=default_topic, content_type=ctype)

        # Save to DB as draft
        draft_id = db.save_draft(callback.from_user.id, post)

        # Format message preview
        formatted_preview = format_post_text(post, include_header=True)

        preview_header = "🔍 <b>RESEARCH POST READY (Pending Approval)</b>\n━━━━━━━━━━━━━━━━━━━━\n"
        preview_footer = "\n━━━━━━━━━━━━━━━━━━━━\n<i>Review the extracted facts below before publishing:</i>"

        await callback.message.edit_text(
            f"{preview_header}{formatted_preview}{preview_footer}",
            parse_mode="HTML",
            reply_markup=get_preview_action_keyboard(draft_id),
            disable_web_page_preview=False,
        )
    except Exception as e:
        await callback.message.edit_text(f"❌ Research pipeline failed: {e}")

    await callback.answer()
