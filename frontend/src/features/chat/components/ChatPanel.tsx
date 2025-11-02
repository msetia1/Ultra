import { useState, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';
import { useCalendarStore } from '@/features/calendar/store/calendarStore';
import { X, Plus } from 'lucide-react';
import { useCalendarChat } from '@/features/calendar/hooks/useCalendarChat';
import ChatInput from './ChatInput';
import MessageList from './MessageList';

export default function ChatPanel() {
  const {
    isOpen,
    closeChat,
    messages,
    streamingMessage,
    isStreaming: isStreamingStore,
    addUserMessage,
    clearMessages
  } = useChatStore();
  const [input, setInput] = useState('');

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

  const { setProposedPatches, commitChanges } = useCalendarStore();

  // Sync proposed patches to calendar store for live UI updates
  useEffect(() => {
    if (proposedPatches.length > 0) {
      console.log('[ChatPanel] Syncing', proposedPatches.length, 'patches to calendarStore');
      setProposedPatches(proposedPatches);
    }
  }, [proposedPatches, setProposedPatches]);

  // Sync backend AI response to Zustand store when streaming completes
  // Auto-accept patches and call backend API
  useEffect(() => {
    if (!isStreaming && streamedMessage && proposedPatches.length > 0) {
      useChatStore.getState().addMessage(streamedMessage, 'ai');

      // Auto-accept patches by calling backend API
      (async () => {
        try {
          const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

          const response = await fetch(`${API_BASE_URL}/calendar/accept-patches/${weekId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              patches: proposedPatches,
              conversation_id: conversationId,
            }),
          });

          if (!response.ok) {
            console.error('[ChatPanel] Failed to accept patches:', response.status);
          } else {
            console.log('[ChatPanel] Patches auto-accepted successfully');
            commitChanges(); // Clear pending state after successful API call
          }
        } catch (error) {
          console.error('[ChatPanel] Error auto-accepting patches:', error);
        }
      })();
    }
  }, [isStreaming, streamedMessage, proposedPatches, conversationId, weekId, commitChanges]);

  const handleSubmit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || isStreaming) return;

    const messageText = input.trim();

    // Add user message to store
    addUserMessage(messageText);

    // Clear input
    setInput('');

    // Send message to backend via SSE
    await sendMessage(messageText);
  };

  const handleInputChange = (newValue: string) => {
    setInput(newValue);
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
        <div className="flex items-center justify-between">
          <button
            onClick={clearMessages}
            className="bg-transparent border-none p-0 outline-none text-[#888888] hover:text-[#fcecc9] transition-colors cursor-pointer"
            style={{
              paddingTop: '16px',
              paddingLeft: '16px',
            }}
            aria-label="New chat"
          >
            <Plus size={24} />
          </button>
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
          isLoading={isStreaming}
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
