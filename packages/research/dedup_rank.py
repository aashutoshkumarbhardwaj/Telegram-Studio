"""
Deduplication, Ranking, and Verification Engine for Heyaaashu Studio Research.
Merges multi-source stories (Official + Reputable + Community), filters expired opportunities,
and enforces source hierarchy (Tier 1 Official > Tier 2 Reputable > Tier 3 Community).
"""

import asyncio
import hashlib
import logging
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

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

logger = logging.getLogger(__name__)

# Targeted Spam Filter (does not block valid jobs or product announcements)
_SPAM_PATTERNS = [
    r"promo\s*code\b",
    r"discount\s*\d+%\b",
    r"\bbuy\s+now\b",
    r"click\s+the\s+link\s+in\s+bio",
    r"free\s+webinar\b",
    r"whatsapp\s+group\b",
    r"t\.me\/\+[a-zA-Z0-9]+",  # Invite links to private spam channels
]
_SPAM_RE = re.compile("|".join(_SPAM_PATTERNS), re.IGNORECASE)


def _normalize_title(title: str) -> str:
    """Normalizes title text for cross-source fuzzy match."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", title.lower())
    stopwords = {"unveils", "announces", "releases", "launches", "the", "a", "an", "is", "for", "in", "and"}
    words = [w for w in clean.split() if w not in stopwords]
    return " ".join(words)


def _is_spam(text: str) -> bool:
    """Checks if text contains promotional spam patterns."""
    return bool(_SPAM_RE.search(text))


def _make_candidate_id(url: str, title: str) -> str:
    """Generates a stable short ID for candidate referencing."""
    slug = f"{url}_{title}".encode("utf-8")
    return hashlib.md5(slug).hexdigest()[:8]


def _is_similar_story(t1: str, t2: str) -> bool:
    """Checks if two stories are discussing the same topic using Jaccard word similarity."""
    w1 = set(_normalize_title(t1).split())
    w2 = set(_normalize_title(t2).split())
    if not w1 or not w2:
        return False
    intersection = len(w1 & w2)
    union = len(w1 | w2)
    similarity = intersection / union
    return similarity >= 0.45


async def collect_and_rank_candidates(
    category: ContentType,
    limit: int = 4,
) -> List[ResearchCandidate]:
    """
    Executes the hardened research pipeline:
    1. Collect across Tier 1, Tier 2, and Tier 3 sources independently.
    2. Filter out spam and expired opportunities.
    3. Multi-source deduplication (merging duplicates into single story with supporting sources).
    4. Trust-based ranking (Tier 1 > Tier 2 > Tier 3).
    5. Preserves verification status and source integrity.
    """
    raw_items: List[Dict[str, Any]] = []

    # 1. Fetch from category sources with failure isolation
    if category == ContentType.AI_NEWS:
        tier1_task = fetch_tier1_official_news()
        tier3_task = fetch_reddit_community_news()
        results = await asyncio.gather(tier1_task, tier3_task, return_exceptions=True)
        for res in results:
            if isinstance(res, list):
                raw_items.extend(res)
            elif isinstance(res, Exception):
                logger.warning(f"A news source fetch failed gracefully: {res}")

    elif category == ContentType.JOB:
        try:
            raw_items = await fetch_verified_jobs()
        except Exception as e:
            logger.warning(f"Jobs fetch failed: {e}")

    elif category == ContentType.INTERNSHIP:
        try:
            raw_items = await fetch_verified_internships()
        except Exception as e:
            logger.warning(f"Internships fetch failed: {e}")

    elif category == ContentType.HACKATHON:
        try:
            raw_items = await fetch_verified_hackathons()
        except Exception as e:
            logger.warning(f"Hackathons fetch failed: {e}")

    elif category == ContentType.AI_TOOL:
        try:
            raw_items = await fetch_verified_ai_tools()
        except Exception as e:
            logger.warning(f"AI tools fetch failed: {e}")

    else:
        raw_items = await fetch_tier1_official_news()

    # 2. Filter Spam and Inactive/Expired
    clean_items: List[Dict[str, Any]] = []
    for item in raw_items:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()
        url = item.get("url", "").strip()

        if not title or not url:
            continue

        if _is_spam(title) or _is_spam(summary):
            continue

        # Filter expired items
        if item.get("is_active") is False:
            continue

        clean_items.append(item)

    # 3. Multi-Source Deduplication & Hierarchy Merge
    merged_candidates: List[ResearchCandidate] = []

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

        matched_candidate = None
        for cand in merged_candidates:
            if _is_similar_story(cand.title, title) or cand.source_url == url:
                matched_candidate = cand
                break

        if matched_candidate:
            if url not in matched_candidate.supporting_sources and url != matched_candidate.source_url:
                matched_candidate.supporting_sources.append(url)

            if trust_tier < matched_candidate.trust_tier:
                matched_candidate.source_url = url
                matched_candidate.source_name = source_name
                matched_candidate.trust_tier = trust_tier
                matched_candidate.verification_status = "verified"
                matched_candidate.title = title
                matched_candidate.summary = summary
                matched_candidate.score = max(matched_candidate.score, score)

        else:
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
            merged_candidates.append(cand)

    # 4. Rank Candidates
    for cand in merged_candidates:
        tier_weight = (4 - cand.trust_tier) * 30
        supp_weight = min(len(cand.supporting_sources) * 5, 15)
        cand.score = cand.score + tier_weight + supp_weight

    merged_candidates.sort(key=lambda c: c.score, reverse=True)
    return merged_candidates[:limit]
