import { ContentType, PostSchema } from './postSchema';

export interface GenerateRequest {
  input: string;
  category?: ContentType | 'auto';
  notes?: string;
}

export interface HookOption {
  text: string;
  score: number;
  style: 'punchy' | 'scale' | 'context' | string;
  clarity: number;
  curiosity: number;
  brevity: number;
}

export interface QualityScores {
  hook: number;
  clarity: number;
  value: number;
  readability: number;
  source: number;
  completeness: number;
  overall: number;
  status: 'ready' | 'needs_review';
}

export interface VisualConcept {
  needs_visual: boolean;
  concept: string;
}

export interface GenerationMetadata {
  input_type: 'url' | 'url_and_notes' | 'rough_idea' | 'raw_text';
  detected_category: string;
  category_confidence: number;
  category_review_needed: boolean;
  hooks: HookOption[];
  source_name: string;
  primary_url?: string;
}

export interface GenerateResponse {
  success: boolean;
  draft_id?: number;
  post?: PostSchema;
  quality?: QualityScores;
  generation?: GenerationMetadata;
  visual?: VisualConcept;
  error?: string;
  url_error?: boolean;
}

export interface HookResponse {
  success: boolean;
  hooks?: HookOption[];
  error?: string;
}
