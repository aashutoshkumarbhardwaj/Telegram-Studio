import React, { useState, useEffect } from 'react';
import { ContentType, InlineButton, MediaItem, PostSchema } from '@/types/postSchema';
import { TemplateStyle, formatPostHtml } from '@/lib/templates';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Sparkles,
  Zap,
  Send,
  ClipboardPaste,
  Trash2,
  Loader2,
  CheckCircle2,
  Link as LinkIcon,
  ExternalLink,
  Plus,
  X,
  ChevronDown,
  ChevronUp,
  SlidersHorizontal,
  Layers,
  Eye,
  Edit3,
  Check,
  Heart,
} from 'lucide-react';
import { generatePostFromInput } from '@/lib/api';
import { extractUrls, buildButtons } from '@/lib/smartExtractor';
import { toast } from 'sonner';

interface ContentEditorProps {
  post: PostSchema;
  templateStyle: TemplateStyle;
  onPostChange: (updater: (prev: PostSchema) => PostSchema) => void;
  onTemplateChange: (style: TemplateStyle) => void;
  onOpenAIGenerator?: () => void;
  onPublishClick?: () => void;
  isPublishing?: boolean;
  onViewPreview?: () => void;
}

export const ContentEditor: React.FC<ContentEditorProps> = ({
  post,
  templateStyle,
  onPostChange,
  onTemplateChange,
  onOpenAIGenerator,
  onPublishClick,
  isPublishing = false,
  onViewPreview,
}) => {
  // Tabs: Content vs Link Tab
  const [activeTab, setActiveTab] = useState<'content' | 'link'>('content');
  const [rawText, setRawText] = useState('');
  const [explicitLink, setExplicitLink] = useState('');
  const [isLinkRemoved, setIsLinkRemoved] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [lastAutoFilledTitle, setLastAutoFilledTitle] = useState<string | null>(null);

  const [isCategoryManual, setIsCategoryManual] = useState(false);
  const [isPreviewEditing, setIsPreviewEditing] = useState(false);
  const [isLiked, setIsLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(0);

  // Custom button adder state
  const [isAddingButton, setIsAddingButton] = useState(false);
  const [newBtnText, setNewBtnText] = useState('');
  const [newBtnUrl, setNewBtnUrl] = useState('');

  // Optional fine-tune text drawer
  const [showFineTune, setShowFineTune] = useState(false);

  const handleRemoveLink = () => {
    setExplicitLink('');
    setIsLinkRemoved(true);
    onPostChange((prev) => {
      const remainingButtons = (prev.buttons || []).filter((btn) => {
        return btn.callback_data === 'react_like' || btn.text.includes('Discuss') || !btn.url;
      });
      return {
        ...prev,
        source: undefined,
        buttons: remainingButtons,
      };
    });
    toast.info('Source link removed');
  };

  const handleLinkChange = (val: string) => {
    setExplicitLink(val);
    if (!val.trim()) {
      handleRemoveLink();
    } else {
      setIsLinkRemoved(false);
      const cleanUrl = val.trim();
      onPostChange((prev) => {
        const updatedButtons = [...(prev.buttons || [])];
        const resourceBtnIdx = updatedButtons.findIndex(
          (b) => b.url && !b.text.includes('Discuss') && b.callback_data !== 'react_like'
        );
        let label = '📚 Read Source';
        if (prev.content_type === 'job') label = '💼 Apply Now';
        else if (prev.content_type === 'internship') label = '🎓 Apply for Internship';
        else if (prev.content_type === 'hackathon') label = '🏆 Register Now';
        else if (prev.content_type === 'ai_tool') label = '🛠 Try Tool';
        else if (prev.content_type === 'github') label = '💻 View on GitHub';
        else if (prev.content_type === 'resource') label = '📖 Access Resource';
        else if (prev.content_type === 'career') label = '🚀 Read Guide';

        if (resourceBtnIdx >= 0) {
          updatedButtons[resourceBtnIdx] = { ...updatedButtons[resourceBtnIdx], url: cleanUrl };
        } else {
          updatedButtons.unshift({ text: label, url: cleanUrl });
        }

        return {
          ...prev,
          source: { title: 'Official Source', url: cleanUrl },
          buttons: updatedButtons,
        };
      });
    }
  };

  // Auto-extract link from raw text if user hasn't explicitly set or removed one
  useEffect(() => {
    if (isLinkRemoved) return;
    const urls = extractUrls(rawText);
    if (urls.length > 0 && !explicitLink) {
      setExplicitLink(urls[0]);
    }
  }, [rawText, explicitLink, isLinkRemoved]);

  // Sync explicitLink if post already has a source URL
  useEffect(() => {
    if (post.source?.url && !explicitLink && !isLinkRemoved) {
      setExplicitLink(post.source.url);
    }
  }, [post.source?.url, explicitLink, isLinkRemoved]);

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
        toast.info('Clipboard access restricted. Use Ctrl+V / Cmd+V directly in the box.');
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

  // 1-Click Auto-Fill
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
        category: isCategoryManual ? post.content_type : undefined,
        link: trimmedLink || undefined,
      });

      if (res.success && res.post) {
        onPostChange(() => res.post!);
        onTemplateChange(res.post.content_type as TemplateStyle);
        setIsCategoryManual(false);
        setLastAutoFilledTitle(res.post.title);
        toast.success('✨ Post auto-populated with Title, Bullets & Buttons!');
      } else {
        toast.error(res.error || 'Failed to auto-generate post.');
      }
    } catch (e: any) {
      toast.error(e.message || 'Auto-generation failed.');
    } finally {
      setIsLoading(false);
    }
  };

  // Category change helper (with auto-updating button labels if mistaken)
  const handleCategoryChange = (newCat: ContentType) => {
    setIsCategoryManual(true);
    onTemplateChange(newCat as TemplateStyle);
    onPostChange((prev) => {
      // Re-label primary resource button if one exists
      const updatedButtons = (prev.buttons || []).map((btn) => {
        if (btn.text.includes('Read Source') || btn.text.includes('Apply') || btn.text.includes('Try Tool') || btn.text.includes('Register') || btn.text.includes('GitHub')) {
          let label = '📚 Read Source';
          if (newCat === 'job') label = '💼 Apply Now';
          else if (newCat === 'internship') label = '🎓 Apply for Internship';
          else if (newCat === 'hackathon') label = '🏆 Register Now';
          else if (newCat === 'ai_tool') label = '🛠 Try Tool';
          else if (newCat === 'github') label = '💻 View on GitHub';
          else if (newCat === 'resource') label = '📖 Access Resource';
          else if (newCat === 'career') label = '🚀 Read Guide';
          return { ...btn, text: label };
        }
        return btn;
      });

      return {
        ...prev,
        content_type: newCat,
        buttons: updatedButtons,
      };
    });
  };

  // Button management helpers
  const handleRemoveButton = (index: number) => {
    onPostChange((prev) => ({
      ...prev,
      buttons: (prev.buttons || []).filter((_, i) => i !== index),
    }));
  };

  const handleAddCustomButton = () => {
    if (!newBtnText.trim() || !newBtnUrl.trim()) {
      toast.error('Please enter both button text and URL.');
      return;
    }
    const newBtn: InlineButton = {
      text: newBtnText.trim(),
      url: newBtnUrl.trim(),
    };
    onPostChange((prev) => ({
      ...prev,
      buttons: [...(prev.buttons || []), newBtn],
    }));
    setNewBtnText('');
    setNewBtnUrl('');
    setIsAddingButton(false);
    toast.success('Button added!');
  };

  // Fine-tune text changes
  const handleTitleChange = (val: string) => {
    onPostChange((prev) => ({ ...prev, title: val }));
  };

  const handleBodyChange = (val: string) => {
    onPostChange((prev) => ({ ...prev, body: val, summary: val }));
  };

  const handleImageChange = (url: string) => {
    const trimmed = url.trim();
    onPostChange((prev) => ({
      ...prev,
      media: trimmed ? [{ type: 'photo', url_or_path: trimmed }] : [],
    }));
  };

  const detectedUrls = extractUrls(rawText);
  const activeButtons = post.buttons || [];

  return (
    <div className="flex flex-col gap-3.5 sm:gap-4 w-full p-1 sm:p-2">
      {/* ─── 1. HERO: MAGIC SMART AUTO-FILL CARD ──────────────────────────── */}
      <div className="flex flex-col gap-3 p-3.5 sm:p-4 rounded-2xl bg-gradient-to-b from-slate-900/95 via-slate-950/90 to-slate-900/95 border border-cyan-500/35 backdrop-blur-xl shadow-xl shadow-black/40">
        {/* Header with Title & Tabs */}
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
                Paste content or link — we auto-configure title, bullets, source & buttons
              </p>
            </div>
          </div>

          {/* Tab Switcher: Content vs Link Tab */}
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

        {/* Tab 1: Content Textarea */}
        {activeTab === 'content' && (
          <div className="flex flex-col gap-2 animate-in fade-in duration-150">
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
              rows={4}
              className="text-xs sm:text-xs leading-relaxed bg-slate-950/80 border-slate-800 text-slate-100 placeholder:text-slate-500 rounded-xl focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40 p-3 shadow-inner resize-none font-sans"
            />

            {/* Quick Action Helpers */}
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
                <span className="text-[10px] text-cyan-400 font-mono flex items-center gap-1 bg-cyan-950/50 px-2 py-0.5 rounded-md border border-cyan-900/60 truncate max-w-[170px] sm:max-w-[220px]">
                  <LinkIcon className="w-2.5 h-2.5 shrink-0" />
                  {detectedUrls[0].replace(/^https?:\/\//, '')}
                </span>
              )}
            </div>

            {/* Compact Link Row */}
            <div className="flex items-center justify-between gap-1.5 bg-slate-950/60 border border-slate-800/80 rounded-xl px-2.5 py-1 mt-0.5">
              <div className="flex items-center gap-1.5 flex-1 min-w-0">
                <LinkIcon className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <input
                  type="text"
                  value={explicitLink}
                  onChange={(e) => handleLinkChange(e.target.value)}
                  placeholder="Source Link (Optional — auto-detected if included in text)"
                  className="bg-transparent border-none text-[11px] text-slate-200 placeholder:text-slate-500 focus:outline-none w-full font-mono"
                />
              </div>
              {explicitLink && (
                <button
                  type="button"
                  onClick={handleRemoveLink}
                  className="text-slate-400 hover:text-rose-400 p-0.5 rounded transition-colors text-[10px] flex items-center gap-0.5 shrink-0"
                  title="Remove source link"
                >
                  <X className="w-3.5 h-3.5" />
                  <span className="hidden sm:inline">Remove</span>
                </button>
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
              {explicitLink && (
                <button
                  type="button"
                  onClick={handleRemoveLink}
                  className="text-xs text-rose-400 hover:text-rose-300 flex items-center gap-1 font-medium transition-colors"
                >
                  <X className="w-3 h-3" />
                  <span>Remove Link</span>
                </button>
              )}
            </div>
            <div className="relative flex items-center">
              <Input
                value={explicitLink}
                onChange={(e) => handleLinkChange(e.target.value)}
                placeholder="https://... (e.g. original article, job posting, repo link)"
                className="h-8 text-xs bg-slate-900 border-slate-800 text-slate-100 placeholder:text-slate-500 rounded-lg font-mono pr-8"
              />
              {explicitLink && (
                <button
                  type="button"
                  onClick={handleRemoveLink}
                  className="absolute right-2 text-slate-400 hover:text-rose-400 p-0.5 rounded"
                  title="Clear link"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
            <p className="text-[10px] text-slate-400 leading-tight">
              💡 If you copied content without links, enter the link here. It will automatically become the primary source and the Telegram action button.
            </p>
          </div>
        )}

        {/* ─── CATEGORY & TEMPLATE CORRECTION ROW ─────────────────────────── */}
        <div className="grid grid-cols-2 gap-2.5 p-2.5 rounded-xl bg-slate-950/70 border border-slate-800/80">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-semibold text-slate-300 flex items-center gap-1">
                <Layers className="w-3 h-3 text-cyan-400" />
                Category
              </span>
              <span className="text-[9px] text-cyan-400/80 font-mono">Auto-chosen</span>
            </div>
            <Select
              value={post.content_type}
              onValueChange={(val) => handleCategoryChange(val as ContentType)}
            >
              <SelectTrigger className="h-8 text-xs bg-slate-900 border-slate-800 text-slate-200 rounded-lg">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-200 text-xs z-50">
                <SelectItem value="ai_news">🚨 AI News</SelectItem>
                <SelectItem value="job">💼 Job Alert</SelectItem>
                <SelectItem value="internship">🎓 Internship</SelectItem>
                <SelectItem value="hackathon">🏆 Hackathon</SelectItem>
                <SelectItem value="ai_tool">🛠 AI Tool</SelectItem>
                <SelectItem value="github">💻 GitHub</SelectItem>
                <SelectItem value="career">🚀 Career</SelectItem>
                <SelectItem value="resource">📚 Resource</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-semibold text-slate-300">Template Layout</span>
              <span className="text-[9px] text-cyan-400/80 font-mono">Layout</span>
            </div>
            <Select
              value={templateStyle}
              onValueChange={(val) => onTemplateChange(val as TemplateStyle)}
            >
              <SelectTrigger className="h-8 text-xs bg-slate-900 border-slate-800 text-slate-200 rounded-lg">
                <SelectValue placeholder="Layout" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-200 text-xs z-50">
                <SelectItem value="auto">✨ Auto (Recommended)</SelectItem>
                <SelectItem value="ai_news">Editorial (AI News)</SelectItem>
                <SelectItem value="job">Job Card</SelectItem>
                <SelectItem value="internship">Internship Card</SelectItem>
                <SelectItem value="hackathon">Hackathon Card</SelectItem>
                <SelectItem value="ai_tool">Tool Card</SelectItem>
                <SelectItem value="github">GitHub Card</SelectItem>
                <SelectItem value="career">Career Card</SelectItem>
                <SelectItem value="resource">Resource Card</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* ─── AUTO-CONFIGURED BUTTONS MANAGER ─────────────────────────────── */}
        <div className="flex flex-col gap-2 p-2.5 sm:p-3 rounded-xl bg-slate-950/70 border border-slate-800/80">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
              <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
              <span>Auto-Configured Buttons</span>
              <span className="text-[10px] text-slate-500 font-normal">({activeButtons.length})</span>
            </div>
            <button
              type="button"
              onClick={() => setIsAddingButton(!isAddingButton)}
              className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-medium transition-colors"
            >
              <Plus className="w-3 h-3" />
              <span>Add Custom Button</span>
            </button>
          </div>

          {/* Button Chips */}
          <div className="flex flex-wrap gap-1.5">
            {activeButtons.length === 0 && (
              <span className="text-[11px] text-slate-500 italic">No buttons attached yet.</span>
            )}
            {activeButtons.map((btn, idx) => (
              <div
                key={idx}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 shadow-sm"
              >
                <span className="font-medium text-[11px]">{btn.text}</span>
                <button
                  type="button"
                  onClick={() => handleRemoveButton(idx)}
                  className="text-slate-500 hover:text-rose-400 p-0.5 rounded transition-colors"
                  title="Remove button"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>

          {/* Inline Add Button Form */}
          {isAddingButton && (
            <div className="flex flex-col gap-2 p-2.5 rounded-lg bg-slate-900/90 border border-slate-800 mt-1 animate-in fade-in duration-150">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                <Input
                  value={newBtnText}
                  onChange={(e) => setNewBtnText(e.target.value)}
                  placeholder="Button Label (e.g. 🎁 Claim Bonus)"
                  className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100"
                />
                <Input
                  value={newBtnUrl}
                  onChange={(e) => setNewBtnUrl(e.target.value)}
                  placeholder="URL (https://...)"
                  className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100 font-mono"
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsAddingButton(false)}
                  className="h-7 text-xs px-2.5 text-slate-400 hover:text-white"
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  size="sm"
                  onClick={handleAddCustomButton}
                  className="h-7 text-xs px-3 bg-cyan-600 hover:bg-cyan-500 text-white"
                >
                  Add
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Primary Action Buttons: Auto-Fill & Publish */}
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
              className="h-9 px-4 text-xs font-bold bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl shadow-lg shadow-emerald-950/60 shrink-0 transition-all active:scale-[0.98]"
              title="Publish directly to Telegram"
            >
              <Send className="w-3.5 h-3.5 mr-1 text-emerald-100" />
              Publish
            </Button>
          )}
        </div>

        {/* Ready Status Feedback */}
        {lastAutoFilledTitle && (
          <div className="flex items-center justify-between px-2.5 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/50 text-[11px] text-emerald-300 animate-in fade-in duration-200">
            <span className="flex items-center gap-1.5 truncate">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span className="truncate font-medium">Ready: {lastAutoFilledTitle}</span>
            </span>
            <span className="text-[10px] text-emerald-400/80 shrink-0 font-semibold pl-2">
              Preview updated
            </span>
          </div>
        )}
      </div>

      {/* ─── 2. LIVE INLINE TELEGRAM MESSAGE PREVIEW CARD ───────────────── */}
      <div className="flex flex-col gap-2.5 p-3 sm:p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800/90 backdrop-blur-xl shadow-lg">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
              <Eye className="w-3.5 h-3.5 text-cyan-400" />
              <span>Live Post Preview</span>
            </span>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-cyan-950/80 border border-cyan-800/60 text-cyan-300">
              {post.content_type.replace('_', ' ')}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setIsPreviewEditing(!isPreviewEditing)}
              className={`text-[11px] px-2.5 py-1 rounded-lg border font-semibold flex items-center gap-1.5 transition-all shadow-sm ${
                isPreviewEditing
                  ? 'bg-cyan-500/20 border-cyan-400/60 text-cyan-200 shadow-cyan-950/50'
                  : 'bg-slate-900 border-slate-700/80 text-slate-300 hover:text-white hover:border-cyan-500/50'
              }`}
              title={isPreviewEditing ? 'Finish editing' : 'Click to edit post text directly in preview'}
            >
              {isPreviewEditing ? (
                <>
                  <Check className="w-3 h-3 text-cyan-300" />
                  <span>Done</span>
                </>
              ) : (
                <>
                  <Edit3 className="w-3 h-3 text-cyan-400" />
                  <span>Edit in Preview</span>
                </>
              )}
            </button>
            {onViewPreview && (
              <button
                type="button"
                onClick={onViewPreview}
                className="text-[11px] text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1 transition-colors pl-1"
              >
                <span>Full View</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* Telegram Chat Bubble */}
        <div className="w-full bg-[#182533] border border-[#243447] text-slate-100 rounded-xl p-3 sm:p-3.5 shadow-md flex flex-col gap-2.5 font-sans transition-all">
          {/* Attached Media */}
          {post.media && post.media.length > 0 && post.media[0].url_or_path && (
            <div className="rounded-lg overflow-hidden border border-[#2b3e55] bg-black/40 max-h-44 flex items-center justify-center">
              <img
                src={post.media[0].url_or_path}
                alt="Post preview"
                className="w-full h-full object-cover max-h-44"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
            </div>
          )}

          {/* In-Preview Edit Mode vs Rendered View */}
          {isPreviewEditing ? (
            <div className="flex flex-col gap-2.5 p-1 animate-in fade-in duration-150">
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider">
                  Headline
                </label>
                <input
                  type="text"
                  value={post.title}
                  onChange={(e) => onPostChange((prev) => ({ ...prev, title: e.target.value }))}
                  placeholder="Post Headline..."
                  className="h-8 text-xs bg-slate-900/90 border border-cyan-500/50 text-white font-semibold rounded-lg px-2.5 focus:outline-none focus:ring-1 focus:ring-cyan-400"
                />
              </div>
              <div className="flex flex-col gap-1">
                <label className="text-[10px] font-bold text-cyan-400 uppercase tracking-wider flex items-center justify-between">
                  <span>Message Content (Preserves formatting & links)</span>
                  <span className="text-[9px] text-slate-400 font-normal">Supports &lt;b&gt;, &lt;a href="..."&gt;</span>
                </label>
                <textarea
                  value={post.body}
                  onChange={(e) => onPostChange((prev) => ({ ...prev, body: e.target.value, summary: e.target.value }))}
                  rows={9}
                  placeholder="Write or edit post content..."
                  className="w-full text-xs leading-relaxed bg-slate-900/90 border border-cyan-500/50 text-slate-100 p-2.5 resize-y font-sans rounded-lg focus:outline-none focus:ring-1 focus:ring-cyan-400"
                />
              </div>
              <div className="flex justify-end pt-1">
                <Button
                  type="button"
                  size="sm"
                  onClick={() => setIsPreviewEditing(false)}
                  className="h-7 text-xs px-3 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg shadow-sm"
                >
                  <Check className="w-3.5 h-3.5 mr-1" />
                  Done Editing
                </Button>
              </div>
            </div>
          ) : (
            <div
              onClick={() => setIsPreviewEditing(true)}
              title="Click to edit post text in preview"
              className="text-xs sm:text-[12.5px] leading-relaxed whitespace-pre-wrap select-text text-slate-100/95 cursor-pointer hover:bg-white/[0.02] p-1 rounded-lg transition-colors group relative"
            >
              <div dangerouslySetInnerHTML={{ __html: formatPostHtml(post, templateStyle) }} />
              <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute top-1 right-1 bg-slate-900/90 border border-slate-700 text-slate-300 text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 shadow-sm">
                <Edit3 className="w-2.5 h-2.5 text-cyan-400" />
                <span>Click to edit</span>
              </div>
            </div>
          )}

          {/* Inline Buttons */}
          {activeButtons.length > 0 && (
            <div className="flex flex-col gap-1.5 pt-1">
              {(() => {
                const rows: typeof activeButtons[] = [];
                for (let i = 0; i < activeButtons.length; i += 2) {
                  rows.push(activeButtons.slice(i, i + 2));
                }
                return rows.map((row, rIdx) => (
                  <div key={rIdx} className="flex items-center gap-1.5 w-full">
                    {row.map((btn, bIdx) => {
                      const isLike = btn.callback_data === 'react_like' || btn.text.includes('❤️') || btn.text.toLowerCase().includes('like');
                      if (isLike || (!btn.url && btn.callback_data)) {
                        return (
                          <button
                            key={bIdx}
                            type="button"
                            onClick={() => {
                              setIsLiked(!isLiked);
                              setLikeCount((prev) => (isLiked ? prev - 1 : prev + 1));
                              if (!isLiked) {
                                toast.success('❤️ Liked! Telegram reaction recorded.');
                              }
                            }}
                            className={`flex-1 border rounded-lg py-1.5 px-2 text-center text-[11px] font-medium flex items-center justify-center gap-1.5 transition-all shadow-sm active:scale-95 ${
                              isLiked
                                ? 'bg-rose-500/20 border-rose-500/60 text-rose-300 shadow-rose-950/40'
                                : 'bg-[#2b3e55]/80 hover:bg-[#344c68] border-[#3b526f]/60 text-white'
                            }`}
                            title="Interactive like reaction"
                          >
                            <Heart className={`w-3.5 h-3.5 ${isLiked ? 'fill-rose-400 text-rose-400 animate-bounce' : 'text-rose-400'}`} />
                            <span className="truncate">{isLiked ? `❤️ Liked (${Math.max(1, likeCount + 1)})` : btn.text}</span>
                          </button>
                        );
                      }
                      return (
                        <a
                          key={bIdx}
                          href={btn.url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex-1 bg-[#2b3e55]/80 hover:bg-[#344c68] active:bg-[#3d597a] border border-[#3b526f]/60 text-white rounded-lg py-1.5 px-2 text-center text-[11px] font-medium flex items-center justify-center gap-1 transition-colors truncate"
                        >
                          <span className="truncate">{btn.text}</span>
                          <ExternalLink className="w-2.5 h-2.5 text-cyan-400/70 shrink-0" />
                        </a>
                      );
                    })}
                  </div>
                ));
              })()}
            </div>
          )}
        </div>
      </div>

      {/* ─── 3. OPTIONAL FINE-TUNE DRAWER (COLLAPSED BY DEFAULT) ─────────── */}
      <div className="rounded-xl border border-slate-800/80 bg-slate-950/50 overflow-hidden shadow-sm">
        <button
          type="button"
          onClick={() => setShowFineTune(!showFineTune)}
          className="w-full px-3.5 py-2.5 text-xs text-slate-400 hover:text-slate-200 flex items-center justify-between transition-colors bg-slate-900/40"
        >
          <span className="flex items-center gap-1.5 font-medium">
            <SlidersHorizontal className="w-3.5 h-3.5 text-cyan-400" />
            <span>Fine-Tune Text & Media (Optional)</span>
          </span>
          {showFineTune ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>

        {showFineTune && (
          <div className="p-3.5 flex flex-col gap-3 border-t border-slate-800/80 animate-in fade-in duration-150">
            <div>
              <span className="text-[11px] font-medium text-slate-300 block mb-1">Headline</span>
              <Input
                value={post.title}
                onChange={(e) => handleTitleChange(e.target.value)}
                placeholder="Post Headline..."
                className="h-8 text-xs bg-slate-900 border-slate-800 text-white font-medium rounded-lg"
              />
            </div>

            <div>
              <span className="text-[11px] font-medium text-slate-300 block mb-1">Formatted Message Body</span>
              <Textarea
                value={post.body}
                onChange={(e) => handleBodyChange(e.target.value)}
                rows={5}
                className="text-xs leading-relaxed bg-slate-900 border-slate-800 text-slate-100 p-2.5 resize-none font-sans rounded-lg"
              />
            </div>

            <div>
              <span className="text-[11px] font-medium text-slate-300 block mb-1">Media Image URL (Optional)</span>
              <Input
                value={post.media && post.media[0] ? post.media[0].url_or_path : ''}
                onChange={(e) => handleImageChange(e.target.value)}
                placeholder="https://... (Optional image attachment)"
                className="h-8 text-xs bg-slate-900 border-slate-800 text-slate-100 font-mono rounded-lg"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
