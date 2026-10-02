"""
AI Content Generator Engine for Heyaaashu Studio.
Translates URLs, raw articles, job listings, and rough ideas into canonical PostSchema instances.
Features:
- Google Gemini API integration (gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-flash)
- Fallback OpenAI-compatible completions (OpenAI, OpenRouter, DeepSeek)
- Robust, timeout-resilient URL scraping with content cleaning
- Deterministic category auto-detection with ambiguity warning flags
- Billion-dollar company grade Telegram copywriting & structure for Jobs, News, Tools, GitHub
- 3 distinct hook generation and multi-metric scoring
- Interactive action buttons (Apply Now, Register, Try Tool, View on GitHub) + Like callback + Discuss
- Multi-dimensional Quality Analyzer (0-100)
- Minimalist editorial visual concept generator
"""

import asyncio
import json
import logging
import os
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
from packages.shared.config import (
    ANTHROPIC_API_KEY,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    GEMINI_API_KEY,
    LLM_MODEL_NAME,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
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


EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"


def extract_urls(text: str) -> List[str]:
    """Finds all HTTP/HTTPS URLs in text."""
    return re.findall(r"https?://[^\s<>\"']+", text)


def extract_emails(text: str) -> List[str]:
    """Finds all email addresses in text."""
    if not text:
        return []
    matches = re.findall(EMAIL_REGEX, text)
    return list(dict.fromkeys(matches))


def get_email_compose_url(email: str, subject: Optional[str] = None) -> str:
    """Generates direct Gmail compose URL targeting the email in To section."""
    import urllib.parse
    clean_email = email.strip()
    url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(clean_email)}"
    if subject:
        url += f"&su={urllib.parse.quote(subject)}"
    return url


