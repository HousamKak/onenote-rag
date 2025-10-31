import { useState } from 'react';
import { Plus, MessageSquare, Trash2, Settings, Database, X } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';
import { useStore } from '../store/useStore';
import { useTheme } from '../context/ThemeContext';
import ConfirmModal from './ConfirmModal';

interface SidebarProps {
  onNewChat: () => void;
}

const Sidebar = ({ onNewChat }: SidebarProps) => {
  const location = useLocation();
  const { theme } = useTheme();
  const {
    conversations,
    currentConversationId,
    setCurrentConversation,
    deleteConversation,
    indexStats,
    isSidebarOpen,
    setSidebarOpen,
  } = useStore();

  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [conversationToDelete, setConversationToDelete] = useState<string | null>(null);

  const isQueryPage = location.pathname === '/query' || location.pathname === '/';

  // Group conversations by time
  const groupedConversations = conversations.reduce((groups, conv) => {
    const date = new Date(conv.updatedAt);
    const now = new Date();
    const diffInDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    let groupKey = 'Older';
    if (diffInDays === 0) groupKey = 'Today';
    else if (diffInDays === 1) groupKey = 'Yesterday';
    else if (diffInDays <= 7) groupKey = 'Last 7 days';
    else if (diffInDays <= 30) groupKey = 'Last 30 days';

    if (!groups[groupKey]) groups[groupKey] = [];
    groups[groupKey].push(conv);
    return groups;
  }, {} as Record<string, typeof conversations>);

  const groupOrder = ['Today', 'Yesterday', 'Last 7 days', 'Last 30 days', 'Older'];

  if (!isSidebarOpen) {
    return null;
  }

  if (theme === 'claude') {
    return (
      <>
        {/* Mobile backdrop */}
        <div
          className="fixed inset-0 bg-black/50 lg:hidden z-40"
          onClick={() => setSidebarOpen(false)}
        />

        {/* Claude Sidebar */}
        <aside className="fixed lg:static inset-y-0 left-0 z-50 w-64 bg-claude-sidebar border-r border-claude-border flex flex-col">
          {/* Header */}
          <div className="p-4 border-b border-claude-border">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold text-claude-text">OneNote RAG</h2>
              <button
                onClick={() => setSidebarOpen(false)}
                className="lg:hidden text-claude-text-secondary hover:text-claude-text p-1 rounded-md hover:bg-gray-200"
              >
                <X size={20} />
              </button>
            </div>

            <button
              onClick={onNewChat}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-claude-primary hover:bg-claude-primary-hover text-white rounded-lg shadow-claude font-medium text-sm"
            >
              <Plus size={18} />
              New Chat
            </button>
          </div>

          {/* Conversations */}
          {isQueryPage && conversations.length > 0 && (
            <div className="flex-1 overflow-y-auto p-3 space-y-3">
              {groupOrder.map((groupKey) => {
                const group = groupedConversations[groupKey];
                if (!group || group.length === 0) return null;

                return (
                  <div key={groupKey}>
                    <h3 className="text-xs font-semibold text-claude-text-secondary uppercase tracking-wider px-2 mb-2">
                      {groupKey}
                    </h3>
                    <div className="space-y-1">
                      {group.map((conv) => (
                        <div
                          key={conv.id}
                          className={`group relative flex items-center gap-2 px-3 py-2.5 rounded-lg cursor-pointer ${
                            conv.id === currentConversationId
                              ? 'bg-claude-user-msg'
                              : 'hover:bg-gray-100'
                          }`}
                          onClick={() => setCurrentConversation(conv.id)}
                        >
                          <MessageSquare size={16} className="flex-shrink-0 text-claude-text-secondary" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm truncate text-claude-text font-medium">{conv.title}</p>
                            <p className="text-xs text-claude-text-secondary">
                              {conv.messages.length} {conv.messages.length === 1 ? 'message' : 'messages'}
                            </p>
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setConversationToDelete(conv.id);
                              setDeleteModalOpen(true);
                            }}
                            className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-100 rounded text-red-600"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Navigation */}
          <div className="border-t border-claude-border p-3 space-y-1">
            <Link
              to="/query"
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium ${
                isQueryPage
                  ? 'bg-claude-user-msg text-claude-text'
                  : 'text-claude-text-secondary hover:bg-gray-100 hover:text-claude-text'
              }`}
            >
              <MessageSquare size={18} />
              <span>Chat</span>
            </Link>
            <Link
              to="/config"
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium ${
                location.pathname === '/config'
                  ? 'bg-claude-user-msg text-claude-text'
                  : 'text-claude-text-secondary hover:bg-gray-100 hover:text-claude-text'
              }`}
            >
              <Settings size={18} />
              <span>Settings</span>
            </Link>
            <Link
              to="/index"
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium ${
                location.pathname === '/index'
                  ? 'bg-claude-user-msg text-claude-text'
                  : 'text-claude-text-secondary hover:bg-gray-100 hover:text-claude-text'
              }`}
            >
              <Database size={18} />
              <span>Data Sources</span>
            </Link>
          </div>

          {/* Stats */}
          {indexStats && (
            <div className="border-t border-claude-border p-4">
              <div className="flex items-center justify-between text-sm">
                <span className="text-claude-text-secondary">Indexed Documents</span>
                <span className="font-semibold text-claude-primary">{indexStats.total_documents}</span>
              </div>
            </div>
          )}
        </aside>

        {/* Delete Confirmation Modal */}
        <ConfirmModal
          isOpen={deleteModalOpen}
          onClose={() => {
            setDeleteModalOpen(false);
            setConversationToDelete(null);
          }}
          onConfirm={() => {
            if (conversationToDelete) {
              deleteConversation(conversationToDelete);
            }
          }}
          title="Delete Conversation"
          message="Are you sure you want to delete this conversation? This action cannot be undone and all messages will be permanently lost."
          confirmText="Delete"
          cancelText="Cancel"
          variant="danger"
        />
      </>
    );
  }

  // Brutalist theme
  return (
    <>
      {/* Mobile backdrop */}
      <div
        className="fixed inset-0 bg-black/50 lg:hidden z-40"
        onClick={() => setSidebarOpen(false)}
      />

      {/* Sidebar */}
      <aside className="fixed lg:static inset-y-0 left-0 z-50 w-72 bg-neo-pink border-r-8 border-neo-black flex flex-col">
        {/* Header */}
        <div className="p-4 border-b-4 border-neo-black bg-neo-yellow">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-black text-neo-black uppercase tracking-tight">RAG CHAT</h2>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-neo-black hover:bg-neo-black hover:text-neo-yellow p-2 border-4 border-neo-black"
            >
              <X size={24} strokeWidth={3} />
            </button>
          </div>

          <button
            onClick={onNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-neo-cyan text-neo-black border-4 border-neo-black shadow-brutal hover:shadow-brutal-hover hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 font-black uppercase text-sm"
          >
            <Plus size={20} strokeWidth={3} />
            NEW CHAT
          </button>
        </div>

        {/* Conversations */}
        {isQueryPage && conversations.length > 0 && (
          <div className="flex-1 overflow-y-auto p-3 space-y-4 bg-neo-pink">
            {groupOrder.map((groupKey) => {
              const group = groupedConversations[groupKey];
              if (!group || group.length === 0) return null;

              return (
                <div key={groupKey}>
                  <h3 className="text-xs font-black text-neo-black uppercase tracking-wider px-2 mb-2 bg-neo-yellow border-l-4 border-neo-black py-1">
                    {groupKey}
                  </h3>
                  <div className="space-y-2">
                    {group.map((conv) => (
                      <div
                        key={conv.id}
                        className={`group relative flex items-center gap-2 px-3 py-3 cursor-pointer border-4 border-neo-black ${
                          conv.id === currentConversationId
                            ? 'bg-neo-lime shadow-brutal-sm'
                            : 'bg-white hover:shadow-brutal-sm hover:translate-x-1 hover:translate-y-1'
                        }`}
                        onClick={() => setCurrentConversation(conv.id)}
                      >
                        <MessageSquare size={18} className="flex-shrink-0 text-neo-black" strokeWidth={2.5} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-bold truncate text-neo-black">{conv.title}</p>
                          <p className="text-xs font-semibold text-neo-black/70">
                            {conv.messages.length} MSG{conv.messages.length !== 1 ? 'S' : ''}
                          </p>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setConversationToDelete(conv.id);
                            setDeleteModalOpen(true);
                          }}
                          className="opacity-0 group-hover:opacity-100 p-1.5 bg-neo-orange border-2 border-neo-black hover:bg-red-500"
                        >
                          <Trash2 size={14} strokeWidth={3} />
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Navigation */}
        <div className="border-t-4 border-neo-black p-3 space-y-2 bg-neo-pink">
          <Link
            to="/query"
            className={`flex items-center gap-3 px-3 py-2.5 border-4 border-neo-black font-black uppercase text-sm ${
              isQueryPage
                ? 'bg-neo-orange text-neo-black shadow-brutal-sm'
                : 'bg-white text-neo-black hover:shadow-brutal-sm hover:translate-x-1 hover:translate-y-1'
            }`}
          >
            <MessageSquare size={18} strokeWidth={3} />
            <span>CHAT</span>
          </Link>
          <Link
            to="/config"
            className={`flex items-center gap-3 px-3 py-2.5 border-4 border-neo-black font-black uppercase text-sm ${
              location.pathname === '/config'
                ? 'bg-neo-orange text-neo-black shadow-brutal-sm'
                : 'bg-white text-neo-black hover:shadow-brutal-sm hover:translate-x-1 hover:translate-y-1'
            }`}
          >
            <Settings size={18} strokeWidth={3} />
            <span>SETTINGS</span>
          </Link>
          <Link
            to="/index"
            className={`flex items-center gap-3 px-3 py-2.5 border-4 border-neo-black font-black uppercase text-sm ${
              location.pathname === '/index'
                ? 'bg-neo-orange text-neo-black shadow-brutal-sm'
                : 'bg-white text-neo-black hover:shadow-brutal-sm hover:translate-x-1 hover:translate-y-1'
            }`}
          >
            <Database size={18} strokeWidth={3} />
            <span>DATA</span>
          </Link>
        </div>

        {/* Stats */}
        {indexStats && (
          <div className="border-t-4 border-neo-black p-4 bg-neo-cyan">
            <div className="flex items-center justify-between">
              <span className="text-xs font-black text-neo-black uppercase">DOCS</span>
              <span className="text-2xl font-black text-neo-black">{indexStats.total_documents}</span>
            </div>
          </div>
        )}
      </aside>

      {/* Delete Confirmation Modal */}
      <ConfirmModal
        isOpen={deleteModalOpen}
        onClose={() => {
          setDeleteModalOpen(false);
          setConversationToDelete(null);
        }}
        onConfirm={() => {
          if (conversationToDelete) {
            deleteConversation(conversationToDelete);
          }
        }}
        title="Delete Conversation"
        message="Are you sure you want to delete this conversation? This action cannot be undone and all messages will be permanently lost."
        confirmText="Delete"
        cancelText="Cancel"
        variant="danger"
      />
    </>
  );
};

export default Sidebar;
