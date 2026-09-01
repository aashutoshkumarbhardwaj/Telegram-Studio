"""
Preview Action Controls Router for Heyaaashu Studio Bot.
Handles Edit, Improve, Regenerate, Add Image, Add Buttons, Add Source, Publish, Cancel.
"""

import logging
from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from apps.bot.keyboards import get_preview_action_keyboard
from packages.ai.extractor import improve_post_schema, regenerate_post_schema
from packages.formatter import format_post_text
from packages.post_schema import InlineButton, MediaItem, PostSchema, SourceInfo
from packages.shared.config import get_target_channel_id
from packages.shared.db import StudioDatabase
from packages.telegram.publisher import publish_post_to_telegram

logger = logging.getLogger(__name__)
router = Router()


class EditDraftFSM(StatesGroup):
    waiting_text_edit = State()
    waiting_button_input = State()
    waiting_source_input = State()
    waiting_image_input = State()


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


async def safe_edit_preview_message(callback: CallbackQuery, text: str, draft_id: int):
    """Safely updates the preview message ignoring 'message is not modified' errors."""
    try:
        await callback.message.edit_text(
            text,
            parse_mode="HTML",
            reply_markup=get_preview_action_keyboard(draft_id),
            disable_web_page_preview=False,
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        else:
            raise e


# ─── 1. PUBLISH ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv:pub:"))
async def cb_publish_draft(callback: CallbackQuery, bot: Bot, db: StudioDatabase):
    draft_id = int(callback.data.split(":")[2])
    post = db.get_post_schema(draft_id)
    if not post:
        await callback.answer("❌ Draft not found.", show_alert=True)
        return

    target_channel = get_target_channel_id()
    await callback.message.edit_text("📡 <i>Publishing post to channel...</i>", parse_mode="HTML")

    try:
        res = await publish_post_to_telegram(post, bot=bot, channel_id=target_channel)
        if res.get("success"):
            db.mark_post_published(
                draft_id,
                int(target_channel) if str(target_channel).startswith("-100") else 0,
                res.get("message_id", 0),
            )
            await callback.message.edit_text(
                f"✅ <b>Published to Channel</b>\n\n"
                f"• <b>Message ID:</b> <code>{res.get('message_id')}</code>\n"
                f"• <b>Channel:</b> {res.get('channel_title') or target_channel}\n\n"
                "Use <code>/new</code> to draft your next post.",
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(f"❌ Failed to publish post: {res}")
    except Exception as e:
        logger.error(f"Error publishing post draft {draft_id}: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ <b>Publishing Error</b>\n\n"
            "An error occurred while publishing to the channel. Please check channel permissions.",
            parse_mode="HTML",
        )

    await callback.answer()


# ─── 2. EDIT ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv:edit:"))
async def cb_edit_draft(callback: CallbackQuery, state: FSMContext, db: StudioDatabase):
    draft_id = int(callback.data.split(":")[2])
    post = db.get_post_schema(draft_id)
    if not post:
        await callback.answer("❌ Draft not found.", show_alert=True)
        return

    await state.update_data(draft_id=draft_id)
    await callback.message.answer(
        "✏️ <b>Edit Post Content</b>\n\n"
        "Send the new text/body for this post (HTML formatting like <b>bold</b>, <i>italic</i>, and <a href='...'>links</a> are supported):\n\n"
        f"<i>Current Body:</i>\n<code>{post.body}</code>",
        parse_mode="HTML",
    )
    await state.set_state(EditDraftFSM.waiting_text_edit)
    await callback.answer()


@router.message(EditDraftFSM.waiting_text_edit)
async def handle_edit_text_submit(message: Message, state: FSMContext, db: StudioDatabase):
    new_text = message.text or message.caption or ""
    if not new_text.strip():
        await message.answer("Please send some text.")
        return

    data = await state.get_data()
    draft_id = data.get("draft_id")
    post = db.get_post_schema(draft_id)
    if not post:
        await message.answer("Draft expired. Please start over with /new.")
        await state.clear()
        return

    post.body = new_text.strip()
    db.update_draft_post(draft_id, post)
    await state.clear()

    preview_content = render_preview_message(post, draft_id)
    await message.answer(
        preview_content,
        parse_mode="HTML",
        reply_markup=get_preview_action_keyboard(draft_id),
        disable_web_page_preview=False,
    )


# ─── 3. IMPROVE & REGENERATE ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv:improve:"))
async def cb_improve_post(callback: CallbackQuery, db: StudioDatabase):
    draft_id = int(callback.data.split(":")[2])
    post = db.get_post_schema(draft_id)
    if not post:
        await callback.answer("Draft not found.", show_alert=True)
        return

    post = improve_post_schema(post)
    db.update_draft_post(draft_id, post)
    preview_content = render_preview_message(post, draft_id)
    await safe_edit_preview_message(callback, preview_content, draft_id)
    await callback.answer("Post improved!")


@router.callback_query(F.data.startswith("pv:regen:"))
async def cb_regenerate_post(callback: CallbackQuery, db: StudioDatabase):
    draft_id = int(callback.data.split(":")[2])
    post = db.get_post_schema(draft_id)
    if not post:
        await callback.answer("Draft not found.", show_alert=True)
        return

    post = regenerate_post_schema(post)
    db.update_draft_post(draft_id, post)
    preview_content = render_preview_message(post, draft_id)
    await safe_edit_preview_message(callback, preview_content, draft_id)
    await callback.answer("Post regenerated!")


# ─── 4. ADD IMAGE ────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv:image:"))
async def cb_add_image(callback: CallbackQuery, state: FSMContext):
    draft_id = int(callback.data.split(":")[2])
    await state.update_data(draft_id=draft_id)
    await callback.message.answer(
        "🖼 <b>Add Image to Post</b>\n\n"
        "Send an image URL (e.g. <code>https://example.com/banner.png</code>) or send a photo directly:",
        parse_mode="HTML",
    )
    await state.set_state(EditDraftFSM.waiting_image_input)
    await callback.answer()


@router.message(EditDraftFSM.waiting_image_input)
async def handle_image_submit(message: Message, state: FSMContext, db: StudioDatabase):
    image_source = None
    if message.photo:
        image_source = message.photo[-1].file_id
    elif message.text and (message.text.startswith("http://") or message.text.startswith("https://")):
        image_source = message.text.strip()
    else:
        await message.answer("Please send a valid image URL or upload a photo.")
        return

    data = await state.get_data()
    draft_id = data.get("draft_id")
    post = db.get_post_schema(draft_id)
    if not post:
        await message.answer("Draft not found.")
        await state.clear()
        return

    post.media = [MediaItem(type="photo", url_or_path=image_source, file_id=image_source)]
    db.update_draft_post(draft_id, post)
    await state.clear()

    preview_content = render_preview_message(post, draft_id)
    if message.photo:
        await message.answer_photo(
            photo=image_source,
            caption=preview_content,
            parse_mode="HTML",
            reply_markup=get_preview_action_keyboard(draft_id),
        )
    else:
        await message.answer(
            preview_content,
            parse_mode="HTML",
            reply_markup=get_preview_action_keyboard(draft_id),
            disable_web_page_preview=False,
        )


# ─── 5. ADD BUTTONS ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv:btn:"))
async def cb_add_button(callback: CallbackQuery, state: FSMContext):
    draft_id = int(callback.data.split(":")[2])
    await state.update_data(draft_id=draft_id)
    await callback.message.answer(
        "🔗 <b>Add Inline Button</b>\n\n"
        "Send the button in format:\n"
        "<code>Button Text | https://example.com</code>\n\n"
        "<i>Example: 💬 Discuss | https://t.me/heyaaahu</i>",
        parse_mode="HTML",
    )
    await state.set_state(EditDraftFSM.waiting_button_input)
    await callback.answer()


@router.message(EditDraftFSM.waiting_button_input)
async def handle_button_submit(message: Message, state: FSMContext, db: StudioDatabase):
    text = message.text or ""
    if "|" not in text:
        await message.answer("Format must be: <code>Text | https://url</code>\nTry again:")
        return

    parts = [part.strip() for part in text.split("|", 1)]
    btn_text, btn_url = parts[0], parts[1]

    data = await state.get_data()
    draft_id = data.get("draft_id")
    post = db.get_post_schema(draft_id)
    if not post:
        await message.answer("Draft not found.")
        await state.clear()
        return

    post.buttons.append(InlineButton(text=btn_text, url=btn_url))
    db.update_draft_post(draft_id, post)
    await state.clear()

    preview_content = render_preview_message(post, draft_id)
    await message.answer(
        preview_content,
        parse_mode="HTML",
        reply_markup=get_preview_action_keyboard(draft_id),
        disable_web_page_preview=False,
    )


# ─── 6. ADD SOURCE ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv:src:"))
async def cb_add_source(callback: CallbackQuery, state: FSMContext):
    draft_id = int(callback.data.split(":")[2])
    await state.update_data(draft_id=draft_id)
    await callback.message.answer(
        "📚 <b>Add Source URL</b>\n\nSend the source link (e.g. <code>https://blog.google/</code>):",
        parse_mode="HTML",
    )
    await state.set_state(EditDraftFSM.waiting_source_input)
    await callback.answer()


@router.message(EditDraftFSM.waiting_source_input)
async def handle_source_submit(message: Message, state: FSMContext, db: StudioDatabase):
    src_url = (message.text or "").strip()
    if not (src_url.startswith("http://") or src_url.startswith("https://")):
        await message.answer("Please send a valid URL starting with http:// or https://")
        return

    data = await state.get_data()
    draft_id = data.get("draft_id")
    post = db.get_post_schema(draft_id)
    if not post:
        await message.answer("Draft not found.")
        await state.clear()
        return

    post.source = SourceInfo(title="Official Source", url=src_url)
    if not any(b.url == src_url for b in post.buttons):
        post.buttons.insert(0, InlineButton(text="📚 Read Source", url=src_url))

    db.update_draft_post(draft_id, post)
    await state.clear()

    preview_content = render_preview_message(post, draft_id)
    await message.answer(
        preview_content,
        parse_mode="HTML",
        reply_markup=get_preview_action_keyboard(draft_id),
        disable_web_page_preview=False,
    )


# ─── 7. CANCEL ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv:cancel:"))
async def cb_cancel_draft(callback: CallbackQuery, db: StudioDatabase):
    draft_id = int(callback.data.split(":")[2])
    db.mark_post_status(draft_id, "cancelled")
    await callback.message.edit_text("❌ Draft cancelled.", parse_mode="HTML")
    await callback.answer()
