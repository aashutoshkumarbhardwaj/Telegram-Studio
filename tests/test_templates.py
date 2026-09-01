"""
Comprehensive Tests for All Dedicated Telegram Content Templates:
AI News, Job, Internship, Hackathon, AI Tool.
Verifies layout hierarchy, field omission, HTML validity, and button matrix.
"""

import pytest
from packages.ai.extractor import extract_post_schema_from_input
from packages.formatter import format_post_text, generate_telegram_payload, validate_telegram_constraints
from packages.post_schema import ContentType, PostSchema


@pytest.mark.asyncio
async def test_ai_news_template():
    raw_input = """Google says Gemini has crossed 1 billion monthly users.

The Gemini app supports voice, camera, screen sharing and image generation.

https://blog.google/"""

    post = await extract_post_schema_from_input(ContentType.AI_NEWS, raw_input)
    assert post.content_type == ContentType.AI_NEWS
    assert "Gemini has crossed 1 billion monthly users" in post.title

    formatted = format_post_text(post)
    assert "🚨 <b>AI NEWS</b>" in formatted
    assert "🔥 <b>" in formatted
    assert "⚡ <b>KEY TAKEAWAYS</b>" in formatted
    assert "💡 <b>WHY IT MATTERS</b>" in formatted
    assert "━━━━━━━━━━━━━━" in formatted
    assert "📚 <b>SOURCE</b>" in formatted

    payload = generate_telegram_payload(post, chat_id="-1003756584531")
    assert payload["parse_mode"] == "HTML"
    assert len(payload["reply_markup"]["inline_keyboard"][0]) >= 1
    assert payload["reply_markup"]["inline_keyboard"][0][0]["text"] == "📚 Read Source"


@pytest.mark.asyncio
async def test_job_template_with_missing_fields_omitted():
    raw_input = """Role: Senior AI Research Engineer
Company: Anthropic
Location: San Francisco, CA
Eligibility: 5+ years in ML & Python
https://anthropic.com/careers"""

    post = await extract_post_schema_from_input(ContentType.JOB, raw_input)
    assert post.content_type == ContentType.JOB
    assert post.title == "Senior AI Research Engineer"

    formatted = format_post_text(post)
    assert "💼 <b>JOB ALERT</b>" in formatted
    assert "🔥 <b>Senior AI Research Engineer</b>" in formatted
    assert "🏢 <b>Company:</b> Anthropic" in formatted
    assert "📍 <b>Location:</b> San Francisco, CA" in formatted
    assert "🎓 <b>Eligibility:</b> 5+ years in ML & Python" in formatted
    # Missing salary & deadline must NOT appear as N/A or Unknown
    assert "N/A" not in formatted
    assert "Unknown" not in formatted
    assert "Not specified" not in formatted
    assert "🧩 <b>WHAT YOU'LL DO</b>" in formatted
    assert "🎯 <b>WHO SHOULD APPLY</b>" in formatted

    payload = generate_telegram_payload(post, chat_id="-1003756584531")
    assert payload["reply_markup"]["inline_keyboard"][0][0]["text"] == "💼 Apply Now"


@pytest.mark.asyncio
async def test_internship_template():
    raw_input = """Role: Machine Learning Research Intern
Company: OpenAI
Location: Remote
Stipend: $10,000 / month
Deadline: Nov 30, 2026
Work on reasoning evaluation benchmarks and safety alignment.
https://openai.com/careers/interns"""

    post = await extract_post_schema_from_input(ContentType.INTERNSHIP, raw_input)
    assert post.content_type == ContentType.INTERNSHIP

    formatted = format_post_text(post)
    assert "🎓 <b>INTERNSHIP ALERT</b>" in formatted
    assert "🔥 <b>Machine Learning Research Intern</b>" in formatted
    assert "🏢 <b>Company:</b> OpenAI" in formatted
    assert "💰 <b>Stipend:</b> $10,000 / month" in formatted
    assert "📅 <b>Deadline:</b> Nov 30, 2026" in formatted
    assert "🧩 <b>ROLE OVERVIEW</b>" in formatted
    assert "🎯 <b>WHO SHOULD APPLY</b>" in formatted

    payload = generate_telegram_payload(post, chat_id="-1003756584531")
    assert payload["reply_markup"]["inline_keyboard"][0][0]["text"] == "🚀 Apply Now"


@pytest.mark.asyncio
async def test_hackathon_template():
    raw_input = """Hackathon: Global AI Agent Hackathon 2026
Prize: $100,000 in Prizes & GPU Grants
Deadline: Oct 15, 2026
Team: 1 - 4 Members
Location: Online / Global
Build autonomous multi-agent workflows solving real enterprise tasks.
https://lablab.ai/event/ai-agent-2026"""

    post = await extract_post_schema_from_input(ContentType.HACKATHON, raw_input)
    assert post.content_type == ContentType.HACKATHON

    formatted = format_post_text(post)
    assert "🏆 <b>HACKATHON</b>" in formatted
    assert "🔥 <b>Global AI Agent Hackathon 2026</b>" in formatted
    assert "💰 <b>Prize:</b> $100,000 in Prizes & GPU Grants" in formatted
    assert "📅 <b>Deadline:</b> Oct 15, 2026" in formatted
    assert "👥 <b>Team Size:</b> 1 - 4 Members" in formatted
    assert "💡 <b>WHAT TO BUILD</b>" in formatted
    assert "🎯 <b>WHY JOIN</b>" in formatted

    payload = generate_telegram_payload(post, chat_id="-1003756584531")
    assert payload["reply_markup"]["inline_keyboard"][0][0]["text"] == "🚀 Register"


@pytest.mark.asyncio
async def test_ai_tool_template():
    raw_input = """AI Tool: Cursor 2.0
Next-generation AI code editor with agentic multi-file editing.
Provides seamless background indexation and context-aware diffs.
Pricing: Free Tier / $20 Pro Plan
https://cursor.com"""

    post = await extract_post_schema_from_input(ContentType.AI_TOOL, raw_input)
    assert post.content_type == ContentType.AI_TOOL

    formatted = format_post_text(post)
    assert "🛠 <b>AI TOOL</b>" in formatted
    assert "🔥 <b>Cursor 2.0</b>" in formatted
    assert "⚡ <b>WHAT IT DOES</b>" in formatted
    assert "🎯 <b>BEST FOR</b>" in formatted
    assert "💰 <b>PRICING</b>" in formatted
    assert "Free Tier / $20 Pro Plan" in formatted

    payload = generate_telegram_payload(post, chat_id="-1003756584531")
    assert payload["reply_markup"]["inline_keyboard"][0][0]["text"] == "🚀 Try Tool"
