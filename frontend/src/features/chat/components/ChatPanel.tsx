import { useState } from 'react';
import { useChatStore } from '../store/chatStore';
import { X, ArrowUp, Square } from 'lucide-react';
import { useCalendarChat } from '@/features/calendar/hooks/useCalendarChat';
import PatchPreview from '@/features/calendar/components/PatchPreview';
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputActions,
  PromptInputAction,
} from '@/components/ui/prompt-input';
import { Button } from '@/components/ui/button';

export default function ChatPanel() {
  console.log('[ChatPanel] Component rendering');
  const { isOpen, closeChat } = useChatStore();
  console.log('[ChatPanel] isOpen state:', isOpen);
  const [input, setInput] = useState('');
  const [isAccepting, setIsAccepting] = useState(false);

  console.log('[ChatPanel] Current input:', input);

  // Get current week_id (you may want to pass this as a prop)
  const getCurrentWeekId = () => {
    const now = new Date();
    const year = now.getFullYear();
    const weekNum = getWeekNumber(now);
    return `${year}-W${String(weekNum).padStart(2, '0')}`;
  };

  const weekId = getCurrentWeekId();

  const {
    sendMessage,
    isStreaming,
    streamedMessage,
    proposedPatches,
    conversationId,
    error,
    clearPatches,
  } = useCalendarChat(weekId);

  const handleSubmit = async (e?: React.FormEvent) => {
    console.log('[ChatPanel] handleSubmit called with input:', input);
    e?.preventDefault();
    if (!input.trim() || isStreaming || isAccepting) return;

    await sendMessage(input.trim());
    setInput('');
  };

  const handleInputChange = (newValue: string) => {
    console.log('[ChatPanel] Input changed:', newValue);
    setInput(newValue);
  };

  const handleAccept = async (patches: any[]) => {
    try {
      setIsAccepting(true);

      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      const response = await fetch(`${API_BASE_URL}/calendar/accept-patches/${weekId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patches,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      // Clear patches and refresh calendar (you may want to trigger a reload)
      clearPatches();

      // TODO: Trigger calendar data refresh
      window.location.reload(); // Simple approach, can be improved

    } catch (error) {
      console.error('Failed to accept patches:', error);
      alert('Failed to apply changes. Please try again.');
    } finally {
      setIsAccepting(false);
    }
  };

  if (!isOpen) {
    console.log('[ChatPanel] Not rendering - isOpen is false');
    return null;
  }

  console.log('[ChatPanel] Rendering panel - isOpen is true');

  return (
    <div
      className={`
        fixed right-0 top-0 h-full w-[418px]
        transform transition-transform duration-300 ease-in-out z-50 flex flex-col
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}
      `}
      style={{
        backgroundColor: '#FF0000',
        border: '5px solid yellow'
      }}
    >
      {/* Chat Header */}
      <div
        className="relative p-6 border-b border-[#606060]"
        style={{
          backgroundColor: '#FFFF00',
          minHeight: '80px',
          flexShrink: 0
        }}
      >
        <div className="flex items-center justify-between">
          <h2 style={{ color: '#000000', fontSize: '20px', fontWeight: 'bold' }}>Calendar Assistant</h2>
          <button
            onClick={closeChat}
            style={{ color: '#000000', fontSize: '24px' }}
            aria-label="Close chat"
          >
            <X size={24} />
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <div
        className="flex-1 overflow-y-auto p-6 space-y-4"
        style={{
          backgroundColor: '#FF00FF',
          minHeight: '200px'
        }}
      >
        {streamedMessage && (
          <div className="bg-[#606060]/20 rounded-lg p-4">
            <div className="text-[#fcecc9] text-sm whitespace-pre-wrap">
              {streamedMessage}
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-900/20 border border-red-700/30 rounded-lg p-4">
            <div className="text-red-400 text-sm">
              {error}
            </div>
          </div>
        )}

        {isStreaming && (
          <div className="flex items-center gap-2 text-[#888888] text-sm">
            <div className="w-2 h-2 bg-[#888888] rounded-full animate-pulse"></div>
            Processing...
          </div>
        )}
      </div>

      {/* Patch Preview */}
      {proposedPatches.length > 0 && (
        <PatchPreview
          patches={proposedPatches}
          onAccept={handleAccept}
          onReject={clearPatches}
          isAccepting={isAccepting}
        />
      )}

      {/* Input */}
      <div
        className="p-4 border-t border-[#606060]"
        style={{
          backgroundColor: '#00FF00',
          minHeight: '120px',
          flexShrink: 0
        }}
      >
        {console.log('[ChatPanel] About to render PromptInput with:', { input, isStreaming, isAccepting })}
        <div style={{ backgroundColor: '#0000FF', border: '3px solid cyan', padding: '10px', minHeight: '80px' }}>
          <PromptInput
            value={input}
            onValueChange={handleInputChange}
            isLoading={isStreaming || isAccepting}
            disabled={isStreaming || isAccepting}
            onSubmit={handleSubmit}
            className="border-[#606060]"
          >
          <PromptInputTextarea
            placeholder="Add meeting tomorrow at 2pm..."
            className="text-[#fcecc9] placeholder:text-[#888888] bg-transparent"
            style={{
              color: '#FFFFFF',
              fontSize: '16px',
              minHeight: '44px',
              width: '100%'
            }}
          />
          <PromptInputActions className="flex items-center justify-end gap-2 pt-2">
            <PromptInputAction
              tooltip={isStreaming || isAccepting ? "Processing..." : "Send message"}
            >
              <Button
                variant="default"
                size="icon"
                className="h-8 w-8 rounded-full bg-[#fcecc9] text-black hover:bg-[#fcecc9]/90"
                onClick={handleSubmit}
                disabled={isStreaming || isAccepting || !input.trim()}
              >
                {isStreaming || isAccepting ? (
                  <Square className="size-5 fill-current" />
                ) : (
                  <ArrowUp className="size-5" />
                )}
              </Button>
            </PromptInputAction>
          </PromptInputActions>
        </PromptInput>
        </div>
      </div>
    </div>
  );
}

// Helper function to get ISO week number
function getWeekNumber(date: Date): number {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
}
