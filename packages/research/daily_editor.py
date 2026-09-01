"""
Daily Editorial Content Engine for Heyaaashu Studio.
Aggregates candidates across all 8 domains, enforces editorial diversity,
applies company/entity caps, suppresses previous daily duplicates, and recommends top 5.
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from packages.post_schema import ContentType
from packages.research.collector import (
    ResearchCandidate,
    TrustTier,
    fetch_reddit_community_news,
    fetch_tier1_official_news,
    fetch_verified_ai_tools,
    fetch_verified_hackathons,
    fetch_verified_internships,
    fetch_verified_jobs,
)
from packages.research.dedup_rank import _is_similar_story, _is_spam, _make_candidate_id
from packages.shared.db import StudioDatabase

logger = logging.getLogger(__name__)


class DailyBrief(BaseModel):
    candidates: List[ResearchCandidate] = Field(default_factory=list)
    top_recommended: List[ResearchCandidate] = Field(default_factory=list)
    total_sources_analyzed: int = 0
    verified_count: int = 0
    unverified_count: int = 0
    failed_sources_count: int = 0


def _extract_company_or_entity(candidate: ResearchCandidate) -> str:
    """Identifies primary organization/company to enforce entity diversity caps."""
    text = f"{candidate.title} {candidate.source_name} {candidate.summary}".lower()
    if "google" in text or "deepmind" in text:
        return "google"
    if "openai" in text:
        return "openai"
    if "anthropic" in text or "claude" in text:
        return "anthropic"
    if "meta" in text or "facebook" in text:
        return "meta"
    if "mistral" in text:
        return "mistral"
    if "modal" in text:
        return "modal"
    if "hugging face" in text or "huggingface" in text:
        return "huggingface"
    if "microsoft" in text:
        return "microsoft"
    return candidate.source_name.lower().strip()


def apply_editorial_diversity(
    candidates: List[ResearchCandidate],
    target_count: int = 5,
    max_per_entity: int = 2,
) -> List[ResearchCandidate]:
    """
    Selects top candidates enforcing target distribution and entity diversity:
    - 2 AI News
    - 1 Job or Internship
    - 1 AI Tool or GitHub
    - 1 Hackathon, Career, or Resource
    Falls back gracefully to highest available scores if a bucket is empty.
    """
    if not candidates:
        return []

    # Bucketing
    ai_news_pool = [c for c in candidates if c.category == ContentType.AI_NEWS]
    jobs_interns_pool = [c for c in candidates if c.category in (ContentType.JOB, ContentType.INTERNSHIP)]
    tools_pool = [c for c in candidates if c.category == ContentType.AI_TOOL]
    hackathons_career_pool = [c for c in candidates if c.category in (ContentType.HACKATHON, ContentType.CAREER, ContentType.RESOURCE)]

    selected: List[ResearchCandidate] = []
    selected_ids: Set[str] = set()
    entity_counts: Dict[str, int] = {}

    def try_add(candidate: ResearchCandidate) -> bool:
        if candidate.id in selected_ids:
            return False
        entity = _extract_company_or_entity(candidate)
        if entity_counts.get(entity, 0) >= max_per_entity:
            return False
        selected.append(candidate)
        selected_ids.add(candidate.id)
        entity_counts[entity] = entity_counts.get(entity, 0) + 1
        return True

    # 1. Target 2 AI News
    news_added = 0
    for c in ai_news_pool:
        if news_added >= 2:
            break
        if try_add(c):
            news_added += 1

    # 2. Target 1 Job / Internship
    for c in jobs_interns_pool:
        if try_add(c):
            break

    # 3. Target 1 AI Tool / GitHub
    for c in tools_pool:
        if try_add(c):
            break

    # 4. Target 1 Hackathon / Career / Resource
    for c in hackathons_career_pool:
        if try_add(c):
            break

    # 5. Fallback Fill: Add remaining highest-ranked candidates regardless of category
    for c in candidates:
        if len(selected) >= target_count:
            break
        try_add(c)

    # 6. If strict entity caps prevented reaching target_count, relax entity caps
    if len(selected) < target_count:
        for c in candidates:
            if len(selected) >= target_count:
                break
            if c.id not in selected_ids:
                selected.append(c)
                selected_ids.add(c.id)

    return selected[:target_count]


async def generate_daily_content_brief(
    db: Optional[StudioDatabase] = None,
    filter_previously_surfaced: bool = True,
) -> DailyBrief:
    """
    Executes full Daily Editorial Pipeline:
    1. Collects up to 30 raw candidates across all 8 domains with failure isolation.
    2. Deduplicates across sources and filters spam/noise.
    3. Suppresses previously surfaced stories from SQLite database.
    4. Ranks candidates by Trust Tier and composite editorial score.
    5. Applies balanced Editorial Diversity (2 News, 1 Job, 1 Tool, 1 Hackathon/Career).
    6. Returns 8-12 ranked candidates with top 5 recommended.
    """
    raw_items: List[Dict[str, Any]] = []
    failed_sources = 0

    # 1. Fetch concurrently across all domain fetchers
    fetch_tasks = [
        fetch_tier1_official_news(),
        fetch_reddit_community_news(),
        fetch_verified_jobs(),
        fetch_verified_internships(),
        fetch_verified_hackathons(),
        fetch_verified_ai_tools(),
    ]

    results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
    for res in results:
        if isinstance(res, list):
            raw_items.extend(res)
        elif isinstance(res, Exception):
            failed_sources += 1
            logger.warning(f"A daily source fetcher failed gracefully: {res}")

    total_sources_analyzed = len(raw_items)

    # 2. Filter Spam and Inactive
    clean_items: List[Dict[str, Any]] = []
    for item in raw_items:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()
        url = item.get("url", "").strip()
        if not title or not url or _is_spam(title) or _is_spam(summary):
            continue
        if item.get("is_active") is False:
            continue
        clean_items.append(item)

    # 3. Deduplicate across sources & Merge Hierarchy
    merged: List[ResearchCandidate] = []
    for item in clean_items:
        title = item["title"]
        summary = item.get("summary", title)
        url = item["url"]
        source_name = item.get("source_name", "Web")
        trust_tier = int(item.get("trust_tier", TrustTier.TIER_2_REPUTABLE))
        verification_status = item.get("verification_status", "verified" if trust_tier <= 2 else "needs_verification")
        published_at = item.get("published_at", "Recent")
        metadata = item.get("metadata", {})
        score = float(item.get("score", 1.0))

        # Determine Category
        category = ContentType.AI_NEWS
        if any(k in source_name.lower() or k in url.lower() for k in ["job", "career", "hiring"]):
            category = ContentType.JOB
        elif "intern" in source_name.lower() or "intern" in url.lower():
            category = ContentType.INTERNSHIP
        elif "hackathon" in source_name.lower() or "hackathon" in url.lower() or "lablab" in url.lower():
            category = ContentType.HACKATHON
        elif "github" in url.lower() or "tool" in source_name.lower():
            category = ContentType.AI_TOOL

        # Check existing duplicates in this run
        matched = None
        for cand in merged:
            if _is_similar_story(cand.title, title) or cand.source_url == url:
                matched = cand
                break

        if matched:
            if url not in matched.supporting_sources and url != matched.source_url:
                matched.supporting_sources.append(url)
            if trust_tier < matched.trust_tier:
                matched.source_url = url
                matched.source_name = source_name
                matched.trust_tier = trust_tier
                matched.verification_status = "verified"
                matched.title = title
                matched.summary = summary
                matched.score = max(matched.score, score)
        else:
            # Check previously surfaced in DB if enabled
            if filter_previously_surfaced and db and db.is_url_surfaced(url):
                continue

            cand_id = _make_candidate_id(url, title)
            cand = ResearchCandidate(
                id=cand_id,
                category=category,
                title=title,
                summary=summary,
                source_url=url,
                source_name=source_name,
                trust_tier=trust_tier,
                verification_status=verification_status,
                supporting_sources=[],
                published_at=published_at,
                metadata=metadata,
                score=score,
            )
            merged.append(cand)

    # 4. Rank Candidates
    for cand in merged:
        tier_weight = (4 - cand.trust_tier) * 30
        supp_weight = min(len(cand.supporting_sources) * 5, 15)
        cand.score = cand.score + tier_weight + supp_weight

    merged.sort(key=lambda c: c.score, reverse=True)
    all_candidates = merged[:12]

    # 5. Apply Editorial Diversity to select Top 5
    top_5 = apply_editorial_diversity(all_candidates, target_count=5, max_per_entity=2)

    # 6. Record surfaced stories in DB
    if db and top_5:
        db.mark_stories_surfaced(top_5)

    verified_count = sum(1 for c in all_candidates if c.verification_status == "verified")
    unverified_count = len(all_candidates) - verified_count

    return DailyBrief(
        candidates=all_candidates,
        top_recommended=top_5,
        total_sources_analyzed=total_sources_analyzed,
        verified_count=verified_count,
        unverified_count=unverified_count,
        failed_sources_count=failed_sources,
    )
