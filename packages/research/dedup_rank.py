"""
Deduplication, Ranking, and Verification Engine for Research Pipeline.
Cleans noise, filters promotional spam, removes duplicate stories, and ranks top candidates.
"""

import hashlib
import re
from typing import List
from urllib.parse import urlparse

from packages.post_schema import ContentType
from packages.research.collector import (
    ResearchCandidate,
    fetch_ai_news_sources,
    fetch_ai_tools_sources,
    fetch_hackathons_sources,
    fetch_internships_sources,
    fetch_jobs_sources,
)

_SPAM_PATTERNS = [
    r"promo\s*code",
    r"discount\s*\d+%",
    r"buy\s*now",
    r"click\s*the\s*link\s*in\s*bio",
    r"free\s*webinar",
    r"whatsapp\s*group",
    r"telegram\s*channel\s*link",
]
_SPAM_RE = re.compile("|".join(_SPAM_PATTERNS), re.IGNORECASE)


def _normalize_title(title: str) -> str:
    """Normalizes title text for similarity checks."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", "", title.lower())
    return " ".join(clean.split())


def _is_spam(text: str) -> bool:
    """Checks if text contains spam/promotional markers."""
    return bool(_SPAM_RE.search(text))


def _make_candidate_id(url: str, title: str) -> str:
    """Generates a stable short ID for candidate referencing in bot callbacks."""
    slug = f"{url}_{title}".encode("utf-8")
    return hashlib.md5(slug).hexdigest()[:8]


async def collect_and_rank_candidates(
    category: ContentType,
    limit: int = 4,
) -> List[ResearchCandidate]:
    """
    Executes full pipeline:
    Collect sources -> Deduplicate -> Filter Spam -> Rank -> Verify.
    """
    raw_items = []
    if category == ContentType.AI_NEWS:
        raw_items = await fetch_ai_news_sources()
    elif category == ContentType.JOB:
        raw_items = await fetch_jobs_sources()
    elif category == ContentType.INTERNSHIP:
        raw_items = await fetch_internships_sources()
    elif category == ContentType.HACKATHON:
        raw_items = await fetch_hackathons_sources()
    elif category == ContentType.AI_TOOL:
        raw_items = await fetch_ai_tools_sources()
    else:
        raw_items = await fetch_ai_news_sources()

    # 1. Deduplicate & Filter Spam
    seen_urls = set()
    seen_titles = set()
    verified_candidates: List[ResearchCandidate] = []

    for item in raw_items:
        title = item.get("title", "").strip()
        summary = item.get("summary", "").strip()
        url = item.get("url", "").strip()
        source_name = item.get("source_name", "Web")
        score = float(item.get("score", 1.0))

        if not title or not url or not url.startswith(("http://", "https://")):
            continue

        if _is_spam(title) or _is_spam(summary):
            continue

        # Clean URL domain + path for deduplication
        parsed = urlparse(url)
        clean_url = f"{parsed.netloc}{parsed.path}".rstrip("/").lower()
        if clean_url in seen_urls:
            continue

        norm_title = _normalize_title(title)
        if norm_title in seen_titles:
            continue

        seen_urls.add(clean_url)
        seen_titles.add(norm_title)

        cand_id = _make_candidate_id(url, title)
        cand = ResearchCandidate(
            id=cand_id,
            category=category,
            title=title,
            summary=summary,
            source_url=url,
            source_name=source_name,
            score=score,
        )
        verified_candidates.append(cand)

    # 2. Rank by score descending
    verified_candidates.sort(key=lambda c: c.score, reverse=True)
    return verified_candidates[:limit]
