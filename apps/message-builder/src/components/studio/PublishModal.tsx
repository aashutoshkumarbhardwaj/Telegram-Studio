import React from 'react';
import { PostSchema } from '@/types/postSchema';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Send, AlertTriangle, ShieldCheck, Calendar } from 'lucide-react';

interface PublishModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmPublish: () => void;
  onOpenSchedule?: () => void;
  post: PostSchema;
  isPublishing?: boolean;
}

export const PublishModal: React.FC<PublishModalProps> = ({
  isOpen,
  onClose,
  onConfirmPublish,
  onOpenSchedule,
  post,
  isPublishing = false,
}) => {
  const isNeedsVerification = post.verification?.status === 'needs_verification';

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !isPublishing && onClose()}>
      <DialogContent className="max-w-[calc(100vw-1.5rem)] sm:max-w-md p-4 sm:p-6 max-h-[92vh] overflow-y-auto bg-slate-950 border-slate-800 text-slate-100 rounded-2xl">
        <DialogHeader>
          <DialogTitle className="text-base font-semibold text-white flex items-center gap-2">
            <Send className="w-4 h-4 text-cyan-400" />
            Publish Post to Telegram
          </DialogTitle>
          <DialogDescription className="text-xs text-slate-400">
            Confirm publishing this post directly to your designated Telegram Channel.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3 my-2 p-3 bg-slate-900/80 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Target Channel:</span>
            <span className="font-semibold text-cyan-300">Heyaaashu | AI & Tech Careers</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Category:</span>
            <span className="font-mono uppercase text-[11px] text-slate-200">
              {post.content_type}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Headline:</span>
            <span className="font-medium text-white truncate max-w-[200px]">{post.title}</span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-400">Verification:</span>
            <span
              className={`flex items-center gap-1 font-semibold text-[11px] ${
                isNeedsVerification ? 'text-amber-400' : 'text-emerald-400'
              }`}
            >
              {isNeedsVerification ? (
                <>
                  <AlertTriangle className="w-3.5 h-3.5" /> Needs Verification
                </>
              ) : (
                <>
                  <ShieldCheck className="w-3.5 h-3.5" /> Verified
                </>
              )}
            </span>
          </div>
        </div>

        {isNeedsVerification && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-amber-300 text-xs leading-relaxed flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
            <span>
              <b>Caution:</b> This story has not been verified against a Tier 1 primary source.
              Ensure facts are accurate before publishing.
            </span>
          </div>
        )}

        <DialogFooter className="flex flex-col-reverse sm:flex-row gap-2 pt-3 w-full sm:justify-between items-center">
          <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={onClose}
              disabled={isPublishing}
              className="w-full sm:w-auto h-10 sm:h-8 border-slate-800 text-slate-300 hover:bg-slate-900 text-xs font-medium"
            >
              Cancel
            </Button>
            {onOpenSchedule && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  onClose();
                  onOpenSchedule();
                }}
                disabled={isPublishing}
                className="w-full sm:w-auto h-10 sm:h-8 border-cyan-800/80 bg-cyan-950/20 text-cyan-300 hover:bg-cyan-950/50 text-xs font-medium flex items-center justify-center gap-1.5"
              >
                <Calendar className="w-3.5 h-3.5 text-cyan-400" />
                Schedule for Later
              </Button>
            )}
          </div>

          <Button
            size="sm"
            onClick={onConfirmPublish}
            disabled={isPublishing}
            className="w-full sm:w-auto h-11 sm:h-8 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-sm sm:text-xs shadow-lg shadow-cyan-950 shrink-0"
          >
            {isPublishing ? (
              'Publishing...'
            ) : (
              <>
                <Send className="w-4 h-4 sm:w-3.5 sm:h-3.5 mr-1.5" /> Confirm & Publish
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
