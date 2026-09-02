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

interface ContentEditorProps {
  post: PostSchema;
  templateStyle: TemplateStyle;
  onPostChange: (updater: (prev: PostSchema) => PostSchema) => void;
  onTemplateChange: (style: TemplateStyle) => void;
  onOpenAIGenerator?: () => void;
}

export const ContentEditor: React.FC<ContentEditorProps> = ({
  post,
  templateStyle,
  onPostChange,
  onTemplateChange,
  onOpenAIGenerator,
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
    <div className="flex flex-col gap-5 sm:gap-6 p-3 sm:p-4 pb-28 sm:pb-12 overflow-y-auto max-w-full">
      {/* Quick AI Generator Banner for Mobile / Fast Entry */}
      {onOpenAIGenerator && (
        <div className="flex items-center justify-between p-3 rounded-xl bg-gradient-to-r from-cyan-950/40 via-blue-950/30 to-slate-900/50 border border-cyan-500/30 shadow-sm">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-900/60 border border-cyan-700/60 flex items-center justify-center text-cyan-300">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h4 className="text-xs font-semibold text-white">Generate with AI</h4>
              <p className="text-[10px] text-slate-400">Paste URL, text, or rough idea</p>
            </div>
          </div>
          <Button
            size="sm"
            onClick={onOpenAIGenerator}
            className="h-8 px-3 text-xs font-medium bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-sm"
          >
            ✨ Start
          </Button>
        </div>
      )}

      {/* 1. Content Type & Template Style */}
      <div className="flex flex-col gap-2 p-3 bg-muted/20 border border-border/60 rounded-xl">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
            <Layers className="w-3.5 h-3.5 text-cyan-400" />
            Category & Template
          </Label>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-[11px] text-muted-foreground mb-1 block">Category</span>
            <Select value={post.content_type} onValueChange={(v) => handleContentTypeChange(v as ContentType)}>
              <SelectTrigger className="h-9 sm:h-8 text-xs bg-background/80">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
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
            <span className="text-[11px] text-muted-foreground mb-1 block">Template Layout</span>
            <Select value={templateStyle} onValueChange={(v) => onTemplateChange(v as TemplateStyle)}>
              <SelectTrigger className="h-9 sm:h-8 text-xs bg-background/80">
                <SelectValue placeholder="Template" />
              </SelectTrigger>
              <SelectContent>
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
      <div className="flex flex-col gap-3">
        <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          Post Content
        </Label>

        <div>
          <span className="text-xs font-medium text-foreground mb-1 block">Headline</span>
          <Input
            value={post.title}
            onChange={(e) => handleTitleChange(e.target.value)}
            placeholder="e.g. Google DeepMind Unveils Next-Gen Gemini Reasoning Architecture"
            className="text-base sm:text-sm font-medium bg-background/80 h-10 sm:h-9"
          />
        </div>

        <div>
          <span className="text-xs font-medium text-foreground mb-1 block">Summary / Body</span>
          <Textarea
            value={post.body}
            onChange={(e) => handleBodyChange(e.target.value)}
            placeholder="Explain the core announcement concisely..."
            rows={4}
            className="text-base sm:text-xs leading-relaxed bg-background/80"
          />
        </div>

        {/* Dynamic Category Metadata */}
        {(post.content_type === 'job' || post.content_type === 'internship') && (
          <div className="grid grid-cols-2 gap-2 p-3 bg-muted/20 border border-border/60 rounded-lg">
            <div>
              <span className="text-[11px] text-muted-foreground block mb-0.5">Company</span>
              <Input
                value={meta.company || ''}
                onChange={(e) => handleMetaChange('company', e.target.value)}
                placeholder="e.g. Modal"
                className="h-7 text-xs bg-background/80"
              />
            </div>
            <div>
              <span className="text-[11px] text-muted-foreground block mb-0.5">Location</span>
              <Input
                value={meta.location || ''}
                onChange={(e) => handleMetaChange('location', e.target.value)}
                placeholder="e.g. Remote / SF"
                className="h-7 text-xs bg-background/80"
              />
            </div>
            <div>
              <span className="text-[11px] text-muted-foreground block mb-0.5">
                {post.content_type === 'job' ? 'Salary' : 'Stipend'} (Optional)
              </span>
              <Input
                value={post.content_type === 'job' ? (meta.salary || '') : (meta.stipend || '')}
                onChange={(e) => handleMetaChange(post.content_type === 'job' ? 'salary' : 'stipend', e.target.value)}
                placeholder="e.g. $180k - $240k"
                className="h-7 text-xs bg-background/80"
              />
            </div>
            <div>
              <span className="text-[11px] text-muted-foreground block mb-0.5">Deadline</span>
              <Input
                value={meta.deadline || ''}
                onChange={(e) => handleMetaChange('deadline', e.target.value)}
                placeholder="e.g. Rolling / Oct 30"
                className="h-7 text-xs bg-background/80"
              />
            </div>
          </div>
        )}

        {post.content_type === 'hackathon' && (
          <div className="grid grid-cols-2 gap-2 p-3 bg-muted/20 border border-border/60 rounded-lg">
            <div>
              <span className="text-[11px] text-muted-foreground block mb-0.5">Prize Pool</span>
              <Input
                value={meta.prize || ''}
                onChange={(e) => handleMetaChange('prize', e.target.value)}
                placeholder="e.g. $150,000"
                className="h-7 text-xs bg-background/80"
              />
            </div>
            <div>
              <span className="text-[11px] text-muted-foreground block mb-0.5">Registration Deadline</span>
              <Input
                value={meta.deadline || ''}
                onChange={(e) => handleMetaChange('deadline', e.target.value)}
                placeholder="e.g. Oct 28, 2026"
                className="h-7 text-xs bg-background/80"
              />
            </div>
            <div>
              <span className="text-[11px] text-muted-foreground block mb-0.5">Team Size</span>
              <Input
                value={meta.team_size || ''}
                onChange={(e) => handleMetaChange('team_size', e.target.value)}
                placeholder="e.g. 1 - 4 Members"
                className="h-7 text-xs bg-background/80"
              />
            </div>
            <div>
              <span className="text-[11px] text-muted-foreground block mb-0.5">Format / Location</span>
              <Input
                value={meta.location || ''}
                onChange={(e) => handleMetaChange('location', e.target.value)}
                placeholder="e.g. Online / Global"
                className="h-7 text-xs bg-background/80"
              />
            </div>
          </div>
        )}

        {post.content_type === 'ai_tool' && (
          <div className="p-3 bg-muted/20 border border-border/60 rounded-lg">
            <span className="text-[11px] text-muted-foreground block mb-0.5">Pricing / Model</span>
            <Input
              value={meta.pricing || ''}
              onChange={(e) => handleMetaChange('pricing', e.target.value)}
              placeholder="e.g. Open Source (MIT) / Free Tier + $20/mo"
              className="h-7 text-xs bg-background/80"
            />
          </div>
        )}

        {/* 3. Key Takeaways List */}
        <div className="flex flex-col gap-2 pt-1">
          <span className="text-xs font-medium text-foreground flex items-center justify-between">
            <span>Key Takeaways (Bullets)</span>
            <span className="text-[10px] text-muted-foreground">{(post.takeaways || []).length} items</span>
          </span>

          <div className="flex flex-col gap-1.5">
            {(post.takeaways || []).map((t, idx) => (
              <div key={idx} className="flex items-center gap-1.5 bg-muted/30 border border-border/50 rounded-md p-1.5">
                <span className="text-cyan-400 font-bold text-xs pl-1">•</span>
                <span className="text-xs text-foreground flex-1 select-text leading-tight">{t}</span>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemoveTakeaway(idx)}
                  className="h-6 w-6 text-muted-foreground hover:text-red-400"
                >
                  <Trash2 className="w-3 h-3" />
                </Button>
              </div>
            ))}

            <div className="flex items-center gap-1.5 mt-1">
              <Input
                value={newTakeaway}
                onChange={(e) => setNewTakeaway(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleAddTakeaway()}
                placeholder="Add a bullet takeaway..."
                className="h-8 text-xs bg-background/80"
              />
              <Button size="sm" onClick={handleAddTakeaway} className="h-8 px-2 text-xs">
                <Plus className="w-3.5 h-3.5" />
              </Button>
            </div>
          </div>
        </div>

        {/* 4. Why It Matters */}
        <div>
          <span className="text-xs font-medium text-foreground mb-1 block">Why It Matters / Best For</span>
          <Textarea
            value={post.why_it_matters || ''}
            onChange={(e) => handleWhyItMattersChange(e.target.value)}
            placeholder="Contextual insight or target audience..."
            rows={2}
            className="text-xs bg-background/80"
          />
        </div>
      </div>

      {/* 5. Source & Verification Panel */}
      <div className="flex flex-col gap-3 p-3 bg-muted/20 border border-border/60 rounded-xl">
        <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
          <LinkIcon className="w-3.5 h-3.5 text-cyan-400" />
          Source & Trust Verification
        </Label>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <span className="text-[11px] text-muted-foreground block mb-0.5">Source Name</span>
            <Input
              value={post.source?.title || ''}
              onChange={(e) => handleSourceNameChange(e.target.value)}
              placeholder="e.g. Google Official Blog"
              className="h-8 text-xs bg-background/80"
            />
          </div>
          <div>
            <span className="text-[11px] text-muted-foreground block mb-0.5">Source URL</span>
            <Input
              value={post.source?.url || ''}
              onChange={(e) => handleSourceUrlChange(e.target.value)}
              placeholder="https://..."
              className="h-8 text-xs bg-background/80"
            />
          </div>
        </div>

        <div>
          <span className="text-[11px] text-muted-foreground block mb-1">Verification Status</span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant={post.verification?.status === 'verified' ? 'default' : 'outline'}
              size="sm"
              onClick={() => handleVerificationChange('verified')}
              className={`h-7 text-xs flex-1 ${
                post.verification?.status === 'verified' ? 'bg-emerald-600 hover:bg-emerald-500 text-white' : ''
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
              className={`h-7 text-xs flex-1 ${
                post.verification?.status === 'needs_verification' ? 'bg-amber-600 hover:bg-amber-500 text-white' : ''
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5 mr-1" />
              Needs Verification
            </Button>
          </div>
        </div>
      </div>

      {/* 6. Media Attachment */}
      <div className="flex flex-col gap-2 p-3 bg-muted/20 border border-border/60 rounded-xl">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
            <ImageIcon className="w-3.5 h-3.5 text-cyan-400" />
            Media Attachment
          </Label>
          {currentMedia && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRemoveImage}
              className="h-6 text-[11px] text-red-400 hover:text-red-300 px-1.5"
            >
              Remove
            </Button>
          )}
        </div>

        {currentMedia ? (
          <div className="relative rounded-lg overflow-hidden border border-border/60 max-h-40 bg-black/40 flex items-center justify-center">
            <img
              src={currentMedia.url_or_path}
              alt="Post media"
              className="w-full h-36 object-cover"
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
              className="h-8 text-xs bg-background/80"
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={() => handleAttachImage(imageUrlInput)} className="h-7 text-xs flex-1">
                Attach Image
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsAddingImage(false)}
                className="h-7 text-xs px-2"
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
            className="h-8 text-xs border-dashed border-border/80 hover:bg-muted/40"
          >
            <Plus className="w-3.5 h-3.5 mr-1" />
            Add Image (URL or Upload)
          </Button>
        )}
      </div>

      {/* 7. Inline Buttons Builder */}
      <div className="flex flex-col gap-2 p-3 bg-muted/20 border border-border/60 rounded-xl">
        <div className="flex items-center justify-between">
          <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
            <ExternalLink className="w-3.5 h-3.5 text-cyan-400" />
            Inline Keyboard Buttons
          </Label>
          <span className="text-[10px] text-muted-foreground">{(post.buttons || []).length} buttons</span>
        </div>

        <div className="flex flex-col gap-1.5">
          {(post.buttons || []).map((btn, idx) => (
            <div
              key={idx}
              className="flex items-center justify-between bg-card/60 border border-border/50 rounded-lg p-2 gap-2"
            >
              <div className="flex-1 min-w-0">
                <span className="text-xs font-medium text-foreground block truncate">{btn.text}</span>
                <span className="text-[10px] text-cyan-400 block truncate">{btn.url}</span>
              </div>
              <div className="flex items-center gap-0.5">
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={idx === 0}
                  onClick={() => handleMoveButton(idx, 'up')}
                  className="h-6 w-6 text-muted-foreground disabled:opacity-20"
                >
                  <ChevronUp className="w-3.5 h-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={idx === (post.buttons || []).length - 1}
                  onClick={() => handleMoveButton(idx, 'down')}
                  className="h-6 w-6 text-muted-foreground disabled:opacity-20"
                >
                  <ChevronDown className="w-3.5 h-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => handleRemoveButton(idx)}
                  className="h-6 w-6 text-muted-foreground hover:text-red-400"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </div>
            </div>
          ))}

          {isAddingButton ? (
            <div className="flex flex-col gap-2 p-2 bg-background/60 border border-border/50 rounded-lg mt-1">
              <Input
                value={newButtonText}
                onChange={(e) => setNewButtonText(e.target.value)}
                placeholder="Button Label (e.g. 📚 Read Source)"
                className="h-7 text-xs"
              />
              <Input
                value={newButtonUrl}
                onChange={(e) => setNewButtonUrl(e.target.value)}
                placeholder="Target URL (https://...)"
                className="h-7 text-xs"
              />
              <div className="flex gap-2">
                <Button size="sm" onClick={handleAddButton} className="h-7 text-xs flex-1">
                  Add Button
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsAddingButton(false)}
                  className="h-7 text-xs px-2"
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
              className="h-8 text-xs border-dashed border-border/80 hover:bg-muted/40 mt-1"
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
