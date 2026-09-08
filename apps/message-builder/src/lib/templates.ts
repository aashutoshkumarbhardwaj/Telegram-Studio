/**
 * Dedicated Template Formatting Engine for Heyaaashu Visual Content Studio.
 * Matches backend packages/formatter/telegram_formatter.py logic.
 */

import { ContentType, PostSchema } from '@/types/postSchema';

export type TemplateStyle =
  | 'auto'
  | 'ai_news'
  | 'job'
  | 'internship'
  | 'hackathon'
  | 'ai_tool'
  | 'github'
  | 'career'
  | 'resource';

export function escapeHtml(text: string): string {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

export function formatPostHtml(post: PostSchema, templateOverride?: TemplateStyle): string {
  const tpl = (!templateOverride || templateOverride === 'auto') ? post.content_type : templateOverride;

  switch (tpl) {
    case 'ai_news':
      return formatAiNewsTemplate(post);
    case 'job':
      return formatJobTemplate(post);
    case 'internship':
      return formatInternshipTemplate(post);
    case 'hackathon':
      return formatHackathonTemplate(post);
    case 'ai_tool':
      return formatAiToolTemplate(post);
    case 'github':
      return formatGitHubTemplate(post);
    case 'career':
      return formatCareerTemplate(post);
    case 'resource':
      return formatResourceTemplate(post);
    default:
      return formatAiNewsTemplate(post);
  }
}

function formatAiNewsTemplate(post: PostSchema): string {
  const parts: string[] = ['🚨 <b>AI NEWS</b>\n'];
  parts.push(`🔥 <b>${escapeHtml(post.title)}</b>\n`);

  if (post.body && post.body.trim()) {
    parts.push(post.body.trim() + '\n');
  } else if (post.summary) {
    parts.push(`${escapeHtml(post.summary)}\n`);
  }

  if (post.takeaways && post.takeaways.length > 0 && (!post.body || !post.body.includes('KEY TAKEAWAYS'))) {
    parts.push('⚡ <b>KEY TAKEAWAYS</b>');
    for (const t of post.takeaways) {
      if (t.trim()) parts.push(`• ${escapeHtml(t.trim())}`);
    }
    parts.push('');
  }

  if (post.why_it_matters && (!post.body || !post.body.includes(post.why_it_matters))) {
    parts.push('💡 <b>WHY IT MATTERS</b>');
    parts.push(`${escapeHtml(post.why_it_matters)}\n`);
  }

  if (post.cta && (!post.body || !post.body.includes(post.cta))) {
    parts.push(`👉 ${escapeHtml(post.cta)}\n`);
  }

  parts.push('━━━━━━━━━━━━━━\n');
  parts.push('📚 <b>SOURCE</b>');

  return parts.join('\n');
}

function formatJobTemplate(post: PostSchema): string {
  const meta = post.metadata || {};
  const parts: string[] = ['💼 <b>JOB ALERT</b>\n'];
  parts.push(`🔥 <b>${escapeHtml(post.title)}</b>\n`);

  const details: string[] = [];
  if (meta.company) details.push(`🏢 <b>Company:</b> ${escapeHtml(meta.company)}`);
  if (meta.location) details.push(`📍 <b>Location:</b> ${escapeHtml(meta.location)}`);
  if (meta.eligibility) details.push(`🎓 <b>Eligibility:</b> ${escapeHtml(meta.eligibility)}`);
  if (meta.salary && meta.salary !== 'N/A') details.push(`💰 <b>Salary:</b> ${escapeHtml(meta.salary)}`);
  if (meta.deadline && meta.deadline !== 'N/A') details.push(`📅 <b>Deadline:</b> ${escapeHtml(meta.deadline)}`);

  if (details.length > 0) {
    parts.push(details.join('\n') + '\n');
  }

  if (post.body && post.body.trim()) {
    parts.push(post.body.trim() + '\n');
  } else if (post.takeaways && post.takeaways.length > 0) {
    parts.push("🧩 <b>WHAT YOU'LL DO</b>");
    for (const t of post.takeaways) {
      if (t.trim()) parts.push(`• ${escapeHtml(t.trim())}`);
    }
    parts.push('');
  }

  if (post.why_it_matters && (!post.body || !post.body.includes(post.why_it_matters))) {
    parts.push('🎯 <b>WHO SHOULD APPLY</b>');
    parts.push(`${escapeHtml(post.why_it_matters)}\n`);
  }

  return parts.join('\n');
}

function formatInternshipTemplate(post: PostSchema): string {
  const meta = post.metadata || {};
  const parts: string[] = ['🎓 <b>INTERNSHIP ALERT</b>\n'];
  parts.push(`🔥 <b>${escapeHtml(post.title)}</b>\n`);

  const details: string[] = [];
  if (meta.company) details.push(`🏢 <b>Company:</b> ${escapeHtml(meta.company)}`);
  if (meta.location) details.push(`📍 <b>Location:</b> ${escapeHtml(meta.location)}`);
  if (meta.stipend && meta.stipend !== 'N/A') details.push(`💰 <b>Stipend:</b> ${escapeHtml(meta.stipend)}`);
  if (meta.eligibility) details.push(`🎓 <b>Eligibility:</b> ${escapeHtml(meta.eligibility)}`);
  if (meta.deadline && meta.deadline !== 'N/A') details.push(`📅 <b>Deadline:</b> ${escapeHtml(meta.deadline)}`);

  if (details.length > 0) {
    parts.push(details.join('\n') + '\n');
  }

  if (post.body && post.body.trim()) {
    parts.push(post.body.trim() + '\n');
  } else if (post.takeaways && post.takeaways.length > 0) {
    parts.push('⚡ <b>PROGRAM HIGHLIGHTS</b>');
    for (const t of post.takeaways) {
      if (t.trim()) parts.push(`• ${escapeHtml(t.trim())}`);
    }
    parts.push('');
  }

  if (post.why_it_matters && (!post.body || !post.body.includes(post.why_it_matters))) {
    parts.push('💡 <b>LEARNING OPPORTUNITY</b>');
    parts.push(`${escapeHtml(post.why_it_matters)}\n`);
  }

  return parts.join('\n');
}

function formatHackathonTemplate(post: PostSchema): string {
  const meta = post.metadata || {};
  const parts: string[] = ['🏆 <b>HACKATHON</b>\n'];
  parts.push(`🔥 <b>${escapeHtml(post.title)}</b>\n`);

  const details: string[] = [];
  if (meta.prize) details.push(`💰 <b>Prize:</b> ${escapeHtml(meta.prize)}`);
  if (meta.deadline) details.push(`📅 <b>Deadline:</b> ${escapeHtml(meta.deadline)}`);
  if (meta.team_size) details.push(`👥 <b>Team Size:</b> ${escapeHtml(meta.team_size)}`);
  if (meta.location) details.push(`🌐 <b>Location:</b> ${escapeHtml(meta.location)}`);

  if (details.length > 0) {
    parts.push(details.join('\n') + '\n');
  }

  if (post.body && post.body.trim()) {
    parts.push(post.body.trim() + '\n');
  } else if (post.takeaways && post.takeaways.length > 0) {
    parts.push('💡 <b>WHAT TO BUILD</b>');
    for (const t of post.takeaways) {
      if (t.trim()) parts.push(`• ${escapeHtml(t.trim())}`);
    }
    parts.push('');
  }

  if (post.why_it_matters && (!post.body || !post.body.includes(post.why_it_matters))) {
    parts.push('🎯 <b>WHY JOIN</b>');
    parts.push(`${escapeHtml(post.why_it_matters)}\n`);
  }

  return parts.join('\n');
}

function formatAiToolTemplate(post: PostSchema): string {
  const meta = post.metadata || {};
  const parts: string[] = ['🛠 <b>AI TOOL</b>\n'];
  parts.push(`🔥 <b>${escapeHtml(post.title)}</b>\n`);

  if (post.body && post.body.trim()) {
    parts.push(post.body.trim() + '\n');
  } else if (post.summary) {
    parts.push(`${escapeHtml(post.summary)}\n`);
  }

  if (post.takeaways && post.takeaways.length > 0 && (!post.body || !post.body.includes('WHAT IT DOES'))) {
    parts.push('⚡ <b>WHAT IT DOES</b>');
    for (const t of post.takeaways) {
      if (t.trim()) parts.push(`• ${escapeHtml(t.trim())}`);
    }
    parts.push('');
  }

  if (post.why_it_matters && (!post.body || !post.body.includes(post.why_it_matters))) {
    parts.push('🎯 <b>BEST FOR</b>');
    parts.push(`${escapeHtml(post.why_it_matters)}\n`);
  }

  if (meta.pricing && (!post.body || !post.body.includes(meta.pricing))) {
    parts.push('💰 <b>PRICING</b>');
    parts.push(`${escapeHtml(meta.pricing)}\n`);
  }

  return parts.join('\n');
}

function formatGitHubTemplate(post: PostSchema): string {
  const meta = post.metadata || {};
  const parts: string[] = ['💻 <b>GITHUB</b>\n'];
  parts.push(`🔥 <b>${escapeHtml(post.title)}</b>\n`);

  if (post.body && post.body.trim()) {
    parts.push(post.body.trim() + '\n');
  } else if (post.summary) {
    parts.push(`${escapeHtml(post.summary)}\n`);
  }

  if (post.why_it_matters && (!post.body || !post.body.includes(post.why_it_matters))) {
    parts.push("⭐ <b>WHY IT'S INTERESTING</b>");
    parts.push(`${escapeHtml(post.why_it_matters)}\n`);
  }

  if (meta.tech_stack && (!post.body || !post.body.includes(meta.tech_stack))) {
    parts.push('🛠 <b>TECH STACK</b>');
    parts.push(`${escapeHtml(meta.tech_stack)}\n`);
  }

  return parts.join('\n');
}

function formatCareerTemplate(post: PostSchema): string {
  const parts: string[] = ['🧠 <b>CAREER INSIGHT</b>\n'];
  parts.push(`🔥 <b>${escapeHtml(post.title)}</b>\n`);

  if (post.body && post.body.trim()) {
    parts.push(post.body.trim() + '\n');
  } else if (post.summary) {
    parts.push(`${escapeHtml(post.summary)}\n`);
  }

  if (post.takeaways && post.takeaways.length > 0 && (!post.body || !post.body.includes('KEY TAKEAWAYS'))) {
    parts.push('⚡ <b>KEY TAKEAWAYS</b>');
    for (const t of post.takeaways) {
      if (t.trim()) parts.push(`• ${escapeHtml(t.trim())}`);
    }
    parts.push('');
  }

  if (post.why_it_matters && (!post.body || !post.body.includes(post.why_it_matters))) {
    parts.push('🎯 <b>ACTION STEPS</b>');
    parts.push(`${escapeHtml(post.why_it_matters)}\n`);
  }

  return parts.join('\n');
}

function formatResourceTemplate(post: PostSchema): string {
  const parts: string[] = ['📚 <b>RESOURCE</b>\n'];
  parts.push(`🔥 <b>${escapeHtml(post.title)}</b>\n`);

  if (post.body && post.body.trim()) {
    parts.push(post.body.trim() + '\n');
  } else if (post.summary) {
    parts.push(`${escapeHtml(post.summary)}\n`);
  }

  if (post.why_it_matters && (!post.body || !post.body.includes(post.why_it_matters))) {
    parts.push('🎯 <b>BEST FOR</b>');
    parts.push(`${escapeHtml(post.why_it_matters)}\n`);
  }

  return parts.join('\n');
}
