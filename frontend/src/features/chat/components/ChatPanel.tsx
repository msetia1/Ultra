import { useState } from 'react';
import { useChatStore } from '../store/chatStore';
import { X } from 'lucide-react';
import { useCalendarChat } from '@/features/calendar/hooks/useCalendarChat';
import PatchPreview from '@/features/calendar/components/PatchPreview';
import ChatInput from './ChatInput';
import MessageList from './MessageList';

export default function ChatPanel() {
  const {
    isOpen,
    closeChat,
    messages,
    streamingMessage,
    isStreaming: isStreamingStore,
    addUserMessage
  } = useChatStore();
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

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isStreaming || isAccepting) return;

    // Add user message to store
    addUserMessage(input.trim());

    // Clear input
    setInput('');

    // TODO: Backend integration - will connect when backend is ready
    // await sendMessage(input.trim());
  };

  const handleInputChange = (newValue: string) => {
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
    return null;
  }

  return (
    <div
      className={`
        fixed right-0 top-0 bottom-0 w-[418px]
        transform transition-transform duration-300 ease-in-out z-[100] flex flex-col
        ${isOpen ? '!translate-x-0' : 'translate-x-full'}
      `}
      style={{
        backgroundColor: '#000000',
        borderLeft: '1px solid #252525',
        position: 'fixed',
        right: 0,
        top: 0,
        bottom: 0,
      }}
    >
      {/* Chat Header */}
      <div
        className="relative p-6 shrink-0"
        style={{
          backgroundColor: '#000000',
        }}
      >
        <div className="flex items-center justify-end">
          <button
            onClick={closeChat}
            className="bg-transparent border-none p-0 outline-none text-[#888888] hover:text-[#fcecc9] transition-colors cursor-pointer"
            style={{
              paddingTop: '16px',
              paddingRight: '16px',
            }}
            aria-label="Close chat"
          >
            <X size={24} />
          </button>
        </div>
      </div>

      {/* Chat Messages */}
      <MessageList
        messages={messages}
        streamingMessage={streamedMessage || streamingMessage}
        isStreaming={isStreaming || isStreamingStore}
        error={error}
      />

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
        className="shrink-0"
        style={{
          backgroundColor: '#000000',
          paddingLeft: '32px',
          paddingRight: '32px',
          paddingTop: '24px',
          paddingBottom: '24px',
        }}
      >
        <ChatInput
          value={input}
          onChange={handleInputChange}
          onSubmit={handleSubmit}
          isLoading={isStreaming || isAccepting}
          placeholder="Add meeting tomorrow at 2pm..."
        />
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
