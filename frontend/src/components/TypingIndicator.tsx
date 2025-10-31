import { useTheme } from '../context/ThemeContext';

const TypingIndicator = () => {
  const { theme } = useTheme();

  if (theme === 'claude') {
    return (
      <div className="flex items-start max-w-3xl">
        <div className="bg-claude-surface rounded-2xl px-4 py-3 shadow-claude">
          <div className="flex gap-1">
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-4 max-w-3xl">
      <div className="w-12 h-12 bg-neo-pink border-4 border-neo-black shadow-brutal-sm flex items-center justify-center flex-shrink-0">
        <span className="text-neo-black text-lg font-black">AI</span>
      </div>
      <div className="bg-white border-4 border-neo-black shadow-brutal px-5 py-4">
        <div className="flex gap-2">
          <div className="w-3 h-3 bg-neo-black animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-3 h-3 bg-neo-black animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-3 h-3 bg-neo-black animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;
