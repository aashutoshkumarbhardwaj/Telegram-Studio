import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { DraftListItem, PostSchema } from '@/types/postSchema';
import { QualityScores, HookOption } from '@/types/generator';
import { ScheduledPost } from '@/types/scheduler';
import { TemplateStyle } from '@/lib/templates';
import {
  fetchDrafts,
  fetchDraftById,
  saveDraftPost,
  deleteDraftById,
  publishDraftToTelegram,
  fetchScheduledPosts,
  reschedulePost,
  publishScheduledNow,
  cancelScheduledPost,
  deleteScheduledPost,
  onAuthRequired,
  checkAuthStatus,
} from '@/lib/api';
import { TopNav } from './TopNav';
import { ContentEditor } from './ContentEditor';
import { TelegramPreview } from './TelegramPreview';
import { SettingsPanel } from './SettingsPanel';
import { DraftsDrawer } from './DraftsDrawer';
import { PublishModal } from './PublishModal';
import { StudioAuthModal } from './StudioAuthModal';
import { AIGeneratorModal } from './AIGeneratorModal';
import { ScheduleDialog } from './ScheduleDialog';
import { ScheduledDrawer } from './ScheduledDrawer';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { Button } from '@/components/ui/button';
import { Save, Send } from 'lucide-react';
import { toast } from 'sonner';

const DEFAULT_POST: PostSchema = {
  schema_version: '1.0.0',
  content_type: 'ai_news',
  title: 'Google DeepMind Unveils Next-Gen Gemini Reasoning Architecture',
  body: 'Google announces multimodal reasoning architecture crossing frontier benchmark scores in coding, mathematics, and live video streaming perception.',
  summary: 'Google announces multimodal reasoning architecture crossing frontier benchmark scores in coding, mathematics, and live video streaming perception.',
  takeaways: [
    'Outperforms leading frontier models in mathematical proofs and autonomous tool use.',
    'Native sub-second streaming audio and visual perception enabled by default.',
    'Full developer API roll-out beginning immediately.',
  ],
  why_it_matters: 'Accelerates the transition from text-only chatbots to ubiquitous multimodal AI systems.',
  cta: 'Explore documentation and benchmark details in the link below.',
  buttons: [
    { text: '📚 Read Source', url: 'https://blog.google/technology/ai/gemini-pro-reasoning/' },
    { text: '💬 Discuss', url: 'https://t.me/heyaaashu' },
  ],
  source: {
    title: 'Google Official Blog',
    url: 'https://blog.google/technology/ai/gemini-pro-reasoning/',
  },
  verification: {
    status: 'verified',
    sources: ['https://blog.google/technology/ai/gemini-pro-reasoning/'],
  },
  parse_mode: 'HTML',
};

