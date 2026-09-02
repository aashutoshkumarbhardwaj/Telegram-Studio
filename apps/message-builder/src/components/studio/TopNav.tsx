import React from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  FolderOpen,
  Save,
  Send,
  Undo2,
  Redo2,
  PlusCircle,
  Eye,
  CheckCircle2,
  Clock,
  Sparkles,
  Key,
} from 'lucide-react';

interface TopNavProps {
  onOpenDrafts: () => void;
  onNewDraft: () => void;
  onOpenAIGenerator?: () => void;
  onSave: () => void;
  onPublishClick: () => void;
  onOpenAuth?: () => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  saveStatus: 'saved' | 'saving' | 'unsaved';
  isPublishing?: boolean;
}

export const TopNav: React.FC<TopNavProps> = ({
  onOpenDrafts,
  onNewDraft,
  onOpenAIGenerator,
  onSave,
  onPublishClick,
  onOpenAuth,
  onUndo,
  onRedo,
  canUndo,
  canRedo,
  saveStatus,
  isPublishing = false,
}) => {
  return (
    <header className="h-13 sm:h-14 border-b border-border/60 bg-card/75 backdrop-blur-md px-2.5 sm:px-4 flex items-center justify-between select-none z-30 shrink-0">
      {/* Left: Brand & Mobile/Desktop Navigation */}
      <div className="flex items-center gap-1.5 sm:gap-3 min-w-0">
        <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
          <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-sm font-bold text-xs sm:text-sm">
            H
          </div>
          <div className="flex items-center gap-1.5">
            <h1 className="text-xs sm:text-sm font-semibold tracking-tight text-foreground">
              Heyaaashu
              <span className="hidden sm:inline text-foreground/80 font-normal ml-1">Studio</span>
            </h1>
            <span className="hidden lg:inline text-[10px] font-medium text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 rounded px-1.5 py-0.2">
              Content OS
            </span>
          </div>
        </div>

        {/* Mobile Save Indicator */}
        <div className="md:hidden flex items-center pl-1 text-[11px]">
          {saveStatus === 'saved' && (
            <span className="w-2 h-2 rounded-full bg-emerald-400" title="All changes saved" />
          )}
          {saveStatus === 'saving' && (
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" title="Saving..." />
          )}
          {saveStatus === 'unsaved' && (
            <span className="w-2 h-2 rounded-full bg-amber-400" title="Unsaved changes" />
          )}
        </div>

        <div className="h-4 w-px bg-border/60 mx-1 hidden md:block" />

        {/* Desktop Quick Links */}
        <div className="hidden sm:flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={onOpenDrafts}
            className="text-xs font-medium text-muted-foreground hover:text-foreground h-8 px-2"
          >
            <FolderOpen className="w-3.5 h-3.5 mr-1" />
            Drafts
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={onNewDraft}
            className="text-xs font-medium text-muted-foreground hover:text-foreground h-8 px-2"
          >
            <PlusCircle className="w-3.5 h-3.5 mr-1 text-cyan-400" />
            New
          </Button>

          {onOpenAIGenerator && (
            <Button
              size="sm"
              onClick={onOpenAIGenerator}
              className="text-xs font-medium bg-gradient-to-r from-cyan-500/20 to-blue-600/20 border border-cyan-500/40 text-cyan-300 hover:text-white hover:bg-cyan-500/30 h-8 px-2.5 shadow-sm"
            >
              <Sparkles className="w-3.5 h-3.5 mr-1 text-cyan-400" />
              AI Generate
            </Button>
          )}
        </div>
      </div>

      {/* Center: Desktop Undo / Redo & Save State */}
      <div className="hidden md:flex items-center gap-2">
        <div className="flex items-center gap-1 bg-muted/40 border border-border/50 rounded-lg p-0.5">
          <Button
            variant="ghost"
            size="icon"
            onClick={onUndo}
            disabled={!canUndo}
            className="h-7 w-7 text-muted-foreground hover:text-foreground disabled:opacity-30"
            title="Undo (Ctrl+Z)"
          >
            <Undo2 className="w-3.5 h-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={onRedo}
            disabled={!canRedo}
            className="h-7 w-7 text-muted-foreground hover:text-foreground disabled:opacity-30"
            title="Redo (Ctrl+Shift+Z)"
          >
            <Redo2 className="w-3.5 h-3.5" />
          </Button>
        </div>

        <div className="flex items-center gap-1.5 text-xs text-muted-foreground px-2">
          {saveStatus === 'saved' && (
            <span className="flex items-center gap-1 text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" /> Saved
            </span>
          )}
          {saveStatus === 'saving' && (
            <span className="flex items-center gap-1 text-cyan-400 animate-pulse">
              <Clock className="w-3.5 h-3.5" /> Saving...
            </span>
          )}
          {saveStatus === 'unsaved' && (
            <span className="flex items-center gap-1 text-amber-400">
              <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" /> Unsaved
            </span>
          )}
        </div>
      </div>

      {/* Right: Actions (Adaptive for Mobile & Desktop) */}
      <div className="flex items-center gap-1 sm:gap-2 shrink-0">
        {/* Mobile AI Generate quick button */}
        {onOpenAIGenerator && (
          <Button
            size="sm"
            onClick={onOpenAIGenerator}
            className="sm:hidden h-8 px-2 text-xs font-medium bg-gradient-to-r from-cyan-500/20 to-blue-600/20 border border-cyan-500/40 text-cyan-300"
            title="AI Content Generator"
          >
            <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
            <span className="ml-1 text-[11px]">AI</span>
          </Button>
        )}

        {/* Mobile Drafts drawer quick button */}
        <Button
          variant="ghost"
          size="sm"
          onClick={onOpenDrafts}
          className="sm:hidden h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
          title="Open Drafts Drawer"
        >
          <FolderOpen className="w-4 h-4" />
        </Button>

        {/* Auth button */}
        {onOpenAuth && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onOpenAuth}
            className="h-8 px-2 sm:px-2.5 text-xs font-medium text-slate-400 hover:text-slate-200 border border-slate-700/60 hover:bg-slate-800/60"
            title="Studio Authentication Settings"
          >
            <Key className="w-3.5 h-3.5 text-cyan-400" />
            <span className="hidden sm:inline ml-1">Auth</span>
          </Button>
        )}

        {/* Desktop Save button */}
        <Button
          variant="outline"
          size="sm"
          onClick={onSave}
          className="hidden sm:flex h-8 text-xs font-medium border-border/80 hover:bg-muted/80"
        >
          <Save className="w-3.5 h-3.5 mr-1.5 text-muted-foreground" />
          Save
        </Button>

        {/* Primary Publish Button (Always visible on mobile & desktop) */}
        <Button
          size="sm"
          onClick={onPublishClick}
          disabled={isPublishing}
          className="h-8 px-2.5 sm:px-3 text-xs font-semibold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-md shadow-cyan-950"
        >
          <Send className="w-3.5 h-3.5 mr-1" />
          <span>{isPublishing ? 'Publishing...' : 'Publish'}</span>
        </Button>
      </div>
    </header>
  );
};
