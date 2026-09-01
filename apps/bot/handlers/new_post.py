"""
New Post Creator Router for Heyaaashu Studio Bot.
Handles /new command, category selection, fast raw text/URL ingestion, and preview generation.
"""

import logging
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from apps.bot.keyboards import get_content_type_keyboard, get_preview_action_keyboard
from packages.ai.extractor import extract_post_schema_from_input
from packages.formatter import format_post_text
from packages.post_schema import ContentType, PostSchema
from packages.shared.db import StudioDatabase

logger = logging.getLogger(__name__)
router = Router()


class CreatePostFSM(StatesGroup):
    choosing_type = State()
    waiting_content = State()
    editing_body = State()
    adding_button = State()
    adding_source = State()


def render_preview_message(post: PostSchema, draft_id: int) -> str:
    """Renders the full preview text including attached buttons and metadata."""
    formatted_text = format_post_text(post, include_header=True)
    
    parts = [
        "👀 <b>POST PREVIEW</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        formatted_text,
        "━━━━━━━━━━━━━━━━━━━━",
    ]

    if post.buttons:
        btn_lines = [f"• <b>[{b.text}]</b> → <code>{b.url}</code>" for b in post.buttons]
        parts.append("🔗 <b>Attached Buttons:</b>\n" + "\n".join(btn_lines))
        parts.append("━━━━━━━━━━━━━━━━━━━━")

    parts.append("<i>Use controls below to edit, improve, or publish:</i>")
    return "\n".join(parts)


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "📝 <b>Create New Post</b>\n\nChoose the content type for your post:",
        parse_mode="HTML",
        reply_markup=get_content_type_keyboard(),
    )
    await state.set_state(CreatePostFSM.choosing_type)


@router.callback_query(F.data.startswith("ctype:"))
async def cb_content_type_selected(callback: CallbackQuery, state: FSMContext):
    ctype_str = callback.data.split(":")[1]
    await state.update_data(content_type=ctype_str)

    type_labels = {
        "ai_news": "🚨 AI News",
        "job": "💼 Job Alert",
        "internship": "🎓 Internship",
        "hackathon": "🏆 Hackathon",
        "ai_tool": "🛠 AI Tool",
        "career": "🧠 Career Insight",
        "resource": "📚 Resource",
    }
    label = type_labels.get(ctype_str, ctype_str.capitalize())

    await callback.message.edit_text(
        f"Selected: <b>{label}</b>\n\n"
        "👉 Please send the raw text, an article URL, or both.\n\n"
        "<i>Heyaaashu AI will instantly extract key facts, headline, source, and buttons.</i>",
        parse_mode="HTML",
    )
    await state.set_state(CreatePostFSM.waiting_content)
    await callback.answer()


@router.message(CreatePostFSM.waiting_content)
async def handle_raw_content_input(message: Message, state: FSMContext, db: StudioDatabase):
    user_input = message.text or message.caption or ""
    if not user_input.strip():
        await message.answer("Please send some text or a valid link to proceed.")
        return

    data = await state.get_data()
    content_type_str = data.get("content_type", "ai_news")
    content_type = ContentType(content_type_str)

    status_msg = await message.answer("⏳ <i>Processing draft...</i>", parse_mode="HTML")

    try:
        # 1. Fast Extraction to PostSchema (< 0.1s)
        post = await extract_post_schema_from_input(content_type, user_input)

        # 2. Save draft to DB
        draft_id = db.save_draft(message.from_user.id, post)
        await state.clear()

        # 3. Format message text for visual preview
        preview_content = render_preview_message(post, draft_id)

        # 4. Remove progress and present preview
        await status_msg.delete()
        await message.answer(
            preview_content,
            parse_mode="HTML",
            reply_markup=get_preview_action_keyboard(draft_id),
            disable_web_page_preview=False,
        )
    except Exception as e:
        logger.error(f"Failed to generate post draft for user {message.from_user.id}: {e}", exc_info=True)
        try:
            await status_msg.edit_text("⚠️ Couldn't generate the draft. Please try again.")
        except Exception:
            await message.answer("⚠️ Couldn't generate the draft. Please try again.")


@router.callback_query(F.data == "action:cancel_creation")
async def cb_cancel_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Action cancelled.", parse_mode="HTML")
    await callback.answer()