async def fetch_and_clean_url(url: str, timeout: float = 2.0) -> Dict[str, Any]:
    """
    Ultra-fast async web scraper. Fetches page content, strips HTML boilerplate,
    and returns cleaned article text and source attribution within 2.0s.
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
            elif soup.find("meta", attrs={"name": "application-name"}):
                site_name = soup.find("meta", attrs={"name": "application-name"}).get("content", "").strip()

            if not site_name:
                domain_match = re.search(r"https?://(?:www\.)?([^/]+)", url)
                if domain_match:
                    domain = domain_match.group(1).lower()
                    if "github.com" in domain:
                        site_name = "GitHub"
                    elif "google" in domain:
                        site_name = "Google"
                    elif "openai" in domain:
                        site_name = "OpenAI"
                    elif "anthropic" in domain:
                        site_name = "Anthropic"
                    elif "huggingface" in domain:
                        site_name = "Hugging Face"
                    elif "devpost" in domain:
                        site_name = "Devpost"
                    elif "linkedin" in domain:
                        site_name = "LinkedIn"
                    else:
                        site_name = domain.split(".")[0].capitalize()
                else:
                    site_name = "Official Source"

            # Extract publication time
            published_at = None
            time_tag = soup.find("time") or soup.find("meta", attrs={"property": "article:published_time"})
            if time_tag:
                published_at = time_tag.get("datetime") or time_tag.get("content")

            # Remove noise: scripts, styles, navigations, footers, sidebars
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "svg"]):
                tag.decompose()

            # Find main article or body content
            main_content = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|post|article|body|job-description|description", re.I)) or soup.body
            raw_text = main_content.get_text(separator="\n") if main_content else soup.get_text(separator="\n")

            # Clean and normalize paragraphs
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            cleaned_text = "\n".join(lines[:60])  # Take first 60 relevant lines

            if len(cleaned_text) < 40 and not title:
                raise UrlFetchError("Extracted content is too short or blocked by paywall/JS rendering.")

            return {
                "title": title or "Official Announcement",
                "site_name": site_name,
                "text": cleaned_text,
                "published_at": published_at,
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
        "remote role", "work with us", "job description", "apply for this job", "senior engineer",
        "staff engineer", "software engineer",
    ],
    ContentType.INTERNSHIP: [
        "internship", "intern", "summer intern", "stipend", "students", "graduates",
        "pre-final year", "co-op", "campus hiring", "fellowship", "2025 intern", "2026 intern",
    ],
    ContentType.HACKATHON: [
        "hackathon", "prize pool", "devpost", "bounties", "submission deadline",
        "team size", "register today", "build products", "hackathon prizes",
    ],
    ContentType.GITHUB: [
        "github.com", "open source", "repository", "stars", "pull request",
        "git clone", "mit license", "apache 2.0", "readme.md", "repo", "forks",
    ],
    ContentType.AI_TOOL: [
        "ai tool", "saas", "pricing", "features", "dashboard", "try for free",
        "browser extension", "web app", "desktop app", "ai assistant tool",
    ],
    ContentType.CAREER: [
        "career guide", "resume", "interview prep", "salary negotiation",
        "roadmap for engineers", "career growth", "promotion", "transition into ai",
    ],
    ContentType.RESOURCE: [
        "cheat sheet", "cheatsheet", "curated list", "collection of prompts",
        "benchmark datasets", "learning resource", "documentation guide", "free course",
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
        url_lower = url.lower()
        if "github.com" in url_lower:
            return ContentType.GITHUB, 0.95, False
        if "devpost.com" in url_lower or "hackerearth.com" in url_lower or "dorahacks.io" in url_lower:
            return ContentType.HACKATHON, 0.95, False
        if any(h in url_lower for h in ["lever.co", "greenhouse.io", "workday", "careers", "jobs.", "/jobs/", "ashbyhq.com", "wellfound.com"]):
            if "intern" in combined:
                return ContentType.INTERNSHIP, 0.92, False
            return ContentType.JOB, 0.92, False

    # Score categories based on keyword occurrences
    scores: Dict[ContentType, int] = {cat: 0 for cat in ContentType}

    for cat, keywords in CATEGORY_SIGNALS.items():
        for kw in keywords:
            if kw in combined:
                scores[cat] += 2 if len(kw.split()) > 1 else 1

    # High priority keyword override for Jobs and Internships
    if any(k in combined for k in ["apply here", "job application", "we are hiring", "we're hiring", "salary:"]):
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

    # 1. Option A: Punchy / Direct Action
    if category == ContentType.JOB:
        opt_a = f"💼 Hiring: {core}" if "hiring" not in core.lower() else f"💼 {core}"
    elif category == ContentType.INTERNSHIP:
        opt_a = f"🎓 Internship Alert: {core}" if "intern" not in core.lower() else f"🎓 {core}"
    elif category == ContentType.HACKATHON:
        opt_a = f"🏆 Hackathon: {core}" if "hackathon" not in core.lower() else f"🏆 {core}"
    elif category == ContentType.GITHUB:
        opt_a = f"💻 GitHub: {core}"
    elif category == ContentType.AI_TOOL:
        opt_a = f"🛠 {core} — Next-Gen AI Tool"
    else:
        opt_a = f"🚀 {core}"

    # 2. Option B: Scale / Impact / Metric
    if "billion" in text.lower() or "million" in text.lower():
        metric_match = re.search(r"(\d+(?:\.\d+)?\s*(?:billion|million|k|b|m))\b", text, re.I)
        metric = metric_match.group(1) if metric_match else "Massive Scale"
        opt_b = f"{core} Crosses {metric}"
    elif category == ContentType.JOB:
        opt_b = f"High-Impact Engineering Role: {core}"
    elif category == ContentType.INTERNSHIP:
        opt_b = f"Frontier Engineering Internship: {core}"
    elif category == ContentType.HACKATHON:
        opt_b = f"{core}: Compete & Build with Next-Gen AI"
    elif category == ContentType.GITHUB:
        opt_b = f"{core} — Open Source AI Repository"
    elif category == ContentType.AI_TOOL:
        opt_b = f"Supercharge Your Workflow With {core}"
    else:
        opt_b = f"{core} Sets New Industry Benchmark"

    # 3. Option C: Strategic / Contextual
    if category == ContentType.JOB:
        opt_c = f"Join the Team Behind {core}"
    elif category == ContentType.INTERNSHIP:
        opt_c = f"Hands-On AI Experience: {core}"
    elif category == ContentType.GITHUB:
        opt_c = f"Why Developers Are Starring {core}"
    elif category == ContentType.AI_TOOL:
        opt_c = f"Why Developers Are Adopting {core}"
    else:
        opt_c = f"Why {core} Signals a Major Shift in AI"

    raw_options = [
        (opt_a, "punchy"),
        (opt_b, "scale"),
        (opt_c, "context"),
    ]

    hook_objects: List[HookOption] = []
    for hook_text, style in raw_options:
        length = len(hook_text)
        brevity = max(60, min(98, 100 - abs(length - 55)))
        clarity = 90 if any(w in hook_text.lower() for w in ["ai", "hiring", "internship", "tool", "launches", "crosses"]) else 75
        curiosity = 95 if style in ("punchy", "scale") else 85
        score = int((clarity * 0.4) + (curiosity * 0.4) + (brevity * 0.2))

        hook_objects.append(
            HookOption(
                text=hook_text,
                score=score,
                style=style,
                clarity=clarity,
                curiosity=curiosity,
                brevity=brevity,
            )
        )

    hook_objects.sort(key=lambda h: h.score, reverse=True)
    return hook_objects


# ─── 4. QUALITY ANALYZER ──────────────────────────────────────────────────────

def analyze_post_quality(post: PostSchema, has_source: bool) -> QualityMetrics:
    """Evaluates the post against Telegram publishing quality criteria."""
    title_len = len(post.title)
    if 25 <= title_len <= 90:
        hook_score = 95
    elif 15 <= title_len < 25:
        hook_score = 80
    else:
        hook_score = 65

    has_bad_formatting = "<p>" in post.body or "<div>" in post.body or "**" in post.body
    clarity_score = 70 if has_bad_formatting else 92

    has_takeaways = bool(post.takeaways) or "⚡" in post.body
    has_why_it_matters = bool(post.why_it_matters) or "💡" in post.body
    value_score = 95 if (has_takeaways and has_why_it_matters) else (80 if has_takeaways else 60)

    body_len = len(post.body)
    if 200 <= body_len <= 1500:
        readability_score = 95
    elif body_len < 200:
        readability_score = 75
    else:
        readability_score = 80

    source_score = 100 if (has_source and post.verification.status == VerificationStatus.VERIFIED) else (85 if has_source else 50)
    has_buttons = len(post.buttons) >= 1
    completeness_score = 95 if (has_buttons and post.title and post.body) else 70

    overall = int(
        (hook_score * 0.20)
        + (clarity_score * 0.20)
        + (value_score * 0.20)
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
    visual_types = {ContentType.AI_NEWS, ContentType.AI_TOOL, ContentType.HACKATHON, ContentType.GITHUB}
    needs_visual = post.content_type in visual_types or "model" in post.title.lower() or "architecture" in post.title.lower()

    if not needs_visual:
        return VisualConcept(
            needs_visual=False,
            concept="Text-first structured announcement. Media optional.",
        )

    concept = (
        f"Minimalist editorial graphic for '{post.title}'. "
        "Dark slate background, glowing cyan and electric blue typography accents, "
        "abstract neural topology / data flow motif, high contrast, clean modern tech aesthetic. "
        "No fake UI frames or generic robot imagery."
    )
    return VisualConcept(needs_visual=True, concept=concept)


# ─── 6. GEMINI & LLM AI COPYWRITING ENGINE ────────────────────────────────────

GEMINI_SYSTEM_PROMPT = """You are the elite chief copywriter for 'Heyaaashu | AI & Tech Careers', a premier Telegram channel with 100,000+ software engineers, AI researchers, and tech builders.
Your Telegram posts are legendary: crisp, high-converting, visually structured, and free of generic corporate fluff.

