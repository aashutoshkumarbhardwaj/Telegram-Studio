import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Lock, Key, Eye, EyeOff, ShieldCheck, AlertCircle, Loader2 } from 'lucide-react';
import { loginStudio, getStudioAuthToken } from '@/lib/api';
import { toast } from 'sonner';

interface StudioAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAuthenticated?: () => void;
}

export const StudioAuthModal: React.FC<StudioAuthModalProps> = ({
  isOpen,
  onClose,
  onAuthenticated,
}) => {
  const [tokenInput, setTokenInput] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) {
      setErrorMsg('Please enter your Studio Access Token.');
      return;
    }

    setIsLoading(true);
    setErrorMsg(null);

    try {
      const res = await loginStudio(tokenInput.trim());
      if (res.success) {
        toast.success('Studio unlocked successfully!');
        setTokenInput('');
        onClose();
        if (onAuthenticated) {
          onAuthenticated();
        }
      } else {
        setErrorMsg(res.error || 'Invalid token. Please check your Render environment configuration.');
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Authentication failed. Please check network connectivity.');
    } finally {
      setIsLoading(false);
    }
  };

  const hasExistingToken = Boolean(getStudioAuthToken());

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-md bg-slate-900/95 border-slate-700/80 backdrop-blur-2xl text-slate-100 shadow-2xl z-50">
        <DialogHeader className="space-y-2">
          <div className="mx-auto w-12 h-12 rounded-xl bg-gradient-to-tr from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-1">
            <Lock className="w-6 h-6" />
          </div>
          <DialogTitle className="text-center text-lg font-semibold text-white flex items-center justify-center gap-2">
            Heyaaashu Studio Access
          </DialogTitle>
          <DialogDescription className="text-center text-xs text-slate-400">
            This deployment is protected with token authentication. Enter your access token to manage drafts and publish to Telegram.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 pt-2">
          {errorMsg && (
            <div className="p-3 rounded-lg bg-red-950/60 border border-red-800/60 text-red-300 text-xs flex items-start gap-2 animate-in fade-in duration-200">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-red-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <Label htmlFor="studio-token" className="text-xs font-medium text-slate-300 flex items-center justify-between">
              <span>Studio Access Token</span>
              {hasExistingToken && (
                <span className="text-[10px] text-emerald-400 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Token stored
                </span>
              )}
            </Label>
            <div className="relative">
              <Key className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <Input
                id="studio-token"
                type={showToken ? 'text' : 'password'}
                placeholder="Enter STUDIO_AUTH_TOKEN..."
                value={tokenInput}
                onChange={(e) => {
                  setTokenInput(e.target.value);
                  setErrorMsg(null);
                }}
                className="pl-9 pr-10 bg-slate-950/70 border-slate-700/80 text-white placeholder:text-slate-500 text-sm focus-visible:ring-cyan-500"
                autoFocus
                disabled={isLoading}
              />
              <button
                type="button"
                onClick={() => setShowToken(!showToken)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200 p-1 rounded"
                tabIndex={-1}
              >
                {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <p className="text-[11px] text-slate-500">
              Found in your Render Web Service dashboard under <strong>Environment Variables</strong> (<code>STUDIO_AUTH_TOKEN</code>).
            </p>
          </div>

          <div className="flex gap-2 pt-2">
            <Button
              type="button"
              variant="ghost"
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800/60"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading || !tokenInput.trim()}
              className="flex-1 text-xs font-medium bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-md shadow-cyan-900/20"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Verifying...
                </>
              ) : (
                'Unlock Studio'
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};
