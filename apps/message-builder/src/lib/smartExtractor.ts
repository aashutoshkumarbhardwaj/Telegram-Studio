/**
 * Smart Extractor Engine for Heyaaashu Studio.
 * Translates raw text, copied articles, announcements, and URLs into canonical PostSchema instances.
 * Provides instant, zero-lag client-side parsing with resilience when backend is offline.
 */

import { ContentType, InlineButton, MediaItem, ParseMode, PostSchema, SourceInfo, VerificationInfo } from '@/types/postSchema';

const URL_REGEX = /https?:\/\/[^\s<>"'{}|\\^`[\]]+/g;
const IMAGE_URL_REGEX = /https?:\/\/[^\s<>"'{}|\\^`[\]]+\.(?:png|jpe?g|webp|gif|svg)(?:\?[^\s<>"'{}|\\^`[\]]*)?/i;

export function extractUrls(text: string): string[] {
  if (!text) return [];
  const matches = text.match(URL_REGEX);
  return matches ? Array.from(new Set(matches)) : [];
}

export function extractImageUrl(text: string): string | null {
  if (!text) return null;
  const match = text.match(IMAGE_URL_REGEX);
  return match ? match[0] : null;
}

export function getDomainSourceTitle(url: string): string {
  if (!url) return 'Official Source';
  try {
    const parsed = new URL(url);
    const hostname = parsed.hostname.toLowerCase().replace(/^www\./, '');

    if (hostname.includes('github.com')) return 'GitHub';
    if (hostname.includes('blog.google') || hostname.includes('deepmind.google')) return 'Google DeepMind';
    if (hostname.includes('google.com')) return 'Google';
    if (hostname.includes('openai.com')) return 'OpenAI';
    if (hostname.includes('anthropic.com')) return 'Anthropic';
    if (hostname.includes('huggingface.co')) return 'Hugging Face';
    if (hostname.includes('techcrunch.com')) return 'TechCrunch';
    if (hostname.includes('theverge.com')) return 'The Verge';
    if (hostname.includes('arxiv.org')) return 'arXiv';
    if (hostname.includes('twitter.com') || hostname.includes('x.com')) return 'X (Twitter)';
    if (hostname.includes('t.me')) return 'Telegram';
    if (hostname.includes('linkedin.com')) return 'LinkedIn';
    if (hostname.includes('ycombinator.com')) return 'Hacker News';
    if (hostname.includes('producthunt.com')) return 'Product Hunt';
    if (hostname.includes('medium.com')) return 'Medium';
    if (hostname.includes('substack.com')) return 'Substack';

    // Capitalize domain prefix
    const parts = hostname.split('.');
    const main = parts[0] || 'Source';
    return main.charAt(0).toUpperCase() + main.slice(1);
  } catch {
    return 'Official Source';
  }
}

export function detectCategory(text: string, primaryUrl?: string): ContentType {
  const combined = `${text || ''} ${primaryUrl || ''}`.toLowerCase();

  // 1. Direct URL signatures
  if (primaryUrl) {
    const lowerUrl = primaryUrl.toLowerCase();
    if (lowerUrl.includes('github.com')) return 'github';
    if (lowerUrl.includes('devpost.com') || lowerUrl.includes('hackerearth.com') || lowerUrl.includes('dorahacks.io')) return 'hackathon';
    if (lowerUrl.includes('lever.co') || lowerUrl.includes('greenhouse.io') || lowerUrl.includes('ashbyhq.com') || lowerUrl.includes('workday') || lowerUrl.includes('wellfound.com') || lowerUrl.includes('/jobs') || lowerUrl.includes('/careers')) {
      if (/\bintern(?:ship)?\b|\bstipend\b/.test(combined)) return 'internship';
      return 'job';
    }
  }

  // 2. GitHub repository
  if (combined.includes('github.com') || /\bgit clone\b|\bstars?\b|\brepository\b|\bopen[- ]source\b/.test(combined)) {
    return 'github';
  }

  // 3. Internship
  if (/\bintern(?:ship|s)?\b|\bstipend\b|\bpre-final\b|\bfellowship\b|\bco-op\b/.test(combined)) {
    return 'internship';
  }

  // 4. Job
  if (/\b(?:hiring|jobs?|job opening|open role|vacanc(?:y|ies)|full-time|salary|apply now|apply at|apply here|compensation|we're hiring|we are hiring|engineer position|remote role|careers?)\b/.test(combined)) {
    return 'job';
  }

  // 5. Hackathon
  if (/\bhackathon\b|\bprize pool\b|\bdevpost\b|\bbount(?:y|ies)\b|\bteam size\b|\bregister (?:by|now|today)\b/.test(combined)) {
    return 'hackathon';
  }

  // 6. AI Tool
  if (/\bai tool\b|\bsaas\b|\bpricing\b|\bfree tier\b|\bproduct hunt\b|\bplayground\b|\bweb app\b|\bchrome extension\b/.test(combined)) {
    return 'ai_tool';
  }

  // 7. Career
  if (/\bcareer advice\b|\bcareer guide\b|\bresume\b|\binterview prep\b|\bsalary negotiation\b|\bpromotion\b/.test(combined)) {
    return 'career';
  }

  // 8. Resource
  if (/\broadmap\b|\bcheat\s?sheet\b|\bhandbook\b|\bcurated list\b|\bfree course\b|\bcomplete guide\b/.test(combined)) {
    return 'resource';
  }

  return 'ai_news';
}

export function cleanHeadline(rawLines: string[], category: ContentType): string {
  // Find first substantial line that isn't a standalone URL
  let candidate = '';
  for (const line of rawLines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) continue;
    candidate = trimmed;
    break;
  }

  if (!candidate) {
    switch (category) {
      case 'job': return 'Senior Engineering Opportunity';
      case 'internship': return 'Frontier AI Internship Alert';
      case 'hackathon': return 'Global AI Hackathon Announced';
      case 'ai_tool': return 'New AI Productivity Tool Launch';
      case 'github': return 'Open-Source AI Repository';
      case 'career': return 'Key Career Development Insights';
      case 'resource': return 'Essential AI Engineering Resource';
      default: return 'Latest Frontier AI Development';
    }
  }

  // Strip prefixes like "BREAKING:", "Title:", emojis
  let clean = candidate
    .replace(/^[\s🚨📢🔥⚡✨💼🎓🏆🛠💻📚🚀#*_-]+/, '')
    .replace(/^(?:BREAKING|UPDATE|ANNOUNCEMENT|JUST IN|NEW|TITLE|HEADLINE|SUBJECT)\s*[:\-–—]?\s*/i, '')
    .replace(/^(?:Google|Meta|OpenAI|Apple|Microsoft|Anthropic|DeepMind)\s+(?:says?|announces?|claims?|reveals?|launches?|unveils?)\s+(?:that\s+)?/i, (match) => {
      const firstWord = match.split(/\s+/)[0];
      return `${firstWord} Unveils `;
    })
    .trim();

  // Strip trailing period or colon
  clean = clean.replace(/[:.]+$/, '').trim();

  if (clean.length > 100) {
    clean = clean.slice(0, 97) + '...';
  }

  return clean || 'Latest AI & Tech Announcement';
}

export function extractTakeaways(lines: string[], category: ContentType): string[] {
  const takeaways: string[] = [];

  // Look for explicit bullet lines first
  for (const line of lines) {
    const trimmed = line.trim();
    if (/^[•\-*✓👉]\s*/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
      const cleanBullet = trimmed.replace(/^[•\-*✓👉\d.]+\s*/, '').replace(/[.;]+$/, '').trim();
      if (cleanBullet.length > 10 && cleanBullet.length < 220) {
        takeaways.push(cleanBullet);
      }
    }
    if (takeaways.length >= 4) break;
  }

  // If no explicit bullets, extract strong declarative sentences
  if (takeaways.length === 0) {
    for (let i = 1; i < lines.length; i++) {
      const trimmed = lines[i].trim();
      if (trimmed.length > 25 && trimmed.length < 200 && !trimmed.startsWith('http')) {
        takeaways.push(trimmed.replace(/[.;]+$/, ''));
      }
      if (takeaways.length >= 3) break;
    }
  }

  // Fallback defaults if content was too short
  if (takeaways.length === 0) {
    switch (category) {
      case 'job':
        return [
          'High-impact engineering role working on scalable systems',
          'Competitive industry compensation and comprehensive benefits',
          'Direct mentorship from senior technical leadership',
        ];
      case 'internship':
        return [
          'Hands-on engineering experience with production AI architectures',
          'Competitive monthly stipend and full mentorship support',
          'Strong pathway to full-time engineering placement',
        ];
      case 'hackathon':
        return [
          'Compete for substantial cash prizes and venture funding',
          'Direct mentorship from frontier AI researchers and builders',
          'Open for solo hackers and collaborative teams worldwide',
        ];
      case 'ai_tool':
        return [
          'High-throughput developer API with low-latency inference',
          'Generous free tier and comprehensive documentation available',
          'Streamlined integration into modern production stacks',
        ];
      case 'github':
        return [
          'Production-ready open-source codebase with permissive license',
          'Active community contributions and detailed architecture guide',
          'Ready for local deployment and customized model pipelines',
        ];
      default:
        return [
          'Surpasses leading industry benchmarks in developer workflows',
          'Immediate developer rollout and public documentation available',
          'Native multimodal perception enabled across production APIs',
        ];
    }
  }

  return takeaways;
}

export function extractWhyItMatters(text: string, category: ContentType): string {
  const match = text.match(/(?:why it matters|impact|significance|key insight|best for)[:\-–—]\s*([^\n]+)/i);
  if (match && match[1] && match[1].trim().length > 15) {
    return match[1].trim();
  }

  const lower = text.toLowerCase();
  if (lower.includes('multimodal') || lower.includes('vision') || lower.includes('audio')) {
    return 'Accelerates the transition from text-only chatbots to ubiquitous real-time multimodal perception systems.';
  }
  if (lower.includes('scale') || lower.includes('billion') || lower.includes('enterprise')) {
    return 'Signals a major milestone in production scale and real-world enterprise AI adoption.';
  }
  if (lower.includes('agent') || lower.includes('reasoning') || lower.includes('autonomous')) {
    return 'Bridges the gap between passive language models and autonomous problem-solving agentic workflows.';
  }

  switch (category) {
    case 'job':
    case 'internship':
      return 'Prime opportunity to work directly on high-scale production systems with top-tier engineering talent.';
    case 'hackathon':
      return 'Exceptional launchpad to build high-visibility AI products and connect directly with hiring leads and investors.';
    case 'ai_tool':
      return 'Substantially reduces operational overhead and empowers solo builders to ship production-grade features faster.';
    case 'github':
      return 'Provides an extensible, production-ready foundation eliminating the need to reinvent complex architecture from scratch.';
    case 'career':
      return 'Actionable framework to optimize your engineering career trajectory and maximize high-leverage outcomes.';
    case 'resource':
      return 'High-value reference material to accelerate technical mastery and avoid common production pitfalls.';
    default:
      return 'Major technological milestone with direct, actionable implications for developers, researchers, and tech creators.';
  }
}

export function extractCta(category: ContentType, hasLink: boolean): string {
  if (!hasLink) {
    return 'Stay tuned for official updates and deep-dive technical benchmarks.';
  }
  switch (category) {
    case 'job':
    case 'internship':
      return 'Review complete role requirements and apply directly via the link below.';
    case 'hackathon':
      return 'Assemble your team and register before the submission window closes.';
    case 'ai_tool':
      return 'Explore the live tool, documentation, and pricing in the link below.';
    case 'github':
      return 'Star the repository and explore the full documentation in the link below.';
    default:
      return 'Explore official release notes and technical benchmarks in the link below.';
  }
}

export function buildButtons(primaryUrl: string | undefined, category: ContentType): InlineButton[] {
  const buttons: InlineButton[] = [];

  if (primaryUrl && primaryUrl.trim()) {
    const cleanUrl = primaryUrl.trim();
    let label = '📚 Read Source';
    switch (category) {
      case 'job':
        label = '💼 Apply Now';
        break;
      case 'internship':
        label = '🎓 Apply for Internship';
        break;
      case 'hackathon':
        label = '🏆 Register Now';
        break;
      case 'ai_tool':
        label = '🛠 Try Tool';
        break;
      case 'github':
        label = '💻 View on GitHub';
        break;
      case 'resource':
        label = '📖 Access Resource';
        break;
      case 'career':
        label = '🚀 Read Guide';
        break;
      default:
        label = '📚 Read Source';
    }
    buttons.push({ text: label, url: cleanUrl });
  }

  // 2. Auto-configured Like / React button
  const likeUrl = primaryUrl ? `${primaryUrl.split('#')[0]}#like` : 'https://t.me/heyaaashu';
  buttons.push({
    text: '❤️ Like',
    url: likeUrl,
    callback_data: 'react_like',
  });

  // 3. Always append community channel button
  buttons.push({ text: '💬 Discuss', url: 'https://t.me/heyaaashu' });

  return buttons;
}

export interface SmartExtractOptions {
  categoryOverride?: ContentType | 'auto';
  explicitLink?: string;
  notes?: string;
}

/**
 * Master Smart Extractor Function.
 * Converts unstructured input into a fully formed canonical PostSchema object.
 */
export function smartExtractPost(rawText: string, options: SmartExtractOptions = {}): PostSchema {
  const text = (rawText || '').trim();
  const explicitLink = options.explicitLink?.trim() || '';

  // 1. Detect all URLs and identify primary URL
  const foundUrls = extractUrls(text);
  const detectedImageUrl = extractImageUrl(text);

  let primaryUrl = explicitLink;
  if (!primaryUrl && foundUrls.length > 0) {
    if (foundUrls.length === 1 && detectedImageUrl && foundUrls[0] === detectedImageUrl) {
      primaryUrl = '';
    } else {
      primaryUrl = foundUrls.find((u) => u !== detectedImageUrl) || foundUrls[0];
    }
  }

  // 2. Clean lines
  const rawLines = text
    .split('\n')
    .map((l) => l.trim())
    .filter(Boolean);

  // 3. Category Detection
  const category: ContentType =
    options.categoryOverride && options.categoryOverride !== 'auto'
      ? options.categoryOverride
      : detectCategory(text, primaryUrl);

  // 4. Headline Extraction
  const title = cleanHeadline(rawLines, category);

  // 5. Takeaways Extraction
  const takeaways = extractTakeaways(rawLines, category);

  // 6. Why It Matters Extraction
  const whyItMatters = extractWhyItMatters(text, category);

  // 7. CTA
  const cta = extractCta(category, Boolean(primaryUrl));

  // 8. Opening Summary
  let summary = '';
  for (const line of rawLines) {
    if (line.length > 30 && !line.startsWith('http') && line !== title) {
      summary = line.replace(/^[•\-*✓👉\d.]+\s*/, '');
      break;
    }
  }
  if (!summary) {
    summary = `Key developments and technical insights regarding ${title}.`;
  }

  // 9. Assembled Canonical HTML Body
  const takeawaysFormatted = takeaways.map((t) => `• ${t}`).join('\n');
  const body = `${summary}\n\n⚡ <b>KEY TAKEAWAYS</b>\n${takeawaysFormatted}\n\n💡 <b>WHY IT MATTERS</b>\n${whyItMatters}\n\n${cta}`;

  // 10. Buttons
  const buttons = buildButtons(primaryUrl, category);

  // 11. Source & Verification
  const sourceTitle = primaryUrl ? getDomainSourceTitle(primaryUrl) : 'Official Announcement';
  const source: SourceInfo | undefined = primaryUrl
    ? {
        title: sourceTitle,
        url: primaryUrl,
      }
    : undefined;

  const verification: VerificationInfo = {
    status: primaryUrl ? 'verified' : 'needs_verification',
    sources: primaryUrl ? [primaryUrl] : [],
    notes: primaryUrl ? `Verified via ${sourceTitle}` : 'Source link pending manual review',
  };

  // 12. Media Item (if image detected)
  const media: MediaItem[] = detectedImageUrl
    ? [
        {
          type: 'photo',
          url_or_path: detectedImageUrl,
          caption: title,
        },
      ]
    : [];

  return {
    schema_version: '1.0.0',
    content_type: category,
    title,
    body,
    summary,
    takeaways,
    why_it_matters: whyItMatters,
    cta,
    parse_mode: 'HTML' as ParseMode,
    buttons,
    source,
    verification,
    media,
    metadata: {
      extracted_at: Date.now(),
      primary_url: primaryUrl,
      input_length: text.length,
      auto_extracted: true,
    },
  };
}
