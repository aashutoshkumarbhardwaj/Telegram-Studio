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
    <header className="h-14 border-b border-border/60 bg-card/70 backdrop-blur-md px-4 flex items-center justify-between select-none z-30">
      {/* Left: Brand & Draft Selector */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-sm font-bold text-sm">
            H
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-foreground flex items-center gap-1.5">
              Heyaaashu Studio
              <span className="text-[10px] font-medium text-cyan-400 bg-cyan-950/60 border border-cyan-800/60 rounded px-1.5 py-0.2">
                Content OS
              </span>
            </h1>
          </div>
        </div>

        <div className="h-4 w-px bg-border/60 mx-1 hidden sm:block" />

        <div className="flex items-center gap-1.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={onOpenDrafts}
            className="text-xs font-medium text-muted-foreground hover:text-foreground h-8 px-2.5"
          >
            <FolderOpen className="w-3.5 h-3.5 mr-1.5" />
            Drafts
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={onNewDraft}
            className="text-xs font-medium text-muted-foreground hover:text-foreground h-8 px-2.5"
          >
            <PlusCircle className="w-3.5 h-3.5 mr-1.5 text-cyan-400" />
            New Post
          </Button>
        </div>
      </div>

      {/* Center: Save State & History */}
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
              <span className="w-2 h-2 rounded-full bg-amber-400 inline-block" /> Unsaved changes
            </span>
          )}
        </div>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2">
        {onOpenAuth && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onOpenAuth}
            className="h-8 text-xs font-medium text-slate-400 hover:text-slate-200 border border-slate-700/60 hover:bg-slate-800/60"
            title="Studio Authentication Settings"
          >
            <Key className="w-3.5 h-3.5 mr-1 text-cyan-400" />
            <span className="hidden sm:inline">Auth</span>
          </Button>
        )}

        <Button
          variant="outline"
          size="sm"
          onClick={onSave}
          className="h-8 text-xs font-medium border-border/80 hover:bg-muted/80"
        >
          <Save className="w-3.5 h-3.5 mr-1.5 text-muted-foreground" />
          Save Draft
        </Button>

        <Button
          size="sm"
          onClick={onPublishClick}
          disabled={isPublishing}
          className="h-8 text-xs font-medium bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-sm"
        >
          <Send className="w-3.5 h-3.5 mr-1.5" />
          {isPublishing ? 'Publishing...' : 'Publish'}
        </Button>
      </div>
    </header>
  );
};
