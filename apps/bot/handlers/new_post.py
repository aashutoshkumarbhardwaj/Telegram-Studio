"""
New Post Creator Router for Heyaaashu Studio Bot.
Handles /new command, category selection, raw text/URL ingestion, and preview generation.
"""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from apps.bot.keyboards import get_content_type_keyboard, get_preview_action_keyboard
from packages.ai.extractor import extract_post_schema_from_input
from packages.formatter import format_post_text
from packages.post_schema import ContentType
from packages.shared.db import StudioDatabase

router = Router()


class CreatePostFSM(StatesGroup):
    choosing_type = State()
    waiting_content = State()
    editing_body = State()
    adding_button = State()
    adding_source = State()


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
        "<i>Heyaaashu AI will automatically extract key facts, headline, source, and buttons.</i>",
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

    status_msg = await message.answer("⚙️ <i>Extracting facts & structuring post draft...</i>", parse_mode="HTML")

    # 1. AI / Heuristic Extraction to PostSchema
    try:
        post = await extract_post_schema_from_input(content_type, user_input)
    except Exception as e:
        await status_msg.edit_text(f"❌ Error generating post draft: {e}")
        return

    # 2. Save draft to DB
    draft_id = db.save_draft(message.from_user.id, post)
    await state.clear()

    # 3. Format message text for visual preview
    formatted_preview = format_post_text(post, include_header=True)

    # 4. Display Post Preview with action controls
    preview_header = "👀 <b>POST PREVIEW</b>\n━━━━━━━━━━━━━━━━━━━━\n"
    preview_footer = "\n━━━━━━━━━━━━━━━━━━━━\n<i>Review your post draft below and select an action:</i>"

    await status_msg.delete()
    await message.answer(
        f"{preview_header}{formatted_preview}{preview_footer}",
        parse_mode="HTML",
        reply_markup=get_preview_action_keyboard(draft_id),
        disable_web_page_preview=False,
    )


@router.callback_query(F.data == "action:cancel_creation")
async def cb_cancel_creation(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Action cancelled.", parse_mode="HTML")
    await callback.answer()
