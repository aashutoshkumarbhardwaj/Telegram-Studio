"""
Tests for StudioDatabase dual backend abstraction.
Verifies CRUD, schema initialization, and PostgreSQL connection routing.
"""

import pytest
from unittest.mock import MagicMock, patch
from packages.post_schema import ContentType, PostSchema
from packages.shared.db import StudioDatabase


def test_sqlite_database_lifecycle(tmp_path):
    db_file = str(tmp_path / "test_db.db")
    db = StudioDatabase(db_path=db_file)
    assert db.is_postgres is False

    post = PostSchema(
        content_type=ContentType.AI_NEWS,
        title="PostgreSQL Migration Live",
        body="Database abstraction supports both SQLite and Postgres.",
    )

    draft_id = db.save_draft(user_id=101, post=post)
    assert draft_id == 1

    loaded = db.get_post_schema(draft_id)
    assert loaded is not None
    assert loaded.title == "PostgreSQL Migration Live"

    # Update draft
    post.title = "PostgreSQL Migration Complete"
    db.update_draft_post(draft_id, post)
    updated = db.get_post_schema(draft_id)
    assert updated.title == "PostgreSQL Migration Complete"


def test_postgres_initialization_detection():
    with patch("packages.shared.db.psycopg", MagicMock()), \
         patch.object(StudioDatabase, "init_db", return_value=None):
        db = StudioDatabase(database_url="postgres://user:pass@dpg-abc-a.render.com/mydb")
        assert db.is_postgres is True
        assert db.database_url.startswith("postgresql://")
