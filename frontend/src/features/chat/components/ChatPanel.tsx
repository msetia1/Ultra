import { useState } from 'react';
import { useChatStore } from '../store/chatStore';
import { X, Send } from 'lucide-react';
import { useCalendarChat } from '@/features/calendar/hooks/useCalendarChat';
import PatchPreview from '@/features/calendar/components/PatchPreview';

export default function ChatPanel() {
  const { isOpen, closeChat } = useChatStore();
  const [input, setInput] = useState('');
  const [isAccepting, setIsAccepting] = useState(false);

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    await sendMessage(input.trim());
    setInput('');
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

  if (!isOpen) return null;

  return (
    <div
      className={`
        fixed right-0 top-0 h-full w-[418px] bg-black border-l border-[#606060]
        transform transition-transform duration-300 ease-in-out z-50 flex flex-col
        ${isOpen ? 'translate-x-0' : 'translate-x-full'}
      `}
    >
      {/* Chat Header */}
      <div className="relative p-6 border-b border-[#606060]">
        <div className="flex items-center justify-between">
          <h2 className="text-[#fcecc9] text-lg font-medium">Calendar Assistant</h2>
          <button
            onClick={closeChat}
            className="text-[#888888] hover:text-[#fcecc9] transition-colors"
            aria-label="Close chat"
          >
            <X size={24} />
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
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
      <form onSubmit={handleSubmit} className="p-4 border-t border-[#606060]">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Add meeting tomorrow at 2pm..."
            disabled={isStreaming || isAccepting}
            className="flex-1 bg-[#606060]/20 text-[#fcecc9] placeholder-[#888888] px-4 py-2 rounded border border-[#606060] focus:border-[#fcecc9] focus:outline-none disabled:opacity-50 text-sm"
          />
          <button
            type="submit"
            disabled={isStreaming || isAccepting || !input.trim()}
            className="bg-[#fcecc9] text-black p-2 rounded hover:bg-[#fcecc9]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Send message"
          >
            <Send size={20} />
          </button>
        </div>
      </form>
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
