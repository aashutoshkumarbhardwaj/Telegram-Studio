"""
Heyaaashu Studio — Single Unified Telegram Bot Process.
There is exactly ONE update receiver for @Heyaashu_bot.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Ensure monorepo root is on sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from apps.bot.handlers.daily import router as daily_router
from apps.bot.handlers.new_post import router as new_post_router
from apps.bot.handlers.preview_actions import router as preview_actions_router
from apps.bot.handlers.research import router as research_router
from apps.bot.handlers.start import router as start_router
from packages.shared.config import BOT_TOKEN
from packages.shared.db import StudioDatabase

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("HeyaaashuBot")


async def start_bot():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("BOT_TOKEN is not configured in .env!")
        return

    logger.info("Initializing Heyaaashu Studio Database...")
    db = StudioDatabase()

    logger.info("Initializing Telegram Bot and Dispatcher...")
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Context injection for handlers
    dp.workflow_data.update(db=db)

    # Register routers
    dp.include_router(start_router)
    dp.include_router(daily_router)
    dp.include_router(new_post_router)
    dp.include_router(preview_actions_router)
    dp.include_router(research_router)

    logger.info("Registered routers: start, daily, new_post, preview_actions, research.")

    try:
        # Drop pending updates so old messages don't spam
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("🚀 Heyaaashu Studio Bot polling started! (Single receiver)")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Heyaaashu Studio Bot session closed.")


def main():
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")


if __name__ == "__main__":
    main()
