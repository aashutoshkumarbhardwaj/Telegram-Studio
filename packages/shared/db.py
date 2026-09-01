"""
Unified Database Layer for Heyaaashu Studio.
Manages drafts, channels, published posts, and reaction counters.
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from packages.post_schema import PostSchema
from packages.shared.config import DATABASE_PATH


class StudioDatabase:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DATABASE_PATH
        # Ensure parent directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Channels table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id INTEGER PRIMARY KEY,
                    title TEXT,
                    username TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # User channels link table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_channels (
                    user_id INTEGER,
                    channel_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, channel_id)
                )
            """)
            
            # Posts / Drafts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    post_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    channel_id INTEGER,
                    content_type TEXT,
                    title TEXT,
                    text TEXT,
                    media_json TEXT,
                    buttons_json TEXT,
                    reactions_json TEXT,
                    source_json TEXT,
                    parse_mode TEXT DEFAULT 'HTML',
                    status TEXT DEFAULT 'draft', -- 'draft', 'approved', 'posted', 'failed', 'cancelled'
                    raw_schema_json TEXT,
                    scheduled_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Sent posts mapping
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sent_posts (
                    channel_id INTEGER,
                    message_id INTEGER,
                    post_id INTEGER,
                    PRIMARY KEY (channel_id, message_id)
                )
            """)
            
            # Votes table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    post_id INTEGER,
                    user_id INTEGER,
                    reaction TEXT,
                    PRIMARY KEY (post_id, user_id)
                )
            """)

            # Dynamic migrations to support existing PostingPost databases
            migrations = [
                ("title", "TEXT"),
                ("media_json", "TEXT"),
                ("buttons_json", "TEXT"),
                ("reactions_json", "TEXT"),
                ("source_json", "TEXT"),
                ("parse_mode", "TEXT DEFAULT 'HTML'"),
                ("raw_schema_json", "TEXT"),
                ("status", "TEXT DEFAULT 'draft'"),
            ]
            for col_name, col_type in migrations:
                try:
                    cursor.execute(f"ALTER TABLE posts ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError:
                    pass

            conn.commit()

    def save_draft(self, user_id: int, post: PostSchema, channel_id: Optional[int] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            schema_json = post.model_dump_json()
            media_json = json.dumps([m.model_dump() for m in post.media])
            buttons_json = json.dumps([b.model_dump() for b in post.buttons])
            source_json = json.dumps(post.source.model_dump() if hasattr(post.source, "model_dump") else post.source)

            cursor.execute("""
                INSERT INTO posts (user_id, channel_id, content_type, title, text, media_json, buttons_json, source_json, parse_mode, status, raw_schema_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?)
            """, (user_id, channel_id, post.content_type.value, post.title, post.body, media_json, buttons_json, source_json, post.parse_mode.value, schema_json))
            conn.commit()
            return cursor.lastrowid

    def update_draft_post(self, post_id: int, post: PostSchema):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            schema_json = post.model_dump_json()
            media_json = json.dumps([m.model_dump() for m in post.media])
            buttons_json = json.dumps([b.model_dump() for b in post.buttons])
            source_json = json.dumps(post.source.model_dump() if hasattr(post.source, "model_dump") else post.source)

            cursor.execute("""
                UPDATE posts 
                SET content_type = ?, title = ?, text = ?, media_json = ?, buttons_json = ?, source_json = ?, parse_mode = ?, raw_schema_json = ?
                WHERE post_id = ?
            """, (post.content_type.value, post.title, post.body, media_json, buttons_json, source_json, post.parse_mode.value, schema_json, post_id))
            conn.commit()

    def get_post_schema(self, post_id: int) -> Optional[PostSchema]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT raw_schema_json, text, title, content_type, parse_mode FROM posts WHERE post_id = ?", (post_id,))
            row = cursor.fetchone()
            if not row:
                return None
            if row["raw_schema_json"]:
                return PostSchema.model_validate_json(row["raw_schema_json"])
            return PostSchema(
                content_type=row["content_type"] or "ai_news",
                title=row["title"] or "Untitled",
                body=row["text"] or "",
                parse_mode=row["parse_mode"] or "HTML",
            )

    def mark_post_published(self, post_id: int, channel_id: int, message_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE posts SET status = 'posted', channel_id = ? WHERE post_id = ?", (channel_id, post_id))
            cursor.execute("INSERT OR REPLACE INTO sent_posts (channel_id, message_id, post_id) VALUES (?, ?, ?)", (channel_id, message_id, post_id))
            conn.commit()

    def mark_post_status(self, post_id: int, status: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE posts SET status = ? WHERE post_id = ?", (status, post_id))
            conn.commit()

    def get_channels_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.channel_id, c.title, c.username 
                FROM channels c
                JOIN user_channels uc ON c.channel_id = uc.channel_id
                WHERE uc.user_id = ?
            """, (user_id,))
            return [dict(r) for r in cursor.fetchall()]
