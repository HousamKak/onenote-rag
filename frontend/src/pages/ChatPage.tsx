import { useState, useEffect, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { queryApi } from '../api/client';
import { useStore } from '../store/useStore';
import { useTheme } from '../context/ThemeContext';
import UserMessage from '../components/UserMessage';
import AssistantMessage from '../components/AssistantMessage';
import TypingIndicator from '../components/TypingIndicator';
import ChatInput from '../components/ChatInput';
import ChatSidebar from '../components/ChatSidebar';

const ChatPage = () => {
  const { theme } = useTheme();
  const [input, setInput] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    conversations,
    currentConversationId,
    createConversation,
    addMessage,
    currentConfig,
  } = useStore();

  const currentConversation = conversations.find((c) => c.id === currentConversationId);

  // Create initial conversation if none exists
  useEffect(() => {
    if (!currentConversationId && conversations.length === 0) {
      createConversation();
    }
  }, [currentConversationId, conversations.length, createConversation]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [currentConversation?.messages]);

  const queryMutation = useMutation({
    mutationFn: (question: string) =>
      queryApi.query({ question, config: currentConfig || undefined }),
    onSuccess: (response) => {
      // Add assistant message
      const conversationId = currentConversationId || createConversation();
      addMessage(conversationId, {
        role: 'assistant',
        content: response.data.answer,
        metadata: response.data.metadata,
        sources: response.data.sources,
      });
    },
    onError: (error) => {
      // Add error message
      const conversationId = currentConversationId || createConversation();
      addMessage(conversationId, {
        role: 'assistant',
        content: `Error: ${error.message || 'An error occurred while processing your query'}`,
      });
    },
  });

  const handleSubmit = () => {
    if (!input.trim() || queryMutation.isPending) return;

    const question = input.trim();
    const conversationId = currentConversationId || createConversation();

    // Add user message
    addMessage(conversationId, {
      role: 'user',
      content: question,
    });

    // Clear input
    setInput('');

    // Send query
    queryMutation.mutate(question);
  };

  const isEmpty = !currentConversation || currentConversation.messages.length === 0;

  const containerHeight = theme === 'claude' ? 'h-[calc(100vh-64px)]' : 'h-[calc(100vh-80px)]';

  return (
    <div className={`flex flex-col ${containerHeight} relative`}>
      {/* Chat Sidebar */}
      <ChatSidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      {/* Messages Container */}
      <div className={`flex-1 overflow-y-auto transition-all duration-300 ${sidebarOpen ? 'pr-80' : 'pr-0'}`}>
        <div className="mx-auto px-4 py-8 max-w-3xl">
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              {theme === 'claude' ? (
                <>
                  <div className="w-16 h-16 rounded-full bg-claude-accent flex items-center justify-center mb-4 animate-scaleIn">
                    <span className="text-white text-2xl font-semibold">AI</span>
                  </div>
                  <h2 className="text-2xl font-semibold text-claude-text mb-2 animate-fadeInUp">
                    What can I help with?
                  </h2>
                  <p className="text-claude-text-secondary mb-8 animate-fadeIn">
                    Ask about your OneNote documents
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
                    <button
                      onClick={() => setInput('Summarize the key points from my recent notes')}
                      className="p-4 text-left border border-claude-border rounded-xl hover:bg-gray-50 transition-all animate-fadeIn hover:-translate-y-1 hover:shadow-lg"
                    >
                      <p className="text-sm font-medium text-claude-text mb-1">Summarize notes</p>
                      <p className="text-xs text-claude-text-secondary">
                        Extract key points from your documents
                      </p>
                    </button>
                    <button
                      onClick={() => setInput('Find information about project deadlines')}
                      className="p-4 text-left border border-claude-border rounded-xl hover:bg-gray-50 transition-all animate-fadeIn hover:-translate-y-1 hover:shadow-lg"
                    >
                      <p className="text-sm font-medium text-claude-text mb-1">Find deadlines</p>
                      <p className="text-xs text-claude-text-secondary">
                        Search for project timeline information
                      </p>
                    </button>
                    <button
                      onClick={() => setInput('What are the main topics in my study notes?')}
                      className="p-4 text-left border border-claude-border rounded-xl hover:bg-gray-50 transition-all animate-fadeIn hover:-translate-y-1 hover:shadow-lg"
                    >
                      <p className="text-sm font-medium text-claude-text mb-1">Analyze topics</p>
                      <p className="text-xs text-claude-text-secondary">
                        Discover patterns in your notes
                      </p>
                    </button>
                    <button
                      onClick={() => setInput('Compare different approaches mentioned in my notes')}
                      className="p-4 text-left border border-claude-border rounded-xl hover:bg-gray-50 transition-all animate-fadeIn hover:-translate-y-1 hover:shadow-lg"
                    >
                      <p className="text-sm font-medium text-claude-text mb-1">Compare approaches</p>
                      <p className="text-xs text-claude-text-secondary">
                        Find similarities and differences
                      </p>
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <div className="w-24 h-24 bg-neo-pink border-8 border-neo-black shadow-brutal-lg flex items-center justify-center mb-6 animate-pulse">
                    <span className="text-neo-black text-4xl font-black">AI</span>
                  </div>
                  <h2 className="text-4xl font-black text-neo-black mb-3 uppercase tracking-tight animate-fadeInUp">
                    WHAT CAN I HELP WITH?
                  </h2>
                  <p className="text-xl font-bold text-neo-black mb-10 uppercase animate-fadeIn">
                    ASK ABOUT YOUR ONENOTE DOCS
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl">
                    <button
                      onClick={() => setInput('Summarize the key points from my recent notes')}
                      className="p-5 text-left border-4 border-neo-black bg-neo-yellow hover:bg-neo-lime shadow-brutal hover:shadow-brutal-hover transition-all hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 animate-fadeIn"
                    >
                      <p className="text-base font-black text-neo-black uppercase mb-1">📝 SUMMARIZE</p>
                      <p className="text-sm font-bold text-neo-black">
                        Key points from docs
                      </p>
                    </button>
                    <button
                      onClick={() => setInput('Find information about project deadlines')}
                      className="p-5 text-left border-4 border-neo-black bg-neo-cyan hover:bg-neo-lime shadow-brutal hover:shadow-brutal-hover transition-all hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 animate-fadeIn"
                    >
                      <p className="text-base font-black text-neo-black uppercase mb-1">⏰ DEADLINES</p>
                      <p className="text-sm font-bold text-neo-black">
                        Project timeline info
                      </p>
                    </button>
                    <button
                      onClick={() => setInput('What are the main topics in my study notes?')}
                      className="p-5 text-left border-4 border-neo-black bg-neo-orange hover:bg-neo-pink shadow-brutal hover:shadow-brutal-hover transition-all hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 animate-fadeIn"
                    >
                      <p className="text-base font-black text-neo-black uppercase mb-1">🔍 ANALYZE</p>
                      <p className="text-sm font-bold text-neo-black">
                        Discover patterns
                      </p>
                    </button>
                    <button
                      onClick={() => setInput('Compare different approaches mentioned in my notes')}
                      className="p-5 text-left border-4 border-neo-black bg-neo-lime hover:bg-neo-yellow shadow-brutal hover:shadow-brutal-hover transition-all hover:translate-x-1 hover:translate-y-1 active:shadow-none active:translate-x-2 active:translate-y-2 animate-fadeIn"
                    >
                      <p className="text-base font-black text-neo-black uppercase mb-1">⚖️ COMPARE</p>
                      <p className="text-sm font-bold text-neo-black">
                        Find similarities
                      </p>
                    </button>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="space-y-6">
              {currentConversation.messages.map((message) =>
                message.role === 'user' ? (
                  <UserMessage key={message.id} message={message} />
                ) : (
                  <AssistantMessage key={message.id} message={message} />
                )
              )}

              {queryMutation.isPending && <TypingIndicator />}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <ChatInput
        value={input}
        onChange={setInput}
        onSubmit={handleSubmit}
        disabled={queryMutation.isPending}
        showConfigBadge={!!currentConfig}
      />
    </div>
  );
};

export default ChatPage;
