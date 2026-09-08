import React, { useState } from 'react';
import { ContentType, InlineButton, PostSchema, VerificationStatus } from '@/types/postSchema';
import { TemplateStyle } from '@/lib/templates';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  Plus,
  Trash2,
  Image as ImageIcon,
  Link as LinkIcon,
  ShieldCheck,
  AlertTriangle,
  Layers,
  Sparkles,
  ExternalLink,
  ChevronUp,
  ChevronDown,
  X,
} from 'lucide-react';
import { SmartAutoFillBar } from './SmartAutoFillBar';

interface ContentEditorProps {
  post: PostSchema;
  templateStyle: TemplateStyle;
  onPostChange: (updater: (prev: PostSchema) => PostSchema) => void;
  onTemplateChange: (style: TemplateStyle) => void;
  onOpenAIGenerator?: () => void;
  onPublishClick?: () => void;
  isPublishing?: boolean;
}

export const ContentEditor: React.FC<ContentEditorProps> = ({
  post,
  templateStyle,
  onPostChange,
  onTemplateChange,
  onOpenAIGenerator,
  onPublishClick,
  isPublishing = false,
}) => {
  const [newTakeaway, setNewTakeaway] = useState('');
  const [newButtonText, setNewButtonText] = useState('');
  const [newButtonUrl, setNewButtonUrl] = useState('');
  const [isAddingButton, setIsAddingButton] = useState(false);
  const [imageUrlInput, setImageUrlInput] = useState('');
  const [isAddingImage, setIsAddingImage] = useState(false);

  // Field change helpers
  const handleTitleChange = (val: string) => {
    onPostChange((prev) => ({ ...prev, title: val }));
  };

  const handleBodyChange = (val: string) => {
    onPostChange((prev) => ({ ...prev, body: val, summary: val }));
  };

  const handleWhyItMattersChange = (val: string) => {
    onPostChange((prev) => ({ ...prev, why_it_matters: val }));
  };

  const handleCtaChange = (val: string) => {
    onPostChange((prev) => ({ ...prev, cta: val }));
  };

  const handleContentTypeChange = (type: ContentType) => {
    onPostChange((prev) => ({ ...prev, content_type: type }));
  };

  // Metadata field change
  const handleMetaChange = (key: string, val: string) => {
    onPostChange((prev) => ({
      ...prev,
      metadata: { ...(prev.metadata || {}), [key]: val },
    }));
  };

  // Takeaways
  const handleAddTakeaway = () => {
    if (!newTakeaway.trim()) return;
    onPostChange((prev) => ({
      ...prev,
      takeaways: [...(prev.takeaways || []), newTakeaway.trim()],
    }));
    setNewTakeaway('');
  };

  const handleRemoveTakeaway = (index: number) => {
    onPostChange((prev) => ({
      ...prev,
      takeaways: (prev.takeaways || []).filter((_, i) => i !== index),
    }));
  };

  // Buttons
  const handleAddButton = () => {
    if (!newButtonText.trim() || !newButtonUrl.trim()) return;
    const btn: InlineButton = {
      text: newButtonText.trim(),
      url: newButtonUrl.trim(),
    };
    onPostChange((prev) => ({
      ...prev,
      buttons: [...(prev.buttons || []), btn],
    }));
    setNewButtonText('');
    setNewButtonUrl('');
    setIsAddingButton(false);
  };

  const handleRemoveButton = (index: number) => {
    onPostChange((prev) => ({
      ...prev,
      buttons: (prev.buttons || []).filter((_, i) => i !== index),
    }));
  };

  const handleMoveButton = (index: number, direction: 'up' | 'down') => {
    onPostChange((prev) => {
      const btns = [...(prev.buttons || [])];
      const targetIdx = direction === 'up' ? index - 1 : index + 1;
      if (targetIdx < 0 || targetIdx >= btns.length) return prev;
      const temp = btns[index];
      btns[index] = btns[targetIdx];
      btns[targetIdx] = temp;
      return { ...prev, buttons: btns };
    });
  };

  // Source & Verification
  const handleSourceNameChange = (val: string) => {
    onPostChange((prev) => ({
      ...prev,
      source: { ...(prev.source || { title: '', url: '' }), title: val },
    }));
  };

  const handleSourceUrlChange = (val: string) => {
    onPostChange((prev) => ({
      ...prev,
      source: { ...(prev.source || { title: '', url: '' }), url: val },
    }));
  };

  const handleVerificationChange = (status: VerificationStatus) => {
    onPostChange((prev) => ({
      ...prev,
      verification: { ...(prev.verification || { status: 'verified', sources: [] }), status },
    }));
  };

  // Media
  const handleAttachImage = (url: string) => {
    if (!url.trim()) return;
    onPostChange((prev) => ({
      ...prev,
      media: [{ type: 'photo', url_or_path: url.trim() }],
    }));
    setImageUrlInput('');
    setIsAddingImage(false);
  };

  const handleRemoveImage = () => {
    onPostChange((prev) => ({
      ...prev,
      media: [],
    }));
  };

  const currentMedia = post.media && post.media.length > 0 ? post.media[0] : null;
  const meta = post.metadata || {};

  return (
    <div className="flex flex-col gap-4 sm:gap-5 w-full">
      {/* 1-Click Smart Auto-Fill & Magic Ingest Bar */}
      <SmartAutoFillBar
        onPostGenerated={(newPost) => {
          onPostChange(() => newPost);
        }}
        onPublishClick={onPublishClick}
        isPublishing={isPublishing}
      />

      {/* Optional link to Full AI Generator Modal */}
      {onOpenAIGenerator && (
        <div className="flex justify-end px-1 -mt-2">
          <button
            type="button"
            onClick={onOpenAIGenerator}
            className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
          >
            <Sparkles className="w-3 h-3 text-cyan-400" />
            <span>Need alternate headline hooks or visual concepts? Open AI Dialog →</span>
          </button>
        </div>
      )}

      {/* 1. Content Type & Template Style */}
      <div className="flex flex-col gap-2.5 p-3.5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm shadow-sm">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            Category & Template
          </Label>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <span className="text-[11px] text-slate-400 font-medium mb-1 block">Category</span>
            <Select value={post.content_type} onValueChange={(v) => handleContentTypeChange(v as ContentType)}>
              <SelectTrigger className="h-9 sm:h-8 text-xs bg-slate-950/70 border-slate-800 text-slate-200 rounded-xl focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-200">
                <SelectItem value="ai_news">🚨 AI News</SelectItem>
                <SelectItem value="job">💼 Job</SelectItem>
                <SelectItem value="internship">🎓 Internship</SelectItem>
                <SelectItem value="hackathon">🏆 Hackathon</SelectItem>
                <SelectItem value="ai_tool">🛠 AI Tool</SelectItem>
                <SelectItem value="github">💻 GitHub</SelectItem>
                <SelectItem value="career">🧠 Career</SelectItem>
                <SelectItem value="resource">📚 Resource</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <span className="text-[11px] text-slate-400 font-medium mb-1 block">Template Layout</span>
            <Select value={templateStyle} onValueChange={(v) => onTemplateChange(v as TemplateStyle)}>
              <SelectTrigger className="h-9 sm:h-8 text-xs bg-slate-950/70 border-slate-800 text-slate-200 rounded-xl focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40">
                <SelectValue placeholder="Template" />
              </SelectTrigger>
              <SelectContent className="bg-slate-900 border-slate-800 text-slate-200">
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
      </div>

      {/* 2. Core Content */}
      <div className="flex flex-col gap-3 p-3.5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm shadow-sm">
        <Label className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
          Post Content
        </Label>

        <div>
          <span className="text-xs font-medium text-slate-300 mb-1 block">Headline</span>
          <Input
            value={post.title}
            onChange={(e) => handleTitleChange(e.target.value)}
            placeholder="e.g. Google DeepMind Unveils Next-Gen Gemini Reasoning Architecture"
            className="text-sm font-semibold bg-slate-950/70 border-slate-800 text-white placeholder:text-slate-500 rounded-xl h-11 focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40 transition-all shadow-inner"
          />
        </div>

        <div>
          <span className="text-xs font-medium text-slate-300 mb-1 block">Summary / Body</span>
          <Textarea
            value={post.body}
            onChange={(e) => handleBodyChange(e.target.value)}
            placeholder="Explain the core announcement concisely..."
            rows={4}
            className="text-sm leading-relaxed bg-slate-950/70 border-slate-800 text-slate-100 placeholder:text-slate-500 rounded-xl focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40 transition-all shadow-inner p-3"
          />
        </div>

        {/* Dynamic Category Metadata */}
        {(post.content_type === 'job' || post.content_type === 'internship') && (
          <div className="grid grid-cols-2 gap-2.5 p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
            <div>
              <span className="text-[11px] text-slate-400 font-medium block mb-0.5">Company</span>
              <Input
                value={meta.company || ''}
                onChange={(e) => handleMetaChange('company', e.target.value)}
                placeholder="e.g. Modal"
                className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100 rounded-lg"
              />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 font-medium block mb-0.5">Location</span>
              <Input
                value={meta.location || ''}
                onChange={(e) => handleMetaChange('location', e.target.value)}
                placeholder="e.g. Remote / SF"
                className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100 rounded-lg"
              />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 font-medium block mb-0.5">
                {post.content_type === 'job' ? 'Salary' : 'Stipend'} (Optional)
              </span>
              <Input
                value={post.content_type === 'job' ? (meta.salary || '') : (meta.stipend || '')}
                onChange={(e) => handleMetaChange(post.content_type === 'job' ? 'salary' : 'stipend', e.target.value)}
                placeholder="e.g. $180k - $240k"
                className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100 rounded-lg"
              />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 font-medium block mb-0.5">Deadline</span>
              <Input
                value={meta.deadline || ''}
                onChange={(e) => handleMetaChange('deadline', e.target.value)}
                placeholder="e.g. Rolling / Oct 30"
                className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100 rounded-lg"
              />
            </div>
          </div>
        )}

        {post.content_type === 'hackathon' && (
          <div className="grid grid-cols-2 gap-2.5 p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
            <div>
              <span className="text-[11px] text-slate-400 font-medium block mb-0.5">Prize Pool</span>
              <Input
                value={meta.prize || ''}
                onChange={(e) => handleMetaChange('prize', e.target.value)}
                placeholder="e.g. $150,000"
                className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100 rounded-lg"
              />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 font-medium block mb-0.5">Registration Deadline</span>
              <Input
                value={meta.deadline || ''}
                onChange={(e) => handleMetaChange('deadline', e.target.value)}
                placeholder="e.g. Oct 28, 2026"
                className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100 rounded-lg"
              />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 font-medium block mb-0.5">Team Size</span>
              <Input
                value={meta.team_size || ''}
                onChange={(e) => handleMetaChange('team_size', e.target.value)}
                placeholder="e.g. 1 - 4 Members"
                className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100 rounded-lg"
              />
            </div>
            <div>
              <span className="text-[11px] text-slate-400 font-medium block mb-0.5">Format / Location</span>
              <Input
                value={meta.location || ''}
                onChange={(e) => handleMetaChange('location', e.target.value)}
                placeholder="e.g. Online / Global"
                className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100 rounded-lg"
              />
            </div>
          </div>
        )}

        {post.content_type === 'ai_tool' && (
          <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl">
            <span className="text-[11px] text-slate-400 font-medium block mb-0.5">Pricing / Model</span>
            <Input
              value={meta.pricing || ''}
              onChange={(e) => handleMetaChange('pricing', e.target.value)}
              placeholder="e.g. Open Source (MIT) / Free Tier + $20/mo"
              className="h-8 text-xs bg-slate-950 border-slate-800 text-slate-100 rounded-lg"
            />
          </div>
        )}

        {/* 3. Key Takeaways List */}
        <div className="flex flex-col gap-2 pt-1">
          <span className="text-xs font-semibold text-slate-300 flex items-center justify-between">
            <span>Key Takeaways (Bullets)</span>
            <span className="text-[10px] text-slate-500 font-normal">{(post.takeaways || []).length} items</span>
          </span>

          <div className="flex flex-col gap-2">
            {(post.takeaways || []).map((t, idx) => (
              <div key={idx} className="flex items-center gap-2 bg-slate-950/70 border border-slate-800/90 rounded-xl p-2.5 shadow-inner">
                <span className="text-cyan-400 font-bold text-xs pl-0.5">•</span>
                <span className="text-xs text-slate-200 flex-1 select-text leading-tight">{t}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemoveTakeaway(idx)}
                  className="h-6 w-6 text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 rounded-lg"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            ))}

            <div className="flex items-center gap-2 mt-1">
              <Input
                value={newTakeaway}
                onChange={(e) => setNewTakeaway(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddTakeaway()}
                placeholder="Add a bullet takeaway..."
                className="h-9 text-xs bg-slate-950/70 border-slate-800 text-slate-100 placeholder:text-slate-500 rounded-xl focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
              />
              <Button size="sm" onClick={handleAddTakeaway} className="h-9 px-3 text-xs bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl shadow-sm">
                <Plus className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>

        {/* 4. Why It Matters */}
        <div>
          <span className="text-xs font-semibold text-slate-300 mb-1 block">Why It Matters / Best For</span>
          <Textarea
            value={post.why_it_matters || ''}
            onChange={(e) => handleWhyItMattersChange(e.target.value)}
            placeholder="Contextual insight or target audience..."
            rows={2}
            className="text-xs leading-relaxed bg-slate-950/70 border-slate-800 text-slate-100 placeholder:text-slate-500 rounded-xl focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40 p-3 shadow-inner"
          />
        </div>
      </div>

      {/* 5. Source & Verification Panel */}
      <div className="flex flex-col gap-3 p-3.5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm shadow-sm">
        <Label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
          <LinkIcon className="w-3.5 h-3.5 text-cyan-400" />
          Source & Trust Verification
        </Label>

        <div className="grid grid-cols-2 gap-2.5">
          <div>
            <span className="text-[11px] text-slate-400 font-medium block mb-1">Source Name</span>
            <Input
              value={post.source?.title || ''}
              onChange={(e) => handleSourceNameChange(e.target.value)}
              placeholder="e.g. Google Official Blog"
              className="h-9 text-xs bg-slate-950/70 border-slate-800 text-slate-100 placeholder:text-slate-500 rounded-xl focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
            />
          </div>
          <div>
            <span className="text-[11px] text-slate-400 font-medium block mb-1">Source URL</span>
            <Input
              value={post.source?.url || ''}
              onChange={(e) => handleSourceUrlChange(e.target.value)}
              placeholder="https://..."
              className="h-9 text-xs bg-slate-950/70 border-slate-800 text-slate-100 placeholder:text-slate-500 rounded-xl focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
            />
          </div>
        </div>

        <div>
          <span className="text-[11px] text-slate-400 font-medium block mb-1.5">Verification Status</span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant={post.verification?.status === 'verified' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleVerificationChange('verified')}
              className={`h-8 text-xs flex-1 rounded-xl transition-all ${
                post.verification?.status === 'verified'
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm shadow-emerald-950 border-emerald-500'
                  : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:text-emerald-300'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5 mr-1" />
              Verified
            </Button>
            <Button
              type="button"
              variant={post.verification?.status === 'needs_verification' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleVerificationChange('needs_verification')}
              className={`h-8 text-xs flex-1 rounded-xl transition-all ${
                post.verification?.status === 'needs_verification'
                  ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-sm shadow-amber-950 border-amber-500'
                  : 'border-slate-800 bg-slate-950/60 text-slate-400 hover:text-amber-300'
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5 mr-1" />
              Needs Verification
            </Button>
          </div>
        </div>
      </div>

      {/* 6. Media Attachment */}
      <div className="flex flex-col gap-2.5 p-3.5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm shadow-sm">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
            Media Attachment
          </Label>
          {currentMedia && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRemoveImage}
              className="h-6 text-[11px] text-rose-400 hover:text-rose-300 hover:bg-rose-950/30 px-2 rounded-lg"
            >
              Remove
            </Button>
          )}
        </div>

        {currentMedia ? (
          <div className="relative rounded-xl overflow-hidden border border-slate-800 max-h-48 bg-slate-950 flex items-center justify-center shadow-inner">
            <img
              src={currentMedia.url_or_path}
              alt="Post media"
              className="w-full h-40 object-cover"
              onError={(e) => {
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
          </div>
        ) : isAddingImage ? (
          <div className="flex flex-col gap-2 pt-1">
            <Input
              value={imageUrlInput}
              onChange={(e) => setImageUrlInput(e.target.value)}
              placeholder="Paste image URL (https://...)"
              className="h-9 text-xs bg-slate-950/70 border-slate-800 text-slate-100 placeholder:text-slate-500 rounded-xl focus:border-cyan-500/80 focus:ring-1 focus:ring-cyan-500/40"
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={() => handleAttachImage(imageUrlInput)} className="h-8 text-xs flex-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl">
                Attach Image
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsAddingImage(false)}
                className="h-8 text-xs px-3 text-slate-400 hover:text-slate-200 rounded-xl"
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsAddingImage(true)}
            className="h-9 text-xs border border-dashed border-slate-800 hover:border-cyan-500/50 bg-slate-950/40 text-slate-300 hover:text-white rounded-xl transition-all"
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            Add Image (URL or Upload)
          </Button>
        )}
      </div>

      {/* 7. Inline Buttons Builder */}
      <div className="flex flex-col gap-2.5 p-3.5 bg-slate-900/60 border border-slate-800/80 rounded-2xl backdrop-blur-sm shadow-sm">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
            Inline Keyboard Buttons
          </Label>
          <span className="text-[10px] text-slate-500">{(post.buttons || []).length} buttons</span>
        </div>

        <div className="flex flex-col gap-2">
          {(post.buttons || []).map((btn, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between bg-slate-950/70 border border-slate-800/90 rounded-xl p-2.5 gap-2 shadow-inner"
            >
              <div className="flex-1 min-w-0">
                <span className="text-xs font-medium text-slate-200 block truncate">{btn.text}</span>
                <span className="text-[10px] text-cyan-400 block truncate font-mono">{btn.url}</span>
              </div>
              <div className="flex items-center gap-0.5">
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={idx === 0}
                  onClick={() => handleMoveButton(idx, 'up')}
                  className="h-6 w-6 text-slate-400 hover:text-slate-200 disabled:opacity-20 rounded-md"
                >
                  <ChevronUp className="w-3.5 h-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={idx === (post.buttons || []).length - 1}
                  onClick={() => handleMoveButton(idx, 'down')}
                  className="h-6 w-6 text-slate-400 hover:text-slate-200 disabled:opacity-20 rounded-md"
                >
                  <ChevronDown className="w-3.5 h-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemoveButton(idx)}
                  className="h-6 w-6 text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 rounded-md"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          ))}

          {isAddingButton ? (
            <div className="flex flex-col gap-2 p-2.5 bg-slate-950/80 border border-slate-800 rounded-xl mt-1">
              <Input
                value={newButtonText}
                onChange={(e) => setNewButtonText(e.target.value)}
                placeholder="Button Label (e.g. 📚 Read Source)"
                className="h-8 text-xs bg-slate-900 border-slate-800 text-slate-100 rounded-lg"
              />
              <Input
                value={newButtonUrl}
                onChange={(e) => setNewButtonUrl(e.target.value)}
                placeholder="Target URL (https://...)"
                className="h-8 text-xs bg-slate-900 border-slate-800 text-slate-100 rounded-lg font-mono"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={handleAddButton} className="h-7 text-xs flex-1 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg">
                  Add Button
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsAddingButton(false)}
                  className="h-7 text-xs px-2 text-slate-400 rounded-lg"
                >
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsAddingButton(true)}
              className="h-9 text-xs border border-dashed border-slate-800 hover:border-cyan-500/50 bg-slate-950/40 text-slate-300 hover:text-white rounded-xl transition-all mt-0.5"
            >
              <Plus className="w-3.5 h-3.5 mr-1" />
              Add Button
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};
