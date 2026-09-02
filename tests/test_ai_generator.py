"""
Tests for Phase 11 AI Content Generator & API endpoints.
Verifies URL scraping, category detection, 3-hook generation, fact extraction,
quality analyzer, visual suggestions, and API route persistence.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from packages.ai import (
    UrlFetchError,
    detect_category,
    generate_hook_options,
    analyze_post_quality,
    suggest_visual_concept,
    generate_post_from_input,
    fetch_and_clean_url,
)
from packages.post_schema import ContentType, PostSchema, ParseMode
from apps.api.server import create_app
from packages.shared.db import StudioDatabase


# ─── 1. URL SCRAPING & CLEANING TESTS ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_url_metadata_extraction_clean():
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Google Announces Gemini 2.0 Reasoning Architecture</title>
        <meta property="og:title" content="Gemini 2.0 Reasoning Architecture" />
        <meta property="og:site_name" content="Google DeepMind" />
        <meta property="article:published_time" content="2026-09-01T12:00:00Z" />
    </head>
    <body>
        <nav><a href="/">Home</a><a href="/about">About</a></nav>
        <header><h1>Google DeepMind Header</h1></header>
        <article>
            <p>Google today unveiled Gemini 2.0, a new reasoning architecture crossing frontier benchmarks.</p>
            <p>The model features native streaming audio and visual perception across mobile devices.</p>
            <p>Developer APIs are available immediately via Google AI Studio.</p>
        </article>
        <footer><p>Copyright 2026 Google LLC. All rights reserved.</p></footer>
    </body>
    </html>
    """

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = sample_html
    mock_resp.url = "https://blog.google/gemini-2"

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        data = await fetch_and_clean_url("https://blog.google/gemini-2", timeout=2.0)

        assert data["title"] == "Gemini 2.0 Reasoning Architecture"
        assert data["site_name"] == "Google DeepMind"
        assert data["published_at"] == "2026-09-01T12:00:00Z"
        assert "Gemini 2.0, a new reasoning architecture" in data["text"]
        # Ensure boilerplate was decomposed
        assert "Home" not in data["text"]
        assert "Copyright 2026" not in data["text"]


@pytest.mark.asyncio
async def test_url_fetch_error_handling():
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(UrlFetchError) as exc_info:
            await fetch_and_clean_url("https://broken-domain.test/not-found", timeout=1.0)
        assert "HTTP 404" in str(exc_info.value)


# ─── 2. CATEGORY AUTO-DETECTION TESTS ─────────────────────────────────────────

def test_category_detection_job():
    job_text = """
    Staff AI Infrastructure Engineer
    Company: Mistral AI
    Location: Remote
    Salary: $220,000 - $280,000 + Equity
    We are hiring experienced distributed systems engineers to build our training clusters.
    Apply now via our careers portal.
    """
    cat, conf, review_needed = detect_category(job_text)
    assert cat == ContentType.JOB
    assert conf >= 0.8
    assert review_needed is False


def test_category_detection_internship():
    intern_text = """
    Summer 2027 Research Internship
    Stipend: $8,000 / month
    Eligibility: Enrolled in CS or related degree program
    Work directly with frontier AI researchers.
    """
    cat, conf, review_needed = detect_category(intern_text)
    assert cat == ContentType.INTERNSHIP
    assert conf >= 0.8
    assert review_needed is False


def test_category_detection_hackathon():
    hack_text = """
    Autonomous Agents Global Hackathon 2026
    Prize Pool: $100,000 in cash and cloud compute credits
    Submission deadline: October 15 on Devpost
    Assemble your team of 1-4 builders.
    """
    cat, conf, review_needed = detect_category(hack_text)
    assert cat == ContentType.HACKATHON
    assert conf >= 0.8
    assert review_needed is False


def test_category_ambiguity_flag():
    ambiguous_text = "Check out this quick thought about future software."
    cat, conf, review_needed = detect_category(ambiguous_text)
    assert cat == ContentType.AI_NEWS
    assert review_needed is True


# ─── 3. 3-HOOK GENERATOR & FACT EXTRACTION TESTS ─────────────────────────────

def test_3_hook_generation_and_scoring():
    title = "Anthropic Unveils Claude 3.7 Sonnet with Hybrid Reasoning"
    text = "Anthropic released Claude 3.7 Sonnet crossing 1 billion tokens in autonomous coding benchmarks."
    hooks = generate_hook_options(title, text, ContentType.AI_NEWS)

    assert len(hooks) == 3
    # Check styles
    styles = {h.style for h in hooks}
    assert styles == {"punchy", "scale", "context"}

    # Scores should be populated
    for h in hooks:
        assert 60 <= h.score <= 100
        assert 0 < len(h.text) <= 100


