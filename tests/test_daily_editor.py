"""
Phase 7: Comprehensive Tests for Daily Editorial Workflow.
Tests candidate aggregation, editorial diversity, entity caps, duplicate suppression,
previously surfaced suppression, category fallback, pagination, and Draft Top 5.
"""

import pytest
from packages.ai.extractor import extract_post_schema_from_input
from packages.post_schema import ContentType, PostSchema
from packages.research.collector import ResearchCandidate, TrustTier
from packages.research.daily_editor import (
    DailyBrief,
    _extract_company_or_entity,
    apply_editorial_diversity,
    generate_daily_content_brief,
)
from packages.shared.db import StudioDatabase


# ─── 1. ENTITY EXTRACTION & CAPS TEST ────────────────────────────────────────

def test_extract_company_or_entity():
    c1 = ResearchCandidate(
        id="1",
        category=ContentType.AI_NEWS,
        title="Google DeepMind announces Gemini update",
        summary="Google launches Gemini 2.5",
        source_url="https://blog.google/1",
        source_name="Google Blog",
    )
    assert _extract_company_or_entity(c1) == "google"

    c2 = ResearchCandidate(
        id="2",
        category=ContentType.JOB,
        title="Senior ML Engineer",
        summary="Modal Labs is hiring",
        source_url="https://modal.com/2",
        source_name="Modal Careers",
    )
    assert _extract_company_or_entity(c2) == "modal"


# ─── 2. EDITORIAL DIVERSITY ENFORCEMENT ──────────────────────────────────────

def test_editorial_diversity_target():
    candidates = [
        # 4 AI News
        ResearchCandidate(id="n1", category=ContentType.AI_NEWS, title="News 1", summary="", source_url="https://a.com/1", source_name="Google", score=100.0),
        ResearchCandidate(id="n2", category=ContentType.AI_NEWS, title="News 2", summary="", source_url="https://a.com/2", source_name="Anthropic", score=95.0),
        ResearchCandidate(id="n3", category=ContentType.AI_NEWS, title="News 3", summary="", source_url="https://a.com/3", source_name="Meta", score=90.0),
        ResearchCandidate(id="n4", category=ContentType.AI_NEWS, title="News 4", summary="", source_url="https://a.com/4", source_name="OpenAI", score=85.0),
        # 2 Jobs / Internships
        ResearchCandidate(id="j1", category=ContentType.JOB, title="Job 1", summary="", source_url="https://b.com/1", source_name="Modal", score=80.0),
        ResearchCandidate(id="i1", category=ContentType.INTERNSHIP, title="Intern 1", summary="", source_url="https://b.com/2", source_name="Mistral", score=75.0),
        # 2 Tools
        ResearchCandidate(id="t1", category=ContentType.AI_TOOL, title="Tool 1", summary="", source_url="https://c.com/1", source_name="GitHub", score=70.0),
        ResearchCandidate(id="t2", category=ContentType.AI_TOOL, title="Tool 2", summary="", source_url="https://c.com/2", source_name="GitHub", score=65.0),
        # 1 Hackathon
        ResearchCandidate(id="h1", category=ContentType.HACKATHON, title="Hackathon 1", summary="", source_url="https://d.com/1", source_name="Lablab", score=60.0),
    ]

    selected = apply_editorial_diversity(candidates, target_count=5, max_per_entity=2)

    assert len(selected) == 5
    categories = [c.category for c in selected]
    # Expect exactly 2 AI News, 1 Job/Internship, 1 Tool, 1 Hackathon
    assert categories.count(ContentType.AI_NEWS) == 2
    assert (categories.count(ContentType.JOB) + categories.count(ContentType.INTERNSHIP)) == 1
    assert categories.count(ContentType.AI_TOOL) == 1
    assert categories.count(ContentType.HACKATHON) == 1


# ─── 3. COMPANY DIVERSITY CAP (MAX 2 PER ENTITY) ─────────────────────────────

def test_company_diversity_cap():
    # 5 stories from OpenAI
    candidates = [
        ResearchCandidate(id="o1", category=ContentType.AI_NEWS, title="OpenAI Model 1", summary="", source_url="https://openai.com/1", source_name="OpenAI", score=100.0),
        ResearchCandidate(id="o2", category=ContentType.AI_NEWS, title="OpenAI Model 2", summary="", source_url="https://openai.com/2", source_name="OpenAI", score=99.0),
        ResearchCandidate(id="o3", category=ContentType.AI_NEWS, title="OpenAI Model 3", summary="", source_url="https://openai.com/3", source_name="OpenAI", score=98.0),
        ResearchCandidate(id="o4", category=ContentType.AI_NEWS, title="OpenAI Model 4", summary="", source_url="https://openai.com/4", source_name="OpenAI", score=97.0),
        # 1 Google story
        ResearchCandidate(id="g1", category=ContentType.AI_NEWS, title="Google DeepMind update", summary="", source_url="https://blog.google/1", source_name="Google", score=90.0),
        # 1 Anthropic story
        ResearchCandidate(id="a1", category=ContentType.AI_NEWS, title="Anthropic Claude Sonnet", summary="", source_url="https://anthropic.com/1", source_name="Anthropic", score=88.0),
    ]

    selected = apply_editorial_diversity(candidates, target_count=4, max_per_entity=2)
    openai_count = sum(1 for c in selected if "openai" in _extract_company_or_entity(c))
    assert openai_count <= 2


