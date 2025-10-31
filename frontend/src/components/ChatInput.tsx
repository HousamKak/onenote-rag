import { useRef, useEffect, type KeyboardEvent } from 'react';
import { ArrowUp, Zap } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
  showConfigBadge?: boolean;
}

const ChatInput = ({
  value,
  onChange,
  onSubmit,
  disabled = false,
  placeholder = 'Ask about your OneNote documents...',
  showConfigBadge = false,
}: ChatInputProps) => {
  const { theme } = useTheme();
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
    }
  }, [value]);

  // Focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSubmit();
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim() && !disabled) {
      onSubmit();
    }
  };

  if (theme === 'claude') {
    return (
      <div className="bg-white border-t border-claude-border">
        <div className="max-w-3xl mx-auto px-4 py-4">
          {showConfigBadge && (
            <div className="mb-3 flex items-center gap-2 px-3 py-1.5 bg-claude-user-msg text-claude-text rounded-lg w-fit">
              <Zap size={14} />
              <span className="text-xs font-medium">Custom config</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="relative">
            <div className="relative flex items-end gap-2 p-2 bg-claude-bg rounded-[24px] border border-claude-border shadow-sm">
              <textarea
                ref={textareaRef}
                value={value}
                onChange={(e) => onChange(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={placeholder}
                disabled={disabled}
                rows={1}
                className="flex-1 resize-none bg-transparent px-3 py-2.5 text-base
                         focus:outline-none
                         disabled:cursor-not-allowed
                         text-claude-text placeholder-claude-text-secondary"
                style={{ maxHeight: '200px', minHeight: '44px' }}
              />

              <button
                type="submit"
                disabled={!value.trim() || disabled}
                className="flex-shrink-0 w-9 h-9 rounded-full bg-claude-primary hover:bg-claude-primary-hover
                         disabled:bg-gray-300 disabled:cursor-not-allowed
                         flex items-center justify-center transition-colors"
              >
                <ArrowUp size={18} className="text-white" />
              </button>
            </div>
          </form>

          <p className="mt-2 text-xs text-claude-text-secondary text-center">
            Enter to send • Shift+Enter for new line
          </p>
        </div>
      </div>
    );
  }

  // Brutalist theme
  return (
    <div className="border-t-8 border-neo-black bg-neo-yellow">
      <div className="max-w-3xl mx-auto p-6">
        {showConfigBadge && (
          <div className="mb-3 flex items-center gap-2 px-3 py-2 bg-neo-cyan border-3 border-neo-black shadow-brutal-sm w-fit">
            <Zap size={18} className="text-neo-black" strokeWidth={3} />
            <span className="text-sm font-black text-neo-black uppercase">CUSTOM CONFIG</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="relative">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            rows={1}
            className="w-full resize-none border-4 border-neo-black pl-4 pr-16 py-4 shadow-brutal
                     focus:outline-none focus:shadow-brutal-lg
                     disabled:bg-gray-300 disabled:cursor-not-allowed
                     text-neo-black placeholder-neo-black/50 font-bold text-base bg-white"
            style={{ maxHeight: '200px' }}
          />

          <button
            type="submit"
            disabled={!value.trim() || disabled}
            className="absolute right-3 bottom-3 w-12 h-12 bg-neo-pink hover:bg-neo-orange
                     disabled:bg-gray-400 disabled:cursor-not-allowed
                     flex items-center justify-center border-4 border-neo-black shadow-brutal
                     hover:shadow-brutal-hover hover:translate-x-1 hover:translate-y-1
                     active:shadow-none active:translate-x-2 active:translate-y-2"
          >
            <ArrowUp size={24} className="text-neo-black" strokeWidth={3} />
          </button>
        </form>

        <p className="mt-3 text-xs font-bold text-neo-black text-center uppercase tracking-wide">
          ENTER = SEND • SHIFT+ENTER = NEW LINE
        </p>
      </div>
    </div>
  );
};

export default ChatInput;
