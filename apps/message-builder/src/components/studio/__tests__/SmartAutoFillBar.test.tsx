import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { SmartAutoFillBar } from '../SmartAutoFillBar';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  generatePostFromInput: vi.fn(),
}));

describe('SmartAutoFillBar Component', () => {
  const mockOnPostGenerated = vi.fn();
  const mockOnPublishClick = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders smart auto-fill bar with textarea, tabs and buttons', () => {
    render(
      <SmartAutoFillBar
        onPostGenerated={mockOnPostGenerated}
        onPublishClick={mockOnPublishClick}
      />
    );

    expect(screen.getByText('Magic Smart Auto-Fill')).toBeDefined();
    expect(screen.getByText('📝 Content')).toBeDefined();
    expect(screen.getByText('Link Tab')).toBeDefined();
    expect(screen.getByPlaceholderText(/Paste article, tweet, newsletter/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /auto-fill post/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /publish/i })).toBeDefined();
  });

  it('switches between Content and Link tabs', () => {
    render(
      <SmartAutoFillBar
        onPostGenerated={mockOnPostGenerated}
        onPublishClick={mockOnPublishClick}
      />
    );

    const linkTabBtn = screen.getByText('Link Tab');
    fireEvent.click(linkTabBtn);

    expect(screen.getByText('Source URL / Action Link')).toBeDefined();
    expect(screen.getByPlaceholderText(/https:\/\/\.\.\. \(e\.g\. original article/i)).toBeDefined();

    const contentTabBtn = screen.getByText('📝 Content');
    fireEvent.click(contentTabBtn);
    expect(screen.getByPlaceholderText(/Paste article, tweet, newsletter/i)).toBeDefined();
  });

  it('automatically detects URL when pasted into the content area', async () => {
    render(
      <SmartAutoFillBar
        onPostGenerated={mockOnPostGenerated}
        onPublishClick={mockOnPublishClick}
      />
    );

    const textarea = screen.getByPlaceholderText(/Paste article, tweet, newsletter/i);
    fireEvent.change(textarea, {
      target: { value: 'Exciting news: https://blog.google/gemini-2-5 is released!' },
    });

    // Link input should auto-sync with detected URL
    const compactLinkInput = screen.getByPlaceholderText(/Source Link \(Optional — auto-detected/i);
    expect((compactLinkInput as HTMLInputElement).value).toBe('https://blog.google/gemini-2-5');
  });

  it('triggers auto-generation and passes post to onPostGenerated', async () => {
    const mockPost = {
      schema_version: '1.0.0',
      content_type: 'ai_news' as any,
      title: 'Google DeepMind Unveils Next-Gen Model',
      body: 'Body text here...',
      takeaways: ['Takeaway 1', 'Takeaway 2'],
      buttons: [{ text: '📚 Read Source', url: 'https://blog.google' }],
      parse_mode: 'HTML' as any,
    };

    (api.generatePostFromInput as any).mockResolvedValue({
      success: true,
      post: mockPost,
      draft_id: 123,
    });

    render(
      <SmartAutoFillBar
        onPostGenerated={mockOnPostGenerated}
        onPublishClick={mockOnPublishClick}
      />
    );

    const textarea = screen.getByPlaceholderText(/Paste article, tweet, newsletter/i);
    fireEvent.change(textarea, {
      target: { value: 'Google DeepMind Unveils Next-Gen Model https://blog.google' },
    });

    const autoFillBtn = screen.getByRole('button', { name: /auto-fill post/i });
    fireEvent.click(autoFillBtn);

    await waitFor(() => {
      expect(api.generatePostFromInput).toHaveBeenCalledWith(
        expect.objectContaining({
          input: 'Google DeepMind Unveils Next-Gen Model https://blog.google',
          link: 'https://blog.google',
        })
      );
      expect(mockOnPostGenerated).toHaveBeenCalledWith(mockPost);
    });

    // Should display the ready status pill
    expect(screen.getByText(/Ready: Google DeepMind Unveils Next-Gen Model/i)).toBeDefined();
  });

  it('invokes onPublishClick when clicking the Publish button', () => {
    render(
      <SmartAutoFillBar
        onPostGenerated={mockOnPostGenerated}
        onPublishClick={mockOnPublishClick}
      />
    );

    const publishBtn = screen.getByRole('button', { name: /publish/i });
    fireEvent.click(publishBtn);

    expect(mockOnPublishClick).toHaveBeenCalledTimes(1);
  });
});
