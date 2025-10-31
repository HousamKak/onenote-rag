import { useTheme } from '../context/ThemeContext';

export const useThemedStyles = () => {
  const { theme } = useTheme();

  if (theme === 'claude') {
    return {
      // Sidebar
      sidebar: {
        container: 'fixed lg:static inset-y-0 left-0 z-50 w-64 bg-claude-sidebar border-r border-claude-border flex flex-col',
        header: 'p-4 border-b border-claude-border',
        title: 'text-lg font-semibold text-claude-text mb-3',
        newButton: 'w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-claude-primary hover:bg-claude-primary-hover text-white rounded-lg shadow-claude font-medium text-sm',
        conversationList: 'flex-1 overflow-y-auto p-3 space-y-3',
        groupTitle: 'text-xs font-semibold text-claude-text-secondary uppercase tracking-wider px-2 mb-2',
        conversation: (isActive: boolean) =>
          `group relative flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer ${
            isActive
              ? 'bg-claude-user-msg'
              : 'hover:bg-gray-100'
          }`,
        nav: 'border-t border-claude-border p-3 space-y-1',
        navLink: (isActive: boolean) =>
          `flex items-center gap-3 px-3 py-2 rounded-lg ${
            isActive
              ? 'bg-claude-user-msg text-claude-text'
              : 'text-claude-text-secondary hover:bg-gray-100 hover:text-claude-text'
          }`,
        stats: 'border-t border-claude-border p-4',
      },

      // Messages
      userMessage: {
        container: 'flex items-start gap-3 max-w-3xl ml-auto justify-end',
        bubble: 'bg-claude-user-msg text-claude-text rounded-2xl px-4 py-3 max-w-[80%]',
        avatar: 'w-8 h-8 rounded-full bg-claude-primary flex items-center justify-center flex-shrink-0',
      },

      assistantMessage: {
        container: 'flex items-start gap-3 max-w-3xl',
        avatar: 'w-8 h-8 rounded-full bg-claude-accent flex items-center justify-center flex-shrink-0',
        bubble: 'bg-claude-surface rounded-2xl px-4 py-3 shadow-claude',
        button: 'text-claude-text-secondary hover:text-claude-text p-1.5 rounded hover:bg-gray-100',
        sourceCard: 'bg-claude-bg rounded-xl p-3 border border-claude-border hover:border-gray-300',
      },

      // Input
      input: {
        container: 'border-t border-claude-border bg-white',
        textarea: 'w-full resize-none rounded-xl border border-claude-border pl-4 pr-12 py-3 focus:outline-none focus:ring-2 focus:ring-claude-accent focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed text-claude-text placeholder-claude-text-secondary',
        button: 'absolute right-2 bottom-2 w-8 h-8 rounded-lg bg-claude-primary hover:bg-claude-primary-hover disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center',
      },

      // Chat Page
      chatPage: {
        container: 'flex flex-col h-[calc(100vh-64px)]',
        emptyAvatar: 'w-16 h-16 rounded-full bg-claude-accent flex items-center justify-center mb-4',
        emptyTitle: 'text-2xl font-semibold text-claude-text mb-2',
        emptySubtitle: 'text-claude-text-secondary mb-8',
        exampleButton: 'p-4 text-left border border-claude-border rounded-xl hover:bg-gray-50',
      },
    };
  }

  // Brutalist theme
  return {
    sidebar: {
      container: 'fixed lg:static inset-y-0 left-0 z-50 w-72 bg-neo-pink border-r-8 border-neo-black flex flex-col',
      header: 'p-4 border-b-4 border-neo-black bg-neo-yellow',
      title: 'text-2xl font-black text-neo-black uppercase tracking-tight mb-4',
      newButton: 'w-full flex items-center justify-center gap-2 px-4 py-3 bg-neo-cyan text-neo-black border-4 border-neo-black shadow-brutal hover:shadow-brutal-hover hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 font-black uppercase text-sm',
      conversationList: 'flex-1 overflow-y-auto p-3 space-y-4 bg-neo-pink',
      groupTitle: 'text-xs font-black text-neo-black uppercase tracking-wider px-2 mb-2 bg-neo-yellow border-l-4 border-neo-black py-1',
      conversation: (isActive: boolean) =>
        `group relative flex items-center gap-2 px-3 py-3 cursor-pointer border-4 border-neo-black ${
          isActive
            ? 'bg-neo-lime shadow-brutal-sm'
            : 'bg-white hover:shadow-brutal-sm hover:translate-x-1 hover:translate-y-1'
        }`,
      nav: 'border-t-4 border-neo-black p-3 space-y-2 bg-neo-pink',
      navLink: (isActive: boolean) =>
        `flex items-center gap-3 px-3 py-2.5 border-4 border-neo-black font-black uppercase text-sm ${
          isActive
            ? 'bg-neo-orange text-neo-black shadow-brutal-sm'
            : 'bg-white text-neo-black hover:shadow-brutal-sm hover:translate-x-1 hover:translate-y-1'
        }`,
      stats: 'border-t-4 border-neo-black p-4 bg-neo-cyan',
    },

    userMessage: {
      container: 'flex items-start gap-4 max-w-3xl ml-auto justify-end',
      bubble: 'bg-neo-blue text-neo-black border-4 border-neo-black shadow-brutal px-5 py-4 max-w-[80%] font-bold',
      avatar: 'w-12 h-12 bg-neo-yellow border-4 border-neo-black shadow-brutal-sm flex items-center justify-center flex-shrink-0',
    },

    assistantMessage: {
      container: 'flex items-start gap-4 max-w-3xl',
      avatar: 'w-12 h-12 bg-neo-pink border-4 border-neo-black shadow-brutal-sm flex items-center justify-center flex-shrink-0',
      bubble: 'bg-white border-4 border-neo-black shadow-brutal px-5 py-4',
      button: 'text-neo-black bg-neo-yellow hover:bg-neo-lime p-2 border-3 border-neo-black shadow-brutal-sm hover:shadow-brutal hover:translate-x-0.5 hover:translate-y-0.5 active:shadow-none active:translate-x-1 active:translate-y-1',
      sourceCard: 'bg-neo-lime border-4 border-neo-black shadow-brutal p-4',
    },

    input: {
      container: 'border-t-8 border-neo-black bg-neo-yellow',
      textarea: 'w-full resize-none border-4 border-neo-black pl-4 pr-16 py-4 shadow-brutal focus:outline-none focus:shadow-brutal-lg disabled:bg-gray-300 disabled:cursor-not-allowed text-neo-black placeholder-neo-black/50 font-bold text-base bg-white',
      button: 'absolute right-3 bottom-3 w-12 h-12 bg-neo-pink hover:bg-neo-orange disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center border-4 border-neo-black shadow-brutal hover:shadow-brutal-hover hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2',
    },

    chatPage: {
      container: 'flex flex-col h-[calc(100vh-80px)]',
      emptyAvatar: 'w-24 h-24 bg-neo-pink border-8 border-neo-black shadow-brutal-lg flex items-center justify-center mb-6',
      emptyTitle: 'text-4xl font-black text-neo-black mb-3 uppercase tracking-tight',
      emptySubtitle: 'text-xl font-bold text-neo-black mb-10 uppercase',
      exampleButton: 'p-5 text-left border-4 border-neo-black shadow-brutal hover:shadow-brutal-hover hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2',
    },
  };
};
