"""
Lightweight In-Process Background Scheduler for Heyaaashu Studio.
Periodically polls database for due scheduled posts, acquires them atomically,
and publishes them via the existing Telegram publisher without external dependencies (Celery/Redis).
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from packages.post_schema import PostSchema
from packages.shared.db import StudioDatabase
from packages.telegram.publisher import publish_post_to_telegram
from packages.shared.config import get_target_channel_id

logger = logging.getLogger(__name__)


class PublisherScheduler:
    def __init__(
        self,
        db: StudioDatabase,
        publish_fn: Optional[Callable] = None,
        poll_interval: float = 15.0,
        stale_threshold_seconds: int = 300,
    ):
        self.db = db
        self.publish_fn = publish_fn or publish_post_to_telegram
        self.poll_interval = poll_interval
        self.stale_threshold_seconds = stale_threshold_seconds
        self._task: Optional[asyncio.Task] = None
        self._is_running = False

    async def start(self):
        """Starts the background scheduling worker loop."""
        if self._is_running:
            return
        self._is_running = True
        logger.info(f"Starting PublisherScheduler with poll_interval={self.poll_interval}s")

        # Recover any stale publishing posts left from previous crash or restart
        try:
            recovered = self.db.recover_stale_publishing_posts(self.stale_threshold_seconds)
            if recovered > 0:
                logger.warning(f"PublisherScheduler recovered {recovered} stale post(s) back to 'scheduled'.")
        except Exception as e:
            logger.error(f"Error during startup recovery: {e}", exc_info=True)

        self._task = asyncio.create_task(self._loop())

    async def stop(self):
        """Stops the scheduler gracefully."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("PublisherScheduler stopped.")

    async def _loop(self):
        while self._is_running:
            try:
                await self.tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in PublisherScheduler loop: {e}", exc_info=True)

            try:
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break

    async def tick(self) -> int:
        """
        Executes a single polling iteration.
        Returns the number of posts processed in this tick.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        due_posts = self.db.acquire_due_scheduled_posts(now_iso, limit=10)

        if not due_posts:
            return 0

        logger.info(f"PublisherScheduler acquired {len(due_posts)} due post(s) for publishing.")
        processed = 0

        for item in due_posts:
            post_id = item["post_id"]
            channel_id = item.get("channel_id") or get_target_channel_id()
            try:
                # Reconstruct PostSchema
                schema_dict = item.get("schema")
                if schema_dict:
                    post = PostSchema.model_validate(schema_dict)
                else:
                    post = self.db.get_post_schema(post_id)

                if not post:
                    self.db.mark_scheduled_failed(post_id, "Post schema is missing or invalid.")
                    continue

                res = await self.publish_fn(post, channel_id=channel_id)

                if res.get("success"):
                    msg_id = res.get("message_id", 0)
                    target_chat = int(channel_id) if str(channel_id).startswith("-100") else 0
                    self.db.mark_scheduled_posted(post_id, target_chat, msg_id)
                    logger.info(f"Successfully published scheduled post #{post_id} to Telegram (msg_id={msg_id}).")
                else:
                    err = res.get("error") or "Publishing rejected by Telegram"
                    self.db.mark_scheduled_failed(post_id, err)
                    logger.error(f"Failed to publish scheduled post #{post_id}: {err}")
            except Exception as e:
                logger.error(f"Exception while publishing scheduled post #{post_id}: {e}", exc_info=True)
                self.db.mark_scheduled_failed(post_id, str(e))
            finally:
                processed += 1

        return processed
