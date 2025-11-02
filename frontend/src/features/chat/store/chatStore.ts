import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Message } from '../types/chat.types';

interface ChatStore {
  isOpen: boolean;
  messages: Message[];

  // Actions
  toggleChat: () => void;
  openChat: () => void;
  closeChat: () => void;
  addMessage: (content: string, sender: 'user' | 'ai') => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatStore>()(
  persist(
    (set) => ({
      isOpen: false,
      messages: [],

      toggleChat: () => set((state) => ({ isOpen: !state.isOpen })),

      openChat: () => set({ isOpen: true }),

      closeChat: () => set({ isOpen: false }),

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

      clearMessages: () => set({ messages: [] })
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({ isOpen: state.isOpen }) // Only persist open/closed state
    }
  )
);
