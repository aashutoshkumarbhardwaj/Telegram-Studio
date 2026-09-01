import { describe, it, expect } from 'vitest';
import { formatPostHtml } from '@/lib/templates';
import { PostSchema } from '@/types/postSchema';

describe('Heyaaashu Visual Content Studio — Formatting & Templates', () => {
  it('formats AI News template with key takeaways and why it matters', () => {
    const post: PostSchema = {
      content_type: 'ai_news',
      title: 'DeepMind Gemini 2.5 Announcement',
      body: 'Google announced multimodal models.',
      takeaways: ['Faster reasoning', 'Sub-second audio'],
      why_it_matters: 'Transforms developer experience.',
    };

    const html = formatPostHtml(post, 'ai_news');
    expect(html).toContain('🚨 <b>AI NEWS</b>');
    expect(html).toContain('🔥 <b>DeepMind Gemini 2.5 Announcement</b>');
    expect(html).toContain('⚡ <b>KEY TAKEAWAYS</b>');
    expect(html).toContain('• Faster reasoning');
    expect(html).toContain('💡 <b>WHY IT MATTERS</b>');
  });

  it('formats Job template with metadata and omission of missing fields', () => {
    const post: PostSchema = {
      content_type: 'job',
      title: 'Senior ML Engineer',
      body: 'Work on post-training.',
      metadata: {
        company: 'Mistral AI',
        location: 'Paris / Remote',
      },
    };

    const html = formatPostHtml(post, 'job');
    expect(html).toContain('💼 <b>JOB ALERT</b>');
    expect(html).toContain('🏢 <b>Company:</b> Mistral AI');
    expect(html).toContain('📍 <b>Location:</b> Paris / Remote');
    // Salary was not provided so it must NOT appear
    expect(html).not.toContain('Salary:');
    expect(html).not.toContain('N/A');
  });

  it('formats AI Tool template with pricing and features', () => {
    const post: PostSchema = {
      content_type: 'ai_tool',
      title: 'Browser-Use 2.0',
      body: 'Open source browser agent.',
      takeaways: ['Full DOM navigation', 'Vision grounding'],
      why_it_matters: 'Enables web automations.',
      metadata: {
        pricing: 'Open Source (MIT)',
      },
    };

    const html = formatPostHtml(post, 'ai_tool');
    expect(html).toContain('🛠 <b>AI TOOL</b>');
    expect(html).toContain('🔥 <b>Browser-Use 2.0</b>');
    expect(html).toContain('⚡ <b>WHAT IT DOES</b>');
    expect(html).toContain('💰 <b>PRICING</b>');
    expect(html).toContain('Open Source (MIT)');
  });
});