Your goal is to write a high-engagement Telegram post from the provided input (job posting, URL content, AI announcement, tool release, GitHub repo, or notes).

STRICT FORMATTING RULES:
1. Parse mode is HTML. Use ONLY supported Telegram HTML tags: <b>bold</b>, <i>italic</i>, <code>code</code>, and <a href="...">links</a>. NEVER use markdown symbols like **, ##, or <p>/<div>/<br>.
2. Headline (title):
   - For Jobs: '💼 [Company] is Hiring [Role Name]' (e.g. '💼 Anthropic is Hiring AI Systems Engineers ($260k-$340k)')
   - For Internships: '🎓 [Company] [Year] [Role] Internship' (e.g. '🎓 Google 2026 AI Research Internship Open')
   - For AI News: Punchy and urgent (e.g. '🚀 OpenAI Launches GPT-5 with Native Multimodal Reasoning')
   - For AI Tools: Clear utility (e.g. '🛠 Cursor 2.0: Next-Gen AI Code Editor')
   - For GitHub: '💻 [Repo Name]: [One-line capability]' (e.g. '💻 vLLM: High-Throughput LLM Serving Engine')
   - For Hackathons: '🏆 [Hackathon Name]: [Prize Pool & Theme]'
3. CRITICAL - PRESERVE KEY CONTACT & APPLICATION DETAILS:
   - If the input contains any email address, phone number, WhatsApp contact, or specific application instructions, you MUST explicitly include them in the body text under ROLE DETAILS or KEY HIGHLIGHTS.
   - For email addresses, write them as clean text or hyperlinked HTML so readers can immediately see and copy them.
   - Do NOT delete, omit, or hardcode contact info. Always use the EXACT emails and phone numbers provided in the input prompt.
