import { useState, useEffect } from 'react';
import { useChatStore } from '../store/chatStore';
import { useCalendarStore } from '@/features/calendar/store/calendarStore';
import { X, Plus } from 'lucide-react';
import { useCalendarChat } from '@/features/calendar/hooks/useCalendarChat';
import { getWeekIdFromDate } from '@/features/calendar/utils/dateHelpers';
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

  // Get current week_id using shared helper
  const weekId = getWeekIdFromDate(new Date());

  const {
    sendMessage,
    isStreaming,
    proposedPatches,
    conversationId,
    error,
    clearPatches,
    clearConversation,
  } = useCalendarChat(weekId);

  const { setProposedPatches, hasPendingChanges, revertChanges, clearProposedPatches } = useCalendarStore();

  console.log('[ChatPanel] Render - hasPendingChanges:', hasPendingChanges);

  // Sync proposed patches to calendar store for live UI updates
  // Only apply when streaming is complete to avoid re-applying patches multiple times
  useEffect(() => {
    console.log('[ChatPanel] useEffect triggered - proposedPatches:', proposedPatches);
    console.log('[ChatPanel] proposedPatches.length:', proposedPatches.length);
    console.log('[ChatPanel] conversationId:', conversationId);
    console.log('[ChatPanel] isStreaming:', isStreaming);

    if (!isStreaming && proposedPatches.length > 0) {
      console.log('[ChatPanel] Condition met! Syncing', proposedPatches.length, 'patches to calendarStore');
      setProposedPatches(proposedPatches, conversationId || undefined);
    } else {
      console.log('[ChatPanel] Condition NOT met - isStreaming:', isStreaming, 'patches.length:', proposedPatches.length);
    }
  }, [proposedPatches, conversationId, isStreaming, setProposedPatches]);

  useEffect(() => {
    console.log('[ChatPanel] hasPendingChanges changed to:', hasPendingChanges);
  }, [hasPendingChanges]);

  // Auto-accept patches when streaming completes
  useEffect(() => {
    if (!isStreaming && proposedPatches.length > 0) {
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
            // Don't clear pending state - keep revert button visible for toggling
          }
        } catch (error) {
          console.error('[ChatPanel] Error auto-accepting patches:', error);
        }
      })();
    }
  }, [isStreaming, proposedPatches, conversationId, weekId]);

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

  const handleClearConversation = () => {
    // Clear chat store messages
    clearMessages();
    // Clear calendar chat hook state (including conversation ID)
    clearConversation();
    // Clear calendar pending changes
    clearProposedPatches();
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
            onClick={handleClearConversation}
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
        streamingMessage={streamingMessage}
        isStreaming={isStreaming || isStreamingStore}
        error={error}
        showRevertButton={hasPendingChanges}
        onRevert={() => {
          console.log('[ChatPanel] Revert button clicked');
          revertChanges(weekId);
        }}
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