export const StudioLayout: React.FC = () => {
  const [post, setPost] = useState<PostSchema>(DEFAULT_POST);
  const [templateStyle, setTemplateStyle] = useState<TemplateStyle>('auto');
  const [currentDraftId, setCurrentDraftId] = useState<number | undefined>(undefined);
  const [drafts, setDrafts] = useState<DraftListItem[]>([]);
  const [isDraftsOpen, setIsDraftsOpen] = useState(false);
  const [isPublishModalOpen, setIsPublishModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isAIGenOpen, setIsAIGenOpen] = useState(false);
  const [isScheduleOpen, setIsScheduleOpen] = useState(false);
  const [isScheduledDrawerOpen, setIsScheduledDrawerOpen] = useState(false);
  const [scheduledPosts, setScheduledPosts] = useState<ScheduledPost[]>([]);
  const [qualityMetrics, setQualityMetrics] = useState<QualityScores | undefined>(undefined);
  const [hookOptions, setHookOptions] = useState<HookOption[] | undefined>(undefined);
  const [isPublishing, setIsPublishing] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');
  const [activeMobileTab, setActiveMobileTab] = useState<'edit' | 'preview' | 'settings'>('edit');

  // Undo / Redo History Stacks
  const historyRef = useRef<PostSchema[]>([DEFAULT_POST]);
  const historyIndexRef = useRef<number>(0);
  const isUndoRedoActionRef = useRef<boolean>(false);

  const loadScheduledList = useCallback(async () => {
    const res = await fetchScheduledPosts();
    if (res.success) {
      setScheduledPosts(res.scheduled_posts);
    }
  }, []);

  const activeScheduledCount = useMemo(() => {
    return scheduledPosts.filter((p) => p.status === 'scheduled').length;
  }, [scheduledPosts]);

  // Load drafts, scheduled posts and verify auth on mount
  useEffect(() => {
    loadDraftsList();
    loadScheduledList();

    const unsubscribe = onAuthRequired((required) => {
      setIsAuthModalOpen(required);
    });

    checkAuthStatus().then((status) => {
      if (status.authRequired && !status.authenticated) {
        setIsAuthModalOpen(true);
      }
    });

    return () => unsubscribe();
  }, [loadScheduledList]);

  const loadDraftsList = async () => {
    const list = await fetchDrafts();
    setDrafts(list);
  };

  // Push to history
  const pushHistory = useCallback((newPost: PostSchema) => {
    if (isUndoRedoActionRef.current) {
      isUndoRedoActionRef.current = false;
      return;
    }
    const currentHist = historyRef.current.slice(0, historyIndexRef.current + 1);
    currentHist.push(newPost);
    historyRef.current = currentHist;
    historyIndexRef.current = currentHist.length - 1;
  }, []);

  const handlePostChange = useCallback(
    (updater: (prev: PostSchema) => PostSchema) => {
      setPost((prev) => {
        const next = updater(prev);
        pushHistory(next);
        setSaveStatus('unsaved');
        return next;
      });
    },
    [pushHistory]
  );

  // Undo / Redo
  const handleUndo = useCallback(() => {
    if (historyIndexRef.current > 0) {
      historyIndexRef.current -= 1;
      isUndoRedoActionRef.current = true;
      setPost(historyRef.current[historyIndexRef.current]);
      setSaveStatus('unsaved');
    }
  }, []);

  const handleRedo = useCallback(() => {
    if (historyIndexRef.current < historyRef.current.length - 1) {
      historyIndexRef.current += 1;
      isUndoRedoActionRef.current = true;
      setPost(historyRef.current[historyIndexRef.current]);
      setSaveStatus('unsaved');
    }
  }, []);

  // Keyboard shortcut for Undo / Redo
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        if (e.shiftKey) {
          e.preventDefault();
          handleRedo();
        } else {
          e.preventDefault();
          handleUndo();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleUndo, handleRedo]);

  // Save Draft
  const handleSave = async () => {
    setSaveStatus('saving');
    const res = await saveDraftPost(post, currentDraftId);
    if (res.success) {
      setCurrentDraftId(res.draftId);
      setSaveStatus('saved');
      toast.success('Draft saved successfully!');
      loadDraftsList();
    } else {
      setSaveStatus('unsaved');
      toast.error(res.error || 'Failed to save draft');
    }
  };

  // New Draft
  const handleNewDraft = () => {
    setPost({
      ...DEFAULT_POST,
      title: 'New Post Title',
      body: 'Write your post body here...',
      summary: 'Write your post body here...',
      takeaways: [],
      why_it_matters: '',
      buttons: [],
    });
    setCurrentDraftId(undefined);
    setTemplateStyle('auto');
    setSaveStatus('unsaved');
    toast.info('Created new draft');
  };

  // Open Draft
  const handleSelectDraft = async (id: number) => {
    const data = await fetchDraftById(id);
    if (data && data.schema) {
      setPost(data.schema);
      setCurrentDraftId(id);
      setTemplateStyle('auto');
      setSaveStatus('saved');
      toast.success(`Loaded draft #${id}`);
    } else {
      toast.error('Could not load draft');
    }
  };

  // Duplicate Draft
  const handleDuplicateDraft = async (id: number) => {
    const data = await fetchDraftById(id);
    if (data && data.schema) {
      const dupPost: PostSchema = {
        ...data.schema,
        title: `${data.schema.title} (Copy)`,
      };
      const res = await saveDraftPost(dupPost);
      if (res.success) {
        toast.success('Draft duplicated!');
        loadDraftsList();
      }
    }
  };

  // Delete Draft
  const handleDeleteDraft = async (id: number) => {
    const ok = await deleteDraftById(id);
    if (ok) {
      toast.success('Draft deleted');
      if (currentDraftId === id) {
        handleNewDraft();
      }
      loadDraftsList();
    }
  };

  // Publish
  const handleConfirmPublish = async () => {
    setIsPublishing(true);
    try {
      const res = await publishDraftToTelegram(post, currentDraftId);
      if (res.success) {
        toast.success(`🚀 Published to Telegram! Message ID: ${res.messageId || 'OK'}`);
        setIsPublishModalOpen(false);
        setSaveStatus('saved');
        loadDraftsList();
      } else {
        toast.error(res.error || 'Publish failed');
      }
    } finally {
      setIsPublishing(false);
    }
  };

  // Scheduling handlers
  const handleReschedulePost = async (postId: number, newTimeIso: string) => {
    const res = await reschedulePost(postId, newTimeIso);
    if (res.success) {
      toast.success('Post rescheduled successfully!');
      await loadScheduledList();
      return true;
    }
    toast.error(res.error || 'Failed to reschedule post');
    return false;
  };

  const handlePublishScheduledNow = async (postId: number) => {
    const res = await publishScheduledNow(postId);
    if (res.success) {
      toast.success(`Published to Telegram! (Message #${res.message_id || 'OK'})`);
      await loadScheduledList();
      return true;
    }
    toast.error(res.error || 'Failed to publish');
    return false;
  };

  const handleCancelSchedule = async (postId: number) => {
    const res = await cancelScheduledPost(postId);
    if (res.success) {
      toast.success('Schedule cancelled.');
      await loadScheduledList();
      return true;
    }
    toast.error(res.error || 'Failed to cancel schedule');
    return false;
  };

  const handleDeleteSchedule = async (postId: number) => {
    const res = await deleteScheduledPost(postId);
    if (res.success) {
      toast.success('Scheduled record deleted.');
      await loadScheduledList();
      return true;
    }
    toast.error(res.error || 'Failed to delete record');
    return false;
  };

  const handleEditScheduledPost = (scheduledPost: PostSchema, postId: number) => {
    setPost(scheduledPost);
    setCurrentDraftId(postId);
    pushHistory(scheduledPost);
    setActiveMobileTab('edit');
  };

  // Handle AI Generated Post
  const handlePostGenerated = (
    newPost: PostSchema,
    draftId: number,
    quality?: QualityScores,
    hooks?: HookOption[]
  ) => {
    setPost(newPost);
    setCurrentDraftId(draftId);
    setQualityMetrics(quality);
    setHookOptions(hooks);
    pushHistory(newPost);
    setSaveStatus('saved');
    setActiveMobileTab('edit');
    loadDraftsList();
  };

  const canUndo = historyIndexRef.current > 0;
  const canRedo = historyIndexRef.current < historyRef.current.length - 1;

  return (
    <div className="h-[100dvh] w-full flex flex-col min-h-0 bg-gradient-to-br from-slate-950 via-slate-900 to-black text-foreground overflow-hidden font-sans">
      {/* Top Bar */}
      <TopNav
        onOpenDrafts={() => setIsDraftsOpen(true)}
        onNewDraft={handleNewDraft}
        onOpenAIGenerator={() => setIsAIGenOpen(true)}
        onOpenScheduled={() => {
          loadScheduledList();
          setIsScheduledDrawerOpen(true);
        }}
        scheduledCount={activeScheduledCount}
        onSave={handleSave}
        onPublishClick={() => setIsPublishModalOpen(true)}
        onOpenAuth={() => setIsAuthModalOpen(true)}
        onUndo={handleUndo}
        onRedo={handleRedo}
        canUndo={canUndo}
        canRedo={canRedo}
        saveStatus={saveStatus}
        isPublishing={isPublishing}
      />

      {/* Main Workspace: Desktop 3-Column Resizable Layout */}
      <div className="flex-1 w-full hidden md:block overflow-hidden">
        <ResizablePanelGroup direction="horizontal">
          {/* Left Panel: Content Editor */}
          <ResizablePanel defaultSize={32} minSize={25} maxSize={45} className="bg-card/30 backdrop-blur-md border-r border-border/60">
            <div className="h-full overflow-y-auto">
              <ContentEditor
                post={post}
                templateStyle={templateStyle}
                onPostChange={handlePostChange}
                onTemplateChange={setTemplateStyle}
                onOpenAIGenerator={() => setIsAIGenOpen(true)}
              />
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Center Canvas: Live Telegram Preview */}
          <ResizablePanel defaultSize={44} minSize={30} className="bg-transparent flex flex-col">
            <div className="flex-1 overflow-y-auto p-4 flex items-center justify-center">
              <TelegramPreview post={post} templateStyle={templateStyle} />
            </div>
          </ResizablePanel>

          <ResizableHandle withHandle />

          {/* Right Panel: Settings & Quality Health */}
          <ResizablePanel defaultSize={24} minSize={20} maxSize={35} className="bg-card/30 backdrop-blur-md border-l border-border/60">
            <div className="h-full overflow-y-auto">
              <SettingsPanel
                post={post}
                templateStyle={templateStyle}
                quality={qualityMetrics}
                hooks={hookOptions}
                onSelectHook={(h) => handlePostChange((p) => ({ ...p, title: h }))}
              />
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>

      {/* Mobile Workspace: Responsive Single Dedicated Scroll Area */}
      <div className="flex-1 w-full md:hidden flex flex-col min-h-0 relative overflow-hidden">
        <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain p-3 pb-32">
          {activeMobileTab === 'edit' && (
            <div className="max-w-xl mx-auto">
              <ContentEditor
                post={post}
                templateStyle={templateStyle}
                onPostChange={handlePostChange}
                onTemplateChange={setTemplateStyle}
                onOpenAIGenerator={() => setIsAIGenOpen(true)}
              />
            </div>
          )}

          {activeMobileTab === 'preview' && (
            <div className="max-w-xl mx-auto flex items-center justify-center pt-2">
              <TelegramPreview
                post={post}
                templateStyle={templateStyle}
                onPublishClick={() => setIsPublishModalOpen(true)}
              />
            </div>
          )}

          {activeMobileTab === 'settings' && (
            <div className="max-w-xl mx-auto">
              <SettingsPanel
                post={post}
                templateStyle={templateStyle}
                quality={qualityMetrics}
                hooks={hookOptions}
                onSelectHook={(h) => handlePostChange((p) => ({ ...p, title: h }))}
              />
            </div>
          )}
        </div>

        {/* Mobile Sticky Bottom Floating Action Bar */}
        <div className="sticky bottom-0 left-0 right-0 z-40 bg-slate-950/90 border-t border-slate-800/80 backdrop-blur-2xl px-3 py-2.5 flex items-center justify-between gap-2 shadow-[0_-10px_30px_rgba(0,0,0,0.7)] shrink-0">
          {/* Quick Tab Switcher */}
          <div className="flex items-center gap-1 bg-slate-900/80 border border-slate-800/80 p-1 rounded-2xl">
            <button
              type="button"
              onClick={() => setActiveMobileTab('edit')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                activeMobileTab === 'edit'
                  ? 'bg-gradient-to-r from-cyan-500/30 to-blue-500/30 text-cyan-300 border border-cyan-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              ✏️ Edit
            </button>
            <button
              type="button"
              onClick={() => setActiveMobileTab('preview')}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                activeMobileTab === 'preview'
                  ? 'bg-gradient-to-r from-cyan-500/30 to-blue-500/30 text-cyan-300 border border-cyan-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              👁 Preview
            </button>
            <button
              type="button"
              onClick={() => setActiveMobileTab('settings')}
              className={`px-2.5 py-1.5 rounded-xl text-xs font-semibold transition-all flex items-center gap-1.5 ${
                activeMobileTab === 'settings'
                  ? 'bg-gradient-to-r from-cyan-500/30 to-blue-500/30 text-cyan-300 border border-cyan-500/50 shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <span>⚙️</span>
              {qualityMetrics && (
                <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-mono font-bold">
                  {qualityMetrics.overall}
                </span>
              )}
            </button>
          </div>

          {/* Quick Actions: Save & Publish */}
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSave}
              className="h-10 px-3 text-xs font-semibold border-slate-800 bg-slate-900/80 hover:bg-slate-800 text-slate-200 rounded-xl shadow-sm"
              title="Save draft"
            >
              <Save className="w-3.5 h-3.5 mr-1 text-slate-400" />
              Save
            </Button>

            <Button
              size="sm"
              onClick={() => setIsPublishModalOpen(true)}
              disabled={isPublishing}
              className="h-10 px-3.5 text-xs font-bold bg-gradient-to-r from-cyan-500 via-blue-600 to-indigo-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-950/80 rounded-xl transition-all"
            >
              <Send className="w-3.5 h-3.5 mr-1" />
              {isPublishing ? '...' : 'Publish'}
            </Button>
          </div>
        </div>
      </div>

      {/* Drawers & Modals */}
      <DraftsDrawer
        isOpen={isDraftsOpen}
        onClose={() => setIsDraftsOpen(false)}
        drafts={drafts}
        currentDraftId={currentDraftId}
        onSelectDraft={handleSelectDraft}
        onDuplicateDraft={handleDuplicateDraft}
        onDeleteDraft={handleDeleteDraft}
        onNewDraft={handleNewDraft}
      />

      <PublishModal
        isOpen={isPublishModalOpen}
        onClose={() => setIsPublishModalOpen(false)}
        onConfirmPublish={handleConfirmPublish}
        onOpenSchedule={() => setIsScheduleOpen(true)}
        post={post}
        isPublishing={isPublishing}
      />

      <ScheduleDialog
        isOpen={isScheduleOpen}
        onClose={() => setIsScheduleOpen(false)}
        post={post}
        postId={currentDraftId}
        onScheduledSuccess={(scheduled) => {
          loadScheduledList();
          loadDraftsList();
        }}
      />

      <ScheduledDrawer
        isOpen={isScheduledDrawerOpen}
        onClose={() => setIsScheduledDrawerOpen(false)}
        scheduledPosts={scheduledPosts}
        onRefresh={loadScheduledList}
        onEditPost={handleEditScheduledPost}
        onReschedulePost={handleReschedulePost}
        onPublishNow={handlePublishScheduledNow}
        onCancelSchedule={handleCancelSchedule}
        onDeleteSchedule={handleDeleteSchedule}
      />

      <StudioAuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthenticated={() => {
          loadDraftsList();
          loadScheduledList();
        }}
      />

      <AIGeneratorModal
        isOpen={isAIGenOpen}
        onClose={() => setIsAIGenOpen(false)}
        onPostGenerated={handlePostGenerated}
      />
    </div>
  );
};
