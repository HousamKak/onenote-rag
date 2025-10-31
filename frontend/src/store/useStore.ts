import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { RAGConfig, QueryResponse, Conversation, Message } from '../types/index';

interface AppState {
  // Current configuration
  currentConfig: RAGConfig | null;
  setCurrentConfig: (config: RAGConfig) => void;

  // Query history (legacy - kept for backward compatibility)
  queryHistory: QueryResponse[];
  addQueryToHistory: (response: QueryResponse) => void;
  clearHistory: () => void;

  // Conversations
  conversations: Conversation[];
  currentConversationId: string | null;

  createConversation: () => string;
  deleteConversation: (id: string) => void;
  setCurrentConversation: (id: string | null) => void;
  addMessage: (conversationId: string, message: Omit<Message, 'id' | 'timestamp'>) => void;
  updateConversationTitle: (id: string, title: string) => void;
  clearConversations: () => void;

  // UI state
  isIndexing: boolean;
  setIsIndexing: (isIndexing: boolean) => void;
  isSidebarOpen: boolean;
  setSidebarOpen: (isOpen: boolean) => void;

  indexStats: { total_documents: number } | null;
  setIndexStats: (stats: { total_documents: number } | null) => void;
}

const generateId = () => Math.random().toString(36).substring(2) + Date.now().toString(36);

const generateTitle = (firstMessage: string): string => {
  const maxLength = 50;
  return firstMessage.length > maxLength
    ? firstMessage.substring(0, maxLength) + '...'
    : firstMessage;
};

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // Config
      currentConfig: null,
      setCurrentConfig: (config) => set({ currentConfig: config }),

      // History (legacy)
      queryHistory: [],
      addQueryToHistory: (response) =>
        set((state) => ({
          queryHistory: [response, ...state.queryHistory].slice(0, 50),
        })),
      clearHistory: () => set({ queryHistory: [] }),

      // Conversations
      conversations: [],
      currentConversationId: null,

      createConversation: () => {
        const id = generateId();
        const newConversation: Conversation = {
          id,
          title: 'New Chat',
          messages: [],
          createdAt: new Date(),
          updatedAt: new Date(),
          config: get().currentConfig || undefined,
        };
        set((state) => ({
          conversations: [newConversation, ...state.conversations],
          currentConversationId: id,
        }));
        return id;
      },

      deleteConversation: (id) => {
        set((state) => ({
          conversations: state.conversations.filter((c) => c.id !== id),
          currentConversationId:
            state.currentConversationId === id ? null : state.currentConversationId,
        }));
      },

      setCurrentConversation: (id) => set({ currentConversationId: id }),

      addMessage: (conversationId, message) => {
        const messageWithId: Message = {
          ...message,
          id: generateId(),
          timestamp: new Date(),
        };

        set((state) => ({
          conversations: state.conversations.map((conv) => {
            if (conv.id === conversationId) {
              const updatedMessages = [...conv.messages, messageWithId];
              // Auto-generate title from first user message
              const title =
                conv.title === 'New Chat' && message.role === 'user'
                  ? generateTitle(message.content)
                  : conv.title;

              return {
                ...conv,
                messages: updatedMessages,
                title,
                updatedAt: new Date(),
              };
            }
            return conv;
          }),
        }));
      },

      updateConversationTitle: (id, title) => {
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === id ? { ...conv, title, updatedAt: new Date() } : conv
          ),
        }));
      },

      clearConversations: () => set({ conversations: [], currentConversationId: null }),

      // UI
      isIndexing: false,
      setIsIndexing: (isIndexing) => set({ isIndexing }),

      isSidebarOpen: true,
      setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),

      indexStats: null,
      setIndexStats: (stats) => set({ indexStats: stats }),
    }),
    {
      name: 'onenote-rag-storage',
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversationId: state.currentConversationId,
        currentConfig: state.currentConfig,
      }),
    }
  )
);
