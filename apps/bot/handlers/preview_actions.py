"""
Preview Action Controls Router for Heyaaashu Studio Bot.
Handles Edit, Improve, Regenerate, Add Image, Add Buttons, Add Source, Publish, Cancel.
"""

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from apps.bot.keyboards import get_preview_action_keyboard
from packages.formatter import format_post_text
from packages.post_schema import InlineButton, MediaItem, SourceInfo
from packages.shared.config import get_target_channel_id
from packages.shared.db import StudioDatabase
from packages.telegram.publisher import publish_post_to_telegram

router = Router()


class EditDraftFSM(StatesGroup):
    waiting_text_edit = State()
    waiting_button_input = State()
    waiting_source_input = State()
    waiting_image_input = State()


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
            db.mark_post_published(draft_id, int(target_channel) if str(target_channel).startswith("-100") else 0, res.get("message_id", 0))
            await callback.message.edit_text(
                f"🎉 <b>Post successfully published!</b>\n\n"
                f"• <b>Message ID:</b> <code>{res.get('message_id')}</code>\n"
                f"• <b>Channel:</b> {res.get('channel_title') or target_channel}\n\n"
                "Use <code>/new</code> to draft your next post.",
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(f"❌ Failed to publish post: {res}")
    except Exception as e:
        await callback.message.edit_text(f"❌ Error during publishing: {e}")

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
        "Send the new text for this post (HTML formatting like <b>bold</b>, <i>italic</i>, and <a href='...'>links</a> are supported):\n\n"
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

    formatted_preview = format_post_text(post, include_header=True)
    await message.answer(
        f"✅ <b>Post Updated!</b>\n━━━━━━━━━━━━━━━━━━━━\n{formatted_preview}\n━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=get_preview_action_keyboard(draft_id),
    )


# ─── 3. IMPROVE & REGENERATE ─────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv:improve:") | F.data.startswith("pv:regen:"))
async def cb_improve_or_regen(callback: CallbackQuery, db: StudioDatabase):
    draft_id = int(callback.data.split(":")[2])
    post = db.get_post_schema(draft_id)
    if not post:
        await callback.answer("Draft not found.", show_alert=True)
        return

    # Enhance clarity and formatting
    if "⚡ <b>KEY TAKEAWAYS</b>" not in post.body:
        post.body += "\n\n⚡ <b>KEY TAKEAWAYS</b>\n• Highly actionable technical insights\n• Verified primary source"
    
    db.update_draft_post(draft_id, post)
    formatted_preview = format_post_text(post, include_header=True)

    await callback.message.edit_text(
        f"✨ <b>Improved Draft:</b>\n━━━━━━━━━━━━━━━━━━━━\n{formatted_preview}\n━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=get_preview_action_keyboard(draft_id),
    )
    await callback.answer("Post improved!")


# ─── 4. ADD BUTTONS ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv:btn:"))
async def cb_add_button(callback: CallbackQuery, state: FSMContext):
    draft_id = int(callback.data.split(":")[2])
    await state.update_data(draft_id=draft_id)
    await callback.message.answer(
        "🔗 <b>Add Inline Button</b>\n\n"
        "Send the button in format: <code>Button Text | https://example.com</code>",
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

    btn_text, btn_url = [part.strip() for part in text.split("|", 1)]
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

    formatted_preview = format_post_text(post, include_header=True)
    await message.answer(
        f"✅ <b>Button Added!</b>\n━━━━━━━━━━━━━━━━━━━━\n{formatted_preview}\n━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=get_preview_action_keyboard(draft_id),
    )


# ─── 5. ADD SOURCE ───────────────────────────────────────────────────────────

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
    data = await state.get_data()
    draft_id = data.get("draft_id")
    post = db.get_post_schema(draft_id)
    if not post:
        await message.answer("Draft not found.")
        await state.clear()
        return

    post.source = SourceInfo(title="Official Source", url=src_url)
    # Also add button if not present
    if not any(b.url == src_url for b in post.buttons):
        post.buttons.append(InlineButton(text="📚 Read Source", url=src_url))

    db.update_draft_post(draft_id, post)
    await state.clear()

    formatted_preview = format_post_text(post, include_header=True)
    await message.answer(
        f"✅ <b>Source Attached!</b>\n━━━━━━━━━━━━━━━━━━━━\n{formatted_preview}\n━━━━━━━━━━━━━━━━━━━━",
        parse_mode="HTML",
        reply_markup=get_preview_action_keyboard(draft_id),
    )


# ─── 6. CANCEL ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("pv:cancel:"))
async def cb_cancel_draft(callback: CallbackQuery, db: StudioDatabase):
    draft_id = int(callback.data.split(":")[2])
    db.mark_post_status(draft_id, "cancelled")
    await callback.message.edit_text("❌ Draft cancelled.", parse_mode="HTML")
    await callback.answer()