4. Body Structure:
   - Opening Hook: 1-2 sharp, engaging sentences explaining the announcement or role opportunity.
   - Middle Section:
     * If Job / Internship:
       ⚡ <b>ROLE DETAILS</b>
       • <b>Company:</b> [Company Name]
       • <b>Location:</b> [Location / Remote status]
       • <b>Experience:</b> [Level or Years required]
       • <b>Key Skills:</b> [Top 3-4 technologies / requirements]
       • <b>Compensation:</b> [Salary / Stipend if mentioned, or 'Competitive Industry Standard']
       • <b>Contact / Apply:</b> [Email / Phone / Link if mentioned in input]
       
       💡 <b>WHY APPLY</b>
       [1-2 sentences on why this role is a great career accelerator]
       
       👉 <i>Click 'Apply Now' below to submit your application directly.</i>
     * If AI News / Tool / GitHub / Hackathon / Resource:
       ⚡ <b>KEY HIGHLIGHTS</b>
       • [Key capability or metric 1]
       • [Key technical breakthrough 2]
       • [Developer availability, pricing, or repo status 3]
       
       💡 <b>WHY IT MATTERS</b>
       [1-2 sentences on industry / builder impact]
       
       👉 <i>Check the official link below for full details.</i>
5. Category must be one of: 'ai_news', 'job', 'internship', 'hackathon', 'ai_tool', 'github', 'career', 'resource'.
6. Suggested Button Label:
   - For Job with email: '📩 Apply via Email'
   - For Job with URL: '💼 Apply Now'
   - For Internship: '🎓 Apply for Internship'
   - For Hackathon: '🏆 Register Now'
   - For AI Tool: '🛠 Try Tool'
   - For GitHub: '💻 View on GitHub'
   - For Career: '🚀 Read Guide'
   - For Resource: '📖 Access Resource'
   - For AI News: '📚 Read Source'

