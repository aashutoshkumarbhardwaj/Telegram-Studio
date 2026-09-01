import React, { useState, useEffect, useCallback, useRef } from 'react';
import { DraftListItem, PostSchema } from '@/types/postSchema';
import { TemplateStyle } from '@/lib/templates';
import { fetchDrafts, fetchDraftById, saveDraftPost, deleteDraftById, publishDraftToTelegram, onAuthRequired, checkAuthStatus } from '@/lib/api';
import { TopNav } from './TopNav';
import { ContentEditor } from './ContentEditor';
import { TelegramPreview } from './TelegramPreview';
import { SettingsPanel } from './SettingsPanel';
import { DraftsDrawer } from './DraftsDrawer';
import { PublishModal } from './PublishModal';
import { StudioAuthModal } from './StudioAuthModal';
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from '@/components/ui/resizable';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
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
  const [isPublishing, setIsPublishing] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'saved' | 'saving' | 'unsaved'>('saved');
  const [activeMobileTab, setActiveMobileTab] = useState<'edit' | 'preview' | 'settings'>('edit');

  // Undo / Redo History Stacks
  const historyRef = useRef<PostSchema[]>([DEFAULT_POST]);
  const historyIndexRef = useRef<number>(0);
  const isUndoRedoActionRef = useRef<boolean>(false);

  // Load drafts and verify auth on mount
  useEffect(() => {
    loadDraftsList();

    const unsubscribe = onAuthRequired((required) => {
      setIsAuthModalOpen(required);
    });

    checkAuthStatus().then((status) => {
      if (status.authRequired && !status.authenticated) {
        setIsAuthModalOpen(true);
      }
    });

    return () => unsubscribe();
  }, []);

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

  const canUndo = historyIndexRef.current > 0;
  const canRedo = historyIndexRef.current < historyRef.current.length - 1;

  return (
    <div className="h-screen w-screen flex flex-col bg-gradient-to-br from-slate-950 via-slate-900 to-black text-foreground overflow-hidden font-sans">
      {/* Top Bar */}
      <TopNav
        onOpenDrafts={() => setIsDraftsOpen(true)}
        onNewDraft={handleNewDraft}
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
              <SettingsPanel post={post} templateStyle={templateStyle} />
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      </div>

      {/* Mobile Workspace: Responsive Tabs */}
      <div className="flex-1 w-full md:hidden flex flex-col overflow-hidden">
        <Tabs value={activeMobileTab} onValueChange={(v) => setActiveMobileTab(v as any)} className="flex-1 flex flex-col">
          <TabsList className="grid grid-cols-3 bg-slate-900 border-b border-border/60 h-10 rounded-none">
            <TabsTrigger value="edit" className="text-xs">
              ✏️ Editor
            </TabsTrigger>
            <TabsTrigger value="preview" className="text-xs">
              👁 Preview
            </TabsTrigger>
            <TabsTrigger value="settings" className="text-xs">
              ⚙️ Settings
            </TabsTrigger>
          </TabsList>

          <TabsContent value="edit" className="flex-1 overflow-y-auto p-2">
            <ContentEditor
              post={post}
              templateStyle={templateStyle}
              onPostChange={handlePostChange}
              onTemplateChange={setTemplateStyle}
            />
          </TabsContent>

          <TabsContent value="preview" className="flex-1 overflow-y-auto p-2 flex items-center justify-center">
            <TelegramPreview post={post} templateStyle={templateStyle} />
          </TabsContent>

          <TabsContent value="settings" className="flex-1 overflow-y-auto p-2">
            <SettingsPanel post={post} templateStyle={templateStyle} />
          </TabsContent>
        </Tabs>
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
        post={post}
        isPublishing={isPublishing}
      />

      <StudioAuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthenticated={() => {
          loadDraftsList();
        }}
      />
    </div>
  );
};
