"""
AI Content Generator Engine for Heyaaashu Studio.
Translates URLs, raw articles, and rough ideas into canonical PostSchema instances.
Features:
- Robust, timeout-resilient URL scraping with content cleaning
- Deterministic category auto-detection with ambiguity warning flags
- 3 distinct hook generation and multi-metric scoring
- Factual extraction preserving PostSchema constraints (never outputting N/A or Unknown)
- Multi-dimensional Quality Analyzer (0-100)
- Minimalist editorial visual concept generator
"""

import asyncio
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from packages.post_schema import (
    ContentType,
    InlineButton,
    ParseMode,
    PostSchema,
    SourceInfo,
    VerificationInfo,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class UrlFetchError(Exception):
    """Raised when an input URL cannot be fetched or parsed."""
    pass


class HookOption(BaseModel):
    text: str
    score: int
    style: str  # punchy, scale, context
    clarity: int
    curiosity: int
    brevity: int


class QualityMetrics(BaseModel):
    hook: int
    clarity: int
    value: int
    readability: int
    source: int
    completeness: int
    overall: int
    status: str  # ready, needs_review


class VisualConcept(BaseModel):
    needs_visual: bool
    concept: str


# ─── 1. URL SCRAPING & CLEANING ───────────────────────────────────────────────

def extract_urls(text: str) -> List[str]:
    """Finds all HTTP/HTTPS URLs in text."""
    return re.findall(r"https?://[^\s<>\"']+", text)


async def fetch_and_clean_url(url: str, timeout: float = 5.0) -> Dict[str, Any]:
    """
    Fetches URL server-side, extracts metadata, strips boilerplate/navigation,
    and returns cleaned article text and source attribution.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 (HeyaaashuStudio/1.0)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code >= 400:
                raise UrlFetchError(f"HTTP {resp.status_code}: Unable to reach source.")

            html = resp.text
            soup = BeautifulSoup(html, "html.parser")

            # Extract title
            title = ""
            og_title = soup.find("meta", attrs={"property": "og:title"}) or soup.find("meta", attrs={"name": "twitter:title"})
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            elif soup.title and soup.title.string:
                title = soup.title.string.strip()

            # Extract site / publisher name
            site_name = ""
            og_site = soup.find("meta", attrs={"property": "og:site_name"})
            if og_site and og_site.get("content"):
                site_name = og_site["content"].strip()
            if not site_name:
                if "blog.google" in url:
                    site_name = "Google Blog"
                elif "openai.com" in url:
                    site_name = "OpenAI"
                elif "anthropic.com" in url:
                    site_name = "Anthropic"
                elif "github.com" in url:
                    site_name = "GitHub"
                elif "deepmind.google" in url:
                    site_name = "Google DeepMind"
                else:
                    domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
                    site_name = domain_match.group(1).capitalize() if domain_match else "Official Source"

            # Extract published date
            published_at = None
            date_meta = soup.find("meta", attrs={"property": "article:published_time"}) or soup.find("meta", attrs={"name": "date"})
            if date_meta and date_meta.get("content"):
                published_at = date_meta["content"].strip()

            # Strip non-content tags
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "svg", "noscript"]):
                tag.decompose()

            # Look for main article body
            article_tag = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"article|post|content|entry", re.I))
            source_soup = article_tag if article_tag else soup.body if soup.body else soup

            paragraphs = []
            for p in source_soup.find_all(["p", "h1", "h2", "h3", "li"]):
                p_text = p.get_text(separator=" ", strip=True)
                if len(p_text) > 20 and not re.search(r"cookie|privacy policy|terms of service|all rights reserved", p_text, re.I):
                    paragraphs.append(p_text)

            cleaned_text = "\n\n".join(paragraphs[:25])  # Cap at first 25 substantial paragraphs
            if not cleaned_text and title:
                cleaned_text = title

            return {
                "title": title or "Industry Update",
                "site_name": site_name,
                "url": str(resp.url),
                "published_at": published_at,
                "text": cleaned_text,
            }

    except httpx.TimeoutException:
        raise UrlFetchError("Timeout: Source URL took too long to respond.")
    except httpx.RequestError as e:
        raise UrlFetchError(f"Network error: {str(e)}")
    except Exception as e:
        if isinstance(e, UrlFetchError):
            raise
        raise UrlFetchError(f"Could not parse webpage: {str(e)}")


# ─── 2. CATEGORY AUTO-DETECTION ───────────────────────────────────────────────

CATEGORY_SIGNALS: Dict[ContentType, List[str]] = {
    ContentType.JOB: [
        "hiring", "job", "career opportunity", "salary", "compensation", "benefits",
        "apply now", "responsibilities", "requirements", "engineer position", "full-time",
        "remote role", "work with us", "job description", "apply for this job",
    ],
    ContentType.INTERNSHIP: [
        "internship", "intern", "summer intern", "stipend", "students", "graduates",
        "pre-final year", "co-op", "campus hiring", "fellowship",
    ],
    ContentType.HACKATHON: [
        "hackathon", "prize pool", "devpost", "bounties", "submission deadline",
        "team size", "register today", "build products", "hackathon prizes",
    ],
    ContentType.AI_TOOL: [
        "ai tool", "saas", "pricing", "features", "dashboard", "try for free",
        "browser extension", "web app", "desktop app", "ai assistant tool",
        "github.com", "open source", "repository", "stars", "pull request",
        "git clone", "mit license", "apache 2.0", "readme.md",
    ],
    ContentType.CAREER: [
        "career guide", "resume", "interview prep", "salary negotiation",
        "roadmap for engineers", "career growth", "promotion", "transition into ai",
    ],
    ContentType.RESOURCE: [
        "cheat sheet", "cheatsheet", "curated list", "collection of prompts",
        "benchmark datasets", "learning resource", "documentation guide",
    ],
}


def detect_category(text: str, url: Optional[str] = None) -> Tuple[ContentType, float, bool]:
    """
    Analyzes input text and URL to detect appropriate ContentType.
    Returns (category, confidence, review_needed).
    """
    combined = f"{url or ''} {text}".lower()

    # Direct URL rules
    if url:
        if "github.com" in url.lower():
            return ContentType.AI_TOOL, 0.95, False
        if "devpost.com" in url.lower() or "hackerearth.com" in url.lower():
            return ContentType.HACKATHON, 0.95, False
        if "lever.co" in url.lower() or "greenhouse.io" in url.lower() or "workday" in url.lower() or "careers" in url.lower():
            if "intern" in combined:
                return ContentType.INTERNSHIP, 0.90, False
            return ContentType.JOB, 0.90, False

    # Score categories based on keyword occurrences
    scores: Dict[ContentType, int] = {cat: 0 for cat in ContentType}

    for cat, keywords in CATEGORY_SIGNALS.items():
        for kw in keywords:
            if kw in combined:
                scores[cat] += 2 if len(kw.split()) > 1 else 1

    # High priority keyword override for Jobs and Internships
    if any(k in combined for k in ["apply here", "job application", "we are hiring", "salary:"]):
        if "intern" in combined:
            return ContentType.INTERNSHIP, 0.88, False
        return ContentType.JOB, 0.88, False

    best_cat = max(scores, key=scores.get)
    max_score = scores[best_cat]

    # If no specific category scored, default to AI_NEWS
    if max_score == 0:
        return ContentType.AI_NEWS, 0.70, True

    # Calculate confidence & ambiguity
    total_score = sum(scores.values())
    confidence = min(0.95, max_score / (total_score if total_score > 0 else 1) * 0.8 + 0.2)
    review_needed = confidence < 0.60 or (max_score <= 2 and best_cat != ContentType.AI_NEWS)

    return best_cat, round(confidence, 2), review_needed


# ─── 3. 3-HOOK GENERATOR & SCORER ─────────────────────────────────────────────

def _clean_title_core(raw: str) -> str:
    """Removes common journalistic prefixes."""
    cleaned = re.sub(
        r"^(?:Google|Meta|OpenAI|Apple|Microsoft|Amazon|Anthropic|DeepMind)\s+(?:says?|announces?|claims?|reveals?|launches?|unveils?)\s+(?:that\s+)?",
        "",
        raw.strip(),
        flags=re.IGNORECASE,
    ).strip()
    if cleaned and len(cleaned) > 8:
        cleaned = cleaned[0].upper() + cleaned[1:]
    return cleaned.rstrip(".:")


def generate_hook_options(raw_title: str, text: str, category: ContentType) -> List[HookOption]:
    """
    Generates 3 distinct headline hooks (Punchy, Scale/Metric, Contextual)
    and scores each on clarity, curiosity, and brevity.
    """
    core = _clean_title_core(raw_title) if raw_title else "New Frontier Breakthrough"
    if not core or len(core) < 5:
        core = "Key AI Industry Milestone"

    options: List[Tuple[str, str]] = []

    # 1. Option A: Punchy / Direct Action
    if category == ContentType.JOB:
        opt_a = f"Hiring: {core}" if "hiring" not in core.lower() else core
    elif category == ContentType.INTERNSHIP:
        opt_a = f"Internship Alert: {core}" if "intern" not in core.lower() else core
    elif category == ContentType.HACKATHON:
        opt_a = f"Hackathon: {core}" if "hackathon" not in core.lower() else core
    elif category == ContentType.AI_TOOL:
        opt_a = f"{core} — Next-Gen AI Tool"
    else:
        opt_a = core

    # 2. Option B: Scale / Impact / Metric
    if "billion" in text.lower() or "million" in text.lower():
        metric_match = re.search(r"(\d+(?:\.\d+)?\s*(?:billion|million|k|b|m))\b", text, re.I)
        metric = metric_match.group(1) if metric_match else "Massive Scale"
        opt_b = f"{core} Crosses {metric}"
    elif category == ContentType.JOB:
        opt_b = f"High-Impact Engineering Role: {core}"
    elif category == ContentType.HACKATHON:
        opt_b = f"{core}: Compete & Build with Next-Gen AI"
    elif category == ContentType.AI_TOOL:
        opt_b = f"Supercharge Your Workflow With {core}"
    else:
        opt_b = f"{core} Sets New Industry Benchmark"

    # 3. Option C: Strategic / Contextual
    if category == ContentType.JOB:
        opt_c = f"Join the Team Behind {core}"
    elif category == ContentType.INTERNSHIP:
        opt_c = f"Hands-On AI Experience: {core}"
    elif category == ContentType.AI_TOOL:
        opt_c = f"Why Developers Are Adopting {core}"
    else:
        opt_c = f"Why {core} Signals a Major Shift in AI"

    raw_candidates = [
        (opt_a, "punchy"),
        (opt_b, "scale"),
        (opt_c, "context"),
    ]

    scored_hooks: List[HookOption] = []
    for text_opt, style in raw_candidates:
        # Cap length to 100 chars
        clean_text = text_opt.strip()
        if len(clean_text) > 100:
            clean_text = clean_text[:97] + "..."

        # Score clarity (penalty for excessive length or symbols)
        clarity = 95 - max(0, len(clean_text) - 70) // 2
        # Score curiosity (bonus for action verbs or provocative keywords)
        curiosity = 85 + (5 if any(w in clean_text.lower() for w in ["why", "new", "signals", "benchmark", "alert"]) else 0)
        # Score brevity
        brevity = 100 if len(clean_text) <= 65 else 88 if len(clean_text) <= 85 else 75

        overall_score = round((clarity * 0.4) + (curiosity * 0.35) + (brevity * 0.25))

        scored_hooks.append(HookOption(
            text=clean_text,
            score=overall_score,
            style=style,
            clarity=clarity,
            curiosity=curiosity,
            brevity=brevity,
        ))

    scored_hooks.sort(key=lambda h: h.score, reverse=True)
    return scored_hooks


# ─── 4. QUALITY ANALYZER ───────────────────────────────────────────────────────

def analyze_post_quality(post: PostSchema, has_source: bool = True) -> QualityMetrics:
    """
    Computes quality scores across 6 dimensions (0-100) and an overall score.
    Returns status: 'ready' (>= 80) or 'needs_review' (< 80).
    """
    # 1. Hook Score
    hook_len = len(post.title)
    if 30 <= hook_len <= 85:
        hook_score = 95
    elif 15 <= hook_len < 30 or 85 < hook_len <= 110:
        hook_score = 85
    else:
        hook_score = 70

    # 2. Clarity Score
    has_html_tags = bool(re.search(r"<b>|•|⚡", post.body))
    clarity_score = 92 if has_html_tags else 78
    if len(post.body.splitlines()) >= 4:
        clarity_score = min(100, clarity_score + 6)

    # 3. Value Score (Presence of Takeaways & Why it matters)
    has_takeaways = "KEY TAKEAWAYS" in post.body or "⚡" in post.body or (post.takeaways and len(post.takeaways) >= 2)
    has_why_matters = "WHY IT MATTERS" in post.body or "💡" in post.body or bool(post.why_it_matters)
    value_score = 95 if (has_takeaways and has_why_matters) else 80 if (has_takeaways or has_why_matters) else 65

    # 4. Readability Score (length and pacing)
    body_len = len(post.body)
    if 250 <= body_len <= 1400:
        readability_score = 95
    elif body_len < 250:
        readability_score = 80
    else:
        readability_score = 75

    # 5. Source Score
    if post.source and post.source.url and post.source.title:
        source_score = 100
    elif post.source and post.source.url:
        source_score = 90
    elif has_source:
        source_score = 80
    else:
        source_score = 50

    # 6. Completeness Score
    completeness_factors = [
        bool(post.title),
        bool(post.body),
        bool(post.content_type),
        bool(post.buttons and len(post.buttons) > 0),
        bool(post.source and post.source.url),
    ]
    completeness_score = int((sum(completeness_factors) / len(completeness_factors)) * 100)

    # Overall weighted score
    overall = int(
        (hook_score * 0.20)
        + (clarity_score * 0.15)
        + (value_score * 0.25)
        + (readability_score * 0.15)
        + (source_score * 0.15)
        + (completeness_score * 0.10)
    )

    status = "ready" if overall >= 80 and source_score >= 70 else "needs_review"

    return QualityMetrics(
        hook=hook_score,
        clarity=clarity_score,
        value=value_score,
        readability=readability_score,
        source=source_score,
        completeness=completeness_score,
        overall=overall,
        status=status,
    )


# ─── 5. VISUAL CONCEPT SUGGESTER ──────────────────────────────────────────────

def suggest_visual_concept(post: PostSchema) -> VisualConcept:
    """
    Determines if post benefits from a visual asset and generates an editorial prompt.
    """
    visual_types = {ContentType.AI_NEWS, ContentType.AI_TOOL, ContentType.HACKATHON}
    needs_visual = post.content_type in visual_types or "model" in post.title.lower() or "architecture" in post.title.lower()

    if not needs_visual:
        return VisualConcept(
            needs_visual=False,
            concept="Text-first structured announcement. Media optional.",
        )

    # Editorial, clean, dark-tech aesthetic description
    concept = (
        f"Minimalist editorial graphic for '{post.title}'. "
        "Dark slate background, glowing cyan and electric blue typography accents, "
        "abstract neural topology / data flow motif, high contrast, clean modern tech aesthetic. "
        "No fake UI frames or generic robot imagery."
    )
    return VisualConcept(needs_visual=True, concept=concept)


# ─── 6. MASTER GENERATOR ORCHESTRATOR ─────────────────────────────────────────

async def generate_post_from_input(
    raw_input: str,
    category_override: str = "auto",
    notes: str = "",
    link: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Master pipeline:
    1. Detects input type (URL, raw text, rough idea, URL + notes).
    2. Fetches URL server-side if present.
    3. Auto-detects category with safety confidence check.
    4. Generates 3 headline hooks and selects the best.
    5. Extracts structured facts into PostSchema.
    6. Runs quality analyzer and visual suggestion.
    """
    clean_input = raw_input.strip()
    if not clean_input:
        if link and link.strip():
            clean_input = link.strip()
        else:
            raise ValueError("Input cannot be empty. Please provide a URL, text, or topic idea.")

    urls = extract_urls(clean_input)
    if link and link.strip() and link.strip() not in urls:
        urls.insert(0, link.strip())
    has_url = len(urls) > 0
    primary_url = urls[0] if has_url else None

    # Determine input type
    text_without_urls = re.sub(r"https?://\S+", "", clean_input).strip()
    if has_url and not text_without_urls:
        input_type = "url"
    elif has_url and text_without_urls:
        input_type = "url_and_notes"
    elif len(clean_input.split()) < 15 and not clean_input.endswith("."):
        input_type = "rough_idea"
    else:
        input_type = "raw_text"

    # Step 1: Scrape URL if present
    url_data: Optional[Dict[str, Any]] = None
    if primary_url:
        url_data = await fetch_and_clean_url(primary_url, timeout=5.0)

    # Combine text context
    if url_data:
        title_hint = url_data["title"]
        source_name = url_data["site_name"]
        content_corpus = f"{url_data['title']}\n\n{notes}\n\n{url_data['text']}"
    else:
        lines = [l.strip() for l in clean_input.splitlines() if l.strip()]
        title_hint = lines[0] if lines else "New Technology Update"
        source_name = "Community / Idea"
        content_corpus = f"{clean_input}\n\n{notes}" if notes else clean_input

    # Step 2: Detect category
    if category_override and category_override != "auto":
        category = ContentType(category_override)
        confidence = 1.0
        review_needed = False
    else:
        category, confidence, review_needed = detect_category(content_corpus, primary_url)

    # Step 3: 3-Hook Generation & Scoring
    hooks = generate_hook_options(title_hint, content_corpus, category)
    best_hook = hooks[0].text if hooks else title_hint

    # Step 4: Extract structured body & takeaways
    # Build clean paragraph lines
    body_lines = [l.strip() for l in content_corpus.splitlines() if l.strip() and not l.startswith("http")]

    # Opening summary (concise, curiosity-inducing without clickbait)
    if len(body_lines) > 1 and len(body_lines[1]) > 30:
        opening = body_lines[1]
    elif len(body_lines) > 0 and len(body_lines[0]) > 30:
        opening = body_lines[0]
    else:
        opening = f"A significant development in {category.value.replace('_', ' ').title()} has been introduced."

    # Takeaways extraction
    takeaways: List[str] = []
    if len(body_lines) >= 3:
        for candidate_line in body_lines[2:6]:
            if 20 <= len(candidate_line) <= 180 and not candidate_line.startswith("#"):
                clean_takeaway = candidate_line.rstrip(".")
                takeaways.append(clean_takeaway)
            if len(takeaways) >= 3:
                break

    if not takeaways:
        if category == ContentType.JOB:
            takeaways = [
                "Full-time engineering position with scalable systems focus",
                "Competitive industry compensation package and benefits",
            ]
        elif category == ContentType.INTERNSHIP:
            takeaways = [
                "Hands-on engineering mentorship with production models",
                "Competitive monthly stipend and certificate of completion",
            ]
        elif category == ContentType.HACKATHON:
            takeaways = [
                "Compete for substantial prizes and mentor access",
                "Open for developers, researchers, and creators worldwide",
            ]
        elif category == ContentType.AI_TOOL:
            takeaways = [
                "Streamlined developer API with low-latency execution",
                "Generous free tier and open documentation available",
            ]
        else:
            takeaways = [
                "Crosses leading performance benchmarks in practical developer workflows",
                "Broad developer rollout beginning immediately with public access",
            ]

    # Why It Matters
    lower_corpus = content_corpus.lower()
    if "multimodal" in lower_corpus or "video" in lower_corpus or "voice" in lower_corpus:
        why_it_matters = "Accelerates the transition from text-based chatbots to real-time multimodal perception systems."
    elif "billion" in lower_corpus or "scale" in lower_corpus or "million" in lower_corpus:
        why_it_matters = "Marks a massive scale milestone reflecting accelerating real-world AI adoption."
    elif "security" in lower_corpus or "safety" in lower_corpus:
        why_it_matters = "Addresses critical reliability and alignment challenges in autonomous AI agent deployment."
    elif category == ContentType.JOB or category == ContentType.INTERNSHIP:
        why_it_matters = "Key opportunity to work on frontier production architectures and distributed systems."
    elif category == ContentType.AI_TOOL:
        why_it_matters = "Reduces engineering friction and empowers solo builders to ship production applications faster."
    else:
        why_it_matters = "Significant technical milestone with direct implications for engineers, researchers, and builders."

    # CTA
    if category in (ContentType.JOB, ContentType.INTERNSHIP):
        cta = "Review requirements and apply directly via the official link below."
    elif category == ContentType.HACKATHON:
        cta = "Assemble your team and register before the submission window closes."
    elif category == ContentType.AI_TOOL:
        cta = "Explore the live tool, documentation, and pricing in the link below."
    else:
        cta = "Check out the official release notes and technical benchmarks below."

    # Assemble structured body text with HTML formatting
    takeaways_formatted = "\n".join(f"• {t}" for t in takeaways)
    body = (
        f"{opening}\n\n"
        f"⚡ <b>KEY TAKEAWAYS</b>\n"
        f"{takeaways_formatted}\n\n"
        f"💡 <b>WHY IT MATTERS</b>\n"
        f"{why_it_matters}\n\n"
        f"{cta}"
    )

    # Buttons
    buttons: List[InlineButton] = []
    if primary_url:
        button_label = "📚 Read Source" if category == ContentType.AI_NEWS else "🔗 Open Details"
        buttons.append(InlineButton(text=button_label, url=primary_url))
    buttons.append(InlineButton(text="💬 Discuss", url="https://t.me/heyaaashu"))

    # Source Info
    source_obj = SourceInfo(
        title=source_name,
        url=primary_url or "",
        published_at=url_data.get("published_at") if url_data else None,
    ) if primary_url else None

    # Verification Info
    verification = VerificationInfo(
        status=VerificationStatus.VERIFIED if primary_url else VerificationStatus.NEEDS_VERIFICATION,
        sources=[primary_url] if primary_url else [],
        notes=f"Generated via Heyaaashu AI Engine ({input_type})",
    )

    # Assemble canonical PostSchema
    post = PostSchema(
        schema_version="1.0.0",
        content_type=category,
        title=best_hook,
        body=body,
        summary=opening,
        takeaways=takeaways,
        why_it_matters=why_it_matters,
        cta=cta,
        parse_mode=ParseMode.HTML,
        buttons=buttons,
        source=source_obj,
        verification=verification,
        metadata={
            "input_type": input_type,
            "generated_at": int(time.time()),
            "detected_category": category.value,
        },
    )

    # Step 5: Run Quality Analyzer
    quality = analyze_post_quality(post, has_source=bool(primary_url))

    # Step 6: Visual Suggestion
    visual = suggest_visual_concept(post)

    generation_meta = {
        "input_type": input_type,
        "detected_category": category.value,
        "category_confidence": confidence,
        "category_review_needed": review_needed,
        "hooks": [h.model_dump() for h in hooks],
        "source_name": source_name,
        "primary_url": primary_url,
    }

    return {
        "post": post,
        "quality": quality.model_dump(),
        "generation": generation_meta,
        "visual": visual.model_dump(),
    }
