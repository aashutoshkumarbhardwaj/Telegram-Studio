import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Sparkles,
  Link as LinkIcon,
  Send,
  ClipboardPaste,
  Trash2,
  Loader2,
  CheckCircle2,
  ExternalLink,
  Zap,
} from 'lucide-react';
import { ContentType, PostSchema } from '@/types/postSchema';
import { generatePostFromInput } from '@/lib/api';
import { extractUrls } from '@/lib/smartExtractor';
import { toast } from 'sonner';

interface SmartAutoFillBarProps {
  onPostGenerated: (post: PostSchema) => void;
  onPublishClick?: () => void;
  isPublishing?: boolean;
}

export const SmartAutoFillBar: React.FC<SmartAutoFillBarProps> = ({
  onPostGenerated,
  onPublishClick,
  isPublishing = false,
}) => {
  const [activeTab, setActiveTab] = useState<'content' | 'link'>('content');
  const [rawText, setRawText] = useState('');
  const [explicitLink, setExplicitLink] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<ContentType | 'auto'>('auto');
  const [isLoading, setIsLoading] = useState(false);
  const [lastAutoFilledTitle, setLastAutoFilledTitle] = useState<string | null>(null);

  // Auto-extract link from raw text if user hasn't explicitly set a custom link
  useEffect(() => {
    const urls = extractUrls(rawText);
    if (urls.length > 0 && !explicitLink) {
      setExplicitLink(urls[0]);
    }
  }, [rawText, explicitLink]);

  const handlePasteClipboard = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.trim()) {
          setRawText((prev) => (prev ? `${prev}\n\n${text.trim()}` : text.trim()));
          const urls = extractUrls(text);
          if (urls.length > 0 && !explicitLink) {
            setExplicitLink(urls[0]);
          }
          toast.success('📋 Pasted from clipboard!');
        } else {
          toast.info('Clipboard is empty. Use Ctrl+V / Cmd+V to paste.');
        }
      } else {
        toast.info('Clipboard access restricted. Use Ctrl+V / Cmd+V directly in the text box.');
      }
    } catch {
      toast.info('Clipboard access denied. Use Ctrl+V / Cmd+V to paste.');
    }
  };

  const handleClear = () => {
    setRawText('');
    setExplicitLink('');
    setLastAutoFilledTitle(null);
  };

  const handleAutoFill = async () => {
    const trimmedText = rawText.trim();
    const trimmedLink = explicitLink.trim();

    if (!trimmedText && !trimmedLink) {
      toast.error('Please paste some content or a link first.');
      return;
    }

    setIsLoading(true);
    try {
      const inputToUse = trimmedText || trimmedLink;
      const res = await generatePostFromInput({
        input: inputToUse,
        category: selectedCategory === 'auto' ? undefined : selectedCategory,
        link: trimmedLink || undefined,
      });

      if (res.success && res.post) {
        onPostGenerated(res.post);
        setLastAutoFilledTitle(res.post.title);
        toast.success('✨ Post auto-populated with Title, Takeaways, Source & Buttons!');
      } else {
        toast.error(res.error || 'Failed to auto-generate post.');
      }
    } catch (e: any) {
      toast.error(e.message || 'Auto-generation failed.');
    } finally {
      setIsLoading(false);
    }
  };

  const detectedUrls = extractUrls(rawText);

  return (
    <div className="flex flex-col gap-3 p-3.5 sm:p-4 rounded-2xl bg-gradient-to-b from-slate-900/90 via-slate-950/80 to-slate-900/90 border border-cyan-500/35 backdrop-blur-xl shadow-xl shadow-black/40">
      {/* Header with Title & Tab Switcher */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/30 border border-cyan-500/50 flex items-center justify-center text-cyan-400 shadow-inner">
            <Zap className="w-4 h-4 text-cyan-300" />
          </div>
          <div>
            <h3 className="text-xs sm:text-sm font-bold text-white tracking-wide flex items-center gap-1.5">
              <span>Magic Smart Auto-Fill</span>
              <span className="text-[10px] font-medium bg-cyan-950/80 border border-cyan-700/60 text-cyan-300 px-1.5 py-0.2 rounded-full">
                1-Click
              </span>
            </h3>
            <p className="text-[10px] text-slate-400">
              Paste content or link — we'll structure title, bullets, source & buttons
            </p>
          </div>
        </div>

        {/* Tab Toggle: Content vs Link Tab */}
        <div className="flex items-center bg-slate-950/80 border border-slate-800 p-0.5 rounded-xl text-xs shrink-0">
          <button
            type="button"
            onClick={() => setActiveTab('content')}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
              activeTab === 'content'
                ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            📝 Content
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('link')}
            className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all flex items-center gap-1 ${
              activeTab === 'link'
                ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/40 shadow-sm'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <LinkIcon className="w-3 h-3" />
            <span>Link Tab</span>
            {explicitLink && <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />}
          </button>
        </div>
      </div>

      {/* Tab 1: Content Input */}
      {activeTab === 'content' && (
        <div className="flex flex-col gap-2 animate-in fade-in duration-150">
          <div className="relative">
            <Textarea
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
                  e.preventDefault();
                  handleAutoFill();
                }
              }}
              placeholder="Paste article, tweet, newsletter, job post, or announcement here... (Press Cmd/Ctrl+Enter to auto-fill)"
              rows={3}
              className="text-xs sm:text-xs leading-relaxed bg-slate-950/80 border-slate-800 text-slate-100 placeholder:text-slate-500 rounded-xl focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40 p-3 shadow-inner resize-none font-sans"
            />
          </div>

          {/* Quick Helper Pill Row */}
          <div className="flex items-center justify-between gap-1 text-[11px]">
            <div className="flex items-center gap-1.5 flex-wrap">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handlePasteClipboard}
                className="h-7 px-2 text-[11px] bg-slate-950/60 border-slate-800 hover:border-cyan-500/40 text-slate-300 hover:text-white rounded-lg"
              >
                <ClipboardPaste className="w-3 h-3 mr-1 text-cyan-400" />
                Paste Clipboard
              </Button>

              {rawText && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={handleClear}
                  className="h-7 px-2 text-[11px] text-slate-400 hover:text-rose-300 rounded-lg"
                >
                  <Trash2 className="w-3 h-3 mr-1" />
                  Clear
                </Button>
              )}
            </div>

            {detectedUrls.length > 0 && (
              <span className="text-[10px] text-cyan-400 font-mono flex items-center gap-1 bg-cyan-950/50 px-2 py-0.5 rounded-md border border-cyan-900/60 truncate max-w-[170px] sm:max-w-[240px]">
                <LinkIcon className="w-2.5 h-2.5 shrink-0" />
                {detectedUrls[0].replace(/^https?:\/\//, '')}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Dedicated Link Tab */}
      {activeTab === 'link' && (
        <div className="flex flex-col gap-2 p-2.5 rounded-xl bg-slate-950/70 border border-slate-800/80 animate-in fade-in duration-150">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
              <LinkIcon className="w-3.5 h-3.5 text-cyan-400" />
              Source URL / Action Link
            </span>
            <span className="text-[10px] text-slate-500">Auto-wired into inline buttons</span>
          </div>
          <Input
            value={explicitLink}
            onChange={(e) => setExplicitLink(e.target.value)}
            placeholder="https://... (e.g. original article, job posting, repo)"
            className="h-8 text-xs bg-slate-900 border-slate-800 text-slate-100 placeholder:text-slate-500 rounded-lg font-mono"
          />
          <p className="text-[10px] text-slate-400 leading-tight">
            💡 If you paste content without links in the Content tab, you can enter the link here. It will automatically become the primary source and the Telegram action button.
          </p>
        </div>
      )}

      {/* Always Visible Compact Link Row when in Content tab (if link exists or user wants quick access) */}
      {activeTab === 'content' && (
        <div className="flex items-center gap-2 pt-0.5">
          <div className="flex-1 flex items-center gap-1.5 bg-slate-950/60 border border-slate-800/80 rounded-xl px-2.5 py-1">
            <LinkIcon className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
            <input
              type="text"
              value={explicitLink}
              onChange={(e) => setExplicitLink(e.target.value)}
              placeholder="Source Link (Optional — auto-detected if in text)"
              className="bg-transparent border-none text-[11px] text-slate-200 placeholder:text-slate-500 focus:outline-none w-full font-mono"
            />
          </div>

          <div className="w-28 shrink-0">
            <Select
              value={selectedCategory}
              onValueChange={(val) => setSelectedCategory(val as any)}
            >
              <SelectTrigger className="h-7 text-[11px] bg-slate-950/60 border-slate-800 text-slate-300 rounded-xl">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-200 text-xs z-50">
                <SelectItem value="auto">✨ Auto Detect</SelectItem>
                <SelectItem value="ai_news">🚨 AI News</SelectItem>
                <SelectItem value="job">💼 Job</SelectItem>
                <SelectItem value="internship">🎓 Internship</SelectItem>
                <SelectItem value="hackathon">🏆 Hackathon</SelectItem>
                <SelectItem value="ai_tool">🛠 AI Tool</SelectItem>
                <SelectItem value="github">💻 GitHub</SelectItem>
                <SelectItem value="career">🚀 Career</SelectItem>
                <SelectItem value="resource">📚 Resource</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      )}

      {/* Primary Action Buttons Row */}
      <div className="flex items-center gap-2 pt-1">
        <Button
          type="button"
          onClick={handleAutoFill}
          disabled={isLoading || (!rawText.trim() && !explicitLink.trim())}
          className="flex-1 h-9 sm:h-9 text-xs sm:text-xs font-bold bg-gradient-to-r from-cyan-600 via-blue-600 to-indigo-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-xl shadow-lg shadow-cyan-950/60 transition-all active:scale-[0.98]"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
              Generating Post...
            </>
          ) : (
            <>
              <Sparkles className="w-3.5 h-3.5 mr-1.5 text-cyan-200" />
              Auto-Fill Post
            </>
          )}
        </Button>

        {onPublishClick && (
          <Button
            type="button"
            onClick={onPublishClick}
            disabled={isPublishing}
            className="h-9 px-3.5 text-xs font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl shadow-lg shadow-emerald-950/60 shrink-0 transition-all active:scale-[0.98]"
            title="Publish directly to Telegram"
          >
            <Send className="w-3.5 h-3.5 mr-1 text-emerald-100" />
            Publish
          </Button>
        )}
      </div>

      {/* Status pill after auto-filling */}
      {lastAutoFilledTitle && (
        <div className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-[11px] text-emerald-300 animate-in fade-in duration-200">
          <span className="flex items-center gap-1.5 truncate">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="truncate font-medium">Ready: {lastAutoFilledTitle}</span>
          </span>
          <span className="text-[10px] text-emerald-400/80 shrink-0 font-semibold pl-2">
            Form & Preview updated
          </span>
        </div>
      )}
    </div>
  );
};
