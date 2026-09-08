import { describe, it, expect } from 'vitest';
import {
  extractUrls,
  extractImageUrl,
  getDomainSourceTitle,
  detectCategory,
  cleanHeadline,
  extractTakeaways,
  extractWhyItMatters,
  buildButtons,
  smartExtractPost,
} from '../smartExtractor';

describe('smartExtractor unit tests', () => {
  describe('extractUrls', () => {
    it('extracts all http/https URLs and deduplicates them', () => {
      const text = 'Check out https://blog.google/technology and also https://github.com/google and repeat https://blog.google/technology';
      const urls = extractUrls(text);
      expect(urls).toEqual(['https://blog.google/technology', 'https://github.com/google']);
    });

    it('returns empty array when no URLs present', () => {
      expect(extractUrls('Just some text without any links')).toEqual([]);
    });
  });

  describe('extractImageUrl', () => {
    it('finds image URL with supported extensions', () => {
      const text = 'Here is a photo: https://example.com/assets/banner.png?v=2 for the announcement.';
      expect(extractImageUrl(text)).toBe('https://example.com/assets/banner.png?v=2');
    });

    it('returns null if no image URL present', () => {
      expect(extractImageUrl('https://example.com/article')).toBeNull();
    });
  });

  describe('getDomainSourceTitle', () => {
    it('maps known domains to clean titles', () => {
      expect(getDomainSourceTitle('https://github.com/facebook/react')).toBe('GitHub');
      expect(getDomainSourceTitle('https://blog.google/technology/ai/')).toBe('Google DeepMind');
      expect(getDomainSourceTitle('https://openai.com/index/gpt-4o/')).toBe('OpenAI');
      expect(getDomainSourceTitle('https://techcrunch.com/2026/01/01/ai')).toBe('TechCrunch');
      expect(getDomainSourceTitle('https://huggingface.co/models')).toBe('Hugging Face');
    });

    it('capitalizes unknown hostnames nicely', () => {
      expect(getDomainSourceTitle('https://news.ycombinator.com')).toBe('Hacker News');
      expect(getDomainSourceTitle('https://venturebeat.com/ai/something')).toBe('Venturebeat');
    });
  });

  describe('detectCategory', () => {
    it('detects job posts', () => {
      const text = 'We are hiring a Senior Distributed Systems Engineer! Full-time role, salary $200k+';
      expect(detectCategory(text)).toBe('job');
    });

    it('detects internship posts', () => {
      const text = 'Summer 2026 AI Research Internship for pre-final year students with competitive stipend.';
      expect(detectCategory(text)).toBe('internship');
    });

    it('detects hackathon announcements', () => {
      const text = 'Announcing the Global Agent Hackathon! $100,000 prize pool. Register your team on Devpost.';
      expect(detectCategory(text)).toBe('hackathon');
    });

    it('detects ai tools', () => {
      const text = 'Launching our new AI tool for automated code reviews. Free tier available on Product Hunt.';
      expect(detectCategory(text)).toBe('ai_tool');
    });

    it('detects GitHub repositories', () => {
      const text = 'Check out this new repo on github.com/openai/swarm with 5000 stars.';
      expect(detectCategory(text)).toBe('github');
    });

    it('defaults to ai_news for general announcements', () => {
      const text = 'Anthropic announced Claude 3.5 Sonnet benchmark results across coding benchmarks.';
      expect(detectCategory(text)).toBe('ai_news');
    });
  });

  describe('cleanHeadline', () => {
    it('strips common clickbait/alert prefixes', () => {
      const lines = ['🚨 BREAKING: Google DeepMind Unveils Next-Gen Reasoning Architecture.'];
      const headline = cleanHeadline(lines, 'ai_news');
      expect(headline).toBe('Google DeepMind Unveils Next-Gen Reasoning Architecture');
    });

    it('cleans speech prefixes', () => {
      const lines = ['Google announces that new multimodal features are now live.'];
      const headline = cleanHeadline(lines, 'ai_news');
      expect(headline).toBe('Google Unveils new multimodal features are now live');
    });

    it('skips standalone URL line to find real title', () => {
      const lines = ['https://blog.google/gemini', 'Gemini 2.5 Flash Released with Extreme Low Latency'];
      const headline = cleanHeadline(lines, 'ai_news');
      expect(headline).toBe('Gemini 2.5 Flash Released with Extreme Low Latency');
    });
  });

  describe('extractTakeaways', () => {
    it('extracts bullet points with bullet characters', () => {
      const lines = [
        'Headline here',
        '• First key feature announced today.',
        '• Second major performance improvement across benchmarks.',
        '• Third developer API rollout schedule.',
      ];
      const takeaways = extractTakeaways(lines, 'ai_news');
      expect(takeaways.length).toBe(3);
      expect(takeaways[0]).toBe('First key feature announced today');
      expect(takeaways[1]).toBe('Second major performance improvement across benchmarks');
    });

    it('provides high quality defaults if input is short', () => {
      const takeaways = extractTakeaways(['Short text'], 'job');
      expect(takeaways.length).toBeGreaterThanOrEqual(2);
      expect(takeaways[0]).toContain('engineering role');
    });
  });

  describe('buildButtons', () => {
    it('constructs primary button with contextual emoji, like button, and discuss button', () => {
      const buttons = buildButtons('https://example.com/apply', 'job');
      expect(buttons).toHaveLength(3);
      expect(buttons[0].text).toBe('💼 Apply Now');
      expect(buttons[0].url).toBe('https://example.com/apply');
      expect(buttons[1].text).toBe('❤️ Like');
      expect(buttons[1].callback_data).toBe('react_like');
      expect(buttons[2].text).toBe('💬 Discuss');
      expect(buttons[2].url).toBe('https://t.me/heyaaashu');
    });

    it('handles missing primaryUrl by including like and discuss buttons', () => {
      const buttons = buildButtons(undefined, 'ai_news');
      expect(buttons).toHaveLength(2);
      expect(buttons[0].text).toBe('❤️ Like');
      expect(buttons[1].text).toBe('💬 Discuss');
    });
  });

  describe('smartExtractPost master pipeline', () => {
    it('turns raw article text into canonical PostSchema with URL and Like buttons', () => {
      const raw = `Google Unveils Gemini 2.5 With Native Audio Streaming
Google has announced Gemini 2.5, delivering sub-second voice perception.
• Native real-time streaming audio and video perception.
• 2x throughput with lower inference latency.
• Full enterprise developer API availability starting today.
Why it matters: Accelerates the transition to real-time multimodal voice interfaces.
Official link: https://blog.google/technology/ai/gemini-2-5/`;

      const post = smartExtractPost(raw);

      expect(post.content_type).toBe('ai_news');
      expect(post.title).toBe('Google Unveils Gemini 2.5 With Native Audio Streaming');
      expect(post.takeaways).toHaveLength(3);
      expect(post.takeaways?.[0]).toBe('Native real-time streaming audio and video perception');
      expect(post.source?.title).toBe('Google DeepMind');
      expect(post.source?.url).toBe('https://blog.google/technology/ai/gemini-2-5/');
      expect(post.verification?.status).toBe('verified');
      expect(post.buttons).toHaveLength(3);
      expect(post.buttons?.[0].url).toBe('https://blog.google/technology/ai/gemini-2-5/');
      expect(post.buttons?.[0].text).toBe('📚 Read Source');
      expect(post.buttons?.[1].text).toBe('❤️ Like');
      expect(post.buttons?.[1].callback_data).toBe('react_like');
      expect(post.body).toContain('Native real-time streaming audio and video perception');
      expect(post.body).toContain('href="https://blog.google/technology/ai/gemini-2-5/"');
    });

    it('honors explicitLink parameter even if text does not contain URL', () => {
      const raw = `Senior ML Platform Engineer
We are looking for an experienced ML engineer to scale our GPU clusters.
Competitive salary $220k - $280k + equity.`;

      const explicitLink = 'https://jobs.lever.co/company/ml-engineer';
      const post = smartExtractPost(raw, { explicitLink });

      expect(post.content_type).toBe('job');
      expect(post.source?.url).toBe(explicitLink);
      expect(post.buttons?.[0].text).toBe('💼 Apply Now');
      expect(post.buttons?.[0].url).toBe(explicitLink);
      expect(post.buttons?.[1].text).toBe('❤️ Like');
    });
  });
});
