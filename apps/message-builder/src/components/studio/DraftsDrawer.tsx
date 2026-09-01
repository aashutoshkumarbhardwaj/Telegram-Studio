import React, { useState } from 'react';
import { DraftListItem } from '@/types/postSchema';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Search, Trash2, Copy, ArrowRight, FileText, Plus } from 'lucide-react';

interface DraftsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  drafts: DraftListItem[];
  currentDraftId?: number;
  onSelectDraft: (id: number) => void;
  onDuplicateDraft: (id: number) => void;
  onDeleteDraft: (id: number) => void;
  onNewDraft: () => void;
}

export const DraftsDrawer: React.FC<DraftsDrawerProps> = ({
  isOpen,
  onClose,
  drafts,
  currentDraftId,
  onSelectDraft,
  onDuplicateDraft,
  onDeleteDraft,
  onNewDraft,
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = drafts.filter((d) =>
    (d.title || 'Untitled').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (d.content_type || '').toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl max-h-[85vh] flex flex-col p-6 bg-slate-950 border-slate-800 text-slate-100">
        <DialogHeader className="flex flex-row items-center justify-between pb-2 border-b border-slate-800">
          <div>
            <DialogTitle className="text-base font-semibold text-white">Saved Drafts</DialogTitle>
            <DialogDescription className="text-xs text-slate-400">
              Manage and resume canonical PostSchema publication drafts.
            </DialogDescription>
          </div>
          <Button
            size="sm"
            onClick={() => {
              onNewDraft();
              onClose();
            }}
            className="h-8 text-xs bg-cyan-600 hover:bg-cyan-500 text-white"
          >
            <Plus className="w-3.5 h-3.5 mr-1" /> New Post
          </Button>
        </DialogHeader>

        {/* Search */}
        <div className="relative my-3">
          <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
          <Input
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by title or category..."
            className="pl-8 h-8 text-xs bg-slate-900 border-slate-800 text-slate-200"
          />
        </div>

        {/* Drafts List */}
        <div className="flex-1 overflow-y-auto flex flex-col gap-2 pr-1 max-h-96">
          {filtered.length === 0 ? (
            <div className="text-center py-12 text-xs text-slate-500">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-30" />
              No drafts found. Click &quot;New Post&quot; to start composing.
            </div>
          ) : (
            filtered.map((d) => {
              const isCurrent = d.post_id === currentDraftId;
              return (
                <div
                  key={d.post_id}
                  className={`flex items-center justify-between p-3 rounded-xl border transition-colors ${
                    isCurrent
                      ? 'bg-cyan-950/40 border-cyan-700/80 shadow-sm'
                      : 'bg-slate-900/60 border-slate-800 hover:bg-slate-900'
                  }`}
                >
                  <div
                    className="flex-1 min-w-0 cursor-pointer"
                    onClick={() => {
                      onSelectDraft(d.post_id);
                      onClose();
                    }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Badge
                        variant="outline"
                        className="text-[10px] px-1.5 py-0 uppercase tracking-wider bg-slate-800/80 border-slate-700 text-cyan-300 font-mono"
                      >
                        {d.content_type}
                      </Badge>
                      <span className="text-[11px] text-slate-400">
                        {new Date(d.created_at).toLocaleDateString()}
                      </span>
                      {d.status === 'posted' && (
                        <span className="text-[10px] text-emerald-400 bg-emerald-950/60 border border-emerald-800/50 px-1 rounded">
                          Published
                        </span>
                      )}
                    </div>
                    <h4 className="text-xs font-medium text-slate-100 truncate">
                      {d.title || 'Untitled Draft'}
                    </h4>
                  </div>

                  <div className="flex items-center gap-1 shrink-0 ml-3">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onDuplicateDraft(d.post_id)}
                      className="h-7 w-7 text-slate-400 hover:text-slate-100"
                      title="Duplicate Draft"
                    >
                      <Copy className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onDeleteDraft(d.post_id)}
                      className="h-7 w-7 text-slate-400 hover:text-red-400"
                      title="Delete Draft"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => {
                        onSelectDraft(d.post_id);
                        onClose();
                      }}
                      className="h-7 px-2.5 text-xs bg-slate-800 hover:bg-cyan-600 text-slate-200 hover:text-white"
                    >
                      Open <ArrowRight className="w-3 h-3 ml-1" />
                    </Button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
