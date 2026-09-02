import React, { useState, useMemo } from 'react';
import { ScheduledPost, ScheduleStatus } from '@/types/scheduler';
import { PostSchema } from '@/types/postSchema';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Calendar,
  Clock,
  Send,
  XCircle,
  Edit3,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Trash2,
  CalendarClock,
} from 'lucide-react';
import { toast } from 'sonner';

interface ScheduledDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  scheduledPosts: ScheduledPost[];
  onRefresh: () => void;
  onEditPost: (post: PostSchema, postId: number) => void;
  onReschedulePost: (postId: number, newTimeIso: string) => Promise<boolean>;
  onPublishNow: (postId: number) => Promise<boolean>;
  onCancelSchedule: (postId: number) => Promise<boolean>;
  onDeleteSchedule: (postId: number) => Promise<boolean>;
}

export const ScheduledDrawer: React.FC<ScheduledDrawerProps> = ({
  isOpen,
  onClose,
  scheduledPosts,
  onRefresh,
  onEditPost,
  onReschedulePost,
  onPublishNow,
  onCancelSchedule,
  onDeleteSchedule,
}) => {
  const [filter, setFilter] = useState<'all' | 'scheduled' | 'posted' | 'failed'>('all');
  const [reschedulingId, setReschedulingId] = useState<number | null>(null);
  const [newDate, setNewDate] = useState('');
  const [newTime, setNewTime] = useState('10:00');
  const [loadingActionId, setLoadingActionId] = useState<number | null>(null);

  const filteredPosts = useMemo(() => {
    if (filter === 'all') return scheduledPosts;
    return scheduledPosts.filter((p) => p.status === filter);
  }, [scheduledPosts, filter]);

  const activeCount = useMemo(() => {
    return scheduledPosts.filter((p) => p.status === 'scheduled').length;
  }, [scheduledPosts]);

  const formatScheduleDateTime = (iso: string) => {
    try {
      const dt = new Date(iso);
      return dt.toLocaleString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });
    } catch {
      return iso;
    }
  };

  const getRelativeTime = (iso: string) => {
    try {
      const target = new Date(iso).getTime();
      const diffMs = target - Date.now();
      if (diffMs > 0) {
        const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        if (diffHrs > 24) {
          const days = Math.floor(diffHrs / 24);
          return `in ~${days}d`;
        }
        if (diffHrs > 0) return `in ${diffHrs}h ${diffMins}m`;
        return `in ${diffMins}m`;
      } else {
        const pastMins = Math.floor(Math.abs(diffMs) / (1000 * 60));
        if (pastMins > 60) {
          const pastHrs = Math.floor(pastMins / 60);
          return `${pastHrs}h ago`;
        }
        return `${pastMins}m ago`;
      }
    } catch {
      return '';
    }
  };

  const renderStatusBadge = (status: ScheduleStatus) => {
    switch (status) {
      case 'scheduled':
        return (
          <Badge className="bg-cyan-950/80 text-cyan-300 border-cyan-800 text-[10px] font-mono">
            <Clock className="w-3 h-3 mr-1" />
            Scheduled
          </Badge>
        );
      case 'publishing':
        return (
          <Badge className="bg-amber-950/80 text-amber-300 border-amber-800 text-[10px] font-mono animate-pulse">
            <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
            Publishing
          </Badge>
        );
      case 'posted':
        return (
          <Badge className="bg-emerald-950/80 text-emerald-300 border-emerald-800 text-[10px] font-mono">
            <CheckCircle2 className="w-3 h-3 mr-1" />
            Posted
          </Badge>
        );
      case 'failed':
        return (
          <Badge className="bg-rose-950/80 text-rose-300 border-rose-800 text-[10px] font-mono">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Failed
          </Badge>
        );
      case 'cancelled':
        return (
          <Badge className="bg-slate-900 text-slate-400 border-slate-700 text-[10px] font-mono">
            <XCircle className="w-3 h-3 mr-1" />
            Cancelled
          </Badge>
        );
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const handleStartReschedule = (item: ScheduledPost) => {
    setReschedulingId(item.post_id);
    try {
      const dt = new Date(item.scheduled_at);
      setNewDate(dt.toISOString().split('T')[0]);
      const hrs = String(dt.getHours()).padStart(2, '0');
      const mins = String(dt.getMinutes()).padStart(2, '0');
      setNewTime(`${hrs}:${mins}`);
    } catch {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      setNewDate(tomorrow.toISOString().split('T')[0]);
      setNewTime('10:00');
    }
  };

  const handleConfirmReschedule = async (postId: number) => {
    if (!newDate || !newTime) {
      toast.error('Please pick both date and time');
      return;
    }
    const [year, month, day] = newDate.split('-').map(Number);
    const [hours, minutes] = newTime.split(':').map(Number);
    const dt = new Date(year, month - 1, day, hours, minutes, 0);

    if (dt.getTime() <= Date.now() + 30000) {
      toast.error('Scheduled time must be in the future');
      return;
    }

    setLoadingActionId(postId);
    const ok = await onReschedulePost(postId, dt.toISOString());
    setLoadingActionId(null);
    if (ok) {
      setReschedulingId(null);
    }
  };

  const handlePublishNowClick = async (postId: number) => {
    setLoadingActionId(postId);
    await onPublishNow(postId);
    setLoadingActionId(null);
  };

  const handleCancelClick = async (postId: number) => {
    setLoadingActionId(postId);
    await onCancelSchedule(postId);
    setLoadingActionId(null);
  };

  const handleDeleteClick = async (postId: number) => {
    setLoadingActionId(postId);
    await onDeleteSchedule(postId);
    setLoadingActionId(null);
  };

  const handleEditClick = (item: ScheduledPost) => {
    if (item.schema) {
      onEditPost(item.schema, item.post_id);
      onClose();
      toast.success('Loaded scheduled post into editor');
    } else {
      toast.error('Post schema not available');
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-full max-w-[calc(100vw-1.5rem)] sm:max-w-2xl max-h-[92vh] overflow-hidden flex flex-col bg-slate-950/95 border-slate-800 text-slate-100 shadow-2xl backdrop-blur-xl p-4 sm:p-6">
        <DialogHeader className="pb-3 border-b border-slate-800 shrink-0">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <CalendarClock className="w-5 h-5 text-cyan-400" />
              <DialogTitle className="text-base sm:text-lg font-bold text-white">
                Scheduled Queue
              </DialogTitle>
              {activeCount > 0 && (
                <span className="px-2 py-0.5 rounded-full text-xs font-mono font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800">
                  {activeCount} Active
                </span>
              )}
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              className="h-8 px-2 text-xs text-slate-400 hover:text-white"
              title="Refresh queue"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </div>

          <DialogDescription className="text-xs text-slate-400 pt-1">
            Automated Telegram broadcasts scheduled for future delivery.
          </DialogDescription>

          {/* Filter Bar */}
          <div className="flex items-center gap-1 pt-2 overflow-x-auto">
            {(['all', 'scheduled', 'posted', 'failed'] as const).map((f) => (
              <button
                key={f}
                type="button"
                onClick={() => setFilter(f)}
                className={`px-3 py-1 rounded-lg text-xs font-medium capitalize transition-all shrink-0 ${
                  filter === f
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                    : 'text-slate-400 hover:text-white bg-slate-900/60'
                }`}
              >
                {f}
              </button>
            ))}
          </div>
        </DialogHeader>

        {/* Scrollable List */}
        <div className="flex-1 overflow-y-auto py-3 space-y-3 pr-1">
          {filteredPosts.length === 0 ? (
            <div className="text-center py-12 px-4 border border-dashed border-slate-800 rounded-xl bg-slate-900/30">
              <Calendar className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-sm font-semibold text-slate-300">No scheduled posts found</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                Schedule any approved draft from the editor or the publish modal to see it here.
              </p>
            </div>
          ) : (
            filteredPosts.map((item) => (
              <div
                key={item.post_id}
                className="p-3.5 rounded-xl bg-slate-900/70 border border-slate-800 hover:border-slate-700 transition-all flex flex-col gap-2.5 shadow-sm"
              >
                {/* Header: Status and Datetime */}
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2">
                    {renderStatusBadge(item.status)}
                    <span className="text-xs font-semibold text-white flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5 text-cyan-400" />
                      {formatScheduleDateTime(item.scheduled_at)}
                    </span>
                    <span className="text-[11px] text-cyan-400/80 font-mono">
                      ({getRelativeTime(item.scheduled_at)})
                    </span>
                  </div>

                  <span className="text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">
                    #{item.post_id} • {item.content_type}
                  </span>
                </div>

                {/* Headline */}
                <h4 className="text-xs sm:text-sm font-semibold text-slate-100 line-clamp-2">
                  {item.title || 'Untitled Post'}
                </h4>

                {/* Error Message if Failed */}
                {item.status === 'failed' && item.error_message && (
                  <div className="p-2 rounded bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                    <span className="truncate">{item.error_message}</span>
                  </div>
                )}

                {/* Reschedule Inline Form */}
                {reschedulingId === item.post_id && (
                  <div className="p-3 rounded-lg bg-slate-950 border border-cyan-800/60 flex flex-col gap-2 my-1">
                    <span className="text-xs font-semibold text-cyan-300 flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5" /> Pick New Schedule Time
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      <input
                        type="date"
                        value={newDate}
                        onChange={(e) => setNewDate(e.target.value)}
                        className="h-8 px-2 rounded bg-slate-900 border border-slate-700 text-xs text-white"
                      />
                      <input
                        type="time"
                        value={newTime}
                        onChange={(e) => setNewTime(e.target.value)}
                        className="h-8 px-2 rounded bg-slate-900 border border-slate-700 text-xs text-white"
                      />
                    </div>
                    <div className="flex items-center justify-end gap-2 pt-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setReschedulingId(null)}
                        className="h-7 text-xs text-slate-400"
                      >
                        Cancel
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => handleConfirmReschedule(item.post_id)}
                        disabled={loadingActionId === item.post_id}
                        className="h-7 px-3 text-xs bg-cyan-600 hover:bg-cyan-500 text-white"
                      >
                        Save Reschedule
                      </Button>
                    </div>
                  </div>
                )}

                {/* Action Bar */}
                <div className="flex items-center justify-between gap-2 pt-1 border-t border-slate-800/80 flex-wrap">
                  <div className="flex items-center gap-1.5">
                    {/* Edit button */}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditClick(item)}
                      className="h-7 px-2.5 text-xs border-slate-700 text-slate-300 hover:text-white"
                      title="Load into visual editor"
                    >
                      <Edit3 className="w-3 h-3 mr-1" />
                      Edit
                    </Button>

                    {/* Reschedule button */}
                    {item.status !== 'posted' && reschedulingId !== item.post_id && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleStartReschedule(item)}
                        className="h-7 px-2.5 text-xs border-slate-700 text-slate-300 hover:text-white"
                        title="Reschedule broadcast"
                      >
                        <Clock className="w-3 h-3 mr-1 text-cyan-400" />
                        Reschedule
                      </Button>
                    )}
                  </div>

                  <div className="flex items-center gap-1.5">
                    {/* Publish Now */}
                    {item.status !== 'posted' && (
                      <Button
                        size="sm"
                        onClick={() => handlePublishNowClick(item.post_id)}
                        disabled={loadingActionId === item.post_id}
                        className="h-7 px-2.5 text-xs bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-medium"
                      >
                        <Send className="w-3 h-3 mr-1" />
                        Publish Now
                      </Button>
                    )}

                    {/* Cancel Schedule */}
                    {item.status === 'scheduled' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCancelClick(item.post_id)}
                        disabled={loadingActionId === item.post_id}
                        className="h-7 px-2 text-xs text-rose-400 hover:bg-rose-950/40 hover:text-rose-300"
                        title="Cancel scheduled broadcast"
                      >
                        <XCircle className="w-3.5 h-3.5 mr-1" />
                        Cancel
                      </Button>
                    )}

                    {/* Delete item if cancelled or failed */}
                    {(item.status === 'cancelled' || item.status === 'failed') && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDeleteClick(item.post_id)}
                        disabled={loadingActionId === item.post_id}
                        className="h-7 px-2 text-xs text-slate-500 hover:text-rose-400"
                        title="Delete record"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
