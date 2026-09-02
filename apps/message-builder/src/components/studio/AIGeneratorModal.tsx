import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Sparkles,
  Link as LinkIcon,
  FileText,
  AlertTriangle,
  CheckCircle2,
  Image as ImageIcon,
  Loader2,
  RefreshCw,
  SlidersHorizontal,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { ContentType, PostSchema } from '@/types/postSchema';
import { GenerateResponse, HookOption, QualityScores } from '@/types/generator';
import { generatePostFromInput } from '@/lib/api';
import { toast } from 'sonner';

interface AIGeneratorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPostGenerated: (post: PostSchema, draftId: number, quality?: QualityScores, hooks?: HookOption[]) => void;
}

const GENERATION_STAGES = [
  'Fetching source & metadata...',
  'Extracting verified facts...',
  'Writing structured draft & hooks...',
  'Evaluating post health & quality...',
];

export const AIGeneratorModal: React.FC<AIGeneratorModalProps> = ({
  isOpen,
  onClose,
  onPostGenerated,
}) => {
  const [inputVal, setInputVal] = useState('');
  const [category, setCategory] = useState<ContentType | 'auto'>('auto');
  const [notes, setNotes] = useState('');
  const [showNotes, setShowNotes] = useState(false);

  // Generation state
  const [isGenerating, setIsGenerating] = useState(false);
  const [stageIndex, setStageIndex] = useState(0);
  const [genResult, setGenResult] = useState<GenerateResponse | null>(null);
  const [selectedHookIndex, setSelectedHookIndex] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isUrlError, setIsUrlError] = useState(false);

  // Reset when opened
  useEffect(() => {
    if (isOpen) {
      setGenResult(null);
      setErrorMessage(null);
      setIsUrlError(false);
      setStageIndex(0);
    }
  }, [isOpen]);

  // Stage simulation while async call runs
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isGenerating) {
      timer = setInterval(() => {
        setStageIndex((prev) => (prev < GENERATION_STAGES.length - 1 ? prev + 1 : prev));
      }, 700);
    }
    return () => clearInterval(timer);
  }, [isGenerating]);

  const handleGenerate = async () => {
    const trimmed = inputVal.trim();
    if (!trimmed) {
      setErrorMessage('Please enter a URL, article text, or rough idea.');
      return;
    }

    setIsGenerating(true);
    setErrorMessage(null);
    setIsUrlError(false);
    setGenResult(null);
    setStageIndex(0);

    try {
      const res = await generatePostFromInput({
        input: trimmed,
        category: category === 'auto' ? undefined : category,
        notes: notes.trim() || undefined,
      });

      if (res.success && res.post && res.draft_id) {
        setGenResult(res);
        setSelectedHookIndex(0);
        toast.success('✨ Draft generated successfully!');
      } else {
        setErrorMessage(res.error || 'Failed to generate post. Please try again.');
        setIsUrlError(Boolean(res.url_error));
      }
    } catch (e: any) {
      setErrorMessage(e.message || 'Network error while generating post.');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleHookChange = (index: number) => {
    if (!genResult || !genResult.post || !genResult.generation?.hooks) return;
    setSelectedHookIndex(index);
    const chosenHook = genResult.generation.hooks[index]?.text;
    if (chosenHook) {
      setGenResult({
        ...genResult,
        post: {
          ...genResult.post,
          title: chosenHook,
        },
      });
    }
  };

  const handleOpenInEditor = () => {
    if (!genResult || !genResult.post || !genResult.draft_id) return;
    onPostGenerated(
      genResult.post,
      genResult.draft_id,
      genResult.quality,
      genResult.generation?.hooks
    );
    onClose();
  };

  const handlePasteTextFallback = () => {
    setInputVal('');
    setIsUrlError(false);
    setErrorMessage(null);
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-xl bg-slate-950/95 border-slate-700/80 backdrop-blur-2xl text-slate-100 shadow-2xl z-50 overflow-hidden">
        <DialogHeader className="space-y-1.5">
          <div className="flex items-center gap-2 text-cyan-400">
            <div className="w-8 h-8 rounded-lg bg-cyan-950/60 border border-cyan-800/80 flex items-center justify-center shadow-inner">
              <Sparkles className="w-4 h-4" />
            </div>
            <DialogTitle className="text-base font-semibold text-white tracking-tight">
              AI Content Generator
            </DialogTitle>
          </div>
          <DialogDescription className="text-xs text-slate-400">
            Paste a URL, raw article, or rough idea. The AI extracts facts, structures takeaways, and prepares a Telegram draft.
          </DialogDescription>
        </DialogHeader>

        {/* ─── STAGE 1: INPUT FORM ────────────────────────────────────────── */}
        {!genResult && (
          <div className="space-y-4 pt-1">
            {errorMessage && (
              <div className="p-3 rounded-lg bg-red-950/60 border border-red-800/70 text-red-300 text-xs flex flex-col gap-2 animate-in fade-in duration-150">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-red-400" />
                  <span>{errorMessage}</span>
                </div>
                {isUrlError && (
                  <div className="flex gap-2 pt-1">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleGenerate}
                      className="h-7 text-[11px] border-red-800 bg-red-950/80 text-red-200"
                    >
                      Try Again
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={handlePasteTextFallback}
                      className="h-7 text-[11px] text-red-300 hover:text-white"
                    >
                      Paste Text Instead
                    </Button>
                  </div>
                )}
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="ai-input" className="text-xs font-medium text-slate-300 flex items-center justify-between">
                <span>Input (URL, Article Text, or Topic Idea)</span>
                <span className="text-[11px] text-slate-500">Auto-detects format</span>
              </Label>
              <Textarea
                id="ai-input"
                placeholder="https://blog.google/gemini-pro...\n\nor: Google announced next-gen multimodal reasoning model...\n\nor: Make a post explaining why AI agents are changing coding."
                value={inputVal}
                onChange={(e) => {
                  setInputVal(e.target.value);
                  setErrorMessage(null);
                }}
                rows={5}
                disabled={isGenerating}
                className="bg-slate-900/80 border-slate-700/80 text-white placeholder:text-slate-500 text-xs focus-visible:ring-cyan-500 resize-none font-sans leading-relaxed"
                autoFocus
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="ai-category" className="text-xs font-medium text-slate-300">
                  Target Category
                </Label>
                <Select
                  value={category}
                  onValueChange={(val) => setCategory(val as any)}
                  disabled={isGenerating}
                >
                  <SelectTrigger id="ai-category" className="h-8 text-xs bg-slate-900/80 border-slate-700/80 text-slate-200">
                    <SelectValue placeholder="Auto Detect" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700 text-slate-200 text-xs z-50">
                    <SelectItem value="auto">✨ Auto Detect Category</SelectItem>
                    <SelectItem value="ai_news">🚨 AI News</SelectItem>
                    <SelectItem value="job">💼 Job Opportunity</SelectItem>
                    <SelectItem value="internship">🎓 Internship Alert</SelectItem>
                    <SelectItem value="hackathon">🏆 Hackathon</SelectItem>
                    <SelectItem value="ai_tool">🛠 AI Tool & SaaS</SelectItem>
                    <SelectItem value="career">🚀 Career Strategy</SelectItem>
                    <SelectItem value="resource">📚 Developer Resource</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex flex-col justify-end">
                <button
                  type="button"
                  onClick={() => setShowNotes(!showNotes)}
                  className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 h-8 px-1"
                >
                  {showNotes ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                  {showNotes ? 'Hide Focus Notes' : '+ Add Focus Notes'}
                </button>
              </div>
            </div>

            {showNotes && (
              <div className="space-y-1 animate-in fade-in duration-150">
                <Label htmlFor="ai-notes" className="text-[11px] text-slate-400">
                  Additional Notes or Instructions (Optional)
                </Label>
                <Input
                  id="ai-notes"
                  placeholder="e.g. Focus on pricing, emphasize benchmark scores, omit background..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  disabled={isGenerating}
                  className="h-8 text-xs bg-slate-900/80 border-slate-700/80 text-white placeholder:text-slate-500"
                />
              </div>
            )}

            {/* Stage Progress Feedback */}
            {isGenerating && (
              <div className="p-3.5 rounded-xl bg-cyan-950/30 border border-cyan-800/40 flex flex-col gap-2 animate-in fade-in duration-150">
                <div className="flex items-center justify-between text-xs text-cyan-300">
                  <span className="flex items-center gap-2 font-medium">
                    <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                    {GENERATION_STAGES[stageIndex]}
                  </span>
                  <span className="text-[10px] text-cyan-400/80 font-mono">
                    Step {stageIndex + 1} of 4
                  </span>
                </div>
                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                  <div
                    className="bg-cyan-400 h-full transition-all duration-300"
                    style={{ width: `${((stageIndex + 1) / 4) * 100}%` }}
                  />
                </div>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                disabled={isGenerating}
                className="text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleGenerate}
                disabled={isGenerating || !inputVal.trim()}
                className="text-xs font-medium bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-md shadow-cyan-950"
              >
                {isGenerating ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                    Generate Post
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {/* ─── STAGE 2: GENERATION RESULTS & QUALITY SCREEN ──────────────── */}
        {genResult && genResult.post && (
          <div className="space-y-4 pt-1 animate-in fade-in duration-200">
            {/* Top Badge Card: Quality & Status */}
            <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-700 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-9 h-9 rounded-lg bg-emerald-950/80 border border-emerald-700/80 flex items-center justify-center text-emerald-400">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-white">Draft Generated</h4>
                  <p className="text-[11px] text-slate-400">
                    Category: <span className="text-cyan-300 font-medium capitalize">{genResult.post.content_type.replace('_', ' ')}</span>
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {genResult.generation?.category_review_needed && (
                  <span className="text-[10px] font-medium text-amber-300 bg-amber-950/80 border border-amber-800/80 px-2 py-0.5 rounded flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" /> Category Needs Review
                  </span>
                )}
                {genResult.quality && (
                  <span className="text-xs font-semibold text-emerald-300 bg-emerald-950/80 border border-emerald-800/80 px-2.5 py-1 rounded-lg">
                    Health: {genResult.quality.overall}/100
                  </span>
                )}
              </div>
            </div>

            {/* Hook Selector: 3 Options */}
            {genResult.generation?.hooks && genResult.generation.hooks.length > 0 && (
              <div className="space-y-1.5">
                <Label className="text-xs font-medium text-slate-300 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <SlidersHorizontal className="w-3.5 h-3.5 text-cyan-400" />
                    Headline Hook Options (Score: {genResult.generation.hooks[selectedHookIndex]?.score}/100)
                  </span>
                  <span className="text-[10px] text-slate-400">Click to switch hook</span>
                </Label>
                <div className="flex flex-col gap-1.5">
                  {genResult.generation.hooks.map((h, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleHookChange(idx)}
                      className={`text-left text-xs p-2 rounded-lg border transition-all flex items-center justify-between ${
                        selectedHookIndex === idx
                          ? 'bg-cyan-950/40 border-cyan-500 text-white font-medium shadow-sm'
                          : 'bg-slate-900/60 border-slate-800 text-slate-300 hover:border-slate-700 hover:bg-slate-900'
                      }`}
                    >
                      <span className="truncate pr-2">{h.text}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 font-mono text-slate-400 shrink-0">
                        {h.score} pts
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Visual Suggestion Banner */}
            {genResult.visual && genResult.visual.needs_visual && (
              <div className="p-2.5 rounded-lg bg-blue-950/30 border border-blue-800/50 flex items-start gap-2.5">
                <ImageIcon className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
                <div className="text-[11px] text-slate-300 leading-snug">
                  <span className="font-medium text-blue-300">Visual Suggested:</span>{' '}
                  <span className="text-slate-400">{genResult.visual.concept}</span>
                </div>
              </div>
            )}

            {/* Preview Snippet */}
            <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 max-h-36 overflow-y-auto font-sans text-xs text-slate-300 whitespace-pre-wrap leading-relaxed">
              <b className="text-white block mb-1">{genResult.post.title}</b>
              {genResult.post.body}
            </div>

            {/* Modal Actions */}
            <div className="flex justify-between items-center pt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setGenResult(null)}
                className="text-xs text-slate-400 hover:text-white"
              >
                <RefreshCw className="w-3.5 h-3.5 mr-1" />
                Regenerate / Edit Input
              </Button>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={onClose}
                  className="text-xs border-slate-700 text-slate-300 hover:bg-slate-800"
                >
                  Close
                </Button>
                <Button
                  size="sm"
                  onClick={handleOpenInEditor}
                  className="text-xs font-medium bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-md shadow-cyan-950"
                >
                  Open in Editor →
                </Button>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
