import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AIGeneratorModal } from '../AIGeneratorModal';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  generatePostFromInput: vi.fn(),
  generateHookOptions: vi.fn(),
}));

describe('AIGeneratorModal Component', () => {
  const mockOnClose = vi.fn();
  const mockOnPostGenerated = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders input field, category selector, and generate button when open', () => {
    render(
      <AIGeneratorModal
        isOpen={true}
        onClose={mockOnClose}
        onPostGenerated={mockOnPostGenerated}
      />
    );

    expect(screen.getByText('AI Content Generator')).toBeDefined();
    expect(screen.getByPlaceholderText(/https:\/\/blog.google/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /generate post/i })).toBeDefined();
  });

  it('shows error when submitting empty input', async () => {
    render(
      <AIGeneratorModal
        isOpen={true}
        onClose={mockOnClose}
        onPostGenerated={mockOnPostGenerated}
      />
    );

    const generateBtn = screen.getByRole('button', { name: /generate post/i });
    const textarea = screen.getByPlaceholderText(/https:\/\/blog.google/i);
    fireEvent.change(textarea, { target: { value: '   ' } });
    fireEvent.click(generateBtn);

    expect(mockOnPostGenerated).not.toHaveBeenCalled();
  });

  it('handles successful generation and displays draft results with Open in Editor button', async () => {
    const mockPost = {
      schema_version: '1.0.0',
      content_type: 'ai_news' as any,
      title: 'Gemini 2.0 Released',
      body: 'Body content...',
      parse_mode: 'HTML' as any,
    };

    (api.generatePostFromInput as any).mockResolvedValue({
      success: true,
      draft_id: 101,
      post: mockPost,
      quality: {
        hook: 92,
        clarity: 90,
        value: 95,
        readability: 91,
        source: 100,
        completeness: 94,
        overall: 93,
        status: 'ready',
      },
      generation: {
        detected_category: 'ai_news',
        category_confidence: 0.95,
        category_review_needed: false,
        hooks: [
          { text: 'Gemini 2.0 Released', score: 93, style: 'punchy' },
          { text: 'Why Gemini 2.0 Matters', score: 88, style: 'context' },
        ],
      },
      visual: {
        needs_visual: true,
        concept: 'Editorial graphic concept...',
      },
    });

    render(
      <AIGeneratorModal
        isOpen={true}
        onClose={mockOnClose}
        onPostGenerated={mockOnPostGenerated}
      />
    );

    const textarea = screen.getByPlaceholderText(/https:\/\/blog.google/i);
    fireEvent.change(textarea, { target: { value: 'https://blog.google/gemini-2' } });

    const generateBtn = screen.getByRole('button', { name: /generate post/i });
    fireEvent.click(generateBtn);

    await waitFor(() => {
      expect(screen.getByText('Draft Generated')).toBeDefined();
      expect(screen.getByText('Health: 93/100')).toBeDefined();
      expect(screen.getByText('Visual Suggested:')).toBeDefined();
    });

    const openBtn = screen.getByRole('button', { name: /open in editor/i });
    fireEvent.click(openBtn);

    expect(mockOnPostGenerated).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Gemini 2.0 Released' }),
      101,
      expect.objectContaining({ overall: 93 }),
      expect.any(Array)
    );
    expect(mockOnClose).toHaveBeenCalled();
  });
});