@pytest.mark.asyncio
async def test_fact_extraction_no_hallucinations():
    raw_idea = "Make a post about why AI agents are becoming important for developers."
    result = await generate_post_from_input(raw_idea)

    post: PostSchema = result["post"]
    assert isinstance(post, PostSchema)
    assert post.title
    assert "⚡ <b>KEY TAKEAWAYS</b>" in post.body
    assert "💡 <b>WHY IT MATTERS</b>" in post.body

    # Strictly assert NO placeholder strings in body or title
    for forbidden in ["N/A", "Unknown", "Not specified", "null"]:
        assert forbidden not in post.body
        assert forbidden not in post.title


# ─── 4. QUALITY ANALYZER & VISUAL SUGGESTION TESTS ───────────────────────────

def test_quality_analyzer_metrics():
    post = PostSchema(
        schema_version="1.0.0",
        content_type=ContentType.AI_NEWS,
        title="OpenAI Releases Next-Gen Search Engine Architecture",
        body=(
            "OpenAI announced a real-time web index integration for developers.\n\n"
            "⚡ <b>KEY TAKEAWAYS</b>\n"
            "• Sub-50ms latency search queries\n"
            "• Direct developer access via standard API\n\n"
            "💡 <b>WHY IT MATTERS</b>\n"
            "Enables autonomous agents to retrieve live verified web data."
        ),
        buttons=[{"text": "📚 Read Source", "url": "https://openai.com"}],
        source={"title": "OpenAI Blog", "url": "https://openai.com"},
        parse_mode=ParseMode.HTML,
    )

    quality = analyze_post_quality(post, has_source=True)
    assert quality.hook >= 80
    assert quality.clarity >= 80
    assert quality.value >= 80
    assert quality.readability >= 80
    assert quality.source == 100
    assert quality.overall >= 80
    assert quality.status == "ready"


def test_visual_suggestion():
    news_post = PostSchema(
        schema_version="1.0.0",
        content_type=ContentType.AI_NEWS,
        title="Google DeepMind Gemini 2.0 Release",
        body="Body text...",
        parse_mode=ParseMode.HTML,
    )
    vis = suggest_visual_concept(news_post)
    assert vis.needs_visual is True
    assert "Minimalist editorial graphic" in vis.concept
    assert "Gemini 2.0" in vis.concept


# ─── 5. API ENDPOINT INTEGRATION TESTS ────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_from_raw_idea_endpoint(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_gen_api.db"))
    from aiohttp.test_utils import TestClient, TestServer
    app = create_app(db=test_db)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        payload = {
            "input": "Google announced a new lightweight reasoning model that runs locally on laptops.",
            "category": "ai_news",
        }
        resp = await client.post("/api/generate", json=payload)
        assert resp.status == 200
        data = await resp.json()

        assert data["success"] is True
        assert data["draft_id"] > 0
        assert data["post"]["content_type"] == "ai_news"
        assert len(data["generation"]["hooks"]) == 3
        assert data["quality"]["overall"] >= 70
        assert data["visual"]["needs_visual"] is True
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_generate_hook_endpoint(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_hook_api.db"))
    from aiohttp.test_utils import TestClient, TestServer
    app = create_app(db=test_db)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        payload = {
            "title": "Meta Llama 4 Open Weights Release",
            "text": "Meta released Llama 4 with 2 million context window.",
            "category": "ai_news",
        }
        resp = await client.post("/api/generate/hook", json=payload)
        assert resp.status == 200
        data = await resp.json()

        assert data["success"] is True
        assert len(data["hooks"]) == 3
        assert any("Llama 4" in h["text"] for h in data["hooks"])
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_empty_input_rejected(tmp_path):
    test_db = StudioDatabase(db_path=str(tmp_path / "test_empty_api.db"))
    from aiohttp.test_utils import TestClient, TestServer
    app = create_app(db=test_db)
    client = TestClient(TestServer(app))
    await client.start_server()

    try:
        resp = await client.post("/api/generate", json={"input": ""})
        assert resp.status == 400
        data = await resp.json()
        assert data["success"] is False
        assert "cannot be empty" in data["error"]
    finally:
        await client.close()

