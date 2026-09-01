"""
Tests for AI Fact Extractor and Pipeline output to PostSchema.
"""

import pytest
from packages.ai.extractor import extract_post_schema_from_input
from packages.ai.pipeline import run_ai_research_pipeline
from packages.post_schema import ContentType, PostSchema


@pytest.mark.asyncio
async def test_extractor_from_raw_text_and_url():
    raw_input = "OpenAI released SearchGPT for all users.\nCheck out the release notes at https://openai.com/search"
    post = await extract_post_schema_from_input(ContentType.AI_NEWS, raw_input)

    assert isinstance(post, PostSchema)
    assert post.content_type == ContentType.AI_NEWS
    assert len(post.buttons) >= 1
    assert "https://openai.com/search" in post.buttons[0].url
    assert post.get_source_url() == "https://openai.com/search"


@pytest.mark.asyncio
async def test_ai_research_pipeline_output():
    post = await run_ai_research_pipeline(
        topic="Llama 4 Release",
        content_type=ContentType.AI_NEWS,
        source_items=[{"url": "https://ai.meta.com/llama"}],
    )

    assert isinstance(post, PostSchema)
    assert post.content_type == ContentType.AI_NEWS
    assert "Llama 4 Release" in post.title
    assert "KEY TAKEAWAYS" in post.body
    assert post.get_source_url() == "https://ai.meta.com/llama"
