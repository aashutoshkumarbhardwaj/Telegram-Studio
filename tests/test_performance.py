"""
Performance and Latency Tests for Heyaaashu Studio /new Fast-Path.
Verifies that simple raw text/URL draft generation completes in milliseconds.
"""

import time
import pytest
from packages.ai.extractor import extract_post_schema_from_input, fetch_url_metadata
from packages.formatter import format_post_text
from packages.post_schema import ContentType, PostSchema


@pytest.mark.asyncio
async def test_fast_path_extraction_performance():
    raw_input = (
        "Google says Gemini has crossed 1 billion monthly users.\n\n"
        "The Gemini app supports voice, camera, screen sharing and image generation.\n\n"
        "https://blog.google/"
    )

    t_start = time.perf_counter()
    post = await extract_post_schema_from_input(ContentType.AI_NEWS, raw_input)
    preview = format_post_text(post)
    elapsed = time.perf_counter() - t_start

    print(f"\n[BENCHMARK] /new fast-path extraction completed in {elapsed * 1000:.2f} ms")

    # Assert that extraction and formatting completes in under 0.5 seconds
    assert elapsed < 0.5, f"Extraction took too long: {elapsed:.3f}s"
    assert post.title == "Gemini has crossed 1 billion monthly users"
    assert "⚡ <b>KEY TAKEAWAYS</b>" in preview
    assert post.get_source_url() == "https://blog.google/"


@pytest.mark.asyncio
async def test_url_metadata_timeout_resilience():
    # Test a non-routable / slow IP to ensure timeout does not block the bot
    t_start = time.perf_counter()
    meta = await fetch_url_metadata("http://10.255.255.1/", timeout=0.5)
    elapsed = time.perf_counter() - t_start

    # Must timeout gracefully within 1.0s and return fallback dict
    assert elapsed < 1.0, f"URL fetch timeout took too long: {elapsed:.3f}s"
    assert isinstance(meta, dict)
    assert meta["url"] == "http://10.255.255.1/"
