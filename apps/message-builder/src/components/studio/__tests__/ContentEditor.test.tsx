import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ContentEditor } from '../ContentEditor';
import { PostSchema } from '@/types/postSchema';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  generatePostFromInput: vi.fn(),
}));

describe('ContentEditor Streamlined Auto-Posting Hub', () => {
  const mockOnPostChange = vi.fn();
  const mockOnTemplateChange = vi.fn();
  const mockOnPublishClick = vi.fn();

  const basePost: PostSchema = {
    schema_version: '1.0.0',
    content_type: 'ai_news',
    title: 'Google DeepMind Unveils Next-Gen Gemini Reasoning',
    body: 'Announcement details...',
    buttons: [
      { text: '📚 Read Source', url: 'https://blog.google' },
      { text: '❤️ Like', url: 'https://blog.google#like', callback_data: 'react_like' },
      { text: '💬 Discuss', url: 'https://t.me/heyaaashu' },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the streamlined auto-posting card with category, layout, and auto-configured buttons', () => {
    render(
      <ContentEditor
        post={basePost}
        templateStyle="auto"
        onPostChange={mockOnPostChange}
        onTemplateChange={mockOnTemplateChange}
        onPublishClick={mockOnPublishClick}
      />
    );

    expect(screen.getByText('Magic Smart Auto-Fill')).toBeDefined();
    expect(screen.getByText('Category')).toBeDefined();
    expect(screen.getByText('Template Layout')).toBeDefined();
    expect(screen.getByText('Auto-Configured Buttons')).toBeDefined();
    expect(screen.getByText('📚 Read Source')).toBeDefined();
    expect(screen.getByText('❤️ Like')).toBeDefined();
    expect(screen.getByText('💬 Discuss')).toBeDefined();
    expect(screen.getByRole('button', { name: /auto-fill post/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /publish/i })).toBeDefined();
  });

  it('allows adding and removing custom buttons', () => {
    render(
      <ContentEditor
        post={basePost}
        templateStyle="auto"
        onPostChange={mockOnPostChange}
        onTemplateChange={mockOnTemplateChange}
        onPublishClick={mockOnPublishClick}
      />
    );

    // Click "Add Custom Button"
    const addBtnToggle = screen.getByText('Add Custom Button');
    fireEvent.click(addBtnToggle);

    expect(screen.getByPlaceholderText(/🎁 Claim Bonus/i)).toBeDefined();
    expect(screen.getByPlaceholderText(/URL \(https/i)).toBeDefined();

    const labelInput = screen.getByPlaceholderText(/🎁 Claim Bonus/i);
    const urlInput = screen.getByPlaceholderText(/URL \(https/i);

    fireEvent.change(labelInput, { target: { value: '🎁 Claim Gift' } });
    fireEvent.change(urlInput, { target: { value: 'https://example.com/gift' } });

    const submitBtn = screen.getByRole('button', { name: /^Add$/i });
    fireEvent.click(submitBtn);

    expect(mockOnPostChange).toHaveBeenCalled();
  });

  it('allows removing an auto-configured button', () => {
    render(
      <ContentEditor
        post={basePost}
        templateStyle="auto"
        onPostChange={mockOnPostChange}
        onTemplateChange={mockOnTemplateChange}
        onPublishClick={mockOnPublishClick}
      />
    );

    // Remove buttons have title "Remove button"
    const removeButtons = screen.getAllByTitle('Remove button');
    expect(removeButtons.length).toBe(3);

    fireEvent.click(removeButtons[0]);
    expect(mockOnPostChange).toHaveBeenCalled();
  });

  it('invokes onPublishClick when clicking the Publish button', () => {
    render(
      <ContentEditor
        post={basePost}
        templateStyle="auto"
        onPostChange={mockOnPostChange}
        onTemplateChange={mockOnTemplateChange}
        onPublishClick={mockOnPublishClick}
      />
    );

    const publishBtn = screen.getByRole('button', { name: /publish/i });
    fireEvent.click(publishBtn);

    expect(mockOnPublishClick).toHaveBeenCalledTimes(1);
  });

  it('fine-tune drawer is collapsed by default and expands on click', () => {
    render(
      <ContentEditor
        post={basePost}
        templateStyle="auto"
        onPostChange={mockOnPostChange}
        onTemplateChange={mockOnTemplateChange}
        onPublishClick={mockOnPublishClick}
      />
    );

    // Fine tune headline input should NOT be visible initially
    expect(screen.queryByPlaceholderText('Post Headline...')).toBeNull();

    // Click toggle to expand
    const toggle = screen.getByText('Fine-Tune Text & Media (Optional)');
    fireEvent.click(toggle);

    // Now it should be visible
    expect(screen.getByPlaceholderText('Post Headline...')).toBeDefined();
  });
});