Return valid JSON with:
{
  "content_type": "...",
  "title": "...",
  "body": "...",
  "summary": "...",
  "takeaways": ["...", "..."],
  "why_it_matters": "...",
  "cta": "...",
  "suggested_button_label": "...",
  "hashtags": ["...", "..."],
  "keywords": ["...", "..."]
}
"""


async def call_gemini_generator(
    content_corpus: str,
    primary_url: Optional[str] = None,
    category_hint: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: float = 12.0,
) -> Optional[Dict[str, Any]]:
    """
    Calls Google Gemini API (gemini-2.5-flash / gemini-2.0-flash / gemini-1.5-flash)
    to generate executive-tier structured Telegram post copy.
    """
    key = (api_key or GEMINI_API_KEY).strip()
    if not key:
        return None

    models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

    user_prompt = "Transform the following input into a canonical Telegram post object.\n\n"
    if primary_url:
        user_prompt += f"PRIMARY URL: {primary_url}\n"
    if category_hint and category_hint != "auto":
        user_prompt += f"CATEGORY OVERRIDE: {category_hint}\n"
    user_prompt += f"INPUT CONTENT:\n{content_corpus[:5000]}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user_prompt}],
            }
        ],
        "systemInstruction": {
            "parts": [{"text": GEMINI_SYSTEM_PROMPT}]
        },
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        for model in models:
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            try:
                resp = await client.post(endpoint, json=payload, headers={"Content-Type": "application/json"})
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            text_resp = parts[0]["text"].strip()
                            if text_resp.startswith("```json"):
                                text_resp = text_resp[7:]
                            if text_resp.startswith("```"):
                                text_resp = text_resp[3:]
                            if text_resp.endswith("```"):
                                text_resp = text_resp[:-3]
                            parsed = json.loads(text_resp.strip())
                            logger.info(f"Successfully generated post copy with Gemini model: {model}")
                            return parsed
                else:
                    logger.warning(f"Gemini model {model} returned HTTP {resp.status_code}: {resp.text[:150]}")
            except Exception as e:
                logger.warning(f"Gemini API attempt with {model} failed: {e}")
                continue

    return None


async def call_openai_compatible_generator(
    content_corpus: str,
    primary_url: Optional[str] = None,
    category_hint: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: str = "https://api.openai.com/v1",
    model: str = "gpt-4o-mini",
    timeout: float = 12.0,
) -> Optional[Dict[str, Any]]:
    """Calls OpenAI-compatible completion API as a secondary LLM option."""
    key = (api_key or OPENAI_API_KEY or OPENROUTER_API_KEY or DEEPSEEK_API_KEY).strip()
    if not key:
        return None

    user_prompt = "Transform the following input into a canonical Telegram post object.\n\n"
    if primary_url:
        user_prompt += f"PRIMARY URL: {primary_url}\n"
    if category_hint and category_hint != "auto":
        user_prompt += f"CATEGORY OVERRIDE: {category_hint}\n"
    user_prompt += f"INPUT CONTENT:\n{content_corpus[:5000]}"

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": GEMINI_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0.3,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
    except Exception as e:
        logger.warning(f"OpenAI-compatible LLM call failed: {e}")

    return None


# ─── 7. DETERMINISTIC COPYWRITING FALLBACK ────────────────────────────────────

def _extract_job_details(text: str, source_name: str) -> Dict[str, Any]:
    """Extracts job-specific fields (company, role, location, skills, salary, contact, phone) from text."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # 1. Company
    company = source_name
    comp_match = re.search(r"(?:at|at the|by|with|joining)\s+([A-Z][A-Za-z0-9\s&.-]{1,25})\b", text)
    if comp_match and comp_match.group(1).lower() not in ["the", "a", "an", "our", "this"]:
        company = comp_match.group(1).strip()
    elif source_name and source_name != "Official Source":
        company = source_name

    # 2. Location
    location = "Remote / Hybrid"
    loc_match = re.search(r"(?:location|based in|workplace)[:\-–—]?\s*([^\n,]+(?:,\s*[A-Z]{2})?)", text, re.I)
    if loc_match:
        location = loc_match.group(1).strip()
    elif re.search(r"\bremote\b", text, re.I):
        location = "Remote"
    elif re.search(r"\bhybrid\b", text, re.I):
        location = "Hybrid"

    # 3. Experience
    experience = "1-3+ Years or Relevant Experience"
    exp_match = re.search(r"(\d+\+?\s*(?:-\s*\d+)?\s*(?:years?|yrs?)(?:\s+of\s+experience)?)", text, re.I)
    if exp_match:
        experience = exp_match.group(1).strip()
    elif re.search(r"\bsenior\b|\bstaff\b|\blead\b", text, re.I):
        experience = "4+ Years (Senior / Staff Level)"
    elif re.search(r"\bintern\b|\bgraduate\b|\bentry\b", text, re.I):
        experience = "Students / Recent Graduates"

    # 4. Skills / Tech Stack
    skills = []
    common_skills = [
        "Python", "PyTorch", "TensorFlow", "TypeScript", "React", "Node.js", "Go", "Golang",
        "Rust", "C++", "Kubernetes", "AWS", "GCP", "PostgreSQL", "LLMs", "RAG", "Docker", "Next.js"
    ]
    for sk in common_skills:
        if re.search(rf"\b{re.escape(sk)}\b", text, re.I):
            skills.append(sk)
    skills_str = ", ".join(skills[:5]) if skills else "Python, Distributed Systems, Modern Stack"

    # 5. Compensation / Salary
    compensation = "Competitive Industry Standard + Equity"
    sal_match = re.search(r"((?:[$€£₹]|INR|USD)\s*[\d,]+(?:\s*-\s*[\d,]+)?(?:\s*(?:k|lpa|per year|/yr))?)", text, re.I)
    if sal_match:
        compensation = sal_match.group(1).strip()

    # 6. Emails & Phone Numbers
    emails = extract_emails(text)
    phones = re.findall(r"(?:(?:\+|00)\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{3,5}\b", text)
    valid_phones = [p.strip() for p in phones if len(re.sub(r"\D", "", p)) >= 10]

    return {
        "company": company,
        "location": location,
        "experience": experience,
        "skills": skills_str,
        "compensation": compensation,
        "emails": emails,
        "phones": valid_phones,
    }


