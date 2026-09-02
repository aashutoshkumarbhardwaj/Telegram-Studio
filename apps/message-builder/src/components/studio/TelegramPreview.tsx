import React from 'react';
import { PostSchema } from '@/types/postSchema';
import { TemplateStyle, formatPostHtml } from '@/lib/templates';
import { Button } from '@/components/ui/button';
import { ExternalLink, CheckCheck, Eye, Send } from 'lucide-react';

interface TelegramPreviewProps {
  post: PostSchema;
  templateStyle: TemplateStyle;
  onPublishClick?: () => void;
}

export const TelegramPreview: React.FC<TelegramPreviewProps> = ({
  post,
  templateStyle,
  onPublishClick,
}) => {
  const formattedHtml = formatPostHtml(post, templateStyle);
  const media = post.media && post.media.length > 0 ? post.media[0] : null;

  // Split buttons into rows of 2
  const buttons = post.buttons || [];
  const buttonRows: typeof buttons[] = [];
  for (let i = 0; i < buttons.length; i += 2) {
    buttonRows.push(buttons.slice(i, i + 2));
  }

  return (
    <div className="w-full max-w-lg mx-auto flex flex-col items-center justify-center p-2 sm:p-4 pb-28 sm:pb-4">
      {/* Device / Telegram Frame Wrapper */}
      <div className="w-full bg-slate-950/90 border border-slate-800/80 rounded-2xl shadow-2xl overflow-hidden backdrop-blur-xl">
        {/* Telegram Channel Header */}
        <div className="bg-slate-900/90 border-b border-slate-800 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white font-bold text-sm shadow-md">
              H
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <h3 className="text-xs font-semibold text-white tracking-wide">
                  Heyaaashu | AI & Tech Careers
                </h3>
                <span className="w-3.5 h-3.5 rounded-full bg-blue-500 flex items-center justify-center text-[9px] text-white">
                  ✓
                </span>
              </div>
              <p className="text-[10px] text-slate-400">14,820 subscribers</p>
            </div>
          </div>
          <span className="text-[11px] text-cyan-400 font-medium bg-cyan-950/70 border border-cyan-800/50 rounded-full px-2.5 py-0.5">
            Channel Preview
          </span>
        </div>

        {/* Telegram Chat Canvas */}
        <div className="p-4 bg-gradient-to-b from-slate-950 via-slate-900 to-slate-950 min-h-[380px] flex flex-col justify-start">
          {/* Post Bubble */}
          <div className="w-full bg-[#182533] border border-[#243447] text-slate-100 rounded-2xl p-4 shadow-lg flex flex-col gap-3 font-sans transition-all duration-200">
            {/* Attached Media */}
            {media && (
              <div className="rounded-xl overflow-hidden border border-[#2b3e55] bg-black/50 max-h-64 flex items-center justify-center">
                <img
                  src={media.url_or_path}
                  alt="Post visual"
                  className="w-full h-full object-cover max-h-64"
                  onError={(e) => {
                    (e.target as HTMLElement).style.display = 'none';
                  }}
                />
              </div>
            )}

            {/* Post Message Body */}
            <div
              className="text-xs sm:text-[13px] leading-relaxed whitespace-pre-wrap select-text text-slate-100/95 font-normal"
              dangerouslySetInnerHTML={{ __html: formattedHtml }}
            />

            {/* Inline Keyboard Buttons */}
            {buttonRows.length > 0 && (
              <div className="flex flex-col gap-1.5 pt-2">
                {buttonRows.map((row, rIdx) => (
                  <div key={rIdx} className="flex items-center gap-1.5 w-full">
                    {row.map((btn, bIdx) => (
                      <a
                        key={bIdx}
                        href={btn.url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex-1 bg-[#2b3e55]/80 hover:bg-[#344c68] active:bg-[#3d597a] border border-[#3b526f]/60 text-white rounded-lg py-2 px-3 text-center text-xs font-medium flex items-center justify-center gap-1.5 transition-colors shadow-sm group"
                      >
                        <span className="truncate">{btn.text}</span>
                        <ExternalLink className="w-3 h-3 text-cyan-400/70 group-hover:text-cyan-300 shrink-0" />
                      </a>
                    ))}
                  </div>
                ))}
              </div>
            )}

            {/* Message Footer: View counter and timestamp */}
            <div className="flex items-center justify-end gap-2 text-[10px] text-slate-400 pt-1 select-none">
              <span className="flex items-center gap-0.5">
                <Eye className="w-3 h-3 text-slate-400" />
                1.4k
              </span>
              <span>17:45</span>
              <CheckCheck className="w-3.5 h-3.5 text-cyan-400" />
            </div>
          </div>
        </div>
      </div>

      {/* Mobile Quick Publish Action Card */}
      {onPublishClick && (
        <div className="w-full mt-3 p-3 rounded-xl bg-slate-900/90 border border-slate-800 flex items-center justify-between gap-3 shadow-lg md:hidden">
          <div className="min-w-0">
            <h4 className="text-xs font-semibold text-white truncate">Ready to broadcast?</h4>
            <p className="text-[11px] text-slate-400 truncate">Publish directly to Telegram</p>
          </div>
          <Button
            size="sm"
            onClick={onPublishClick}
            className="h-9 px-3.5 text-xs font-semibold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-md shadow-cyan-950 shrink-0"
          >
            <Send className="w-3.5 h-3.5 mr-1.5" />
            Publish
          </Button>
        </div>
      )}
    </div>
  );
};