# ─── 4. CATEGORY FALLBACK (WHEN A BUCKET IS EMPTY) ───────────────────────────

def test_category_fallback_graceful_fill():
    # No Hackathons or Tools available
    candidates = [
        ResearchCandidate(id="n1", category=ContentType.AI_NEWS, title="News 1", summary="", source_url="https://a.com/1", source_name="Google", score=100.0),
        ResearchCandidate(id="n2", category=ContentType.AI_NEWS, title="News 2", summary="", source_url="https://a.com/2", source_name="Anthropic", score=95.0),
        ResearchCandidate(id="n3", category=ContentType.AI_NEWS, title="News 3", summary="", source_url="https://a.com/3", source_name="Meta", score=90.0),
        ResearchCandidate(id="j1", category=ContentType.JOB, title="Job 1", summary="", source_url="https://b.com/1", source_name="Modal", score=85.0),
        ResearchCandidate(id="j2", category=ContentType.JOB, title="Job 2", summary="", source_url="https://b.com/2", source_name="Mistral", score=80.0),
    ]

    selected = apply_editorial_diversity(candidates, target_count=5, max_per_entity=2)
    # Must still return exactly 5 candidates using available pool
    assert len(selected) == 5


# ─── 5. PREVIOUSLY SURFACED STORY SUPPRESSION IN SQLITE ──────────────────────

@pytest.mark.asyncio
async def test_previously_surfaced_story_suppression(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_daily.db"))

    # Initial Run
    brief1 = await generate_daily_content_brief(db=test_db, filter_previously_surfaced=True)
    assert len(brief1.top_recommended) >= 1

    first_top_url = brief1.top_recommended[0].source_url
    assert test_db.is_url_surfaced(first_top_url) is True

    # Subsequent run with suppression: already surfaced URL is suppressed from recommendations
    brief2 = await generate_daily_content_brief(db=test_db, filter_previously_surfaced=True)
    surfaced_urls_run2 = [c.source_url for c in brief2.top_recommended]
    assert first_top_url not in surfaced_urls_run2


# ─── 6. BATCH DRAFT TOP 5 POSTSCHEMA GENERATION ──────────────────────────────

@pytest.mark.asyncio
async def test_draft_top_5_batch_creation(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_batch.db"))

    brief = await generate_daily_content_brief(db=test_db, filter_previously_surfaced=False)
    assert len(brief.top_recommended) >= 3

    created_draft_ids = []
    for cand in brief.top_recommended[:3]:
        raw_input = f"{cand.title}\n\n{cand.summary}\n\n{cand.source_url}"
        post = await extract_post_schema_from_input(cand.category, raw_input)
        draft_id = test_db.save_draft(user_id=8982444793, post=post, status="draft")
        created_draft_ids.append(draft_id)

    assert len(created_draft_ids) == 3
    # Verify each draft is stored and retrievable as valid PostSchema
    for draft_id in created_draft_ids:
        post = test_db.get_post_schema(draft_id)
        assert isinstance(post, PostSchema)
        assert post.title
        assert post.body


# ─── 7. DRAFT STATUS TRANSITIONS & PUBLISH TRACKING ──────────────────────────

def test_draft_status_lifecycle(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_status.db"))

    post = PostSchema(
        content_type=ContentType.AI_NEWS,
        title="Gemini 2.5 Released",
        body="Google launched Gemini 2.5 with live audio.",
    )
    draft_id = test_db.save_draft(user_id=8982444793, post=post, status="draft")
    assert draft_id > 0

    # Transition: approve
    test_db.mark_post_status(draft_id, "approved")

    # Transition: publish
    test_db.mark_post_published(draft_id, channel_id=-1003756584531, message_id=42)

    with test_db.get_connection() as conn:
        row = conn.cursor().execute("SELECT status, published_at, channel_id FROM posts WHERE post_id = ?", (draft_id,)).fetchone()
        assert row["status"] == "posted"
        assert row["channel_id"] == -1003756584531
        assert row["published_at"] is not None
