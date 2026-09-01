"""
Centralized Configuration Loader for Heyaaashu Studio.
Automatically checks root .env, apps/telegram-publisher/.env, and apps/ai-content/.env.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Search for env files in logical order
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATHS = [
    ROOT_DIR / ".env",
    ROOT_DIR / "apps" / "telegram-publisher" / ".env",
    ROOT_DIR / "apps" / "ai-content" / ".env",
]

for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)


# --- Telegram Bot Config ---
BOT_TOKEN: str = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or ""
ADMIN_CHAT_ID: int = int(os.getenv("ADMIN_CHAT_ID") or "8982444793")
TARGET_CHANNEL_ID: str = os.getenv("TARGET_CHANNEL_ID") or "-1003756584531"

# --- Database ---
DATABASE_PATH: str = os.getenv(
    "DATABASE_PATH",
    str(ROOT_DIR / "apps" / "telegram-publisher" / "posting_bot.db"),
)

# --- LLM & AI ---
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").strip().lower()
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o")

# --- Language ---
LANGUAGE: str = os.getenv("LANGUAGE", os.getenv("CONTENT_LANGUAGE", "en"))
CONTENT_LANGUAGE: str = os.getenv("CONTENT_LANGUAGE", LANGUAGE)

# --- Studio Authentication & Security ---
STUDIO_AUTH_TOKEN: str = os.getenv("STUDIO_AUTH_TOKEN", "").strip()
SESSION_SECRET: str = os.getenv("SESSION_SECRET", "").strip()
ALLOWED_ORIGINS: list[str] = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost,http://127.0.0.1").split(",") if o.strip()
]


def get_target_channel_id() -> str:
    """Returns the target channel ID/username configured for publishing."""
    return TARGET_CHANNEL_ID or "-1003756584531"
