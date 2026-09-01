"""
AI Extractor Engine for Heyaaashu Studio.
Extracts facts, headlines, takeaways, buttons, and structured fields from raw text/URLs into PostSchema.
"""

import json
import re
from typing import Optional, Union
import httpx
from bs4 import BeautifulSoup

from packages.post_schema import ContentType, InlineButton, ParseMode, PostSchema, SourceInfo, VerificationInfo, VerificationStatus
from packages.shared.config import (
    ANTHROPIC_API_KEY,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    LLM_MODEL_NAME,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
)


def _extract_urls(text: str) -> list[str]:
    """Finds all HTTP/HTTPS URLs in text."""
    return re.findall(r"https?://[^\s<>\"']+", text)


async def fetch_url_metadata(url: str) -> dict:
    """Fetches title and snippet from a given URL."""
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (HeyaaashuStudio/1.0)"})
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else ""
                # Get meta description
                desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
                description = desc_tag.get("content", "").strip() if desc_tag else ""
                return {"title": title, "description": description, "url": url}
    except Exception:
        pass
    return {"title": "", "description": "", "url": url}


def _heuristic_extract(content_type: ContentType, raw_text: str, source_url: Optional[str] = None) -> PostSchema:
    """Fallback extraction when LLM is unavailable or for instant deterministic parsing."""
    lines = [line.strip() for line in raw_text.strip().split("\n") if line.strip()]
    first_line = lines[0] if lines else "New Update"
    
    # Remove URL if first line was just a URL
    if first_line.startswith("http://") or first_line.startswith("https://"):
        title = "Important Update"
        body_lines = lines
    else:
        title = first_line[:100]
        body_lines = lines[1:] if len(lines) > 1 else lines

    body_text = "\n".join(body_lines)
    if not body_text:
        body_text = title

    # Extract URLs from text
    found_urls = _extract_urls(raw_text)
    primary_url = source_url or (found_urls[0] if found_urls else None)
    
    buttons = []
    if primary_url:
        btn_text = "📚 Read Source"
        if content_type in [ContentType.JOB, ContentType.INTERNSHIP]:
            btn_text = "💼 Apply Now"
        elif content_type == ContentType.HACKATHON:
            btn_text = "🚀 Register"
        elif content_type == ContentType.AI_TOOL:
            btn_text = "🛠 Try Tool"
            
        buttons.append(InlineButton(text=btn_text, url=primary_url))

    # Clean body text formatting
    if content_type == ContentType.AI_NEWS:
        formatted_body = f"{body_text}\n\n⚡ <b>KEY TAKEAWAYS</b>\n• Timely industry insight\n• High practical relevance\n\n💡 <b>WHY IT MATTERS</b>\nCrucial update for tech & AI professionals."
    elif content_type == ContentType.JOB:
        formatted_body = f"<b>About the Role:</b>\n{body_text}\n\n📍 <b>Location:</b> Remote / Hybrid\n💼 <b>Role Type:</b> Full-Time\n📅 <b>Apply Before:</b> Rolling Basis"
    elif content_type == ContentType.INTERNSHIP:
        formatted_body = f"<b>Overview:</b>\n{body_text}\n\n🎓 <b>Target:</b> Students & Recent Graduates\n💰 <b>Stipend:</b> Competitive\n📅 <b>Deadline:</b> Open"
    elif content_type == ContentType.HACKATHON:
        formatted_body = f"<b>Details:</b>\n{body_text}\n\n🏆 <b>Prizes:</b> Cash + Mentorship\n👥 <b>Team Size:</b> 1-4 members\n🌐 <b>Location:</b> Online"
    elif content_type == ContentType.AI_TOOL:
        formatted_body = f"{body_text}\n\n🔥 <b>Best For:</b> Developers & Creators\n💰 <b>Pricing:</b> Freemium"
    else:
        formatted_body = body_text

    return PostSchema(
        content_type=content_type,
        title=title,
        body=formatted_body,
        parse_mode=ParseMode.HTML,
        source=SourceInfo(title="Official Source", url=primary_url) if primary_url else None,
        buttons=buttons,
        hashtags=[content_type.value.capitalize(), "Tech", "Careers"],
        keywords=[title],
        verification=VerificationInfo(
            status=VerificationStatus.VERIFIED if primary_url else VerificationStatus.NEEDS_VERIFICATION,
            sources=[primary_url] if primary_url else [],
        ),
    )


async def extract_post_schema_from_input(
    content_type: Union[ContentType, str],
    raw_input: str,
) -> PostSchema:
    """
    Main entry point: converts raw user input (text, link, or both) into a canonical PostSchema.
    """
    if isinstance(content_type, str):
        content_type = ContentType(content_type)

    urls = _extract_urls(raw_input)
    meta = None
    if urls:
        meta = await fetch_url_metadata(urls[0])

    # If LLM key is present, attempt LLM structured parsing
    if OPENAI_API_KEY or DEEPSEEK_API_KEY or OPENROUTER_API_KEY or ANTHROPIC_API_KEY:
        try:
            return await _llm_extract(content_type, raw_input, meta)
        except Exception:
            pass

    # Deterministic fallback
    primary_url = urls[0] if urls else None
    enhanced_input = raw_input
    if meta and meta.get("title") and len(raw_input.strip()) <= len(urls[0]) + 5:
        enhanced_input = f"{meta['title']}\n\n{meta.get('description', '')}\n\n{meta['url']}"

    return _heuristic_extract(content_type, enhanced_input, primary_url)


async def _llm_extract(content_type: ContentType, raw_input: str, meta: Optional[dict]) -> PostSchema:
    """Uses LLM to perform high-precision extraction into PostSchema."""
    prompt = f"""
You are an expert fact extractor and content writer for Telegram channel @Heyaashu.
Extract all solid facts from the raw input and structure them into JSON matching this exact PostSchema:

Content Type: {content_type.value}
Raw Input:
{raw_input}
URL Metadata: {json.dumps(meta) if meta else 'None'}

Return ONLY a JSON object with keys:
- "title": concise factual headline (no clickbait)
- "body": formatted body text using HTML tags (<b>, <i>, <code>, <a href>). NEVER leak raw unclosed tags.
- "source": {{"title": "...", "url": "..."}} or null
- "buttons": [{{"text": "...", "url": "..."}}]
- "hashtags": ["tag1", "tag2"]
- "verification": {{"status": "verified", "sources": ["..."]}}
"""
    # Simple OpenAI / DeepSeek API invocation via httpx
    if OPENAI_API_KEY:
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            data = res.json()["choices"][0]["message"]["content"]
            parsed = json.loads(data)
            parsed["content_type"] = content_type.value
            parsed["parse_mode"] = "HTML"
            return PostSchema(**parsed)

    raise NotImplementedError("LLM Provider not configured")
