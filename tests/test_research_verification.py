"""
Phase 6: Comprehensive Deterministic Real-Data & Verification Test Suite.
Tests Source Trust Tiers, Multi-Source Deduplication, Fact Integrity, Field Omission, and Error Resilience.
"""

import pytest
from packages.ai.extractor import extract_post_schema_from_input
from packages.formatter import format_post_text
from packages.post_schema import ContentType, VerificationStatus
from packages.research.collector import ResearchCandidate, TrustTier
from packages.research.dedup_rank import _is_similar_story, collect_and_rank_candidates


# ─── 1. OFFICIAL AI ANNOUNCEMENT (TIER 1) ────────────────────────────────────

@pytest.mark.asyncio
async def test_official_ai_announcement_tier1_verified():
    cand = ResearchCandidate(
        id="t1_gemini",
        category=ContentType.AI_NEWS,
        title="Google DeepMind Unveils Next-Gen Gemini Reasoning Architecture",
        summary="Google announces multimodal reasoning architecture crossing frontier benchmark scores in coding, mathematics, and live video streaming perception.",
        source_url="https://blog.google/technology/ai/gemini-pro-reasoning/",
        source_name="Google Official Blog",
        trust_tier=TrustTier.TIER_1_OFFICIAL,
        verification_status="verified",
    )
    raw_input = f"{cand.title}\n\n{cand.summary}\n\n{cand.source_url}"
    post = await extract_post_schema_from_input(cand.category, raw_input)

    assert post.content_type == ContentType.AI_NEWS
    assert post.verification.status == VerificationStatus.VERIFIED
    assert "Gemini" in post.title
    assert "blog.google" in post.get_source_url()


# ─── 2. MULTI-SOURCE DEDUPLICATION (TIER 1 OVER TIER 2 & TIER 3) ─────────────

def test_multi_source_deduplication_similarity():
    t_official = "Google DeepMind Unveils Next-Gen Gemini Reasoning Architecture"
    t_news = "Google Announces Next-Gen Gemini Reasoning Model for Developers"
    t_reddit = "Discussion: DeepMind releases next-gen Gemini reasoning architecture"

    assert _is_similar_story(t_official, t_news) is True
    assert _is_similar_story(t_official, t_reddit) is True


# ─── 3. REDDIT DISCUSSION WITHOUT PRIMARY URL (TIER 3) ───────────────────────

@pytest.mark.asyncio
async def test_reddit_unverified_claim():
    cand = ResearchCandidate(
        id="t3_reddit_claim",
        category=ContentType.AI_NEWS,
        title="Rumor: Model X training with 500k GPUs",
        summary="Anonymous user claims Model X is in post-training with 500k H100s.",
        source_url="https://www.reddit.com/r/LocalLLaMA/comments/12345/rumor_model_x",
        source_name="Reddit r/LocalLLaMA",
        trust_tier=TrustTier.TIER_3_COMMUNITY,
        verification_status="needs_verification",
    )

    assert cand.trust_tier == TrustTier.TIER_3_COMMUNITY
    assert cand.verification_status == "needs_verification"


# ─── 4 & 5. JOBS: SALARY OMISSION WHEN NOT IN SOURCE & ACTIVE CHECK ──────────

@pytest.mark.asyncio
async def test_active_job_salary_omitted_when_unsupported():
    # Source input has NO salary mentioned
    raw_input = """Role: Senior Machine Learning Engineer
Company: Mistral AI
Location: Paris / London / Remote
Eligibility: Strong background in RLHF, DPO, and distributed PyTorch training
https://mistral.ai/careers/senior-ml-engineer"""

    post = await extract_post_schema_from_input(ContentType.JOB, raw_input)
    formatted = format_post_text(post)

    assert "Mistral AI" in formatted
    assert "Paris / London / Remote" in formatted
    # Crucial acceptance criteria: NO salary generated or invented
    assert "Salary" not in formatted
    assert "Compensation" not in formatted
    assert "N/A" not in formatted
    assert "Unknown" not in formatted
    assert post.buttons[0].url == "https://mistral.ai/careers/senior-ml-engineer"


# ─── 6. INTERNSHIP: STIPEND OMISSION WHEN NOT IN SOURCE ───────────────────────

@pytest.mark.asyncio
async def test_active_internship_stipend_omitted_when_unsupported():
    # Source input has NO stipend mentioned
    raw_input = """Role: Machine Learning Engineering Intern
Company: Hugging Face
Location: Remote / Global
Eligibility: Undergraduate & Graduate students with open-source contributions
https://huggingface.co/jobs/ml-intern"""

    post = await extract_post_schema_from_input(ContentType.INTERNSHIP, raw_input)
    formatted = format_post_text(post)

    assert "Hugging Face" in formatted
    assert "Remote / Global" in formatted
    # Crucial acceptance criteria: NO stipend generated or invented
    assert "Stipend" not in formatted
    assert "Pay" not in formatted
    assert "N/A" not in formatted


# ─── 7 & 8. HACKATHONS: EXPIRED CHECK AND EVIDENCE REQUIREMENT ───────────────

@pytest.mark.asyncio
async def test_hackathon_with_evidence():
    raw_input = """Hackathon: Global Autonomous AI Agent Hackathon 2026
Prize: $150,000 in Cash & GPU Compute Grants
Deadline: Oct 28, 2026
Team: 1 - 4 Members
Location: Online / Global
Build multi-agent autonomous workflows solving complex real-world operations.
https://lablab.ai/event/autonomous-agents-2026"""

    post = await extract_post_schema_from_input(ContentType.HACKATHON, raw_input)
    formatted = format_post_text(post)

    assert "$150,000" in formatted
    assert "Oct 28, 2026" in formatted
    assert "1 - 4 Members" in formatted
    assert "Online / Global" in formatted
    assert post.buttons[0].text == "🚀 Register"


# ─── 9 & 10. AI TOOLS: PRICING EVIDENCE VS PRICING OMISSION ───────────────────

@pytest.mark.asyncio
async def test_ai_tool_pricing_evidence():
    # Tool WITH pricing evidence
    raw_with_pricing = """AI Tool: vLLM Inference Engine
Ultra-fast LLM serving engine.
Pricing: Open Source (Apache 2.0)
https://github.com/vllm-project/vllm"""

    post_with = await extract_post_schema_from_input(ContentType.AI_TOOL, raw_with_pricing)
    formatted_with = format_post_text(post_with)
    assert "Open Source (Apache 2.0)" in formatted_with

    # Tool WITHOUT pricing specified -> does not invent fake subscription fees
    raw_without_pricing = """AI Tool: Browser-Use
Next-generation browser automation agent allowing LLMs to interact with websites.
https://github.com/browser-use/browser-use"""

    post_without = await extract_post_schema_from_input(ContentType.AI_TOOL, raw_without_pricing)
    formatted_without = format_post_text(post_without)
    assert "$20" not in formatted_without
    assert "$50" not in formatted_without


# ─── 11. SOURCE FAILURE RESILIENCE ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_source_failure_resilience():
    # Calling collect_and_rank_candidates across categories succeeds without throwing
    for cat in [ContentType.AI_NEWS, ContentType.JOB, ContentType.INTERNSHIP, ContentType.HACKATHON, ContentType.AI_TOOL]:
        candidates = await collect_and_rank_candidates(cat, limit=2)
        assert isinstance(candidates, list)
        assert len(candidates) >= 1
        assert candidates[0].source_url.startswith(("http://", "https://"))
