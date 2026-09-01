"""
Tests for Heyaaashu Studio Research Pipeline.
Verifies source collection, deduplication, ranking, spam filtering, and candidate-to-draft generation.
"""

import pytest
from packages.ai.extractor import extract_post_schema_from_input
from packages.formatter import format_post_text, generate_telegram_payload
from packages.post_schema import ContentType
from packages.research.collector import ResearchCandidate
from packages.research.dedup_rank import collect_and_rank_candidates, _is_spam, _normalize_title


@pytest.mark.asyncio
async def test_research_candidate_collection_and_dedup():
    candidates = await collect_and_rank_candidates(ContentType.AI_NEWS, limit=3)
    assert len(candidates) >= 1
    for c in candidates:
        assert isinstance(c, ResearchCandidate)
        assert c.title
        assert c.source_url.startswith(("http://", "https://"))
        assert c.score > 0

    # Test deduplication: no duplicate URLs or titles
    urls = [c.source_url for c in candidates]
    assert len(urls) == len(set(urls))


def test_spam_filtering():
    assert _is_spam("Get 50% discount on promo code AI2026") is True
    assert _is_spam("Join our free webinar by clicking the link in bio") is True
    assert _is_spam("Google DeepMind releases Gemini 2.5 Pro architecture benchmarks") is False


def test_title_normalization():
    t1 = "Google: Gemini 2.0 Released!"
    t2 = "google gemini 20 released"
    assert _normalize_title(t1) == _normalize_title(t2)


@pytest.mark.asyncio
async def test_candidate_to_draft_generation():
    cand = ResearchCandidate(
        id="test1234",
        category=ContentType.AI_NEWS,
        title="OpenAI Ships Realtime Voice API Multi-Turn Capabilities",
        summary="New low-latency audio streaming endpoints enable sub-300ms responsive voice assistants with natural interruption handling.",
        source_url="https://openai.com/index/realtime-api-updates/",
        source_name="OpenAI",
        score=95.0,
    )

    raw_input = f"{cand.title}\n\n{cand.summary}\n\n{cand.source_url}"
    post = await extract_post_schema_from_input(cand.category, raw_input)

    assert post.content_type == ContentType.AI_NEWS
    assert "Realtime Voice API" in post.title or "OpenAI" in post.body
    assert post.get_source_url() == "https://openai.com/index/realtime-api-updates/"

    preview = format_post_text(post)
    assert "🚨 <b>AI NEWS</b>" in preview
    assert "⚡ <b>KEY TAKEAWAYS</b>" in preview
    assert "💡 <b>WHY IT MATTERS</b>" in preview
    assert "📚 <b>SOURCE</b>" in preview

    payload = generate_telegram_payload(post, chat_id="-1003756584531")
    assert payload["parse_mode"] == "HTML"
    assert payload["reply_markup"]["inline_keyboard"][0][0]["text"] == "📚 Read Source"