def _build_deterministic_copy(
    category: ContentType,
    content_corpus: str,
    source_name: str,
    title_hint: str,
    primary_url: Optional[str],
) -> Dict[str, Any]:
    """Generates structured, executive-grade copy when LLM is unavailable."""
    body_lines = [l.strip() for l in content_corpus.splitlines() if l.strip() and not l.startswith("http")]

    if category in (ContentType.JOB, ContentType.INTERNSHIP):
        job_info = _extract_job_details(content_corpus, source_name)
        role_title = _clean_title_core(title_hint)
        if category == ContentType.INTERNSHIP:
            title = f"🎓 {job_info['company']} is Hiring: {role_title}" if "intern" in role_title.lower() else f"🎓 {job_info['company']} {role_title} Internship"
            hook = f"{job_info['company']} has opened applications for their {role_title} internship program."
            details_header = "⚡ <b>INTERNSHIP DETAILS</b>"
            why_header = "💡 <b>WHY APPLY</b>"
            why_text = f"Accelerate your engineering journey with hands-on production experience at {job_info['company']}."
            cta = "Submit your application or email resume directly via the link below."
            btn_label = "🎓 Email Resume" if job_info["emails"] else "🎓 Apply for Internship"
        else:
            title = f"💼 {job_info['company']} is Hiring: {role_title}"
            hook = f"{job_info['company']} is actively expanding its team and looking for a {role_title}."
            details_header = "⚡ <b>ROLE DETAILS</b>"
            why_header = "💡 <b>WHY APPLY</b>"
            why_text = f"Opportunity to work on frontier scalable architectures with top-tier engineering leadership at {job_info['company']}."
            cta = "Submit your application or send your CV directly via the link below."
            btn_label = "📩 Apply via Email" if job_info["emails"] else "💼 Apply Now"

        detail_bullets = [
            f"• <b>Company:</b> {job_info['company']}",
            f"• <b>Location:</b> {job_info['location']}",
            f"• <b>Experience:</b> {job_info['experience']}",
            f"• <b>Key Skills:</b> {job_info['skills']}",
            f"• <b>Compensation:</b> {job_info['compensation']}",
        ]
        if job_info["emails"]:
            primary_em = job_info["emails"][0]
            gmail_link = get_email_compose_url(primary_em)
            detail_bullets.append(f'• <b>Send CV to:</b> <a href="{gmail_link}">{primary_em}</a>')
        if job_info["phones"]:
            detail_bullets.append(f"• <b>Contact / Phone:</b> {job_info['phones'][0]}")

        body = (
            f"{hook}\n\n"
            f"{details_header}\n"
            f"{chr(10).join(detail_bullets)}\n\n"
            f"{why_header}\n"
            f"{why_text}\n\n"
            f"👉 <i>{cta}</i>"
        )
        takeaways = [
            f"Company: {job_info['company']} | Location: {job_info['location']}",
            f"Experience: {job_info['experience']}",
            f"Tech Stack: {job_info['skills']}",
            f"Compensation: {job_info['compensation']}",
        ]
        if job_info["emails"]:
            takeaways.append(f"Direct Email: {job_info['emails'][0]}")
        why_it_matters = why_text
    else:
        # AI News, Tools, GitHub, Hackathon
        core_title = _clean_title_core(title_hint)
        if category == ContentType.GITHUB:
            title = f"💻 GitHub: {core_title}"
            btn_label = "💻 View on GitHub"
            why_it_matters = "Provides an open-source, extensible foundation eliminating the need to reinvent complex model pipelines."
            cta = "Star the repository and explore the complete architecture guide below."
        elif category == ContentType.AI_TOOL:
            title = f"🛠 {core_title} — Next-Gen AI Tool"
            btn_label = "🛠 Try Tool"
            why_it_matters = "Streamlines developer friction and empowers engineers to build production applications faster."
            cta = "Explore the live tool, documentation, and playground in the link below."
        elif category == ContentType.HACKATHON:
            title = f"🏆 {core_title} Hackathon Open"
            btn_label = "🏆 Register Now"
            why_it_matters = "High-visibility launchpad to build frontier AI products and connect directly with hiring leads."
            cta = "Assemble your team and register before the deadline closes."
        else:
            title = f"🚀 {core_title}"
            btn_label = "📚 Read Source"
            why_it_matters = "Major technological milestone with direct implications for developers, researchers, and creators."
            cta = "Check out the official release notes and technical benchmarks below."

        opening = body_lines[1] if len(body_lines) > 1 and len(body_lines[1]) > 25 else (body_lines[0] if body_lines else f"A major development in {category.value.replace('_', ' ').title()} has been announced.")
        
        takeaways = []
        if len(body_lines) >= 3:
            for cand in body_lines[2:6]:
                if 20 <= len(cand) <= 180 and not cand.startswith("#"):
                    takeaways.append(cand.rstrip("."))
                if len(takeaways) >= 3:
                    break
        if not takeaways:
            takeaways = [
                "Crosses leading performance benchmarks in practical developer workflows",
                "Broad developer rollout beginning immediately with public access",
            ]

        takeaways_formatted = "\n".join(f"• {t}" for t in takeaways)
        body = (
            f"{opening}\n\n"
            f"⚡ <b>KEY TAKEAWAYS</b>\n"
            f"{takeaways_formatted}\n\n"
            f"💡 <b>WHY IT MATTERS</b>\n"
            f"{why_it_matters}\n\n"
            f"👉 <i>{cta}</i>"
        )
        hook = opening

    return {
        "content_type": category.value,
        "title": title,
        "body": body,
        "summary": hook,
        "takeaways": takeaways,
        "why_it_matters": why_it_matters,
        "cta": cta,
        "suggested_button_label": btn_label,
        "hashtags": ["AI", "Tech", category.value.replace("_", "")],
        "keywords": [source_name, category.value],
    }


