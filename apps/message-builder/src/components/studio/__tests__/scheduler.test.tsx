import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { ScheduleDialog } from '../ScheduleDialog';
import { ScheduledDrawer } from '../ScheduledDrawer';
import { PostSchema } from '@/types/postSchema';
import { ScheduledPost } from '@/types/scheduler';
import * as api from '@/lib/api';

vi.mock('@/lib/api', () => ({
  schedulePost: vi.fn(),
  fetchScheduledPosts: vi.fn(),
  reschedulePost: vi.fn(),
  publishScheduledNow: vi.fn(),
  cancelScheduledPost: vi.fn(),
  deleteScheduledPost: vi.fn(),
}));

const mockPost: PostSchema = {
  schema_version: '1.0.0',
  content_type: 'ai_news',
  title: 'Anthropic Announces Claude 3.7 Sonnet',
  body: 'Hybrid reasoning model released today.',
  summary: 'Hybrid reasoning model released today.',
  parse_mode: 'HTML',
};

const mockScheduledList: ScheduledPost[] = [
  {
    post_id: 101,
    content_type: 'ai_news',
    title: 'Upcoming AI Model Release',
    status: 'scheduled',
    scheduled_at: new Date(Date.now() + 3600000).toISOString(),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    schema: mockPost,
  },
  {
    post_id: 102,
    content_type: 'job',
    title: 'Lead Research Scientist at OpenAI',
    status: 'posted',
    scheduled_at: new Date(Date.now() - 3600000).toISOString(),
    published_at: new Date().toISOString(),
    telegram_message_id: 5544,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    schema: { ...mockPost, content_type: 'job' },
  },
];

describe('Phase 12A: ScheduleDialog Component', () => {
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders date and time pickers, timezone indicator, and submit button', () => {
    render(
      <ScheduleDialog
        isOpen={true}
        onClose={mockOnClose}
        post={mockPost}
        postId={101}
        onScheduledSuccess={mockOnSuccess}
      />
    );

    expect(screen.getByText('Schedule for Telegram')).toBeDefined();
    expect(screen.getByLabelText(/date/i)).toBeDefined();
    expect(screen.getByLabelText(/time/i)).toBeDefined();
    expect(screen.getByText(/timezone:/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /schedule post/i })).toBeDefined();
  });

  it('submits valid future schedule and calls api.schedulePost', async () => {
    (api.schedulePost as any).mockResolvedValue({
      success: true,
      scheduled_post: mockScheduledList[0],
    });

    render(
      <ScheduleDialog
        isOpen={true}
        onClose={mockOnClose}
        post={mockPost}
        postId={101}
        onScheduledSuccess={mockOnSuccess}
      />
    );

    const submitBtn = screen.getByRole('button', { name: /schedule post/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.schedulePost).toHaveBeenCalledTimes(1);
      expect(mockOnSuccess).toHaveBeenCalledWith(mockScheduledList[0]);
      expect(mockOnClose).toHaveBeenCalled();
    });
  });
});

describe('Phase 12A: ScheduledDrawer Component', () => {
  const mockOnClose = vi.fn();
  const mockOnRefresh = vi.fn();
  const mockOnEdit = vi.fn();
  const mockOnReschedule = vi.fn().mockResolvedValue(true);
  const mockOnPublishNow = vi.fn().mockResolvedValue(true);
  const mockOnCancel = vi.fn().mockResolvedValue(true);
  const mockOnDelete = vi.fn().mockResolvedValue(true);

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders scheduled queue items with status badges and actions', () => {
    render(
      <ScheduledDrawer
        isOpen={true}
        onClose={mockOnClose}
        scheduledPosts={mockScheduledList}
        onRefresh={mockOnRefresh}
        onEditPost={mockOnEdit}
        onReschedulePost={mockOnReschedule}
        onPublishNow={mockOnPublishNow}
        onCancelSchedule={mockOnCancel}
        onDeleteSchedule={mockOnDelete}
      />
    );

    expect(screen.getByText('Scheduled Queue')).toBeDefined();
    expect(screen.getByText('Upcoming AI Model Release')).toBeDefined();
    expect(screen.getByText('Lead Research Scientist at OpenAI')).toBeDefined();
    expect(screen.getByText('1 Active')).toBeDefined();
  });

  it('triggers Publish Now when clicked', async () => {
    render(
      <ScheduledDrawer
        isOpen={true}
        onClose={mockOnClose}
        scheduledPosts={mockScheduledList}
        onRefresh={mockOnRefresh}
        onEditPost={mockOnEdit}
        onReschedulePost={mockOnReschedule}
        onPublishNow={mockOnPublishNow}
        onCancelSchedule={mockOnCancel}
        onDeleteSchedule={mockOnDelete}
      />
    );

    const publishNowButtons = screen.getAllByRole('button', { name: /publish now/i });
    expect(publishNowButtons.length).toBeGreaterThan(0);
    fireEvent.click(publishNowButtons[0]);

    await waitFor(() => {
      expect(mockOnPublishNow).toHaveBeenCalledWith(101);
    });
  });

  it('triggers Cancel schedule when clicked', async () => {
    render(
      <ScheduledDrawer
        isOpen={true}
        onClose={mockOnClose}
        scheduledPosts={mockScheduledList}
        onRefresh={mockOnRefresh}
        onEditPost={mockOnEdit}
        onReschedulePost={mockOnReschedule}
        onPublishNow={mockOnPublishNow}
        onCancelSchedule={mockOnCancel}
        onDeleteSchedule={mockOnDelete}
      />
    );

    const cancelButtons = screen.getAllByRole('button', { name: /cancel/i });
    // Click the cancel schedule action button for post 101
    const postCancelBtn = cancelButtons.find((btn) => btn.getAttribute('title')?.includes('Cancel scheduled'));
    expect(postCancelBtn).toBeDefined();
    if (postCancelBtn) {
      fireEvent.click(postCancelBtn);
      await waitFor(() => {
        expect(mockOnCancel).toHaveBeenCalledWith(101);
      });
    }
  });

  it('triggers Edit and loads post into editor', async () => {
    render(
      <ScheduledDrawer
        isOpen={true}
        onClose={mockOnClose}
        scheduledPosts={mockScheduledList}
        onRefresh={mockOnRefresh}
        onEditPost={mockOnEdit}
        onReschedulePost={mockOnReschedule}
        onPublishNow={mockOnPublishNow}
        onCancelSchedule={mockOnCancel}
        onDeleteSchedule={mockOnDelete}
      />
    );

    const editButtons = screen.getAllByRole('button', { name: /edit/i });
    fireEvent.click(editButtons[0]);

    expect(mockOnEdit).toHaveBeenCalledWith(mockPost, 101);
    expect(mockOnClose).toHaveBeenCalled();
  });
});
