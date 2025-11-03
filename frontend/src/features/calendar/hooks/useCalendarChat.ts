import { useState, useCallback } from 'react';
import { useChatStore } from '@/features/chat/store/chatStore';

export interface CalendarPatch {
  patch_id: string;
  op: 'add_event' | 'remove_event' | 'modify_event' | 'move_event';
  target_day: {
    scheduled_date: string;
    anchor: any;
  };
  [key: string]: any;
}

interface SSEEvent {
  type: 'patch_proposed' | 'message_delta' | 'final' | 'error';
  patch?: CalendarPatch;
  delta?: string;
  message?: string;
  patches?: CalendarPatch[];
  conversation_id?: string;
}

export function useCalendarChat(weekId: string) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [proposedPatches, setProposedPatches] = useState<CalendarPatch[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(async (message: string) => {
    try {
      setIsStreaming(true);
      // Clear previous state for new conversation turn
      useChatStore.getState().setStreaming(true);
      useChatStore.getState().updateStreamingMessage(''); // Clear previous streaming message
      setProposedPatches([]);
      setError(null);

      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

      // Start SSE stream
      const response = await fetch(`${API_BASE_URL}/calendar/chat/${weekId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      // Read SSE stream
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete events (separated by \n\n)
        const events = buffer.split('\n\n');
        buffer = events.pop() || '';

        for (const event of events) {
          if (!event.trim() || !event.startsWith('data: ')) continue;

          try {
            const data: SSEEvent = JSON.parse(event.slice(6));

            if (data.type === 'message_delta') {
              // Append streaming text to Zustand store
              useChatStore.getState().updateStreamingMessage(data.delta || '');

            } else if (data.type === 'patch_proposed') {
              // Add patch to preview list
              if (data.patch) {
                setProposedPatches(prev => [...prev, data.patch!]);
              }

            } else if (data.type === 'final') {
              // Complete response - add AI message from final event
              if (data.message) {
                useChatStore.getState().addMessage(data.message, 'ai');
              }

              setProposedPatches(data.patches || []);
              if (data.conversation_id) {
                setConversationId(data.conversation_id);
              }

            } else if (data.type === 'error') {
              setError(data.message || 'Unknown error occurred');
            }

          } catch (e) {
            console.error('Failed to parse SSE event:', e);
          }
        }
      }

    } catch (error) {
      console.error('Calendar chat error:', error);
      setError(error instanceof Error ? error.message : 'Failed to send message');
    } finally {
      setIsStreaming(false);
      useChatStore.getState().setStreaming(false);
    }
  }, [weekId, conversationId]);

  const clearPatches = useCallback(() => {
    setProposedPatches([]);
    setError(null);
  }, []);

  const clearConversation = useCallback(() => {
    setProposedPatches([]);
    setConversationId(null);
    setError(null);
    setIsStreaming(false);
    // Note: Message clearing is handled by chatStore.clearMessages()
  }, []);

  return {
    sendMessage,
    isStreaming,
    proposedPatches,
    conversationId,
    error,
    clearPatches,
    clearConversation,
  };
}