# ─── 8. MASTER GENERATOR ORCHESTRATOR ─────────────────────────────────────────

async def generate_post_from_input(
    raw_input: str,
    category_override: str = "auto",
    notes: str = "",
    link: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Master pipeline:
    1. Extracts primary URL and scrapes metadata/content server-side.
    2. Calls Gemini API (or OpenAI-compatible API) for elite copywriting.
    3. Falls back gracefully to deterministic executive copywriter if offline.
    4. Constructs canonical PostSchema with action buttons, like reaction button, and discuss button.
    5. Runs Quality Analyzer & Visual concept suggestion.
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
    source_name = "Official Source"

    # Detect emails in input
    found_emails = extract_emails(clean_input)
    if not primary_url and found_emails:
        primary_email = found_emails[0]
        primary_url = get_email_compose_url(primary_email)
        source_name = f"Email: {primary_email}"

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

    # Step 1: Scrape URL if present (skip if primary_url is mail compose)
    url_data: Optional[Dict[str, Any]] = None
    if primary_url and "mail.google.com" not in primary_url:
        try:
            url_data = await fetch_and_clean_url(primary_url, timeout=2.0)
        except Exception as e:
            logger.warning(f"URL scraping unavailable for {primary_url}: {e}. Proceeding with user text.")
            url_data = None

    # Combine text context
    if url_data:
        title_hint = url_data["title"]
        source_name = url_data["site_name"]
        content_corpus = f"{url_data['title']}\n\n{notes}\n\n{url_data['text']}"
    else:
        if not source_name or source_name == "Official Source":
            if primary_url and "mail.google.com" not in primary_url:
                domain_match = re.search(r"https?://(?:www\.)?([^/]+)", primary_url)
                source_name = domain_match.group(1).capitalize() if domain_match else "Official Source"
            elif found_emails:
                source_name = f"Email: {found_emails[0]}"
            else:
                source_name = "Official Source"
        lines = [l.strip() for l in (text_without_urls or clean_input).splitlines() if l.strip()]
        title_hint = lines[0] if lines else f"{source_name} Update"
        content_corpus = f"{clean_input}\n\n{notes}" if notes else clean_input

    # Step 2: Detect category
    if category_override and category_override != "auto":
        try:
            category = ContentType(category_override)
            confidence = 1.0
            review_needed = False
        except ValueError:
            category, confidence, review_needed = detect_category(content_corpus, primary_url)
    else:
        category, confidence, review_needed = detect_category(content_corpus, primary_url)

    # Step 3: Generate copy via Gemini LLM (or Fallback Engine)
    llm_result = None
    active_key = (api_key or GEMINI_API_KEY).strip()
    if active_key:
        llm_result = await call_gemini_generator(
            content_corpus=content_corpus,
            primary_url=primary_url,
            category_hint=category.value,
            api_key=active_key,
            timeout=3.5,
        )

    # Try OpenAI-compatible secondary if Gemini key not set but OpenAI is
    if not llm_result and (OPENAI_API_KEY or OPENROUTER_API_KEY or DEEPSEEK_API_KEY):
        llm_result = await call_openai_compatible_generator(
            content_corpus=content_corpus,
            primary_url=primary_url,
            category_hint=category.value,
            api_key=OPENAI_API_KEY or OPENROUTER_API_KEY or DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL if DEEPSEEK_API_KEY else "https://api.openai.com/v1",
            model=LLM_MODEL_NAME,
            timeout=3.5,
        )

    # Use LLM output if valid, otherwise use deterministic copywriting engine
    if llm_result and "title" in llm_result and "body" in llm_result:
        post_title = llm_result.get("title", title_hint)
        post_body = llm_result.get("body", "")
        post_summary = llm_result.get("summary", post_title)
        post_takeaways = llm_result.get("takeaways", [])
        post_why_it_matters = llm_result.get("why_it_matters", "")
        post_cta = llm_result.get("cta", "")
        btn_label = llm_result.get("suggested_button_label", "")
        hashtags = llm_result.get("hashtags", [])
        keywords = llm_result.get("keywords", [])
        
        # Validate LLM content_type
        llm_cat = llm_result.get("content_type", "")
        try:
            if llm_cat:
                category = ContentType(llm_cat)
        except ValueError:
            pass
    else:
        det_result = _build_deterministic_copy(
            category=category,
            content_corpus=content_corpus,
            source_name=source_name,
            title_hint=title_hint,
            primary_url=primary_url,
        )
        post_title = det_result["title"]
        post_body = det_result["body"]
        post_summary = det_result["summary"]
        post_takeaways = det_result["takeaways"]
        post_why_it_matters = det_result["why_it_matters"]
        post_cta = det_result["cta"]
        btn_label = det_result["suggested_button_label"]
        hashtags = det_result["hashtags"]
        keywords = det_result["keywords"]

    # Hyperlink any email addresses in post_body to direct Gmail compose URL
    if found_emails:
        for em in found_emails:
            gmail_link = get_email_compose_url(em)
            if f'href="{gmail_link}"' not in post_body:
                post_body = re.sub(
                    rf'(?<![a-zA-Z0-9_.+-])({re.escape(em)})(?![^<]*>)',
                    rf'<a href="{gmail_link}">{em}</a>',
                    post_body
                )

    # Step 4: Construct Buttons
    buttons: List[InlineButton] = []
    if primary_url:
        is_email_url = "mail.google.com" in primary_url or primary_url.startswith("mailto:")
        if not btn_label:
            if is_email_url:
                if category == ContentType.JOB:
                    btn_label = "📩 Apply via Email"
                elif category == ContentType.INTERNSHIP:
                    btn_label = "🎓 Email Resume"
                else:
                    btn_label = "✉️ Send Email"
            elif category == ContentType.JOB:
                btn_label = "💼 Apply Now"
            elif category == ContentType.INTERNSHIP:
                btn_label = "🎓 Apply for Internship"
            elif category == ContentType.HACKATHON:
                btn_label = "🏆 Register Now"
            elif category == ContentType.GITHUB:
                btn_label = "💻 View on GitHub"
            elif category == ContentType.AI_TOOL:
                btn_label = "🛠 Try Tool"
            elif category == ContentType.CAREER:
                btn_label = "🚀 Read Guide"
            elif category == ContentType.RESOURCE:
                btn_label = "📖 Access Resource"
            else:
                btn_label = "📚 Read Source"
        buttons.append(InlineButton(text=btn_label, url=primary_url))

    # If primary was a web URL and an email was also found, add secondary email button
    if found_emails and primary_url and "mail.google.com" not in primary_url and not primary_url.startswith("mailto:"):
        email_to_use = found_emails[0]
        email_url = get_email_compose_url(email_to_use)
        email_btn_label = "📩 Email Resume" if category in (ContentType.JOB, ContentType.INTERNSHIP) else "✉️ Send Email"
        buttons.append(InlineButton(text=email_btn_label, url=email_url))

    # Real callback-based like button & discuss community button
    buttons.append(InlineButton(text="❤️ Like", callback_data="react_like"))
    buttons.append(InlineButton(text="💬 Discuss", url="https://t.me/heyaaashu"))

    # Step 5: Source & Verification
    source_obj = SourceInfo(
        title=source_name,
        url=primary_url or "",
        published_at=url_data.get("published_at") if url_data else None,
    ) if primary_url else None

    verification = VerificationInfo(
        status=VerificationStatus.VERIFIED if primary_url else VerificationStatus.NEEDS_VERIFICATION,
        sources=[primary_url] if primary_url else [],
        notes=f"Generated via Heyaaashu AI Engine ({input_type})",
    )

    # Step 6: 3-Hook Options
    hooks = generate_hook_options(post_title, content_corpus, category)

    # Assemble canonical PostSchema
    post = PostSchema(
        schema_version="1.0.0",
        content_type=category,
        title=post_title,
        body=post_body,
        summary=post_summary,
        takeaways=post_takeaways,
        why_it_matters=post_why_it_matters,
        cta=post_cta,
        parse_mode=ParseMode.HTML,
        buttons=buttons,
        source=source_obj,
        verification=verification,
        hashtags=hashtags,
        keywords=keywords,
        metadata={
            "input_type": input_type,
            "generated_at": int(time.time()),
            "detected_category": category.value,
            "llm_powered": bool(llm_result),
        },
    )

    # Step 7: Quality & Visual Suggestion
    quality = analyze_post_quality(post, has_source=bool(primary_url))
    visual = suggest_visual_concept(post)

    generation_meta = {
        "input_type": input_type,
        "detected_category": category.value,
        "category_confidence": confidence,
        "category_review_needed": review_needed,
        "hooks": [h.model_dump() for h in hooks],
        "source_name": source_name,
        "primary_url": primary_url,
        "llm_powered": bool(llm_result),
    }

    return {
        "post": post,
        "quality": quality.model_dump(),
        "generation": generation_meta,
        "visual": visual.model_dump(),
    }
