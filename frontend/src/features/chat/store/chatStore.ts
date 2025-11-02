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
    (set) => {
      console.log('[chatStore] Store initializing with isOpen: true');
      return {
        isOpen: true, // Temporarily true for debugging
        messages: [],

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

      clearMessages: () => set({ messages: [] })
      };
    },
    {
      name: 'chat-storage',
      partialize: (state) => ({ isOpen: state.isOpen }) // Only persist open/closed state
    }
  )
);
