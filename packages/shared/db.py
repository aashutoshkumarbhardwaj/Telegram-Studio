"""
Unified Database Layer for Heyaaashu Studio.
Supports both SQLite (local development) and PostgreSQL (Render cloud production).
Manages drafts, channels, published posts, reaction counters, research cache, and surfaced stories.
"""

import hashlib
import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None

from packages.post_schema import PostSchema
from packages.shared.config import DATABASE_PATH, DATABASE_URL

logger = logging.getLogger(__name__)


class StudioDatabase:
    def __init__(self, db_path: Optional[str] = None, database_url: Optional[str] = None):
        self.database_url = database_url or DATABASE_URL
        self.db_path = db_path or DATABASE_PATH
        self.is_postgres = bool(
            self.database_url and (
                self.database_url.startswith("postgres://") or
                self.database_url.startswith("postgresql://")
            )
        )

        if self.is_postgres:
            if self.database_url.startswith("postgres://"):
                self.database_url = "postgresql://" + self.database_url[len("postgres://"):]
            logger.info("StudioDatabase initialized with PostgreSQL backend.")
        else:
            try:
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                fallback_path = Path(__file__).resolve().parent.parent.parent / "data" / "studio.db"
                fallback_path.parent.mkdir(parents=True, exist_ok=True)
                self.db_path = str(fallback_path)
            logger.info(f"StudioDatabase initialized with SQLite backend at {self.db_path}")

        self.init_db()

    @contextmanager
    def get_connection(self) -> Generator[Any, None, None]:
        if self.is_postgres:
            if not psycopg:
                raise RuntimeError("psycopg is not installed. Install psycopg[binary] to use PostgreSQL.")
            conn = psycopg.connect(self.database_url, autocommit=True, row_factory=dict_row)
            try:
                yield conn
            finally:
                conn.close()
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()

    def init_db(self):
        """Initializes tables and migrations for SQLite or PostgreSQL."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            if self.is_postgres:
                # PostgreSQL DDL
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS channels (
                        channel_id BIGINT PRIMARY KEY,
                        title TEXT,
                        username TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_channels (
                        user_id BIGINT,
                        channel_id BIGINT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, channel_id)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS posts (
                        post_id SERIAL PRIMARY KEY,
                        user_id BIGINT,
                        channel_id BIGINT,
                        content_type TEXT,
                        title TEXT,
                        text TEXT,
                        media_json TEXT,
                        buttons_json TEXT,
                        reactions_json TEXT,
                        source_json TEXT,
                        parse_mode TEXT DEFAULT 'HTML',
                        status TEXT DEFAULT 'draft',
                        raw_schema_json TEXT,
                        scheduled_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        published_at TIMESTAMPTZ,
                        telegram_message_id BIGINT,
                        error_message TEXT,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                for col_name, col_type in [
                    ("telegram_message_id", "BIGINT"),
                    ("error_message", "TEXT"),
                    ("updated_at", "TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP"),
                    ("scheduled_at", "TIMESTAMPTZ"),
                ]:
                    try:
                        cursor.execute(f"ALTER TABLE posts ADD COLUMN IF NOT EXISTS {col_name} {col_type};")
                    except Exception:
                        pass
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sent_posts (
                        channel_id BIGINT,
                        message_id BIGINT,
                        post_id INTEGER,
                        PRIMARY KEY (channel_id, message_id)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS votes (
                        post_id INTEGER,
                        user_id BIGINT,
                        reaction TEXT,
                        PRIMARY KEY (post_id, user_id)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS research_cache (
                        candidate_id TEXT PRIMARY KEY,
                        category TEXT,
                        title TEXT,
                        summary TEXT,
                        source_url TEXT,
                        source_name TEXT,
                        trust_tier INTEGER DEFAULT 2,
                        verification_status TEXT DEFAULT 'verified',
                        supporting_sources_json TEXT,
                        metadata_json TEXT,
                        score REAL DEFAULT 1.0,
                        published_at TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS surfaced_stories (
                        url_hash TEXT PRIMARY KEY,
                        url TEXT,
                        title TEXT,
                        category TEXT,
                        surfaced_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    );
                """)
            else:
                # SQLite DDL
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        first_name TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS channels (
                        channel_id INTEGER PRIMARY KEY,
                        title TEXT,
                        username TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_channels (
                        user_id INTEGER,
                        channel_id INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, channel_id)
                    );
                """)
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
                        status TEXT DEFAULT 'draft',
                        raw_schema_json TEXT,
                        scheduled_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        published_at TIMESTAMP,
                        telegram_message_id INTEGER,
                        error_message TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sent_posts (
                        channel_id INTEGER,
                        message_id INTEGER,
                        post_id INTEGER,
                        PRIMARY KEY (channel_id, message_id)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS votes (
                        post_id INTEGER,
                        user_id INTEGER,
                        reaction TEXT,
                        PRIMARY KEY (post_id, user_id)
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS research_cache (
                        candidate_id TEXT PRIMARY KEY,
                        category TEXT,
                        title TEXT,
                        summary TEXT,
                        source_url TEXT,
                        source_name TEXT,
                        trust_tier INTEGER DEFAULT 2,
                        verification_status TEXT DEFAULT 'verified',
                        supporting_sources_json TEXT,
                        metadata_json TEXT,
                        score REAL DEFAULT 1.0,
                        published_at TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS surfaced_stories (
                        url_hash TEXT PRIMARY KEY,
                        url TEXT,
                        title TEXT,
                        category TEXT,
                        surfaced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                # Migrations for existing SQLite stores
                migrations = [
                    ("title", "TEXT"),
                    ("media_json", "TEXT"),
                    ("buttons_json", "TEXT"),
                    ("reactions_json", "TEXT"),
                    ("source_json", "TEXT"),
                    ("parse_mode", "TEXT DEFAULT 'HTML'"),
                    ("raw_schema_json", "TEXT"),
                    ("status", "TEXT DEFAULT 'draft'"),
                    ("scheduled_at", "TIMESTAMP"),
                    ("published_at", "TIMESTAMP"),
                    ("telegram_message_id", "INTEGER"),
                    ("error_message", "TEXT"),
                    ("updated_at", "TIMESTAMP"),
                ]
                for col_name, col_type in migrations:
                    try:
                        cursor.execute(f"ALTER TABLE posts ADD COLUMN {col_name} {col_type}")
                    except sqlite3.OperationalError:
                        pass
                conn.commit()

    def save_draft(self, user_id: int, post: PostSchema, channel_id: Optional[int] = None, status: str = "draft") -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            schema_json = post.model_dump_json()
            media_json = json.dumps([m.model_dump() for m in post.media])
            buttons_json = json.dumps([b.model_dump() for b in post.buttons])
            source_json = json.dumps(post.source.model_dump() if hasattr(post.source, "model_dump") else post.source)

            if self.is_postgres:
                cursor.execute("""
                    INSERT INTO posts (user_id, channel_id, content_type, title, text, media_json, buttons_json, source_json, parse_mode, status, raw_schema_json)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING post_id;
                """, (user_id, channel_id, post.content_type.value, post.title, post.body, media_json, buttons_json, source_json, post.parse_mode.value, status, schema_json))
                row = cursor.fetchone()
                return row["post_id"] if isinstance(row, dict) else row[0]
            else:
                cursor.execute("""
                    INSERT INTO posts (user_id, channel_id, content_type, title, text, media_json, buttons_json, source_json, parse_mode, status, raw_schema_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, channel_id, post.content_type.value, post.title, post.body, media_json, buttons_json, source_json, post.parse_mode.value, status, schema_json))
                conn.commit()
                return cursor.lastrowid

    def update_draft_post(self, post_id: int, post: PostSchema):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            schema_json = post.model_dump_json()
            media_json = json.dumps([m.model_dump() for m in post.media])
            buttons_json = json.dumps([b.model_dump() for b in post.buttons])
            source_json = json.dumps(post.source.model_dump() if hasattr(post.source, "model_dump") else post.source)

            if self.is_postgres:
                cursor.execute("""
                    UPDATE posts 
                    SET content_type = %s, title = %s, text = %s, media_json = %s, buttons_json = %s, source_json = %s, parse_mode = %s, raw_schema_json = %s
                    WHERE post_id = %s
                """, (post.content_type.value, post.title, post.body, media_json, buttons_json, source_json, post.parse_mode.value, schema_json, post_id))
            else:
                cursor.execute("""
                    UPDATE posts 
                    SET content_type = ?, title = ?, text = ?, media_json = ?, buttons_json = ?, source_json = ?, parse_mode = ?, raw_schema_json = ?
                    WHERE post_id = ?
                """, (post.content_type.value, post.title, post.body, media_json, buttons_json, source_json, post.parse_mode.value, schema_json, post_id))
                conn.commit()

    def get_post_schema(self, post_id: int) -> Optional[PostSchema]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT raw_schema_json, text, title, content_type, parse_mode FROM posts WHERE post_id = " + ("%s" if self.is_postgres else "?")
            cursor.execute(query, (post_id,))
            row = cursor.fetchone()
            if not row:
                return None
            row_dict = dict(row)
            if row_dict.get("raw_schema_json"):
                return PostSchema.model_validate_json(row_dict["raw_schema_json"])
            return PostSchema(
                content_type=row_dict.get("content_type") or "ai_news",
                title=row_dict.get("title") or "Untitled",
                body=row_dict.get("text") or "",
                parse_mode=row_dict.get("parse_mode") or "HTML",
            )

    def mark_post_published(self, post_id: int, channel_id: int, message_id: int):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.is_postgres:
                cursor.execute("""
                    UPDATE posts 
                    SET status = 'posted', channel_id = %s, published_at = CURRENT_TIMESTAMP 
                    WHERE post_id = %s
                """, (channel_id, post_id))
                cursor.execute("""
                    INSERT INTO sent_posts (channel_id, message_id, post_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (channel_id, message_id) DO UPDATE SET post_id = EXCLUDED.post_id;
                """, (channel_id, message_id, post_id))
            else:
                cursor.execute("""
                    UPDATE posts 
                    SET status = 'posted', channel_id = ?, published_at = CURRENT_TIMESTAMP 
                    WHERE post_id = ?
                """, (channel_id, post_id))
                cursor.execute("INSERT OR REPLACE INTO sent_posts (channel_id, message_id, post_id) VALUES (?, ?, ?)", (channel_id, message_id, post_id))
                conn.commit()

    def mark_post_status(self, post_id: int, status: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "UPDATE posts SET status = " + ("%s WHERE post_id = %s" if self.is_postgres else "? WHERE post_id = ?")
            cursor.execute(query, (status, post_id))
            if not self.is_postgres:
                conn.commit()

    def get_channels_for_user(self, user_id: int) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT c.channel_id, c.title, c.username 
                FROM channels c
                JOIN user_channels uc ON c.channel_id = uc.channel_id
                WHERE uc.user_id = """ + ("%s" if self.is_postgres else "?")
            cursor.execute(query, (user_id,))
            return [dict(r) for r in cursor.fetchall()]

    # ─── RESEARCH CACHE ──────────────────────────────────────────────────────────

    def cache_research_candidates(self, category: str, candidates: list):
        """Caches research candidates into database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for c in candidates:
                supp_json = json.dumps(getattr(c, "supporting_sources", []))
                meta_json = json.dumps(getattr(c, "metadata", {}))
                params = (
                    c.id, category, c.title, c.summary, c.source_url, c.source_name,
                    getattr(c, "trust_tier", 2),
                    getattr(c, "verification_status", "verified"),
                    supp_json, meta_json, getattr(c, "score", 1.0),
                    getattr(c, "published_at", None),
                )
                if self.is_postgres:
                    cursor.execute("""
                        INSERT INTO research_cache (
                            candidate_id, category, title, summary, source_url, source_name,
                            trust_tier, verification_status, supporting_sources_json, metadata_json,
                            score, published_at, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (candidate_id) DO UPDATE SET
                            title = EXCLUDED.title, summary = EXCLUDED.summary, score = EXCLUDED.score,
                            verification_status = EXCLUDED.verification_status, supporting_sources_json = EXCLUDED.supporting_sources_json;
                    """, params)
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO research_cache (
                            candidate_id, category, title, summary, source_url, source_name,
                            trust_tier, verification_status, supporting_sources_json, metadata_json,
                            score, published_at, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, params)
            if not self.is_postgres:
                conn.commit()

    def get_cached_candidates(self, category: str, limit: int = 4) -> List[Dict[str, Any]]:
        """Retrieves cached candidates for a category."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                SELECT * FROM research_cache 
                WHERE category = """ + ("%s ORDER BY score DESC, created_at DESC LIMIT %s" if self.is_postgres else "? ORDER BY score DESC, created_at DESC LIMIT ?")
            cursor.execute(query, (category, limit))
            return [dict(r) for r in cursor.fetchall()]

    def get_cached_candidate_by_id(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single candidate by ID from cache."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM research_cache WHERE candidate_id = " + ("%s" if self.is_postgres else "?")
            cursor.execute(query, (candidate_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # ─── SURFACED STORIES TRACKING ───────────────────────────────────────────────

    def is_url_surfaced(self, url: str) -> bool:
        """Checks if a URL has already been surfaced in previous daily runs."""
        url_hash = hashlib.md5(url.strip().lower().encode("utf-8")).hexdigest()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT 1 FROM surfaced_stories WHERE url_hash = " + ("%s" if self.is_postgres else "?")
            cursor.execute(query, (url_hash,))
            return cursor.fetchone() is not None

    def mark_stories_surfaced(self, candidates: list):
        """Records surfaced candidate URLs to prevent consecutive duplicate recommendations."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for c in candidates:
                url = getattr(c, "source_url", "")
                if not url:
                    continue
                url_hash = hashlib.md5(url.strip().lower().encode("utf-8")).hexdigest()
                category = getattr(c, "category", "")
                cat_val = category.value if hasattr(category, "value") else str(category)
                params = (url_hash, url, getattr(c, "title", ""), cat_val)

                if self.is_postgres:
                    cursor.execute("""
                        INSERT INTO surfaced_stories (url_hash, url, title, category, surfaced_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (url_hash) DO NOTHING;
                    """, params)
                else:
                    cursor.execute("""
                        INSERT OR REPLACE INTO surfaced_stories (url_hash, url, title, category, surfaced_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, params)
            if not self.is_postgres:
                conn.commit()

    # ─── SCHEDULING PERSISTENCE & LIFECYCLE ──────────────────────────────────────

    def create_scheduled_post(
        self,
        post: PostSchema,
        scheduled_at: str,
        post_id: Optional[int] = None,
        user_id: int = 1,
        channel_id: Optional[int] = None,
    ) -> int:
        """
        Creates a new scheduled post or transitions an existing draft to 'scheduled'.
        Prevents scheduling if the post is already scheduled, publishing, or posted.
        """
        schema_json = post.model_dump_json()
        media_json = json.dumps([m.model_dump() for m in post.media])
        buttons_json = json.dumps([b.model_dump() for b in post.buttons])
        source_json = json.dumps(post.source.model_dump() if hasattr(post.source, "model_dump") else post.source)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            if post_id is not None:
                query = "SELECT status FROM posts WHERE post_id = " + ("%s" if self.is_postgres else "?")
                cursor.execute(query, (post_id,))
                row = cursor.fetchone()
                if row:
                    current_status = row["status"] if isinstance(row, dict) else row[0]
                    if current_status in ("scheduled", "publishing", "posted"):
                        raise ValueError(f"Post #{post_id} is already in '{current_status}' status. Duplicate scheduling is not allowed.")

                update_sql = """
                    UPDATE posts
                    SET content_type = %s, title = %s, text = %s, media_json = %s, buttons_json = %s,
                        source_json = %s, parse_mode = %s, raw_schema_json = %s, scheduled_at = %s,
                        status = 'scheduled', updated_at = CURRENT_TIMESTAMP
                    WHERE post_id = %s
                """ if self.is_postgres else """
                    UPDATE posts
                    SET content_type = ?, title = ?, text = ?, media_json = ?, buttons_json = ?,
                        source_json = ?, parse_mode = ?, raw_schema_json = ?, scheduled_at = ?,
                        status = 'scheduled', updated_at = CURRENT_TIMESTAMP
                    WHERE post_id = ?
                """
                params = (
                    post.content_type.value, post.title, post.body, media_json, buttons_json,
                    source_json, post.parse_mode.value, schema_json, scheduled_at, post_id
                )
                cursor.execute(update_sql, params)
                if not self.is_postgres:
                    conn.commit()
                return post_id
            else:
                if self.is_postgres:
                    cursor.execute("""
                        INSERT INTO posts (
                            user_id, channel_id, content_type, title, text, media_json, buttons_json,
                            source_json, parse_mode, status, raw_schema_json, scheduled_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'scheduled', %s, %s, CURRENT_TIMESTAMP)
                        RETURNING post_id;
                    """, (
                        user_id, channel_id, post.content_type.value, post.title, post.body,
                        media_json, buttons_json, source_json, post.parse_mode.value,
                        schema_json, scheduled_at
                    ))
                    res = cursor.fetchone()
                    return res["post_id"] if isinstance(res, dict) else res[0]
                else:
                    cursor.execute("""
                        INSERT INTO posts (
                            user_id, channel_id, content_type, title, text, media_json, buttons_json,
                            source_json, parse_mode, status, raw_schema_json, scheduled_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'scheduled', ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        user_id, channel_id, post.content_type.value, post.title, post.body,
                        media_json, buttons_json, source_json, post.parse_mode.value,
                        schema_json, scheduled_at
                    ))
                    conn.commit()
                    return cursor.lastrowid

    def get_scheduled_posts(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves all scheduled, publishing, posted, failed, or cancelled posts."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if status_filter:
                query = "SELECT * FROM posts WHERE status = " + ("%s" if self.is_postgres else "?") + " ORDER BY scheduled_at ASC, created_at DESC"
                cursor.execute(query, (status_filter,))
            else:
                query = "SELECT * FROM posts WHERE status != 'draft' OR scheduled_at IS NOT NULL ORDER BY scheduled_at ASC, created_at DESC"
                cursor.execute(query)

            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if item.get("raw_schema_json"):
                    try:
                        item["schema"] = json.loads(item["raw_schema_json"])
                    except Exception:
                        item["schema"] = None
                else:
                    item["schema"] = None
                for k in ("created_at", "updated_at", "scheduled_at", "published_at"):
                    if item.get(k) is not None:
                        item[k] = str(item[k])
                results.append(item)
            return results

    def get_scheduled_post_by_id(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves a single scheduled post by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM posts WHERE post_id = " + ("%s" if self.is_postgres else "?")
            cursor.execute(query, (post_id,))
            row = cursor.fetchone()
            if not row:
                return None
            item = dict(row)
            if item.get("raw_schema_json"):
                try:
                    item["schema"] = json.loads(item["raw_schema_json"])
                except Exception:
                    item["schema"] = None
            else:
                item["schema"] = None
            for k in ("created_at", "updated_at", "scheduled_at", "published_at"):
                if item.get(k) is not None:
                    item[k] = str(item[k])
            return item

    def update_scheduled_post(
        self,
        post_id: int,
        scheduled_at: Optional[str] = None,
        post: Optional[PostSchema] = None,
        status: Optional[str] = None,
    ) -> bool:
        """Updates schedule date, content, or status."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            updates = ["updated_at = CURRENT_TIMESTAMP"]
            params = []

            if scheduled_at is not None:
                updates.append("scheduled_at = " + ("%s" if self.is_postgres else "?"))
                params.append(scheduled_at)
            if status is not None:
                updates.append("status = " + ("%s" if self.is_postgres else "?"))
                params.append(status)
            if post is not None:
                schema_json = post.model_dump_json()
                media_json = json.dumps([m.model_dump() for m in post.media])
                buttons_json = json.dumps([b.model_dump() for b in post.buttons])
                source_json = json.dumps(post.source.model_dump() if hasattr(post.source, "model_dump") else post.source)
                for col, val in [
                    ("content_type", post.content_type.value),
                    ("title", post.title),
                    ("text", post.body),
                    ("media_json", media_json),
                    ("buttons_json", buttons_json),
                    ("source_json", source_json),
                    ("parse_mode", post.parse_mode.value),
                    ("raw_schema_json", schema_json),
                ]:
                    updates.append(f"{col} = " + ("%s" if self.is_postgres else "?"))
                    params.append(val)

            params.append(post_id)
            sql = f"UPDATE posts SET {', '.join(updates)} WHERE post_id = " + ("%s" if self.is_postgres else "?")
            cursor.execute(sql, tuple(params))
            if not self.is_postgres:
                conn.commit()
            return cursor.rowcount > 0

    def cancel_scheduled_post(self, post_id: int) -> bool:
        """Transitions post to cancelled status."""
        return self.update_scheduled_post(post_id=post_id, status="cancelled")

    def delete_scheduled_post(self, post_id: int) -> bool:
        """Deletes scheduled post."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "DELETE FROM posts WHERE post_id = " + ("%s" if self.is_postgres else "?")
            cursor.execute(query, (post_id,))
            if not self.is_postgres:
                conn.commit()
            return cursor.rowcount > 0

    def acquire_due_scheduled_posts(self, now_iso: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Atomically finds and locks due scheduled posts by transitioning their status to 'publishing'.
        Avoids race conditions and guarantees zero duplicate publishing.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            acquired = []

            if self.is_postgres:
                cursor.execute("""
                    WITH due_candidates AS (
                        SELECT post_id FROM posts
                        WHERE status = 'scheduled' AND scheduled_at <= %s
                        ORDER BY scheduled_at ASC
                        FOR UPDATE SKIP LOCKED
                        LIMIT %s
                    )
                    UPDATE posts p
                    SET status = 'publishing', updated_at = CURRENT_TIMESTAMP
                    FROM due_candidates c
                    WHERE p.post_id = c.post_id
                    RETURNING p.*;
                """, (now_iso, limit))
                rows = cursor.fetchall()
                for r in rows:
                    item = dict(r)
                    if item.get("raw_schema_json"):
                        try:
                            item["schema"] = json.loads(item["raw_schema_json"])
                        except Exception:
                            item["schema"] = None
                    acquired.append(item)
            else:
                cursor.execute("""
                    SELECT post_id FROM posts
                    WHERE status = 'scheduled' AND scheduled_at <= ?
                    ORDER BY scheduled_at ASC
                    LIMIT ?
                """, (now_iso, limit))
                candidate_ids = [r[0] for r in cursor.fetchall()]

                for pid in candidate_ids:
                    cursor.execute("""
                        UPDATE posts
                        SET status = 'publishing', updated_at = CURRENT_TIMESTAMP
                        WHERE post_id = ? AND status = 'scheduled'
                    """, (pid,))
                    if cursor.rowcount > 0:
                        cursor.execute("SELECT * FROM posts WHERE post_id = ?", (pid,))
                        row = cursor.fetchone()
                        if row:
                            item = dict(row)
                            if item.get("raw_schema_json"):
                                try:
                                    item["schema"] = json.loads(item["raw_schema_json"])
                                except Exception:
                                    item["schema"] = None
                            acquired.append(item)
                conn.commit()

            return acquired

    def mark_scheduled_posted(self, post_id: int, channel_id: int, message_id: int):
        """Marks post as successfully posted."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.is_postgres:
                cursor.execute("""
                    UPDATE posts 
                    SET status = 'posted', channel_id = %s, telegram_message_id = %s,
                        published_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP, error_message = NULL
                    WHERE post_id = %s
                """, (channel_id, message_id, post_id))
                cursor.execute("""
                    INSERT INTO sent_posts (channel_id, message_id, post_id)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (channel_id, message_id) DO UPDATE SET post_id = EXCLUDED.post_id;
                """, (channel_id, message_id, post_id))
            else:
                cursor.execute("""
                    UPDATE posts 
                    SET status = 'posted', channel_id = ?, telegram_message_id = ?,
                        published_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP, error_message = NULL
                    WHERE post_id = ?
                """, (channel_id, message_id, post_id))
                cursor.execute("INSERT OR REPLACE INTO sent_posts (channel_id, message_id, post_id) VALUES (?, ?, ?)", (channel_id, message_id, post_id))
                conn.commit()

    def mark_scheduled_failed(self, post_id: int, error_message: str):
        """Marks post as failed with error details."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = """
                UPDATE posts 
                SET status = 'failed', error_message = """ + ("%s, updated_at = CURRENT_TIMESTAMP WHERE post_id = %s" if self.is_postgres else "?, updated_at = CURRENT_TIMESTAMP WHERE post_id = ?")
            cursor.execute(query, (str(error_message), post_id))
            if not self.is_postgres:
                conn.commit()

    def recover_stale_publishing_posts(self, stale_seconds: int = 300) -> int:
        """Resets posts stuck in 'publishing' longer than stale_seconds back to 'scheduled'."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if self.is_postgres:
                cursor.execute("""
                    UPDATE posts
                    SET status = 'scheduled', updated_at = CURRENT_TIMESTAMP
                    WHERE status = 'publishing' AND (updated_at <= CURRENT_TIMESTAMP - (%s || ' seconds')::interval OR %s <= 0)
                """, (str(stale_seconds), stale_seconds))
                return cursor.rowcount
            else:
                cursor.execute("""
                    UPDATE posts
                    SET status = 'scheduled', updated_at = CURRENT_TIMESTAMP
                    WHERE status = 'publishing' AND (updated_at <= datetime('now', '-' || ? || ' seconds') OR ? <= 0)
                """, (str(stale_seconds), stale_seconds))
                conn.commit()
                return cursor.rowcount

