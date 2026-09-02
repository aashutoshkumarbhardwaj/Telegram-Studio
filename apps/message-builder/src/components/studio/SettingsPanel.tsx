import React, { useState } from 'react';
import { PostSchema } from '@/types/postSchema';
import { QualityScores, HookOption } from '@/types/generator';
import { TemplateStyle, formatPostHtml } from '@/lib/templates';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import {
  AlertTriangle,
  CheckCircle2,
  Copy,
  Check,
  Code2,
  FileText,
  ShieldAlert,
  Sliders,
  Activity,
  Sparkles,
} from 'lucide-react';
import { toast } from 'sonner';

interface SettingsPanelProps {
  post: PostSchema;
  templateStyle: TemplateStyle;
  quality?: QualityScores;
  hooks?: HookOption[];
  onSelectHook?: (hookText: string) => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  post,
  templateStyle,
  quality,
  hooks,
  onSelectHook,
}) => {
  const [copiedJson, setCopiedJson] = useState(false);
  const [copiedHtml, setCopiedHtml] = useState(false);

  const formattedHtml = formatPostHtml(post, templateStyle);
  const charCount = formattedHtml.length;
  const hasMedia = Boolean(post.media && post.media.length > 0);
  const maxChars = hasMedia ? 1024 : 4096;
  const progressPercent = Math.min(100, Math.round((charCount / maxChars) * 100));

  // Warnings
  const warnings: string[] = [];
  if (post.title.length > 120) {
    warnings.push('Headline is long (>120 chars). Consider keeping it punchy.');
  }
  if (charCount > maxChars - 100) {
    warnings.push(`Post is approaching Telegram limit (${charCount}/${maxChars} chars).`);
  }
  if (!post.source?.url) {
    warnings.push('No primary source URL attached.');
  }
  if (post.verification?.status === 'needs_verification') {
    warnings.push('This story is marked as "Needs Verification". Please verify before publishing.');
  }

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(post, null, 2));
    setCopiedJson(true);
    toast.success('PostSchema JSON copied to clipboard!');
    setTimeout(() => setCopiedJson(false), 2000);
  };

  const handleCopyHtml = () => {
    navigator.clipboard.writeText(formattedHtml);
    setCopiedHtml(true);
    toast.success('Telegram HTML copied to clipboard!');
    setTimeout(() => setCopiedHtml(false), 2000);
  };

  return (
    <div className="flex flex-col gap-6 p-4 pb-12 overflow-y-auto max-w-full">
      {/* 1. Quality Analyzer Score Card */}
      {quality && (
        <div className="flex flex-col gap-3 p-3 bg-slate-900/60 border border-slate-800 rounded-xl">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              Post Health
            </Label>
            <span
              className={`text-[11px] font-semibold px-2 py-0.5 rounded ${
                quality.overall >= 80
                  ? 'bg-emerald-950/80 border border-emerald-800 text-emerald-300'
                  : 'bg-amber-950/80 border border-amber-800 text-amber-300'
              }`}
            >
              {quality.overall}/100 {quality.status === 'ready' ? '✅ Ready' : '⚠️ Review'}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-xs pt-1">
            <div className="flex justify-between p-1.5 rounded bg-slate-950/50 border border-slate-800/80">
              <span className="text-slate-400">Hook</span>
              <span className="font-mono text-cyan-300">{quality.hook}</span>
            </div>
            <div className="flex justify-between p-1.5 rounded bg-slate-950/50 border border-slate-800/80">
              <span className="text-slate-400">Clarity</span>
              <span className="font-mono text-cyan-300">{quality.clarity}</span>
            </div>
            <div className="flex justify-between p-1.5 rounded bg-slate-950/50 border border-slate-800/80">
              <span className="text-slate-400">Value</span>
              <span className="font-mono text-cyan-300">{quality.value}</span>
            </div>
            <div className="flex justify-between p-1.5 rounded bg-slate-950/50 border border-slate-800/80">
              <span className="text-slate-400">Source</span>
              <span className="font-mono text-cyan-300">{quality.source}</span>
            </div>
          </div>
        </div>
      )}

      {/* 2. Alternative Hooks Switcher */}
      {hooks && hooks.length > 1 && onSelectHook && (
        <div className="flex flex-col gap-2 p-3 bg-muted/20 border border-border/60 rounded-xl">
          <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            Headline Hook Switcher
          </Label>
          <div className="flex flex-col gap-1.5 pt-1">
            {hooks.map((h, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  onSelectHook(h.text);
                  toast.success(`Switched to hook #${idx + 1}`);
                }}
                className={`text-left text-xs p-2 rounded-lg border transition-all ${
                  post.title === h.text
                    ? 'bg-cyan-950/40 border-cyan-500 text-white font-medium'
                    : 'bg-card/40 border-border/40 text-muted-foreground hover:text-foreground hover:bg-card/80'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] uppercase font-mono text-cyan-400">{h.style}</span>
                  <span className="text-[10px] font-mono text-slate-500">{h.score} pts</span>
                </div>
                <p className="mt-0.5 line-clamp-2">{h.text}</p>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 3. Quality & Limit Analyzer */}
      <div className="flex flex-col gap-3 p-3 bg-muted/20 border border-border/60 rounded-xl">
        <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
          <Sliders className="w-3.5 h-3.5 text-cyan-400" />
          Telegram Limits & Health
        </Label>

        <div className="flex flex-col gap-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Character Count</span>
            <span className="font-mono font-medium text-foreground">
              {charCount} / {maxChars} {hasMedia ? '(Caption)' : '(Message)'}
            </span>
          </div>
          <Progress
            value={progressPercent}
            className={`h-1.5 ${
              progressPercent > 90 ? 'bg-red-500' : progressPercent > 75 ? 'bg-amber-500' : 'bg-cyan-500'
            }`}
          />
        </div>

        {/* Quality Alerts */}
        {warnings.length > 0 ? (
          <div className="flex flex-col gap-1.5 pt-1">
            {warnings.map((w, idx) => (
              <div
                key={idx}
                className="flex items-start gap-1.5 p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] leading-tight"
              >
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-amber-400" />
                <span>{w}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex items-center gap-1.5 p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[11px]">
            <CheckCircle2 className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
            <span>Ready for publication. Zero constraint warnings.</span>
          </div>
        )}
      </div>

      {/* 4. Verification Info */}
      <div className="flex flex-col gap-2 p-3 bg-muted/20 border border-border/60 rounded-xl">
        <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
          <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />
          Editorial Verification
        </Label>

        <div className="flex items-center justify-between text-xs pt-1">
          <span className="text-muted-foreground">Status</span>
          <span
            className={`font-semibold px-2 py-0.5 rounded text-[11px] ${
              post.verification?.status === 'verified'
                ? 'bg-emerald-950/70 border border-emerald-800 text-emerald-300'
                : 'bg-amber-950/70 border border-amber-800 text-amber-300'
            }`}
          >
            {post.verification?.status === 'verified' ? '✅ Verified' : '⚠️ Needs Verification'}
          </span>
        </div>

        <div className="text-[11px] text-muted-foreground pt-1">
          {post.source?.title ? (
            <span>
              Primary Source: <b className="text-foreground">{post.source.title}</b>
            </span>
          ) : (
            <span>No primary source named.</span>
          )}
        </div>
      </div>

      {/* 5. Export & Schema */}
      <div className="flex flex-col gap-2 p-3 bg-muted/20 border border-border/60 rounded-xl">
        <Label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-1.5">
          <Code2 className="w-3.5 h-3.5 text-cyan-400" />
          Canonical PostSchema Export
        </Label>

        <div className="grid grid-cols-2 gap-2 pt-1">
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyJson}
            className="h-8 text-xs font-medium border-border/80"
          >
            {copiedJson ? <Check className="w-3.5 h-3.5 mr-1 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 mr-1" />}
            Copy JSON
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleCopyHtml}
            className="h-8 text-xs font-medium border-border/80"
          >
            {copiedHtml ? <Check className="w-3.5 h-3.5 mr-1 text-emerald-400" /> : <FileText className="w-3.5 h-3.5 mr-1" />}
            Copy HTML
          </Button>
        </div>
      </div>
    </div>
  );
};
