import { PostSchema } from './postSchema';

export type ScheduleStatus =
  | 'draft'
  | 'scheduled'
  | 'publishing'
  | 'posted'
  | 'failed'
  | 'cancelled';

export interface ScheduledPost {
  post_id: number;
  user_id?: number;
  channel_id?: number;
  content_type: string;
  title: string;
  text?: string;
  status: ScheduleStatus;
  scheduled_at: string;
  published_at?: string | null;
  telegram_message_id?: number | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  schema?: PostSchema | null;
}

export interface ScheduleRequest {
  schema: PostSchema;
  scheduled_at: string; // ISO-8601 string
  post_id?: number;
  channel_id?: number;
}
