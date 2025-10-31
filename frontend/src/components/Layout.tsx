import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { Menu, Plus } from 'lucide-react';
import { useStore } from '../store/useStore';
import { useTheme } from '../context/ThemeContext';
import Sidebar from './Sidebar';
import ThemeSwitcher from './ThemeSwitcher';

const Layout = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme } = useTheme();
  const { setSidebarOpen, createConversation, setCurrentConversation, conversations, currentConversationId } = useStore();

  const isQueryPage = location.pathname === '/query' || location.pathname === '/';

  const handleNewChat = () => {
    // Check if current conversation is empty
    const currentConversation = conversations.find((c) => c.id === currentConversationId);
    const isCurrentEmpty = !currentConversation || currentConversation.messages.length === 0;

    // Only create new conversation if current one has messages
    if (!isCurrentEmpty) {
      const id = createConversation();
      setCurrentConversation(id);
    } else if (currentConversationId) {
      // If current conversation is empty, just navigate to it
      setCurrentConversation(currentConversationId);
    } else {
      // If no conversation exists, create one
      const id = createConversation();
      setCurrentConversation(id);
    }

    if (!isQueryPage) {
      navigate('/query');
    }
  };

  if (theme === 'claude') {
    return (
      <div className="flex h-screen bg-claude-bg">
        {/* Sidebar */}
        <Sidebar onNewChat={handleNewChat} />

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Claude Header */}
          <header className="bg-white border-b border-claude-border h-16 flex items-center px-6 flex-shrink-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 text-claude-text hover:bg-gray-100 rounded-md mr-3"
            >
              <Menu size={20} />
            </button>

            <div className="flex-1">
              <h1 className="text-lg font-semibold text-claude-text">
                {isQueryPage ? 'Chat' : location.pathname.slice(1).charAt(0).toUpperCase() + location.pathname.slice(2)}
              </h1>
            </div>

            <div className="flex items-center gap-3">
              <ThemeSwitcher />
              {isQueryPage && (
                <button
                  onClick={handleNewChat}
                  className="hidden lg:flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-claude-primary hover:bg-claude-primary-hover rounded-lg shadow-claude"
                >
                  <Plus size={18} />
                  New Chat
                </button>
              )}
            </div>
          </header>

          {/* Page Content */}
          <main className="flex-1 overflow-hidden bg-claude-bg">
            <Outlet />
          </main>
        </div>
      </div>
    );
  }

  // Brutalist theme
  return (
    <div className="flex h-screen bg-[#FFFBF0]">
      {/* Sidebar */}
      <Sidebar onNewChat={handleNewChat} />

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Neo-Brutalism Header */}
        <header className="bg-neo-cyan border-b-8 border-neo-black h-20 flex items-center px-6 flex-shrink-0">
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-3 text-neo-black bg-neo-yellow border-4 border-neo-black shadow-brutal-sm hover:shadow-brutal hover:translate-x-0.5 hover:translate-y-0.5 mr-4"
          >
            <Menu size={24} strokeWidth={3} />
          </button>

          <div className="flex-1">
            <h1 className="text-2xl font-black text-neo-black uppercase tracking-tight">
              {isQueryPage ? '💬 CHAT' : '⚙️ ' + location.pathname.slice(1).toUpperCase()}
            </h1>
          </div>

          <div className="flex items-center gap-3">
            <ThemeSwitcher />
            {isQueryPage && (
              <button
                onClick={handleNewChat}
                className="hidden lg:flex items-center gap-2 px-5 py-3 font-black text-neo-black bg-neo-lime border-4 border-neo-black shadow-brutal hover:shadow-brutal-hover hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 uppercase text-sm"
              >
                <Plus size={20} strokeWidth={3} />
                NEW CHAT
              </button>
            )}
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-hidden bg-[#FFFBF0]">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export default Layout;
