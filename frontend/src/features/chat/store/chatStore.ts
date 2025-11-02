import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Message } from '../types/chat.types';

interface ChatStore {
  isOpen: boolean;
  messages: Message[];
  streamingMessage: string;
  isStreaming: boolean;

  // Actions
  toggleChat: () => void;
  openChat: () => void;
  closeChat: () => void;
  addMessage: (content: string, sender: 'user' | 'ai') => void;
  addUserMessage: (content: string) => void;
  updateStreamingMessage: (delta: string) => void;
  finalizeStreamingMessage: () => void;
  clearMessages: () => void;
  setStreaming: (isStreaming: boolean) => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set) => {
      console.log('[chatStore] Store initializing');
      return {
        isOpen: false,
        messages: [],
        streamingMessage: '',
        isStreaming: false,

      toggleChat: () => {
        console.log('[chatStore] toggleChat called');
        return set((state) => {
          console.log('[chatStore] Current isOpen:', state.isOpen, '-> New isOpen:', !state.isOpen);
          return { isOpen: !state.isOpen };
        });
      },

      openChat: () => {
        console.log('[chatStore] openChat called');
        return set({ isOpen: true });
      },

      closeChat: () => {
        console.log('[chatStore] closeChat called');
        return set({ isOpen: false });
      },

      addMessage: (content: string, sender: 'user' | 'ai') =>
        set((state) => ({
          messages: [
            ...state.messages,
            {
              id: `msg-${Date.now()}-${Math.random()}`,
              content,
              timestamp: new Date(),
              sender
            }
          ]
        })),

      addUserMessage: (content: string) =>
        set((state) => ({
          messages: [
            ...state.messages,
            {
              id: `msg-${Date.now()}-${Math.random()}`,
              content,
              timestamp: new Date(),
              sender: 'user'
            }
          ]
        })),

      updateStreamingMessage: (delta: string) =>
        set((state) => ({
          streamingMessage: state.streamingMessage + delta
        })),

      finalizeStreamingMessage: () =>
        set((state) => {
          const finalMessage = {
            id: `msg-${Date.now()}-${Math.random()}`,
            content: state.streamingMessage,
            timestamp: new Date(),
            sender: 'ai' as const
          };
          return {
            messages: [...state.messages, finalMessage],
            streamingMessage: '',
            isStreaming: false
          };
        }),

      setStreaming: (isStreaming: boolean) => set({ isStreaming }),

      clearMessages: () => set({ messages: [], streamingMessage: '', isStreaming: false })
      };
    },
    {
      name: 'chat-storage',
      partialize: (state) => ({ isOpen: state.isOpen }) // Only persist open/closed state
    }
  )
);
