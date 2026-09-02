import React, { useState, useEffect, useMemo } from 'react';
import { PostSchema } from '@/types/postSchema';
import { ScheduledPost } from '@/types/scheduler';
import { schedulePost } from '@/lib/api';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Calendar, Clock, Globe, AlertCircle, Send } from 'lucide-react';
import { toast } from 'sonner';

interface ScheduleDialogProps {
  isOpen: boolean;
  onClose: () => void;
  post: PostSchema;
  postId?: number;
  onScheduledSuccess: (scheduledPost: ScheduledPost) => void;
}

export const ScheduleDialog: React.FC<ScheduleDialogProps> = ({
  isOpen,
  onClose,
  post,
  postId,
  onScheduledSuccess,
}) => {
  // Default to tomorrow 09:00 AM local time
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedTime, setSelectedTime] = useState('09:00');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const todayStr = useMemo(() => {
    const d = new Date();
    return d.toISOString().split('T')[0];
  }, []);

  const userTimezone = useMemo(() => {
    try {
      const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      const offsetMinutes = new Date().getTimezoneOffset();
      const sign = offsetMinutes <= 0 ? '+' : '-';
      const hours = String(Math.floor(Math.abs(offsetMinutes) / 60)).padStart(2, '0');
      const mins = String(Math.abs(offsetMinutes) % 60).padStart(2, '0');
      return `${tz} (UTC${sign}${hours}:${mins})`;
    } catch {
      return 'Local Timezone';
    }
  }, []);

  useEffect(() => {
    if (isOpen) {
      setErrorMessage(null);
      // Default date to tomorrow
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      setSelectedDate(tomorrow.toISOString().split('T')[0]);
      setSelectedTime('09:00');
    }
  }, [isOpen]);

  // Compute calculated target ISO & human-friendly preview
  const { targetDate, isValidFuture, previewString, relativeString } = useMemo(() => {
    if (!selectedDate || !selectedTime) {
      return { targetDate: null, isValidFuture: false, previewString: '', relativeString: '' };
    }

    try {
      const [year, month, day] = selectedDate.split('-').map(Number);
      const [hours, minutes] = selectedTime.split(':').map(Number);
      const dt = new Date(year, month - 1, day, hours, minutes, 0);

      const now = new Date();
      const diffMs = dt.getTime() - now.getTime();
      const isValid = diffMs > 30000; // at least 30s in future

      const preview = dt.toLocaleString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      });

      let rel = '';
      if (isValid) {
        const diffHrs = Math.floor(diffMs / (1000 * 60 * 60));
        const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        if (diffHrs > 24) {
          const days = Math.floor(diffHrs / 24);
          rel = `in ~${days} day${days > 1 ? 's' : ''}`;
        } else if (diffHrs > 0) {
          rel = `in ${diffHrs}h ${diffMins}m`;
        } else {
          rel = `in ${diffMins} minutes`;
        }
      }

      return {
        targetDate: dt,
        isValidFuture: isValid,
        previewString: preview,
        relativeString: rel,
      };
    } catch {
      return { targetDate: null, isValidFuture: false, previewString: '', relativeString: '' };
    }
  }, [selectedDate, selectedTime]);

  const handleConfirmSchedule = async () => {
    if (!targetDate || !isValidFuture) {
      setErrorMessage('Scheduled time must be at least 1 minute in the future.');
      return;
    }

    if (!post.title || !post.title.trim()) {
      setErrorMessage('Post headline cannot be empty before scheduling.');
      return;
    }

    if (!post.body || !post.body.trim()) {
      setErrorMessage('Post body cannot be empty before scheduling.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const isoString = targetDate.toISOString();
      const res = await schedulePost({
        schema: post,
        scheduled_at: isoString,
        post_id: postId,
      });

      if (res.success && res.scheduled_post) {
        toast.success(`Post scheduled for ${previewString}!`);
        onScheduledSuccess(res.scheduled_post);
        onClose();
      } else {
        const err = res.error || 'Failed to schedule post';
        setErrorMessage(err);
        toast.error(err);
      }
    } catch (e: any) {
      const err = e.message || 'Error occurred while scheduling';
      setErrorMessage(err);
      toast.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="w-full max-w-[calc(100vw-1.5rem)] sm:max-w-md bg-slate-950/95 border-slate-800 text-slate-100 shadow-2xl backdrop-blur-xl">
        <DialogHeader>
          <DialogTitle className="text-base sm:text-lg font-bold flex items-center gap-2">
            <Calendar className="w-5 h-5 text-cyan-400" />
            Schedule for Telegram
          </DialogTitle>
          <DialogDescription className="text-xs text-slate-400">
            Choose when this post will automatically broadcast to @heyaaashu.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4 py-2">
          {/* Headline Preview */}
          <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800/80 text-xs text-slate-300 line-clamp-2">
            <span className="font-semibold text-white">Headline: </span>
            {post.title || 'Untitled Post'}
          </div>

          {/* Date and Time Pickers */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="sched-date" className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-cyan-400" />
                Date
              </Label>
              <input
                id="sched-date"
                type="date"
                min={todayStr}
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                className="w-full h-10 sm:h-9 px-3 rounded-md bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="sched-time" className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-cyan-400" />
                Time
              </Label>
              <input
                id="sched-time"
                type="time"
                value={selectedTime}
                onChange={(e) => setSelectedTime(e.target.value)}
                className="w-full h-10 sm:h-9 px-3 rounded-md bg-slate-900 border border-slate-700 text-sm text-white focus:outline-none focus:ring-1 focus:ring-cyan-500"
              />
            </div>
          </div>

          {/* Timezone Notice */}
          <div className="flex items-center gap-1.5 text-[11px] text-slate-400 bg-slate-900/40 p-2 rounded-md border border-slate-800/60">
            <Globe className="w-3.5 h-3.5 text-cyan-400/80 shrink-0" />
            <span className="truncate">Timezone: {userTimezone}</span>
          </div>

          {/* Human Readable Delivery Callout */}
          {previewString && (
            <div
              className={`p-3 rounded-lg border text-xs flex flex-col gap-1 ${
                isValidFuture
                  ? 'bg-cyan-950/20 border-cyan-800/50 text-cyan-200'
                  : 'bg-rose-950/20 border-rose-800/50 text-rose-300'
              }`}
            >
              <div className="font-semibold flex items-center justify-between">
                <span>{isValidFuture ? 'Scheduled Broadcast:' : 'Invalid Time:'}</span>
                {relativeString && <span className="font-mono text-[11px] text-cyan-400">{relativeString}</span>}
              </div>
              <p className="text-[11px] opacity-90">{previewString}</p>
            </div>
          )}

          {/* Error Message if any */}
          {errorMessage && (
            <div className="p-2.5 rounded-md bg-rose-950/30 border border-rose-800/80 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMessage}</span>
            </div>
          )}
        </div>

        <DialogFooter className="flex flex-col-reverse sm:flex-row gap-2 pt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={isSubmitting}
            className="w-full sm:w-auto h-11 sm:h-9 border-slate-700 text-slate-300 hover:bg-slate-900"
          >
            Cancel
          </Button>

          <Button
            size="sm"
            onClick={handleConfirmSchedule}
            disabled={isSubmitting || !isValidFuture}
            className="w-full sm:w-auto h-11 sm:h-9 font-semibold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-lg shadow-cyan-950/50"
          >
            <Calendar className="w-4 h-4 mr-1.5" />
            {isSubmitting ? 'Scheduling...' : 'Schedule Post'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
