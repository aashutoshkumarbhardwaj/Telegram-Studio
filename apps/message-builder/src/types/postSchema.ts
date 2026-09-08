/**
 * Canonical PostSchema TypeScript Definitions.
 * Strict match with packages/post-schema/post.schema.json and packages/post_schema/schema.py.
 */

export type ContentType =
  | 'ai_news'
  | 'job'
  | 'internship'
  | 'hackathon'
  | 'ai_tool'
  | 'github'
  | 'career'
  | 'resource';

export type ParseMode = 'HTML' | 'MarkdownV2';

export type VerificationStatus = 'unverified' | 'needs_verification' | 'verified';

export interface MediaItem {
  type: 'photo' | 'video' | 'document' | 'animation';
  url_or_path: string;
  caption?: string;
  file_id?: string;
}

export interface InlineButton {
  text: string;
  url?: string;
  callback_data?: string;
  row?: number;
}

export interface SourceInfo {
  title: string;
  url: string;
  author?: string;
  published_at?: string;
}

export interface VerificationInfo {
  status: VerificationStatus;
  sources: string[];
  notes?: string;
  verified_by?: string;
  verified_at?: string;
}

export interface PostSchema {
  schema_version?: string;
  content_type: ContentType;
  title: string;
  body: string;
  summary?: string;
  takeaways?: string[];
  why_it_matters?: string;
  cta?: string;
  metadata?: Record<string, any>;
  media?: MediaItem[];
  buttons?: InlineButton[];
  source?: SourceInfo;
  verification?: VerificationInfo;
  parse_mode?: ParseMode;
  reactions?: string[];
}

export interface DraftListItem {
  post_id: number;
  user_id?: number;
  channel_id?: number;
  content_type: ContentType;
  title: string;
  text?: string;
  status: 'candidate' | 'draft' | 'approved' | 'posted' | 'rejected' | 'cancelled';
  created_at: string;
  published_at?: string;
  raw_schema_json?: string;
}
